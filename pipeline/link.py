"""Resolve the original study for discovered replications that name it but give no DOI.

The triage step asks DeepSeek which study a replication tested. For most psychology replications it answers with
an author surname, a year and a one-line description rather than a DOI. This module turns that into a DOI:

  1. the library first, and free: every original already in the wiki is indexed by (author surname, year);
  2. OpenAlex second, one cached call per unresolved candidate: works by that surname in that year, ranked here.

Nothing is guessed silently. Every link records its method, what it matched on, the runner-up, and a confidence
band, so a reviewer can see why a pair was proposed. Candidates whose best match is weak stay unresolved.

    python -m pipeline link                     # library pass only (free)
    python -m pipeline link --openalex --max-usd 1.0
    python -m pipeline link --check             # accuracy against the citation-resolved originals
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict

from .discover import _get, _spent
from .load import DISCOVERY

# a proposed link below this score is not worth a reviewer's time
FLOOR = 0.42
# the OpenAlex pass must see the described finding in the title; the library pass is already a curated pool
MIN_SIM_OPENALEX = 0.15
STOP = {"the", "a", "an", "of", "on", "in", "and", "or", "to", "for", "with", "that", "is", "are", "was", "were",
        "effect", "effects", "study", "studies", "task", "people", "more", "than", "from", "by", "their", "its"}


def fold(s) -> str:
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()


def surnames(raw) -> list[str]:
    """['smith'] / ['smith', 'jones'] from 'Smith', 'Smith & Jones', 'Smith et al.', 'Nisbett and Wilson'."""
    t = re.sub(r"\bet al\.?", " ", fold(raw))
    out = []
    for part in re.split(r"\s*(?:&|,|\band\b)\s*", t):
        p = re.sub(r"\s+", " ", re.sub(r"[^a-z' -]", " ", part)).strip()
        if len(p) >= 2:
            out.append(p)
    return out


def words(s) -> set[str]:
    return {w for w in re.findall(r"[a-z]{3,}", fold(s)) if w not in STOP}


def text_sim(desc: str | None, title: str | None) -> float | None:
    """Share of the described finding's content words that appear in the candidate's title. None when we cannot tell.

    Plain word overlap, not a fuzzy ratio: measured on 40 originals the citation graph had already resolved, the
    right paper had median overlap .40 and the wrong one .00, while rapidfuzz's token_set_ratio sat around .5 for
    both and hid the difference.
    """
    if not desc or not title:
        return None
    dw, tw = words(desc), words(title)
    if not dw or not tw:
        return None
    return round(len(dw & tw) / len(dw), 3)


def year_weight(named: int, cand: int | None) -> float:
    if cand is None:
        return 0.0
    d = abs(int(cand) - int(named))
    return {0: 1.0, 1: 0.6, 2: 0.35}.get(d, 0.0)


def score_candidate(named: dict, cand: dict, min_sim: float = 0.0) -> dict | None:
    """named = {'authors', 'year', 'description'}; cand = {'doi', 'title', 'year', 'surnames'}.

    min_sim rejects a candidate that shares an author and a year but is about something else. The library pass
    does not need it (its pool is the 3,424 originals already in the wiki); the OpenAlex pass does, because every
    surname has namesakes in other fields — without it the pass proposed retinal surgery and Raman spectroscopy
    papers as psychology originals, at 68% precision instead of 89%.
    """
    yw = year_weight(named["year"], cand.get("year"))
    if not yw:
        return None
    want = surnames(named["authors"])
    have = cand.get("surnames") or []
    matched = [s for s in want if any(s == h or (len(s) > 3 and (s in h or h in s)) for h in have)]
    if not matched or want[0] not in matched:            # the first-named author must be there
        return None
    au = len(matched) / len(want)
    sim = text_sim(named.get("description"), cand.get("title"))
    if sim is not None and sim < min_sim:
        return None
    # no description or no title: judge on author and year alone, and say so by scoring lower
    s = 0.45 * au + 0.25 * yw + (0.30 * sim if sim is not None else 0.30 * 0.35)
    return {"doi_o": cand["doi"], "title_o": cand.get("title"), "year_o": cand.get("year"),
            "score": round(s, 3), "authors_matched": f"{len(matched)}/{len(want)}", "year_delta": abs(int(cand["year"]) - int(named["year"])),
            "text_sim": sim}


def band(best: dict, runner: dict | None) -> str:
    """high = the named study and only it; medium = a good match; low = plausible, needs a person."""
    clear = runner is None or best["score"] - runner["score"] >= 0.08
    if best["year_delta"] == 0 and (best["text_sim"] or 0) >= 0.5 and clear:
        return "high"
    if best["year_delta"] == 0 and ((best["text_sim"] or 0) >= 0.3 or (clear and best["text_sim"] is None)):
        return "medium"
    return "low"


def is_self(named: dict, cand: dict) -> bool:
    """The record we found can be an abstracting-service entry for the replication itself, in which case the best
    same-surname, same-year match is that very paper. "Attitude Dimensions of Leisure: A Replication Study" was
    linked to itself this way. A paper is not its own original."""
    a, b = named.get("title_r"), cand.get("title")
    if not a or not b:
        return False
    wa, wb = words(a), words(b)
    return bool(wa) and len(wa & wb) / len(wa) >= 0.8


def choose(named: dict, cands: list[dict], method: str, min_sim: float = 0.0) -> dict | None:
    cands = [c for c in cands if not is_self(named, c)]
    scored = sorted(filter(None, (score_candidate(named, c, min_sim) for c in cands)), key=lambda x: -x["score"])
    if not scored or scored[0]["score"] < FLOOR:
        return None
    best, runner = scored[0], (scored[1] if len(scored) > 1 else None)
    return {**best, "method": method, "confidence": band(best, runner), "n_candidates": len(scored),
            "runner_up": {k: runner[k] for k in ("doi_o", "title_o", "score")} if runner else None}


# ---------------------------------------------------------------- the library (free)

def library_index(g: dict) -> tuple[dict, dict]:
    """(surname, year) -> [doi] over the originals already in the wiki, plus the paper record for each doi."""
    idx: dict[tuple[str, int], list[str]] = defaultdict(list)
    recs: dict[str, dict] = {}
    for doi in g["findings"]:
        p = g["papers"].get(doi) or {}
        if not p.get("authors") or not p.get("year"):
            continue
        y = int(p["year"])
        sn = surnames(p["authors"])
        recs[doi] = {"doi": doi, "title": p.get("title"), "year": y, "surnames": sn}
        for s in sn:
            for dy in (-2, -1, 0, 1, 2):                 # the named year may be the preprint's or the issue's
                idx[(s, y + dy)].append(doi)
    return idx, recs


def from_library(named: dict, idx: dict, recs: dict) -> dict | None:
    dois = {d for s in surnames(named["authors"]) for d in idx.get((s, int(named["year"])), [])}
    return choose(named, [recs[d] for d in dois], "library_author_year") if dois else None


# ---------------------------------------------------------------- OpenAlex (one cached call each)

def from_openalex(named: dict, cid: str) -> dict | None:
    """Works by the named surname in the named year (±1), ranked here rather than by OpenAlex's relevance."""
    first = surnames(named["authors"])[0]
    y = int(named["year"])
    key = "link-" + re.sub(r"[^a-z0-9]+", "-", f"{first}-{y}")
    d = _get({"filter": f"publication_year:{y - 1}|{y}|{y + 1},raw_author_name.search:{first}",
              "select": "id,doi,title,publication_year,authorships,cited_by_count", "per_page": 50}, key)
    from .ids import norm_doi
    cands = []
    for w in d.get("results", []):
        doi = norm_doi(w.get("doi"))
        if not doi:
            continue
        cands.append({"doi": doi, "title": w.get("title"), "year": w.get("publication_year"),
                      "surnames": [n.split()[-1] for a in (w.get("authorships") or [])
                                   if (n := fold((a.get("author") or {}).get("display_name")).strip())],
                      "cited_by": w.get("cited_by_count")})
    return choose(named, cands, "openalex_author_year", MIN_SIM_OPENALEX)


# ---------------------------------------------------------------- run

def named_unlinked(triaged: list[dict]) -> list[dict]:
    """Psychology replications whose original is named by the model but has no DOI yet.

    High-tier finds come first. The library pass is free and reaches all of them, but OpenAlex lookups are metered,
    and a high-tier find is worth resolving: its screen is right about 96% of the time against 39% for the medium
    tier. Ordering here means a spending cap spends what there is on the candidates most likely to be real.
    """
    out = []
    for r in triaged:
        t = r["triage"]
        o = t.get("original") or {}
        if t.get("kind") != "replication" or t.get("field") != "psychology" or t.get("original_doi"):
            continue
        if o.get("authors") and o.get("year"):
            out.append({"cid": r["cid"], "tier": r.get("tier"), "authors": o["authors"], "year": int(o["year"]),
                        "description": o.get("description"), "title_r": r.get("title_r")})
    out.sort(key=lambda n: n["tier"] != "high")
    return out


def run(use_openalex: bool, max_usd: float, check: bool) -> int:
    from . import load, registry
    from .ids import EffectLedger
    from .load import ROOT

    triaged = json.loads((DISCOVERY / "triaged.json").read_text(encoding="utf-8"))
    src = {k: getattr(load, f"load_{k}")() for k in ("flora", "fred", "legacy", "famous", "openalex", "merges")}
    g = registry.build(src, EffectLedger(ROOT / "data" / "curated" / "registry" / "effect_ids.csv"))
    idx, recs = library_index(g)
    if check:
        return report_check(triaged, idx, recs, use_openalex, max_usd)

    todo = named_unlinked(triaged)
    n_high = sum(1 for n in todo if n["tier"] == "high")
    print(f"  {len(todo)} psychology replications name an original without a DOI ({n_high} high tier)")
    links, stuck = {}, []
    for n in todo:
        hit = from_library(n, idx, recs)
        if hit:
            links[n["cid"]] = {**hit, "named": n}
        else:
            stuck.append(n)
    print(f"  library: {len(links)} resolved for free, {len(stuck)} left")
    stopped = None
    if use_openalex:
        for i, n in enumerate(stuck, 1):
            if _spent["usd"] >= max_usd:
                stopped = f"spending cap ${max_usd:.2f} after {i - 1} lookups"
                break
            try:
                hit = from_openalex(n, n["cid"])
            except SystemExit as e:                        # OpenAlex daily budget: keep what we have
                stopped = f"{e} (after {i - 1} lookups)"
                break
            if hit:
                links[n["cid"]] = {**hit, "named": n}
            if i % 100 == 0:
                print(f"    {i}/{len(stuck)} · ${_spent['usd']:.3f}", flush=True)
        if stopped:
            print(f"  stopped early: {stopped}. Re-run to resume; fetched pages are cached and free.")
        print(f"  openalex: {len(links)} resolved in total · {_spent['calls']} calls · ${_spent['usd']:.3f}")

    bands = {b: sum(1 for v in links.values() if v["confidence"] == b) for b in ("high", "medium", "low")}
    by_tier = {t: sum(1 for v in links.values() if v["named"].get("tier") == t) for t in ("high", "medium")}
    in_wiki = sum(1 for v in links.values() if v["doi_o"] in g["findings"])
    out = {"summary": {"named_unlinked": len(todo), "resolved": len(links), "stopped_early": stopped, "by_confidence": bands, "by_search_tier": by_tier,
                       "by_method": {m: sum(1 for v in links.values() if v["method"] == m) for m in
                                     ("library_author_year", "openalex_author_year")},
                       "original_already_in_wiki": in_wiki, "api_calls": _spent["calls"], "cost_usd": round(_spent["usd"], 3)},
           "links": links}
    DISCOVERY.mkdir(parents=True, exist_ok=True)
    (DISCOVERY / "links.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out["summary"], indent=1))
    return 0


def report_check(triaged: list[dict], idx: dict, recs: dict, use_openalex: bool, max_usd: float) -> int:
    """Accuracy on the psychology replications whose original the citation graph already resolved:
    hide that DOI, resolve from the model's (author, year, description), compare."""
    gold = []
    for r in triaged:
        t = r["triage"]
        o = t.get("original") or {}
        if t.get("kind") == "replication" and t.get("field") == "psychology" and t.get("original_doi") \
                and o.get("authors") and o.get("year"):
            gold.append(({"cid": r["cid"], "authors": o["authors"], "year": int(o["year"]),
                          "description": o.get("description")}, t["original_doi"]))
    rows = {"library": [], "openalex": []}
    for n, truth in gold:
        hit = from_library(n, idx, recs)
        if hit:
            rows["library"].append((hit, truth))
        elif use_openalex and _spent["usd"] < max_usd:
            hit = from_openalex(n, n["cid"])
            if hit:
                rows["openalex"].append((hit, truth))
    print(f"  gold set: {len(gold)} pairs the citation graph resolved and the model also named")
    for src_name, rs in rows.items():
        if not rs:
            continue
        for b in ("high", "medium", "low"):
            sel = [(h, t) for h, t in rs if h["confidence"] == b]
            if sel:
                ok = sum(h["doi_o"] == t for h, t in sel)
                print(f"    {src_name:9s} {b:6s}: {ok}/{len(sel)} correct ({ok / len(sel):.0%})")
        ok = sum(h["doi_o"] == t for h, t in rs)
        print(f"    {src_name:9s} {'all':6s}: {ok}/{len(rs)} correct ({ok / len(rs):.0%}) · "
              f"{len(gold) - len(rs)} not proposed by this pass")
    print(f"  cost ${_spent['usd']:.3f}")
    return 0
