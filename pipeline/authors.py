"""Everything OpenAlex knows about the original papers our finds point at.

Independence is the strongest signal in FORRT's data — replications sharing an author with the original report
success 70% of the time against 38% for independent teams — and it is the one rigour dimension we can settle
outright. Surnames only suggest it: across 171,000 author slots the median surname appears once, but "chen"
appears 832 times, so a naive match called 16 coincidences author overlap. OpenAlex author ids do not have that
problem.

It began as an author-identity fetch, because independence is the strongest signal in FORRT's data and a surname
is not a person. It now takes the whole record, because we held a title for only 416 of 2,690 originals: a find
could name the study it replicates and still have nothing to show a reader but a DOI. Title, year, venue and
abstract come back in the same call as the authorships, so the extra information is free.

Originals are fetched 50 DOIs per call, so the whole set costs about fifty calls.

    python -m pipeline authors [--max-usd 0.10]

Results go to data/discovery/original_authors.json, keyed by DOI. Re-runs replay the OpenAlex cache for free.
"""
from __future__ import annotations

import hashlib
import json

from .discover import _get, _spent
from .ids import norm_doi
from .load import DISCOVERY


def _abstract(inv: dict | None) -> str | None:
    """OpenAlex stores abstracts as a word -> positions index; put the words back in order."""
    if not inv:
        return None
    pos = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    text = " ".join(pos[i] for i in sorted(pos))
    return text[:4000] or None


def _short(au: list) -> str | None:
    fams = [n.split()[-1] for a in au if (n := ((a.get("author") or {}).get("display_name") or "").strip())]
    if not fams:
        return None
    return fams[0] if len(fams) == 1 else (f"{fams[0]} & {fams[1]}" if len(fams) == 2 else f"{fams[0]} et al.")


def fetch(dois: list[str], max_usd: float) -> dict[str, dict]:
    out: dict[str, dict] = {}
    clean = sorted({d for d in dois if d and "|" not in d and "," not in d})
    for i in range(0, len(clean), 50):
        if _spent["usd"] >= max_usd:
            print(f"  stopping at the ${max_usd:.2f} cap after {i} originals")
            break
        chunk = clean[i:i + 50]
        # key on WHICH dois were asked for, not on their position: the list of originals still needing a fetch
        # shrinks every run, so a positional key silently replays the previous run's answers for different papers
        # 'orig-' not 'auth-': the earlier cache holds responses selected down to authorships alone
        key = "orig-" + hashlib.sha256("|".join(chunk).encode()).hexdigest()[:16]
        d = _get({"filter": "doi:" + "|".join(chunk),
                  "select": "id,doi,title,publication_year,authorships,primary_location,cited_by_count,"
                            "abstract_inverted_index,type,is_retracted",
                  "per_page": 50}, key)
        for w in d.get("results", []):
            doi = norm_doi(w.get("doi"))
            if not doi:
                continue
            au = w.get("authorships") or []
            out[doi] = {
                "ids": [x.rsplit("/", 1)[-1] for a in au if (x := (a.get("author") or {}).get("id"))],
                "surnames": [n.split()[-1].lower() for a in au
                             if (n := ((a.get("author") or {}).get("display_name") or "").strip())],
                "title": w.get("title"), "year": w.get("publication_year"),
                "journal": ((w.get("primary_location") or {}).get("source") or {}).get("display_name"),
                "cited_by": w.get("cited_by_count"), "type": w.get("type"),
                "is_retracted": w.get("is_retracted"),
                "abstract": _abstract(w.get("abstract_inverted_index")),
                "authors": _short(au),
            }
        if (i // 50) % 5 == 0:
            print(f"    {i + len(chunk)}/{len(clean)} · ${_spent['usd']:.3f}", flush=True)
    return out


def run(max_usd: float = 0.10) -> int:
    from . import load, queue, registry
    from .ids import EffectLedger
    from .load import ROOT

    src = {k: getattr(load, f"load_{k}")() for k in ("flora", "fred", "legacy", "famous", "openalex", "merges")}
    g = registry.build(src, EffectLedger(ROOT / "data" / "curated" / "registry" / "effect_ids.csv"))
    cands = queue.build_retested(load.load_triaged(),
                                 {**load.load_reference_links(), **load.load_links()}, g,
                                 load.load_known_replication_dois(), load.load_known_osf_ids())
    # only the originals our finds actually point at, and only where we do not already have a list from FLoRA
    want = sorted({c["doi_o"] for c in cands
                   if c["doi_o"] and not (g["papers"].get(c["doi_o"]) or {}).get("surnames")})
    have = sorted({c["doi_o"] for c in cands if c["doi_o"] and (g["papers"].get(c["doi_o"]) or {}).get("surnames")})
    print(f"  originals our finds point at: {len(want) + len(have)}  "
          f"({len(have)} already have an author list from FLoRA, {len(want)} to fetch)")
    existing = {d: v for d, v in load.load_original_authors().items() if "title" in v}
    want = [d for d in sorted(set(want) | set(have)) if d not in existing]   # every original, not just the unnamed
    print(f"  {len(want)} not yet fetched")
    out = {**existing, **fetch(want, max_usd)}
    DISCOVERY.mkdir(parents=True, exist_ok=True)
    (DISCOVERY / "original_authors.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"  author lists for {len(out)} originals · {_spent['calls']} calls · ${_spent['usd']:.3f}")
    return 0
