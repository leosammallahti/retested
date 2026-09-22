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
import re

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


_STOP = set("the a an of and or in on for to with by is are as at from that which".split())


def _overlap(asked: str, got: str | None) -> float:
    """Share of the asked title's content words present in the returned one."""
    norm = lambda s: set(re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).split()) - _STOP  # noqa: E731
    a = norm(asked)
    return len(a & norm(got)) / max(1, len(a))


_QUOTED = re.compile(r"[\u2018'\"\u201c]\s*([^\u2019'\"\u201d]{12,200})[\u2019'\"\u201d]")


def run_famous(max_usd: float = 0.30) -> int:
    """Give the famous tier a real source, by finding each effect's original paper in OpenAlex by title.

    Every famous card was written from a one-line curated gloss plus a citation string, because those entries
    carry no DOI. That is the same starvation that made the study tier invent directions before its abstracts
    were fetched, and the 80-card review put the famous tier's serious-error rate at 20% because of it. The
    curated `original_paper` field quotes the paper's title for 328 of 353 entries; OpenAlex will find most of
    them from that.

    Stored under the card's own id rather than a DOI, because these entries have none.
    """
    from . import game, load, registry, score
    from .ids import EffectLedger
    from .load import ROOT
    import hashlib

    src = {k: getattr(load, f"load_{k}")() for k in ("flora", "fred", "legacy", "famous", "openalex", "merges")}
    g = registry.build(src, EffectLedger(ROOT / "data" / "curated" / "registry" / "effect_ids.csv"))
    score.score(g)
    want = {}
    for e in g["effects"].values():
        f = e.get("famous")
        if not f or not f.get("original_paper"):
            continue
        m = _QUOTED.search(f["original_paper"])
        if m:
            want["f" + hashlib.md5(e["key"].encode()).hexdigest()[:9]] = m.group(1).strip()
    existing = load.load_original_authors()
    todo = {k: v for k, v in want.items() if k not in existing}
    print(f"  {len(want)} famous effects name a paper title · {len(todo)} not yet looked up")
    out, found = dict(existing), 0
    for i, (gid, title) in enumerate(sorted(todo.items())):
        if _spent["usd"] >= max_usd:
            print(f"  stopping at the ${max_usd:.2f} cap after {i}")
            break
        key = "fam-" + hashlib.sha256(title.encode()).hexdigest()[:16]
        # A comma inside an OpenAlex filter means AND, so a title with one 400s. Question marks and pipes break
        # it too. Strip them: they carry no search signal anyway.
        # Keep letters, digits and spaces and nothing else. A comma means AND inside an OpenAlex filter, and
        # brackets, slashes, quotes and dashes break it in their own ways; none carries search signal.
        q = re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9 ]", " ", title)).strip()[:180]
        d = _get({"filter": f"title.search:{q}", "per_page": 3,
                  "select": "id,doi,title,publication_year,authorships,primary_location,cited_by_count,"
                            "abstract_inverted_index,type,is_retracted"}, key)
        # Take the best of three by content-word overlap and keep it only if it is essentially the same title.
        # A bare title search returns an impostor as readily as the author+year matcher did — "Automaticity of
        # social behaviour" comes back as "Automatic Visual Tracking and Social Behaviour Analysis in Mice" —
        # and an unvalidated match here would put a card in front of a player about the wrong paper entirely.
        w = max(d.get("results") or [], key=lambda r: _overlap(title, r.get("title")), default=None)
        if not w or _overlap(title, w.get("title")) < 0.8:
            out[gid] = {"title": None, "abstract": None, "asked": title,
                        "rejected": (w or {}).get("title")}
            continue
        au = w.get("authorships") or []
        out[gid] = {"title": w.get("title"), "year": w.get("publication_year"),
                    "authors": _short(au), "abstract": _abstract(w.get("abstract_inverted_index")),
                    "asked": title}
        found += bool(out[gid]["abstract"])
        if i % 40 == 0:
            print(f"    {i}/{len(todo)} · ${_spent['usd']:.3f}", flush=True)
    DISCOVERY.mkdir(parents=True, exist_ok=True)
    (DISCOVERY / "original_authors.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    got = sum(1 for k in want if (out.get(k) or {}).get("abstract"))
    print(f"  {got} of {len(want)} famous effects now have an abstract · {_spent['calls']} calls · ${_spent['usd']:.3f}")
    return 0


def run_deck(max_usd: float = 0.20) -> int:
    """Fetch the OpenAlex record — above all the abstract — for every original the game deals a card about.

    The claim writer was being given a bare result sentence, and FReD's result sentences are often an omnibus
    F or chi-square with no direction in them. Asked to write a finding from that, a model supplies the direction
    from the title, which is how a card ends up asserting something the study never reported. The study's own
    abstract is the material that was missing, OpenAlex serves it free, and we already hold the identifiers.
    """
    from . import game, load, registry, score
    from .ids import EffectLedger
    from .load import ROOT

    src = {k: getattr(load, f"load_{k}")() for k in ("flora", "fred", "legacy", "famous", "openalex", "merges")}
    g = registry.build(src, EffectLedger(ROOT / "data" / "curated" / "registry" / "effect_ids.csv"))
    score.score(g)
    items, _ = game.build(g, load.load_claims())
    from .claims import cards as claim_cards
    want = sorted({c["doi_o"] for c in claim_cards(g, items) if c.get("doi_o")})
    existing = load.load_original_authors()
    todo = [d for d in want if not (existing.get(d) or {}).get("abstract")]
    print(f"  {len(want)} originals behind game cards · {len(want) - len(todo)} already have an abstract · "
          f"{len(todo)} to fetch")
    out = {**existing, **fetch(todo, max_usd)}
    DISCOVERY.mkdir(parents=True, exist_ok=True)
    (DISCOVERY / "original_authors.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    got = sum(1 for d in want if (out.get(d) or {}).get("abstract"))
    print(f"  {got} of {len(want)} card originals now have an abstract · {_spent['calls']} calls · ${_spent['usd']:.3f}")
    return 0


def run(max_usd: float = 0.10) -> int:
    from . import load, queue, registry
    from .ids import EffectLedger
    from .load import ROOT

    src = {k: getattr(load, f"load_{k}")() for k in ("flora", "fred", "legacy", "famous", "openalex", "merges")}
    g = registry.build(src, EffectLedger(ROOT / "data" / "curated" / "registry" / "effect_ids.csv"))
    cands = queue.build_retested(load.load_triaged(),
                                 load.merged_links(), g,
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
