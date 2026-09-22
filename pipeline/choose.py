"""Ask which paper in the bibliography is the one being replicated, instead of asking about one paper at a time.

`pipeline verify` asks a yes/no question about a single pairing, and that framing is what limits it. With one
candidate in front of it and nothing to compare against, the judge cannot tell a study from a review of that
study, or the right paper by an author from a neighbouring one; it says "unclear" for 663 links and confirmed a
methodological critique of the Bem Sex-Role Inventory as the paper that used it. Alternatives are the context
that question was missing.

So: show the model the papers the replication actually cites and ask **which one, if any**. It is a better
question and a cheaper one — a find costs one call rather than one call per candidate pairing.

WHAT MADE THIS POSSIBLE, AND IT WAS NOT AN IDEA. Measured against FORRT's 2,802 known (replication, original)
pairs where we hold the bibliography, the true original was findable in that bibliography **23%** of the time,
which would have sunk the design. That number was an artifact: `reference_titles.json` held 68,598 titles and
the scan silently ignored every reference missing one, so it was reading about a third of each bibliography.
Fetching the rest cost **$0.14** and took the file to 131,794:

    true original visible in the bibliography    23%  ->  82%
    our text-similarity scorer ranks it first    10%  ->  31%
    ...somewhere in its top 8                    19%  ->  56%

The answer is usually sitting in the list and the mechanical scorer is picking the wrong line. That is the whole
case for this module, and none of it was visible until the intermediate it rested on was checked.

VALIDATION IS FREE AND LARGE. Those same 2,802 known pairs are ground truth nobody had to label: hide the answer,
offer the candidates, see whether the model picks the paper FORRT recorded. That is a better calibration set than
the 441 hand-read links — independent, objective, and an order of magnitude bigger.

    python -m pipeline choose --check --limit 400     # score against the known pairs
    python -m pipeline choose --all --max-usd 2       # choose an original for every psychology find
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from . import references
from .ids import norm_doi
from .load import CACHE, DISCOVERY
from .triage import URL, Meter, _key, balance

MODEL = "deepseek-v4-flash"
PROMPT_VERSION = "ch1"
N_CANDIDATES = 8
OUT = DISCOVERY / "chosen_links.json"

SYSTEM = """A psychology paper reports re-testing an earlier finding. You are given the papers it cites. Decide
which cited paper holds the finding being re-tested. Reply with one JSON object, nothing else.

  {"choice": <number from the list, or 0>, "why": "<one short sentence>"}

Choose 0 when the paper being re-tested is not in the list. That is a normal answer, not a failure: the list is
a shortlist and the right paper is often outside it. A wrong pick is far worse than a 0, because a wrong pick
gets published as this paper's original.

HOW TO CHOOSE
- Match the FINDING, not the field. Several candidates will be about the same topic; only one reports the
  result being re-tested.
- The replication often names its target — an author, a year, a scale, a paradigm. That naming decides it.
- Prefer the paper that REPORTS the finding over one that reviews, critiques, summarises or cites it. A review
  of a literature is not the study. A methodological critique of a scale is not the paper that used the scale.
  A later paper by the same author extending the work is not the original.
- The earlier paper must predate the replication. Same year is possible; later is not.
- Where two candidates are the same work (a preprint and its published version), pick the published one.
- Beware the companion paper: authors publish "…in men" and "…in women", or "Part I" and "Part II". Read which
  one the replication is about."""


def _fmt(cands: list[dict]) -> str:
    out = []
    for i, c in enumerate(cands, 1):
        bits = [f"{i}. {c['title']}"]
        if c.get("year"):
            bits.append(f"({c['year']})")
        if c.get("authors"):
            bits.append(f"— {c['authors']}")
        out.append(" ".join(bits))
    return "\n".join(out)


def _user_msg(case: dict) -> str:
    out = [f"THE REPLICATION, {case.get('year_r')}:", f"  title: {case['title_r']}"]
    if case.get("abstract_r"):
        out.append(f"  abstract: {case['abstract_r'][:1600]}")
    if case.get("says"):
        out.append(f"  it says it re-tested: {case['says']}")
    out += ["", f"PAPERS IT CITES ({len(case['candidates'])} of them, the closest by wording):",
            _fmt(case["candidates"]),
            "", "Which one holds the finding being re-tested? Answer 0 if it is not listed."]
    return "\n".join(out)


def shortlist(query: str | None, refs: list[str], titles: dict, authors: dict | None = None,
              n: int = N_CANDIDATES) -> list[dict]:
    """The n cited works whose titles sit closest to what the replication says it re-tested.

    Ranked by the same text similarity `references.pick` uses, so this is that function's own top n rather than
    a second opinion — the model is being asked to choose among the lines the scorer could not choose between.
    """
    if not query:
        return []
    scored = sorted(((references.text_sim(query, t["title"]) or 0.0, r, t)
                     for r in refs if (t := titles.get(r)) and t.get("title") and t.get("doi")),
                    key=lambda x: -x[0])
    out = []
    for s, r, t in scored[:n]:
        # reference_authors.json stores a bare list of surnames per work
        a = (authors or {}).get(r) or []
        short = (a[0] + (" et al." if len(a) > 2 else f" & {a[1]}" if len(a) == 2 else "")) if a else None
        out.append({"id": r, "doi": t["doi"], "title": t["title"], "year": t.get("year"),
                    "authors": short, "score": round(s, 3)})
    return out


def choose_one(case: dict, key: str, meter: Meter, cache_dir: Path) -> dict | None:
    stamp = hashlib.md5("|".join(c["doi"] or "" for c in case["candidates"]).encode()).hexdigest()[:8]
    gid = re.sub(r"[^A-Za-z0-9._-]+", "_", case["cid"])[:100]
    f = cache_dir / f"{gid}-{stamp}.json"        # keyed on the shortlist too: a different list is a different question
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    if meter.over:
        return None
    body = json.dumps({
        "model": MODEL, "temperature": 0, "max_tokens": 200, "thinking": {"type": "disabled"},
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": _user_msg(case)}],
    }).encode()
    d = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(URL, data=body, headers={"Authorization": f"Bearer {key}",
                                                                  "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.loads(r.read())
            break
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == 4:
                return None
            time.sleep(2 * 2 ** attempt)
    meter.add(d.get("usage") or {})
    try:
        out = json.loads(d["choices"][0]["message"]["content"])
        pick = int(out.get("choice") or 0)
    except (KeyError, ValueError, TypeError, json.JSONDecodeError):
        out, pick = {}, 0
    chosen = case["candidates"][pick - 1] if 1 <= pick <= len(case["candidates"]) else None
    rec = {"id": case["cid"], "choice": pick, "doi_o": chosen["doi"] if chosen else None,
           "title_o": chosen["title"] if chosen else None, "year_o": chosen.get("year") if chosen else None,
           "rank": pick or None, "n_offered": len(case["candidates"]),
           "why": (out.get("why") or "")[:300], "model": MODEL, "prompt_version": PROMPT_VERSION}
    f.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    return rec


def _run(cases: list[dict], max_usd: float, workers: int, label: str) -> list[dict]:
    key = _key()
    cache_dir = CACHE / "choose" / MODEL / PROMPT_VERSION
    cache_dir.mkdir(parents=True, exist_ok=True)
    meter = Meter(max_usd)
    print(f"  {len(cases)} {label} · model {MODEL} · prompt {PROMPT_VERSION} · cap ${max_usd:.2f} "
          f"· balance ${balance(key)}")
    got, t0 = [], time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(choose_one, c, key, meter, cache_dir) for c in cases]
        for i, fu in enumerate(as_completed(futs), 1):
            r = fu.result()
            if r:
                got.append(r)
            if i % 250 == 0:
                print(f"    {i}/{len(cases)} · est ${meter.usd:.3f} · {time.time() - t0:.0f}s")
    print(f"  done: {len(got)} chosen, {len(cases) - len(got)} not (cap or errors) · est ${meter.usd:.3f}")
    return got


def _titles() -> dict:
    return json.loads((DISCOVERY / "reference_titles.json").read_text(encoding="utf-8"))


def _authors() -> dict:
    p = DISCOVERY / "reference_authors.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def check(limit: int | None, max_usd: float, workers: int) -> int:
    """Score against FORRT's own (replication, original) pairs, which nobody had to label."""
    from . import load, registry
    from .ids import EffectLedger
    src = {k: getattr(load, f"load_{k}")() for k in ("flora", "fred", "legacy", "famous", "openalex", "merges")}
    g = registry.build(src, EffectLedger(load.ROOT / "data" / "curated" / "registry" / "effect_ids.csv"))
    pairs = [(a["doi_r"], a["doi_o"], a.get("title_r"), (a.get("rows") or [{}])[0].get("description"),
              a.get("year_r")) for a in g["attempts"].values()
             if a["type"] == "replication" and a.get("doi_o") and a.get("doi_r")]
    refs = references.reference_lists({p[0] for p in pairs})
    titles, authors = _titles(), _authors()
    cases, truth = [], {}
    for dr, do, tr, desc, yr in pairs:
        if dr not in refs:
            continue
        cands = shortlist(desc or references.stem_title(tr), refs[dr], titles, authors)
        if not cands:
            continue
        cases.append({"cid": dr, "title_r": tr, "year_r": yr, "abstract_r": None,
                      "says": desc, "candidates": cands})
        truth[dr] = norm_doi(do)
    random.Random(19).shuffle(cases)          # a deterministic sample, so a capped run is not a biased one
    if limit:
        cases = cases[:limit]
    got = _run(cases, max_usd, workers, "known pairs, answer hidden")
    _score(got, truth, {c["cid"]: c for c in cases})
    return 0


def _score(got: list[dict], truth: dict[str, str], cases: dict[str, dict]) -> None:
    from .audit import wilson
    picked_right = picked_wrong = said_none_rightly = said_none_wrongly = 0
    base_top1 = 0
    for r in got:
        t = truth.get(r["id"])
        cands = cases[r["id"]]["candidates"]
        present = any(norm_doi(c["doi"]) == t for c in cands)
        if cands and norm_doi(cands[0]["doi"]) == t:
            base_top1 += 1
        if r["doi_o"]:
            if norm_doi(r["doi_o"]) == t:
                picked_right += 1
            else:
                picked_wrong += 1
        elif present:
            said_none_wrongly += 1
        else:
            said_none_rightly += 1
    n = len(got)
    picks = picked_right + picked_wrong
    print(f"\n   {n} known pairs, the answer hidden\n")
    if picks:
        lo, hi = wilson(picked_right, picks)
        print(f"   it named a paper {picks} times and was right {picked_right} — "
              f"{picked_right / picks:.0%} (95%: {lo:.0%}–{hi:.0%})")
        print(f"   {'CLEARS' if lo >= 0.90 else 'DOES NOT CLEAR'} the 90% bar")
    print(f"   it answered 'not listed' {said_none_rightly + said_none_wrongly} times — "
          f"{said_none_rightly} correctly, {said_none_wrongly} when the paper was in fact there")
    print(f"\n   for comparison, the text-similarity scorer's top line is right {base_top1} of {n} "
          f"({base_top1 / max(n, 1):.0%}); this names a right paper {picked_right} of {n} "
          f"({picked_right / max(n, 1):.0%})")
    print(f"   where it picked right, the scorer had ranked that paper: "
          f"{Counter(r['rank'] for r in got if r['doi_o'] and norm_doi(r['doi_o']) == truth.get(r['id'])).most_common()}")


def run(max_usd: float, workers: int, limit: int | None) -> int:
    from . import load
    tri = load.load_triaged()
    psy = {r["cid"]: r for r in tri
           if (r.get("triage") or {}).get("field") == "psychology"
           and (r.get("triage") or {}).get("kind") in ("replication", "reproduction")}
    refs = references.reference_lists(set(psy))
    titles, authors = _titles(), _authors()
    cases = []
    for cid, r in psy.items():
        if cid not in refs:
            continue
        o = (r.get("triage") or {}).get("original") or {}
        q = o.get("description") or references.stem_title(r.get("title_r"))
        cands = shortlist(q, refs[cid], titles, authors)
        if not cands:
            continue
        says = ", ".join(str(o[k]) for k in ("authors", "year") if o.get(k)) or None
        if o.get("description"):
            says = f"{says or ''} — {o['description']}".strip(" —")
        cases.append({"cid": cid, "title_r": r.get("title_r"), "year_r": r.get("year_r"),
                      "abstract_r": r.get("abstract"), "says": says, "candidates": cands})
    if limit:
        cases = cases[:limit]
    got = _run(cases, max_usd, workers, "psychology finds with a bibliography")
    merged = {r["id"]: r for r in (json.loads(OUT.read_text()) if OUT.exists() else [])}
    merged.update({r["id"]: r for r in got})
    OUT.write_text(json.dumps(sorted(merged.values(), key=lambda r: r["id"]), ensure_ascii=False, indent=0),
                   encoding="utf-8")
    named = sum(1 for r in merged.values() if r["doi_o"])
    print(f"  wrote {OUT} · {len(merged)} answered, {named} naming a paper "
          f"({named / max(len(merged), 1):.0%}), {len(merged) - named} saying it is not in the list")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="pipeline choose", description=__doc__.split("\n")[0])
    p.add_argument("--check", action="store_true", help="score against FORRT's known pairs with the answer hidden")
    p.add_argument("--all", action="store_true", help="choose an original for every psychology find")
    p.add_argument("--max-usd", type=float, default=1.0)
    p.add_argument("--workers", type=int, default=16)
    p.add_argument("--limit", type=int)
    a = p.parse_args(argv)
    if a.check:
        return check(a.limit, a.max_usd, a.workers)
    if a.all:
        return run(a.max_usd, a.workers, a.limit)
    p.print_help()
    return 1
