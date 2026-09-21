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

from .discover import _get, _spent
from .ids import norm_doi
from .link import text_sim
from .load import CACHE, DISCOVERY

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


def pick(description: str, refs: list[str], titles: dict[str, dict]) -> dict | None:
    """The referenced work whose title best matches the described finding, with its margin over the runner-up."""
    scored = sorted(((text_sim(description, t["title"]) or 0.0, t)
                     for r in refs if (t := titles.get(r)) and t.get("title") and t.get("doi")),
                    key=lambda x: -x[0])
    if not scored or scored[0][0] < FLOOR:
        return None
    top, runner = scored[0], (scored[1] if len(scored) > 1 else (0.0, None))
    margin = round(top[0] - runner[0], 3)
    band = ("high" if top[0] >= HIGH[0] and margin >= HIGH[1]
            else "medium" if top[0] >= MEDIUM[0] and margin >= MEDIUM[1] else "low")
    return {"doi_o": top[1]["doi"], "title_o": top[1]["title"], "year_o": top[1].get("year"),
            "method": "reference_scan", "confidence": band, "score": round(top[0], 3), "text_sim": round(top[0], 3),
            "margin": margin, "n_references": len(scored),
            "runner_up": {"doi_o": runner[1]["doi"], "title_o": runner[1]["title"],
                          "score": round(runner[0], 3)} if runner[1] else None}


def run(max_usd: float = 1.20) -> int:
    from . import load
    triaged = load.load_triaged()
    links = load.load_links()
    todo = {}
    for r in triaged:
        t = r["triage"]
        o = t.get("original") or {}
        if t.get("kind") not in ("replication", "reproduction") or t.get("field") != "psychology":
            continue
        if t.get("original_doi") or r["cid"] in links or not o.get("description"):
            continue
        todo[r["cid"]] = o["description"]
    print(f"  {len(todo):,} psychology replications still have no original but describe one")
    refs = reference_lists(set(todo))
    print(f"  {len(refs):,} of them cite a reference list we already hold")
    titles = resolve_titles(sorted({w for v in refs.values() for w in v}), max_usd)
    out = {}
    for cid, desc in todo.items():
        hit = pick(desc, refs.get(cid, []), titles)
        if hit:
            out[cid] = {**hit, "named": {"description": desc}}
    (DISCOVERY / "reference_links.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    from collections import Counter
    print(f"  proposed an original for {len(out):,} of the {len(refs):,} with references "
          f"· {_spent['calls']} calls · ${_spent['usd']:.3f}")
    print("  by confidence:", dict(Counter(v["confidence"] for v in out.values())))
    return 0
