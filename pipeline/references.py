"""Find the replicated original in the replication's own reference list.

Most of our unlinked finds describe what was replicated but never name who wrote it — the authors' own words are
"a replication of a previous study", so there is no author for the triage step to report. Searching OpenAlex for
the description alone finds the right paper 17% of the time; there are thousands of papers about any given effect.

But a replication cites the study it replicates. On links verified by hand, the original is in the paper's
reference list 84% of the time, and scoring those 35-odd references against the description picks it out at the
top 78% of the time. That is a haystack of 35, not of 250 million.

    python -m pipeline references [--max-usd 1.20]

Measured on 61 finds whose link was independently verified, with the 16% where the reference list does not
contain the original included in the denominator:

    score >= 0.50 and margin >= 0.15   89% correct   -> high
    score >= 0.30 and margin >= 0.05   74% correct   -> medium
    anything proposed at all           66% correct   -> low

Reference lists come from the cached discovery responses rather than being re-fetched; only the titles of the
referenced works cost anything, at 50 per call.
"""
from __future__ import annotations

import glob
import hashlib
import json
import re
from collections import Counter

from .discover import _get, _spent
from .ids import norm_doi
from .link import text_sim
from .load import CACHE, DISCOVERY

# A replication's own title usually mirrors the original's: "Replication of <original title>", or
# "<original title>: a conceptual replication of ...". Stripping the replication clause leaves a usable query for
# the 693 finds OpenAlex holds as a bare title with no abstract, where the triage step had nothing to describe.
# It ranks the original top 55% of the time against 78% for a description, so a title-derived link is capped one
# band lower than the same score from a description.
_LEAD = re.compile(r"^.{0,60}?\b(?:replicat\w*|reproduc\w*)\s+(?:and\s+extension\s+)?(?:of|study\s+of)\s+", re.I)
_TAIL = re.compile(r"[:;,.\-\u2013\u2014]\s*(?:a|an|the)?\s*[\w\s\-]{0,40}?\b(?:replicat\w*|reproduc\w*)\b.*$", re.I)
_NOISE = re.compile(r"\((?:19|20)\d{2}[a-z]?\)|\bet\s+al\.?|\bstudy\s+\d+\b"
                    r"|\bat\s+[A-Z][\w'\u2019\- ]+(?:University|College|Universit\w+)\b", re.I)


def stem_title(title: str | None) -> str | None:
    """The replication's title with its own replication clause removed, or None if nothing usable is left."""
    s = title or ""
    m = _LEAD.search(s)
    s = s[m.end():] if m else _TAIL.sub("", s)
    s = _NOISE.sub(" ", s).strip(" :,-\u2013\u2014\u2019'\"\u201c\u201d\u00ab\u00bb")
    return s if len(s.split()) >= 3 else None


HIGH = (0.50, 0.15)
MEDIUM = (0.30, 0.05)
FLOOR = 0.15          # below this the top reference is not about the described finding at all


def reference_lists(wanted: set[str]) -> dict[str, list[str]]:
    """cid -> OpenAlex ids it cites, read out of the cached search responses (no new calls)."""
    out: dict[str, list[str]] = {}
    for f in glob.glob(str(CACHE / "openalex" / "kw-*.json")) + glob.glob(str(CACHE / "openalex" / "cites-*.json")):
        try:
            d = json.loads(open(f, encoding="utf-8").read())
        except Exception:  # noqa: BLE001 - a truncated cache entry is not worth failing the run for
            continue
        for w in d.get("results", []):
            wid = w["id"].rsplit("/", 1)[-1]
            doi = norm_doi(w.get("doi"))
            cid = doi if doi in wanted else (wid if wid in wanted else None)
            if cid and cid not in out and w.get("referenced_works"):
                out[cid] = [x.rsplit("/", 1)[-1] for x in w["referenced_works"]]
    return out


def resolve_titles(ids: list[str], max_usd: float) -> dict[str, dict]:
    """OpenAlex id -> {doi, title, year}, 50 per call, keyed on the ids asked for."""
    known = json.loads((DISCOVERY / "reference_titles.json").read_text(encoding="utf-8")) \
        if (DISCOVERY / "reference_titles.json").exists() else {}
    todo = sorted(set(ids) - set(known))
    print(f"  {len(ids):,} referenced works, {len(todo):,} still to resolve")
    for i in range(0, len(todo), 50):
        if _spent["usd"] >= max_usd:
            print(f"  stopping at the ${max_usd:.2f} cap with {len(todo) - i:,} unresolved")
            break
        chunk = todo[i:i + 50]
        key = "ref-" + hashlib.sha256("|".join(chunk).encode()).hexdigest()[:16]
        d = _get({"filter": "openalex_id:" + "|".join(chunk), "select": "id,doi,title,publication_year",
                  "per_page": 50}, key)
        for w in d.get("results", []):
            known[w["id"].rsplit("/", 1)[-1]] = {"doi": norm_doi(w.get("doi")), "title": w.get("title"),
                                                 "year": w.get("publication_year")}
        if (i // 50) % 50 == 0:
            print(f"    {i:,}/{len(todo):,} · ${_spent['usd']:.3f}", flush=True)
    DISCOVERY.mkdir(parents=True, exist_ok=True)
    (DISCOVERY / "reference_titles.json").write_text(json.dumps(known, ensure_ascii=False), encoding="utf-8")
    return known


def resolve_authors(ids: list[str], max_usd: float) -> dict[str, list[str]]:
    """OpenAlex id -> the surnames on that referenced work, 50 per call.

    Kept apart from resolve_titles because the titles were already fetched without authorships, and refetching
    63,000 works to add one field would cost more than asking only for the ones a named author could match.
    """
    f = DISCOVERY / "reference_authors.json"
    known = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    todo = sorted(set(ids) - set(known))
    print(f"  {len(todo):,} referenced works still need their author list")
    for i in range(0, len(todo), 50):
        if _spent["usd"] >= max_usd:
            print(f"  stopping at the ${max_usd:.2f} cap with {len(todo) - i:,} unresolved")
            break
        chunk = todo[i:i + 50]
        key = "refau-" + hashlib.sha256("|".join(chunk).encode()).hexdigest()[:16]
        d = _get({"filter": "openalex_id:" + "|".join(chunk), "select": "id,authorships", "per_page": 50}, key)
        for w in d.get("results", []):
            known[w["id"].rsplit("/", 1)[-1]] = [
                n.split()[-1].lower() for a in (w.get("authorships") or [])
                if (n := ((a.get("author") or {}).get("display_name") or "").strip())]
        if (i // 50) % 50 == 0:
            print(f"    {i:,}/{len(todo):,} · ${_spent['usd']:.3f}", flush=True)
    DISCOVERY.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(known, ensure_ascii=False), encoding="utf-8")
    return known


_SURNAME = re.compile(r"[A-Z][a-zA-Z'\u2019-]{2,}")


def named_surnames(named: str | None) -> list[str]:
    """The surnames a replication's abstract gives for the study it replicated: "Thomson, Besner and Smilek"."""
    if not named:
        return []
    drop = {"And", "Et", "Al", "The", "Study", "Experiment", "Colleagues"}
    return [w.lower() for w in _SURNAME.findall(named) if w not in drop]


def pick_by_author(named: str | None, year: int | None, refs: list[str], titles: dict, authors: dict,
                   description: str | None) -> dict | None:
    """The referenced work written by the named author around the named year.

    This is the piece that was missing. The reference scan matched the DESCRIPTION against reference TITLES,
    which fails whenever the two use different words: a replication described as "online semantic vigilance task
    results replicated in laboratory setting" never matches "A critical examination of the evidence for
    sensitivity loss in modern vigilance tasks" — and that is the paper, sitting in its own reference list all
    along. An author and a year find it immediately.

    The year is deliberately loose. A paper the citing author calls 2016 is frequently 2015 in OpenAlex, because
    one is the print year and the other is when it appeared online.
    """
    want = named_surnames(named)
    if not want or not refs:
        return None
    hits = []
    for r in refs:
        t, au = titles.get(r), authors.get(r)
        if not t or not t.get("doi") or not au:
            continue
        if year and t.get("year") and abs(int(t["year"]) - int(year)) > 2:
            continue
        shared = [w for w in want if w in au]
        if not shared:
            continue
        # first-author match is much stronger than being somewhere in the list
        hits.append((len(shared) + (1.0 if au and au[0] in want else 0.0),
                     text_sim(description or "", t["title"]) or 0.0, t))
    if not hits:
        return None
    hits.sort(key=lambda x: (-x[0], -x[1]))
    top = hits[0]
    band = "high" if len(hits) == 1 or hits[0][0] > hits[1][0] else ("medium" if len(hits) <= 3 else "low")
    return {"doi_o": top[2]["doi"], "title_o": top[2]["title"], "year_o": top[2].get("year"),
            "method": "reference_author", "confidence": band, "score": round(top[0], 2),
            "text_sim": round(top[1], 3), "n_references": len(refs), "n_candidates": len(hits),
            "matched_on": "author+year in the reference list",
            "runner_up": {"doi_o": hits[1][2]["doi"], "title_o": hits[1][2]["title"]} if len(hits) > 1 else None}


def pick(description: str | None, refs: list[str], titles: dict[str, dict], title_r: str | None = None) -> dict | None:
    """The referenced work whose title best matches the described finding, with its margin over the runner-up."""
    query, basis = (description, "description") if description else (stem_title(title_r), "title")
    if not query:
        return None
    scored = sorted(((text_sim(query, t["title"]) or 0.0, t)
                     for r in refs if (t := titles.get(r)) and t.get("title") and t.get("doi")),
                    key=lambda x: -x[0])
    if not scored or scored[0][0] < FLOOR:
        return None
    top, runner = scored[0], (scored[1] if len(scored) > 1 else (0.0, None))
    margin = round(top[0] - runner[0], 3)
    band = ("high" if top[0] >= HIGH[0] and margin >= HIGH[1]
            else "medium" if top[0] >= MEDIUM[0] and margin >= MEDIUM[1] else "low")
    if basis == "title":
        band = {"high": "medium", "medium": "low", "low": "low"}[band]
    return {"doi_o": top[1]["doi"], "title_o": top[1]["title"], "year_o": top[1].get("year"),
            "method": "reference_scan", "confidence": band, "score": round(top[0], 3), "text_sim": round(top[0], 3),
            "margin": margin, "n_references": len(scored), "matched_on": basis,
            "runner_up": {"doi_o": runner[1]["doi"], "title_o": runner[1]["title"],
                          "score": round(runner[0], 3)} if runner[1] else None}


def run_author(max_usd: float = 0.50) -> int:
    """Match the author and year a replication names against its own reference list.

    Runs over every psychology find whose abstract names an author, whatever link it already has: the weak bands
    it would be replacing are right 12-35% of the time, so there is little to protect.
    """
    from . import load
    from .queue import TRUSTED_LINKS
    triaged, links = load.load_triaged(), load.merged_links()
    todo = {}
    for r in triaged:
        t = r["triage"]
        if t.get("kind") not in ("replication", "reproduction") or t.get("field") != "psychology":
            continue
        o = t.get("original") or {}
        if not o.get("authors"):
            continue
        cur = links.get(r["cid"]) or {}
        if cur and (cur.get("method"), cur.get("confidence")) in TRUSTED_LINKS:
            continue                                   # already matched by a method measured at 90%+
        todo[r["cid"]] = (o.get("authors"), o.get("year"), o.get("description"))
    print(f"  {len(todo):,} psychology finds name an author and have no strong link")
    refs = reference_lists(set(todo))
    print(f"  {len(refs):,} of them cite a reference list we already hold")
    wanted = sorted({w for c in refs for w in refs[c]})
    titles = resolve_titles(wanted, max_usd)
    authors = resolve_authors(wanted, max_usd)
    out, band = {}, Counter()
    for cid, (named, year, desc) in todo.items():
        hit = pick_by_author(named, year, refs.get(cid, []), titles, authors, desc)
        if hit:
            out[cid] = {**hit, "named": {"authors": named, "year": year, "description": desc}}
            band[hit["confidence"]] += 1
    (DISCOVERY / "reference_author_links.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"  matched {len(out):,} of the {len(refs):,} with references · by confidence: {dict(band)} "
          f"· {_spent['calls']} calls · ${_spent['usd']:.3f}")
    return 0


def run(max_usd: float = 1.20, relink: bool = False) -> int:
    from . import load
    triaged = load.load_triaged()
    links = load.load_links()
    todo = {}
    for r in triaged:
        t = r["triage"]
        o = t.get("original") or {}
        if t.get("kind") not in ("replication", "reproduction") or t.get("field") != "psychology":
            continue
        if t.get("original_doi"):
            continue
        # Normally this pass only looks at finds with no original at all. But a find whose author-and-year match
        # landed in the "low" band has an original that is right about a quarter of the time, and this method is
        # right 78-89% — and it was skipping them precisely because they already had an answer. A worse method
        # running first should not block a better one.
        existing = links.get(r["cid"])
        if existing and not (relink and existing.get("confidence") == "low"):
            continue
        todo[r["cid"]] = (o.get("description"), r.get("title_r"))
    described = sum(1 for d, _ in todo.values() if d)
    print(f"  {len(todo):,} psychology replications still have no original "
          f"({described:,} describe one, {len(todo) - described:,} are a bare title)")
    refs = reference_lists(set(todo))
    print(f"  {len(refs):,} of them cite a reference list we already hold")
    titles = resolve_titles(sorted({w for v in refs.values() for w in v}), max_usd)
    out = {}
    for cid, (desc, title_r) in todo.items():
        hit = pick(desc, refs.get(cid, []), titles, title_r)
        if hit:
            out[cid] = {**hit, "named": {"description": desc}}
    if relink:                                    # keep what the earlier pass found; add, never replace
        prior = load.load_reference_links()
        out = {**prior, **out}
    (DISCOVERY / "reference_links.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    from collections import Counter
    print(f"  proposed an original for {len(out):,} of the {len(refs):,} with references "
          f"· {_spent['calls']} calls · ${_spent['usd']:.3f}")
    print("  by confidence:", dict(Counter(v["confidence"] for v in out.values())))
    print("  matched on:", dict(Counter(v["matched_on"] for v in out.values())))
    return 0
