"""Citation-graph discovery: find replications FORRT has not recorded.

A replication almost always cites the study it replicates. So for every original in the wiki we ask OpenAlex
for works that (a) cite it and (b) mention replication in title or abstract, score them on replication-specific
language, and keep only those absent from BOTH FORRT's curated data (FLoRA/FReD/legacy) AND FORRT's own
machine-found candidate files. What remains is what FORRT's self-description-based pipeline missed.

    python -m pipeline discover            # crawl (cached, resumable) + score + write data/build/discovered.json

Cost: roughly 1 OpenAlex call per 50 seeds for ID lookup plus 1+ call per 50 seeds for citations (~$0.001/call).
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz

from .ids import norm_doi
from .load import CACHE, FORRT, ROOT

API = "https://api.openalex.org/works"
MAILTO = "leosammallahti@gmail.com"
OA_CACHE = CACHE / "openalex"
SELECT = "id,doi,title,publication_year,type,referenced_works,abstract_inverted_index,primary_location,authorships"

# ---------------------------------------------------------------- OpenAlex access (cached, polite)

_spent = {"calls": 0, "usd": 0.0}


def _api_key() -> str | None:
    """OPENALEX_API_KEY from the environment or ROOT/.env (gitignored, chmod 600). Never logged, never cached."""
    import os
    if os.environ.get("OPENALEX_API_KEY"):
        return os.environ["OPENALEX_API_KEY"].strip()
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("OPENALEX_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'") or None
    return None


def _get(params: dict, cache_key: str) -> dict:
    OA_CACHE.mkdir(parents=True, exist_ok=True)
    f = OA_CACHE / f"{cache_key}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    key = _api_key()
    q = urllib.parse.urlencode({**params, "mailto": MAILTO, **({"api_key": key} if key else {})}, safe=":|,*")
    for attempt in range(6):
        try:
            req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": f"Retested/0.1 (mailto:{MAILTO})"})
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            left = e.headers.get("X-RateLimit-Remaining-USD")
            if e.code == 429 and left is not None and float(left) <= 0.0005:
                reset = int(e.headers.get("X-RateLimit-Reset") or 0)
                raise SystemExit(f"OpenAlex daily budget used up (resets in {reset // 3600} h {reset % 3600 // 60} min). "
                                 f"{'Add OPENALEX_API_KEY to .env for a larger allowance. ' if not key else ''}Re-run to resume from cache.")
            if attempt == 5:
                raise
            wait = int(e.headers.get("Retry-After") or 0) or 1.5 * 2 ** attempt
            print(f"    retry {attempt + 1}: HTTP {e.code}, waiting {wait:.0f}s")
            time.sleep(wait)
        except Exception as e:  # noqa: BLE001 - transient network error
            if attempt == 5:
                raise
            time.sleep(1.5 * 2 ** attempt)
            print(f"    retry {attempt + 1}: {type(e).__name__}")
    _spent["calls"] += 1
    _spent["usd"] += float((d.get("meta") or {}).get("cost_usd") or 0)
    f.write_text(json.dumps(d), encoding="utf-8")
    time.sleep(0.12)
    return d


def resolve_ids(dois: list[str]) -> dict[str, str]:
    """DOI -> OpenAlex work id (W...). 50 DOIs per call."""
    out: dict[str, str] = {}
    dois = sorted(set(d for d in dois if d and "|" not in d and "," not in d))
    for i in range(0, len(dois), 50):
        chunk = dois[i:i + 50]
        d = _get({"filter": "doi:" + "|".join(chunk), "select": "id,doi", "per_page": 50}, f"ids-{i // 50:04d}-{len(chunk)}")
        for w in d.get("results", []):
            if w.get("doi"):
                out[norm_doi(w["doi"])] = w["id"].rsplit("/", 1)[-1]
    return out


def citing_replications(seed_ids: list[str]) -> list[dict]:
    """Works citing any seed and mentioning replication (OpenAlex stems: replicate/replicated/replicating match)."""
    works: dict[str, dict] = {}
    for i in range(0, len(seed_ids), 50):
        chunk = seed_ids[i:i + 50]
        cursor, page = "*", 0
        while cursor:
            d = _get({"filter": "cites:" + "|".join(chunk) + ",title_and_abstract.search:replication",
                      "select": SELECT, "per_page": 200, "cursor": cursor},
                     f"cites-{i // 50:04d}-{page:02d}-{len(chunk)}")
            for w in d.get("results", []):
                works[w["id"]] = w
            cursor = (d.get("meta") or {}).get("next_cursor")
            page += 1
            if not d.get("results"):
                break
        if (i // 50) % 10 == 0:
            print(f"    seeds {i + len(chunk)}/{len(seed_ids)} -> {len(works)} citing works")
    return list(works.values())


def abstract(inv: dict | None) -> str:
    if not inv:
        return ""
    pos = {}
    for word, idxs in inv.items():
        for k in idxs:
            pos[k] = word
    return " ".join(pos[k] for k in sorted(pos))


# ---------------------------------------------------------------- scoring

STRONG = re.compile(
    r"(fail(ed|ure)? to replicate|did not replicate|(direct|close|exact|conceptual|independent|preregistered|pre-registered|"
    r"registered|high-powered|large-scale|multi-?site|multi-?lab) replications?|replication (attempt|study|of|and extension)|"
    r"attempt(ed|s)? to replicate|we (tried|sought|aimed|set out) to replicate|successfully replicated|"
    r"(could|can|was|were) not (be )?replicated|replicat(e|ed|ing) (the |a |an )?(original|previous|prior|seminal|classic|influential|findings?|effects?|results?|study|studies|experiment)|"
    r"registered replication report|many labs|this replication|our replication|the present replication|reproduction of)", re.I)
TITLE = re.compile(r"replicat|revisit|reexamin|re-examin|does .{3,60} (really|still)|reproducib", re.I)
META = re.compile(r"replicability|replication crisis|reproducibility crisis|replication problem|meta-?analy|systematic review|"
                  r"predict(ing)? (which|the) .{0,40}replicat|forecast|open science|questionable research|p-hacking|"
                  r"commentary|reply to|response to|comment on|editorial|erratum|corrigendum", re.I)
GOOD_TYPES = {"article", "preprint", "report", "dissertation", "book-chapter"}


def score(w: dict, n_seeds_cited: int) -> dict:
    title = w.get("title") or ""
    ab = abstract(w.get("abstract_inverted_index"))
    text = f"{title}. {ab}"
    s, why = 0, []
    if TITLE.search(title):
        s += 3; why.append("title")
    m = STRONG.search(text)
    if m:
        s += 3; why.append(f"phrase:{m.group(0)[:40].lower()}")
    if META.search(title):
        s -= 4; why.append("meta-title")
    elif META.search(ab) and not m:
        s -= 2; why.append("meta-abstract")
    if n_seeds_cited >= 8:
        s -= 1; why.append(f"cites {n_seeds_cited} originals")
    if w.get("type") not in GOOD_TYPES:
        s -= 3; why.append(f"type:{w.get('type')}")
    if not ab:
        why.append("no abstract")
    tier = "high" if s >= 5 else "medium" if s >= 3 else "low"
    return {"score": s, "tier": tier, "why": why, "abstract": ab}


# ---------------------------------------------------------------- what FORRT already knows

def known_to_forrt(g: dict) -> tuple[set[str], set[str], list[str]]:
    """(replication DOIs, (doi_o|doi_r) pairs, titles) across FORRT curated data AND FORRT's candidate files."""
    reps, pairs, titles = set(), set(), []
    for a in g["attempts"].values():
        if a["doi_r"]:
            reps.add(a["doi_r"]); pairs.add(f"{a['doi_o']}|{a['doi_r']}")
        if a.get("title_r"):
            titles.append(a["title_r"])
    feeds = FORRT / "feeds"
    for f in feeds.glob("flora-extractor_*.csv"):
        df = pd.read_csv(f, dtype=str, keep_default_na=False, usecols=lambda c: c in ("doi_r", "doi_o", "title_r"))
        for r in df.to_dict("records"):
            d = norm_doi(r.get("doi_r"))
            if d:
                reps.add(d)
                if norm_doi(r.get("doi_o")):
                    pairs.add(f"{norm_doi(r['doi_o'])}|{d}")
            if r.get("title_r"):
                titles.append(r["title_r"])
    for f in ("flora-validation_validated_export.csv", "flora-validation_flora_entry_sheets.csv"):
        p = feeds / f
        if p.exists():
            df = pd.read_csv(p, dtype=str, keep_default_na=False)
            for col in ("doi_r", "doi_r_published"):
                if col in df:
                    reps.update(filter(None, (norm_doi(x) for x in df[col])))
            if "title_r" in df:
                titles.extend(t for t in df["title_r"] if t)
    return reps, pairs, titles


def _tkey(t: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", (t or "").lower())[:160]


# ---------------------------------------------------------------- run

def keyword_sweep() -> list[dict]:
    """Every OpenAlex work with a Psychology topic and 'replication' (stemmed) in the title, all years."""
    works: dict[str, dict] = {}
    cursor, page = "*", 0
    while cursor:
        d = _get({"filter": "topics.field.id:32,title.search:replication", "select": SELECT, "per_page": 200, "cursor": cursor},
                 f"kw-{page:03d}")
        for w in d.get("results", []):
            works[w["id"]] = w
        cursor = (d.get("meta") or {}).get("next_cursor")
        page += 1
        if not d.get("results"):
            break
        if page % 10 == 0:
            print(f"    page {page}: {len(works)} works")
    return list(works.values())


def run(g: dict, mode: str = "cites") -> dict:
    t0 = time.time()
    seeds_doi = sorted(g["findings"])
    print(f"  seeds: {len(seeds_doi)} original papers")
    idmap = resolve_ids(seeds_doi)
    rev = {v: k for k, v in idmap.items()}
    print(f"  resolved {len(idmap)}/{len(seeds_doi)} to OpenAlex ids ({time.time() - t0:.0f}s)")
    if mode == "coverage":
        return coverage(g)
    works = citing_replications(sorted(rev)) if mode == "cites" else keyword_sweep()
    print(f"  {len(works)} works ({mode}) ({time.time() - t0:.0f}s, {_spent['calls']} API calls, ${_spent['usd']:.3f})")

    reps, pairs, titles = known_to_forrt(g)
    tset = {_tkey(t) for t in titles if t}
    tlist = [k for k in tset if len(k) > 25]
    P = g["papers"]

    # ---- recall against FORRT: for each known pair whose original resolved, did we surface that replication?
    found_pairs = set()
    rows = []
    for w in works:
        doi_r = norm_doi(w.get("doi"))
        cited = [rev[x.rsplit("/", 1)[-1]] for x in (w.get("referenced_works") or []) if x.rsplit("/", 1)[-1] in rev]
        for d in cited:
            if doi_r:
                found_pairs.add(f"{d}|{doi_r}")
        sc = score(w, len(cited))
        tk = _tkey(w.get("title"))
        known_rep = bool(doi_r and doi_r in reps)
        known_title = not known_rep and tk in tset or (len(tk) > 25 and any(fuzz.ratio(tk, k) >= 92 for k in tlist if abs(len(k) - len(tk)) < 12))
        src = (w.get("primary_location") or {}).get("source") or {}
        au = w.get("authorships") or []
        rows.append({
            "openalex_id": w["id"].rsplit("/", 1)[-1], "doi_r": doi_r, "title_r": w.get("title"),
            "year_r": w.get("publication_year"), "type": w.get("type"), "venue": src.get("display_name"),
            "authors_r": (au[0]["author"]["display_name"].split()[-1] + (" et al." if len(au) > 2 else f" & {au[1]['author']['display_name'].split()[-1]}" if len(au) == 2 else "")) if au else None,
            "originals": cited, "original_titles": [P.get(d, {}).get("title") for d in cited[:5]],
            "known_to_forrt": known_rep or known_title, "known_how": "doi" if known_rep else ("title (preprint/published twin)" if known_title else None),
            **sc,
        })

    recall_base = [p for p in pairs if p.split("|")[0] in idmap]
    recall = {
        "known_pairs_with_resolvable_original": len(recall_base),
        "recovered_by_crawl": sum(1 for p in recall_base if p in found_pairs),
    }
    new = [r for r in rows if not r["known_to_forrt"]]
    summary = {
        "mode": mode, "seeds": len(seeds_doi), "seeds_resolved": len(idmap), "citing_works": len(works),
        "known_to_forrt": len(rows) - len(new), "new": len(new),
        "new_by_tier": {t: sum(1 for r in new if r["tier"] == t) for t in ("high", "medium", "low")},
        "recall": recall, "api_calls": _spent["calls"], "cost_usd": round(_spent["usd"], 3),
    }
    new.sort(key=lambda r: (-r["score"], -(r["year_r"] or 0)))
    out = ROOT / "data" / "build" / f"discovered-{mode}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "candidates": new}, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    return summary


# ---------------------------------------------------------------- how much can a keyword search even see?

def coverage(g: dict) -> dict:
    """Use FORRT's own replication papers as an answer key: what share are in OpenAlex, tagged Psychology,
    and have 'replic...' in the title? That is the ceiling for a 'psychology + replication in title' search."""
    from collections import Counter
    reps = sorted({a["doi_r"] for a in g["attempts"].values() if a["type"] == "replication" and a["doi_r"] and "flora" in a["sources"]})
    found = {}
    for i in range(0, len(reps), 50):
        chunk = reps[i:i + 50]
        d = _get({"filter": "doi:" + "|".join(chunk), "select": "id,doi,title,topics,primary_topic,type", "per_page": 50}, f"cov-{i // 50:04d}")
        for w in d.get("results", []):
            found[norm_doi(w["doi"])] = w
    is_psych = lambda w: any((t.get("field") or {}).get("id", "").endswith("/32") for t in (w.get("topics") or []))  # noqa: E731
    is_psych_main = lambda w: ((w.get("primary_topic") or {}).get("field") or {}).get("id", "").endswith("/32")  # noqa: E731
    in_title = lambda w: bool(re.search(r"replic", w.get("title") or "", re.I))  # noqa: E731
    W = list(found.values())
    n = len(reps)
    out = {
        "flora_replication_papers": n,
        "in_openalex": len(W),
        "tagged_psychology_any_topic": sum(map(is_psych, W)),
        "tagged_psychology_main_topic": sum(map(is_psych_main, W)),
        "replic_in_title": sum(map(in_title, W)),
        "visible_to_keyword_search": sum(1 for w in W if is_psych(w) and in_title(w)),
        "fields_of_untagged": Counter(((w.get("primary_topic") or {}).get("field") or {}).get("display_name") for w in W if not is_psych(w)).most_common(10),
    }
    out["share_visible_to_keyword_search"] = round(out["visible_to_keyword_search"] / n, 3)
    (ROOT / "data" / "build").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "build" / "coverage.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
    return out
