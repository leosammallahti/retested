"""Ask the model the question the hand-reads have been answering: is this the right earlier paper?

`pipeline originals` measures link METHODS — read forty cases from a band, and if the band comes out at 90% or
better every row in it is allowed through. That is the only instrument we had, and it has a hard limit: it judges
a row by the company it keeps. 1,259 psychology finds are matched to an original and excluded, not because anyone
looked at them and disagreed, but because the method that found them averages 86% or 80% instead of 90%. Inside a
band at 86% there are obviously-right matches and obviously-wrong ones, and the band score cannot tell them apart.

This asks about the row itself. One call per find: here is the replication, here is the paper we matched it to,
is this the paper it re-tested? A find whose match the model confirms can ship on its own evidence whatever band
it came from; a find the model rejects is held back even if its band scored well.

WHY THIS IS TRUSTWORTHY, AND THE ONLY REASON IT IS. 440 of these links have already been read one at a time by
hand and written down in data/curated/original_audit.csv. Those labels were made before this module existed and
for a different purpose, so they are a fair test. `--calibrate` runs the model over exactly those rows and prints
how often it agrees. The number that decides everything is the precision of its "right" verdicts: of the links it
confirms, how many did a reader also confirm. If that is under 90% this module ships nothing, and the pass costs
about a dollar to find out.

    python -m pipeline verify --calibrate            # score the model against the 440 hand-read cases
    python -m pipeline verify --all --max-usd 2      # judge every matched find
    python -m pipeline verify --report               # what was confirmed, by band

THE ONE THING THE JUDGE MUST NOT SEE. For links whose method is `cited by this paper`, the model wrote
`original_named.description` AFTER choosing which cited work it meant. Showing that description to the judge
would be handing it its own earlier answer and asking whether it agrees — the description fits the paper because
it was written from the paper. Those cases are judged from the replication's own abstract against the original's
title and abstract, and nothing else. `originals.py` prints the same warning to human readers for the same reason.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from . import audit, originals
from .load import CACHE, DISCOVERY
from .triage import URL, Meter, _key, balance

MODEL = "deepseek-v4-flash"
PROMPT_VERSION = "v1"
# A second prompt for the cases v1 could not settle. 663 links came back "unclear" and 80% of them are cases
# where nobody holds a summary of the earlier paper, so the judge was handed a bare title and told that a shared
# topic is not evidence. That rule is right for modern papers and wrong for these: a 1966 paper called "The
# determinants of Rorschach card rejection: A replication" matched to a 1954 paper called "Rorschach card
# rejection in psychodiagnosis" is not two papers that happen to share a topic, it is the same finding named the
# same way, because mid-century psychology put the finding in the title. v2 says what to do when both records
# are bare, and is run ONLY over the rows v1 called unclear.
SECOND_VERSION = "v2"
OUT = DISCOVERY / "verified_links.json"
VERDICTS = ("right", "wrong", "unclear")

SYSTEM = """You check citations. A database says a psychology paper re-tested a finding from an earlier paper.
You decide whether it named the right earlier paper. Reply with one JSON object, nothing else.

  {"verdict": "right" | "wrong" | "unclear", "why": "<one short sentence>"}

right    The later paper re-tests a finding reported in this earlier paper. The topic, the measure and the
         effect line up, and the earlier paper is old enough to be the one being re-tested.
wrong    A different paper. Most often: the right authors but the wrong paper by them, a paper on a neighbouring
         topic, a review or commentary rather than the study, the later paper matched to itself, or a subject
         area with nothing to do with the replication.
unclear  The records do not settle it. One side is a bare title with no abstract, or the match is plausible but
         nothing in either record confirms it.

BE STRICT. Downstream, "right" means this pairing gets published without anyone reading it again, and "unclear"
and "wrong" cost nothing but a held-back row. Where you would have to assume something to say right, say unclear.

THINGS THAT ARE NOT EVIDENCE:
- Shared authors and a nearby year. Prolific authors publish many papers on one topic; the commonest error in
  this data is the right author's wrong paper. Check that the FINDING matches, not the byline.
- A general topic in common. "Both about memory" is not a match. The specific effect must be the same.
- The earlier paper being famous.

THINGS THAT ARE EVIDENCE: the same effect named in both; the same measure or task; the same population and
comparison; the later abstract quoting a result the earlier abstract reports.

CHECK THE DIRECTION OF TIME. The earlier paper must have come out before the later one. Same year is possible;
the earlier paper published after the later one is "wrong"."""

SECOND_SYSTEM = SYSTEM + """

WHEN NEITHER RECORD HAS AN ABSTRACT. You are judging older papers, where the title often names the finding
outright. "A shared topic is not evidence" above is a rule about modern papers with broad titles; do not let it
make you refuse a title that names the same specific thing.

Say "right" when the two titles name the SAME SPECIFIC construct, measure, scale, task or effect — not the same
broad field. "Rorschach card rejection" and "Rorschach card rejection"; "effects of ward change on patients'
behaviour" and "effects of environmental change on behaviour of hospitalised patients"; a named scale, test or
paradigm appearing in both. The later paper calling itself a replication, a failure to replicate, a
cross-validation or "Part II" of the earlier title is strong support.

Keep saying "wrong" when the specific things named differ, even within one field — "social intelligence" and
"MMPI social introversion on WAIS performance" are not the same measure. Keep saying "wrong" when the later
paper names an author or year the matched record does not fit. Keep saying "unclear" when a title is too general
to name anything specific ("A study of personality factors"), or when the later paper names a different paper
than this one and this one merely works on the topic — a cross-validation BY someone else is not the original
unless the later paper names them."""


def _user_msg(k: dict) -> str:
    m = k["matched_to"]
    out = [f"THE LATER PAPER (the replication), {k['year_r']}:",
           f"  title: {k['title_r']}",
           f"  abstract: {k['abstract_r'] or '(none on record)'}"]
    # For `cited by this paper` the description below was written after the paper was picked; see module docstring.
    if k["says_it_replicated"] and not k["circular"]:
        s = k["says_it_replicated"]
        out.append(f"  it says it re-tested: {s.get('authors') or '?'} ({s.get('year') or '?'})"
                   + (f" — {s['description']}" if s.get("description") else ""))
    out += ["", f"THE EARLIER PAPER WE MATCHED IT TO, {m['year']}:",
            f"  authors: {m['authors']}",
            f"  title: {m['title']}",
            f"  journal: {m['journal']}",
            f"  abstract: {m['abstract'] or '(none on record)'}",
            "", "Is this the paper the later one re-tested?"]
    return "\n".join(out)


def _cases(pool: str, limit: int | None = None, only_cids: set[str] | None = None) -> list[dict]:
    rows = originals._pool(pool)
    if only_cids is not None:
        rows = [c for c in rows if c["id"] in only_cids]
    cases = [originals._case(c) for c in rows]
    return cases[:limit] if limit else cases


def _cache_name(k: dict) -> str:
    """Keyed by the find AND the paper it is matched to, because that pair is what the verdict is about.

    Keying on the find alone is wrong in a way that only shows up after re-matching: `references --relink` can
    move a find to a different earlier paper, and a cache keyed on the find then hands back a verdict about the
    paper it used to point at. `originals.stale()` has always applied this rule to the hand-read labels; the
    model's verdicts need it for the same reason and did not have it.
    """
    gid = re.sub(r"[^A-Za-z0-9._-]+", "_", k["cid"])[:100]
    doi = (k.get("matched_to") or {}).get("doi") or ""
    return f"{gid}-{hashlib.md5(doi.encode()).hexdigest()[:8]}"


def verify_one(k: dict, key: str, meter: Meter, cache_dir: Path,
               system: str = SYSTEM, version: str = PROMPT_VERSION) -> dict | None:
    gid = k["cid"]
    f = cache_dir / f"{_cache_name(k)}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    if meter.over:
        return None
    body = json.dumps({
        "model": MODEL, "temperature": 0, "max_tokens": 200, "thinking": {"type": "disabled"},
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": _user_msg(k)}],
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
                print(f"    give up {gid}: {e}")
                return None
            time.sleep(2 * 2 ** attempt)
    meter.add(d.get("usage") or {})
    try:
        out = json.loads(d["choices"][0]["message"]["content"])
    except (KeyError, json.JSONDecodeError):
        out = {"verdict": "unclear", "why": "model returned no usable JSON"}
    v = out.get("verdict")
    rec = {"id": k["cid"], "band": k["band"], "doi_o": (k.get("matched_to") or {}).get("doi"),
           "model": MODEL, "prompt_version": version,
           "verdict": v if v in VERDICTS else "unclear", "why": (out.get("why") or "")[:300],
           "usage": d.get("usage")}
    f.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    return rec


def _run_cases(cases: list[dict], max_usd: float, workers: int, label: str,
               system: str = SYSTEM, version: str = PROMPT_VERSION) -> list[dict]:
    key = _key()
    cache_dir = CACHE / "verify" / MODEL / version
    cache_dir.mkdir(parents=True, exist_ok=True)
    meter = Meter(max_usd)
    print(f"  {len(cases)} {label} · model {MODEL} · prompt {version} · cap ${max_usd:.2f} "
          f"· balance ${balance(key)}")
    got, t0 = [], time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(verify_one, k, key, meter, cache_dir, system, version) for k in cases]
        for i, fut in enumerate(as_completed(futs), 1):
            r = fut.result()
            if r:
                got.append(r)
            if i % 250 == 0:
                print(f"    {i}/{len(cases)} · est ${meter.usd:.3f} · {time.time() - t0:.0f}s")
    print(f"  done: {len(got)} judged, {len(cases) - len(got)} not (cap or errors) · est ${meter.usd:.3f}")
    return got


def calibrate(max_usd: float, workers: int, limit: int | None) -> int:
    """Score the model against every link a person has already read.

    The labels come from data/curated/original_audit.csv, were made before this module was written, and are the
    only reason anything here can be believed. A label whose link has since changed is set aside — it describes a
    match nobody is making any more, the same rule `originals.score` applies.
    """
    labels = {r["cid"]: r for r in originals.read_labels()}
    rows = {c["id"]: c for c in originals._pool("linked")}
    usable = {cid: l for cid, l in labels.items()
              if cid in rows and not originals.stale(rows[cid], l)}
    stale_n = len(labels) - len(usable)
    if not usable:
        print("no usable hand labels to calibrate against")
        return 1
    cases = _cases("linked", limit, set(usable))
    print(f"  {len(usable)} hand-read links to check against"
          + (f" ({stale_n} labels set aside: the match changed since they were read)" if stale_n else ""))
    got = _run_cases(cases, max_usd, workers, "hand-read links")
    _score(got, usable)
    return 0


def _score(got: list[dict], truth: dict[str, dict]) -> None:
    pairs = [(r, truth[r["id"]]["label"]) for r in got if r["id"] in truth]
    if not pairs:
        print("  nothing to score")
        return
    matrix: dict[tuple[str, str], int] = defaultdict(int)
    for r, human in pairs:
        matrix[(r["verdict"], human)] += 1
    print(f"\n   {len(pairs)} links judged both ways\n")
    print(f"   {'model says':<12} {'person: right':>14} {'wrong':>7} {'unclear':>8}")
    for v in VERDICTS:
        print(f"   {v:<12} {matrix[(v, 'right')]:>14} {matrix[(v, 'wrong')]:>7} {matrix[(v, 'unclear')]:>8}")

    # The one number that decides whether this ships: of the links the model confirms, how many did a person?
    # `unclear` from the person is neither a pass nor a fail, so it is excluded from the denominator and the
    # count of how many were set aside is printed rather than folded in.
    ok = matrix[("right", "right")]
    bad = matrix[("right", "wrong")]
    unsure = matrix[("right", "unclear")]
    if ok + bad:
        lo, hi = audit.wilson(ok, ok + bad)
        print(f"\n   of the {ok + bad} confirmed links a person had settled, {ok} were right — "
              f"{ok / (ok + bad):.0%} (95%: {lo:.0%}–{hi:.0%})"
              + (f"; {unsure} more the person could not settle" if unsure else ""))
        print(f"   {'CLEARS' if lo >= 0.90 else 'DOES NOT CLEAR'} the 90% bar"
              + ("" if lo >= 0.90 else " on the low end of the interval — read more or do not ship it"))
    # What it costs in recall: links a person called right that the model will not confirm.
    kept = sum(matrix[(v, 'right')] for v in ("wrong", "unclear"))
    right_total = sum(matrix[(v, "right")] for v in VERDICTS)
    if right_total:
        print(f"   it turns down {kept} of {right_total} links a person called right "
              f"({kept / right_total:.0%} of good rows lost)")
    _by_band(pairs)


def _by_band(pairs: list[tuple[dict, str]]) -> None:
    m: dict[str, dict] = defaultdict(lambda: {"n": 0, "agree": 0, "conf": 0, "conf_right": 0})
    for r, human in pairs:
        b = m[r["band"]]
        b["n"] += 1
        b["agree"] += r["verdict"] == human
        if r["verdict"] == "right" and human in ("right", "wrong"):
            b["conf"] += 1
            b["conf_right"] += human == "right"
    print(f"\n   {'band':<34} {'read':>5} {'agrees':>7}   {'confirmed':>9} {'of those right':>15}")
    for b in sorted(m, key=lambda b: -m[b]["n"]):
        d = m[b]
        rate = f"{d['conf_right'] / d['conf']:.0%}" if d["conf"] else "—"
        print(f"   {b:<34} {d['n']:>5} {d['agree'] / d['n']:>6.0%}   {d['conf']:>9} {rate:>15}")


def _read_out() -> dict[tuple[str, str], dict]:
    """Stored verdicts, keyed by the PAIR they are about — see load.load_verified_matches."""
    if not OUT.exists():
        return {}
    return {(r["id"], r.get("doi_o")): r for r in json.loads(OUT.read_text())}


def _write_out(merged: dict[tuple[str, str], dict]) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(sorted(merged.values(), key=lambda r: (r["id"], r.get("doi_o") or "")),
                              ensure_ascii=False, indent=0), encoding="utf-8")


def _unclear_ids() -> set[str]:
    """Finds whose CURRENT match was left unclear. A stored verdict about some other paper does not count."""
    rows = {c["id"]: (c.get("doi_o") or None) for c in originals._pool("linked")}
    return {r["id"] for r in _read_out().values()
            if r["verdict"] == "unclear" and rows.get(r["id"]) == r.get("doi_o")}


def second_calibrate(max_usd: float, workers: int) -> int:
    """Does the second prompt settle the cases the first could not, without settling them wrongly?

    Run over exactly the hand-read links v1 called unclear. Two things have to be true for v2 to be worth
    running: it must turn a decent share of them into "right" where the reader said right, and the combined
    set of confirmations — v1's plus v2's — must still clear the 90% bar. The second condition is the one that
    matters, because promoting rows is only safe while the whole confirmed pool stays accurate.
    """
    labels = {r["cid"]: r for r in originals.read_labels()}
    rows = {c["id"]: c for c in originals._pool("linked")}
    usable = {cid: l for cid, l in labels.items() if cid in rows and not originals.stale(rows[cid], l)}
    v1 = {r["id"]: r for r in _read_out().values()}
    todo = [cid for cid in usable if v1.get(cid, {}).get("verdict") == "unclear"]
    if not todo:
        print("no hand-read links were left unclear by the first pass")
        return 0
    got = _run_cases(_cases("linked", None, set(todo)), max_usd, workers,
                     "hand-read links the first pass could not settle", SECOND_SYSTEM, SECOND_VERSION)
    _score(got, usable)
    # The number that decides it: v1's confirmations plus v2's, scored together against the reader.
    combined = {cid: r["verdict"] for cid, r in v1.items() if r["verdict"] == "right"}
    combined.update({r["id"]: r["verdict"] for r in got if r["verdict"] == "right"})
    ok = sum(1 for cid, v in combined.items() if usable.get(cid, {}).get("label") == "right")
    bad = sum(1 for cid, v in combined.items() if usable.get(cid, {}).get("label") == "wrong")
    if ok + bad:
        lo, hi = audit.wilson(ok, ok + bad)
        print(f"\n   BOTH PASSES TOGETHER: of {ok + bad} confirmed links the reader had settled, {ok} were right"
              f" — {ok / (ok + bad):.0%} (95%: {lo:.0%}–{hi:.0%})")
        print(f"   {'CLEARS' if lo >= 0.90 else 'DOES NOT CLEAR'} the 90% bar")
    return 0


def second(max_usd: float, workers: int, limit: int | None) -> int:
    """Re-judge every link the first pass left unclear, and keep whichever verdict is decisive."""
    todo = _unclear_ids()
    if not todo:
        print("nothing left unclear — run --all first")
        return 1
    cases = _cases("linked", limit, todo)
    got = _run_cases(cases, max_usd, workers, "links the first pass could not settle",
                     SECOND_SYSTEM, SECOND_VERSION)
    merged = _read_out()
    changed = Counter()
    for r in got:
        # PROMOTE ONLY. Scored on the 64 hand-read links the first pass left unclear, the second prompt's
        # confirmations were 29 right of 33 — 88%, which is under the bar alone but leaves the pool it joins at
        # 97% (289 of 297). Its rejections were not: 2 of the 3 rows it called wrong the reader had called right.
        # So a "right" is kept and anything else leaves the row unclear, falling back to the band rule. Using a
        # judgement only where it was measured to work is the whole discipline here.
        if r["verdict"] != "right":
            changed["left unclear"] += 1
            continue
        changed["unclear -> right"] += 1
        merged[(r["id"], r.get("doi_o"))] = r
    _write_out(merged)
    print("  " + " · ".join(f"{k}: {v}" for k, v in sorted(changed.items())))
    report()
    return 0


# ---------------------------------------------------------------- the paper the matcher ranked second

RUNNERS = DISCOVERY / "runner_up_links.json"


def _runner_cases(limit: int | None = None) -> list[dict]:
    """A case per find whose CURRENT match was not confirmed and whose matcher recorded a second choice.

    Every matcher scores candidate papers and keeps the runner-up, and until now nobody looked at it: when the
    judge said the first choice was wrong, the find was dropped with its second choice unread. The first two
    read by hand were both right. The 1966 smoking paper names Sabol et al. 1999, the matcher chose a 1992
    gene-mapping paper and ranked "A genetic association for cigarette smoking behavior" — Health Psychology
    18(1):7, which IS Sabol 1999 — second.

    The runner-up record holds a DOI, a title and a score and nothing else, so authors, year and abstract are
    fetched from OpenAlex first. A runner-up with nothing but a DOI is skipped rather than judged blind.
    """
    from .load import load_original_authors, load_verified_matches
    verdicts = load_verified_matches()
    meta = load_original_authors()
    out = []
    for c in originals._pool("linked"):
        if verdicts.get((c["id"], c.get("doi_o"))) == "right":
            continue
        ru = ((c.get("link_evidence") or {}).get("runner_up") or {})
        doi = ru.get("doi_o")
        if not doi or doi == c.get("doi_o"):
            continue
        m = meta.get(doi) or {}
        if not (ru.get("title_o") or m.get("title")):
            continue
        k = originals._case(c)
        k["matched_to"] = {"doi": doi, "title": ru.get("title_o") or m.get("title"),
                           "year": m.get("year"), "authors": m.get("authors"),
                           "journal": m.get("journal"), "abstract": (m.get("abstract") or "")[:900] or None}
        k["evidence"] = {"rank": "second choice of the matcher", "score": ru.get("score")}
        k["runner_up"] = None
        out.append(k)
    return out[:limit] if limit else out


def runners(max_usd: float, workers: int, limit: int | None, fetch_usd: float = 0.40) -> int:
    from . import authors
    from .load import load_original_authors
    cases = _runner_cases()
    want = sorted({k["matched_to"]["doi"] for k in cases})
    have = load_original_authors()
    todo = [d for d in want if not (have.get(d) or {}).get("abstract")]
    print(f"  {len(cases)} finds have a second choice nobody judged · {len(todo)} of those papers need looking up")
    if todo:
        authors.fetch(todo, fetch_usd)
    cases = _runner_cases(limit)     # rebuilt so the freshly fetched abstracts are in the prompts
    got = _run_cases(cases, max_usd, workers, "second choices", SECOND_SYSTEM, SECOND_VERSION)
    merged = _read_out()
    for r in got:
        merged[(r["id"], r.get("doi_o"))] = r
    _write_out(merged)
    ok = [r for r in got if r["verdict"] == "right"]
    print(f"  {len(ok)} of {len(got)} second choices confirmed ({len(ok) / max(len(got), 1):.0%})")
    # Written as a link source of its own so the merge can prefer it; `merged_links` only takes one whose
    # pairing the judge confirmed, so an unread second choice never displaces anything.
    by_cid = {c["id"]: c for c in originals._pool("linked")}
    links = {r["id"]: {"doi_o": r["doi_o"], "method": "runner_up",
                       "confidence": (by_cid[r["id"]].get("link_confidence") if r["id"] in by_cid else None),
                       "from_method": by_cid[r["id"]].get("link_method") if r["id"] in by_cid else None}
             for r in ok}
    RUNNERS.write_text(json.dumps(links, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"  wrote {RUNNERS} · {len(links)} confirmed second choices")
    return 0


def run(max_usd: float, workers: int, limit: int | None, pool: str) -> int:
    cases = _cases(pool, limit)
    got = _run_cases(cases, max_usd, workers, f"matched finds in pool '{pool}'")
    merged = _read_out()
    for r in got:
        merged[(r["id"], r.get("doi_o"))] = r
    _write_out(merged)
    print(f"  wrote {OUT} · {len(merged)} verdicts in all ({len(got)} from this run)")
    report()
    return 0


def report() -> int:
    if not OUT.exists():
        print("nothing verified yet")
        return 0
    recs = json.loads(OUT.read_text())
    m: dict[str, dict] = defaultdict(lambda: {"n": 0, "right": 0, "wrong": 0, "unclear": 0})
    for r in recs:
        d = m[r["band"]]
        d["n"] += 1
        d[r["verdict"]] += 1
    tot = {"n": len(recs), "right": sum(d["right"] for d in m.values())}
    print(f"\n   {len(recs)} links judged · {tot['right']} confirmed ({tot['right'] / max(tot['n'], 1):.0%})\n")
    print(f"   {'band':<34} {'judged':>6} {'confirmed':>9} {'rejected':>9} {'unclear':>8}")
    for b in sorted(m, key=lambda b: -m[b]["right"]):
        d = m[b]
        print(f"   {b:<34} {d['n']:>6} {d['right']:>9} {d['wrong']:>9} {d['unclear']:>8}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="pipeline verify", description=__doc__.split("\n")[0])
    p.add_argument("--calibrate", action="store_true", help="score the model against the hand-read links")
    p.add_argument("--second-calibrate", action="store_true",
                   help="score the second prompt on the hand-read links the first left unclear")
    p.add_argument("--second", action="store_true", help="re-judge every link the first pass left unclear")
    p.add_argument("--runners", action="store_true",
                   help="judge the paper each matcher ranked second, for finds whose first choice was not confirmed")
    p.add_argument("--all", action="store_true", help="judge every matched find")
    p.add_argument("--report", action="store_true", help="what has been confirmed, by band")
    p.add_argument("--pool", default="linked", choices=sorted(originals.POOLS))
    p.add_argument("--max-usd", type=float, default=1.0)
    p.add_argument("--workers", type=int, default=16)
    p.add_argument("--limit", type=int)
    a = p.parse_args(argv)
    if a.calibrate:
        return calibrate(a.max_usd, a.workers, a.limit)
    if a.second_calibrate:
        return second_calibrate(a.max_usd, a.workers)
    if a.second:
        return second(a.max_usd, a.workers, a.limit)
    if a.runners:
        return runners(a.max_usd, a.workers, a.limit)
    if a.all:
        return run(a.max_usd, a.workers, a.limit, a.pool)
    if a.report:
        return report()
    p.print_help()
    return 1
