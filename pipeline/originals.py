"""Was the find matched to the right earlier paper?

The 65-case audit of 2026-09-19 (docs/LINK_AUDIT_20260919.md) read five link bands and found them ranging from
96% down to 36%, which is why effect and finding pages now show only the three best. It left most of the pool
unmeasured: of the 1,442 rows that could become a game card, **694 sit in bands nobody has read a single case
from** — `reference_scan` low, `openalex_author_year` low — and the two largest measured ones rest on 11 and 46
reads. A card needs a right original twice over: the reveal names it, and the claim would be written from its
abstract. A wrong original is a wrong card no matter how well the verdict was read.

This is the same instrument as `pipeline outcomes`, pointed at the link instead of the verdict: a deterministic
stratified draw, one case at a time, labels accumulating in data/curated/original_audit.csv keyed by candidate id.

    python -m pipeline originals --sample 40                            # spread over every band
    python -m pipeline originals --sample 30 --band reference_scan/low  # one band
    python -m pipeline originals --record < labels.tsv                  # cid<TAB>label<TAB>note
    python -m pipeline originals --score

LABELS (does this paper re-test a finding from the paper it was matched to?):
    right     yes — the replication's own account of what it re-tested fits this paper
    wrong     no — a different paper, or the same paper as itself, or nothing to do with it
    unclear   the records do not settle it: a bare title on one side, or a plausible but unconfirmable match

One warning the reader has to carry. For links whose method is `cited by this paper`, the model wrote
`original_named.description` *after* choosing which cited work it meant, so that description agreeing with the
chosen paper's title proves nothing. Judge that band from the replication's own abstract against the original's
title and abstract, and nothing else. The sampler prints the warning on those cases.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict

from . import audit

LABELS = audit.CURATED / "original_audit.csv"
VALID = ("right", "wrong", "unclear")
CIRCULAR = "cited by this paper"      # the model's description of the original was written after it picked one

POOLS = {
    "card": ("psychology finds with a binary verdict and a linked original — the game-card pool",
             lambda c: c.get("field") == "psychology" and c.get("outcome") in ("successful", "failed") and c.get("doi_o")),
    "page": ("the links effect and finding pages are allowed to show",
             lambda c: c.get("doi_o") and _shows(c)),
    # What a reader actually sees. `page` is the set of bands allowed through; this is the rows that get through
    # them, which is a narrower and different population — the original has to be one the wiki already holds and
    # the find has to come from the high search tier. Measure the shipped rows, not the band they belong to.
    "shown": ("the rows that actually appear in a 'not in the record yet' box on a page",
              lambda c: c.get("doi_o") and c.get("original_in_wiki") and c.get("search_tier") == "high"
              and _shows(c)),
    "linked": ("every psychology find matched to an original, verdict or not",
               lambda c: c.get("field") == "psychology" and c.get("doi_o")),
}


def _shows(c: dict) -> bool:
    """Whether a page may show this link — asked of queue.py rather than copied, so the two cannot drift apart.

    This used to be a set of bands. It is now a question about the row, because `pipeline verify` judges rows.
    That matters to the audit and not only to the build: a pool defined by band and a pool defined per row are
    different sets of rows, and a measurement made on one says nothing about the other.
    """
    from .queue import _link_trusted
    return _link_trusted(c)


def band(c: dict) -> str:
    return f"{c.get('link_method')}/{c.get('link_confidence')}"


def _pool(name: str, rows: list[dict] | None = None) -> list[dict]:
    return audit.pool(POOLS, name, rows)


def stale(c: dict, label: dict) -> bool:
    """Does this label still describe the match that is actually in force?

    A label says "this find was matched to the right earlier paper" about the link that existed when somebody
    read it. Re-running the matchers can replace that link with a different paper, and then the label is about
    a match nobody is making any more — counting it is the same error as measuring a band over rows it was
    never computed on. The band recorded with the label is the tell: if the row has moved, the label has to be
    re-read before it means anything.

    Renaming a band is NOT a changed match: when `cited by this paper` stopped calling itself "high" and became
    "unscored", 36 labels still carried the old name and were being set aside as stale though nothing about the
    link had moved. A rename has to migrate the labels with it.

    The band is too coarse to be the only test, which took until 2026-09-22 to show. Completing the reference
    titles moved many rows to a different paper WITHIN `reference_scan/medium`, so their labels stayed live and
    described matches nobody was making: the band read 81% on them and 95% on twenty fresh reads. Labels now
    record the paper as well, and one written before that date has the column empty and is taken at its word —
    it is the best that can be said about it.
    """
    if label.get("matched_to") and label["matched_to"] != (c.get("doi_o") or ""):
        return True       # read against a different paper; the band it sat in is beside the point
    return label.get("recorded") not in (None, "", band(c))


def read_labels() -> list[dict]:
    return audit.read_labels(LABELS)


_ABSTRACTS: dict[str, str] | None = None


def _abstract(cid: str) -> str | None:
    global _ABSTRACTS
    if _ABSTRACTS is None:
        from .load import load_triaged
        _ABSTRACTS = {r["cid"]: r.get("abstract") for r in load_triaged() if r.get("abstract")}
    return _ABSTRACTS.get(cid)


def _case(c: dict) -> dict:
    named = c.get("original_named") or {}
    ev = c.get("link_evidence") or {}
    return {
        "cid": c["id"], "band": band(c),
        "title_r": c.get("title_r"), "year_r": c.get("year_r"),
        "abstract_r": _abstract(c["id"]) or c.get("abstract"),
        "says_it_replicated": {k: named.get(k) for k in ("authors", "year", "description") if named.get(k)} or None,
        "circular": c.get("link_method") == CIRCULAR,
        "matched_to": {"doi": c.get("doi_o"), "title": c.get("title_o"), "year": c.get("year_o"),
                       "authors": c.get("authors_o"), "journal": c.get("journal_o"),
                       "abstract": (c.get("abstract_o") or "")[:900] or None},
        "evidence": {k: ev[k] for k in ("score", "text_sim", "authors_matched", "year_delta", "margin",
                                        "n_references") if k in ev} or None,
        "runner_up": (ev.get("runner_up") or {}).get("title_o"),
    }


def sample(pool: str, n: int, seed: str, as_json: bool, only: str | None) -> int:
    rows = _pool(pool)
    done = {r["cid"] for r in read_labels()}
    picked = audit.draw(rows, done, n, seed, band, only)
    if as_json:
        print(json.dumps([_case(c) for c in picked], indent=1, ensure_ascii=False))
        return 0
    print(f"# {len(picked)} unlabelled cases from pool '{pool}' ({POOLS[pool][0]}), seed {seed!r}\n"
          f"# {len(rows)} rows in the pool, {len(done)} already labelled\n")
    for i, c in enumerate(picked, 1):
        k = _case(c)
        print(f"--- {i}. {k['cid']}   BAND: {k['band']}")
        print(f"    replication: {k['title_r']} ({k['year_r']})")
        print(f"    abstract:    {k['abstract_r']}")
        if k["circular"]:
            print("    !! the model wrote this description AFTER picking the paper — it is not evidence")
        print(f"    says it replicated: {k['says_it_replicated']}")
        m = k["matched_to"]
        print(f"    matched to:  {m['authors']} ({m['year']}) {m['title']!r} — {m['journal']}")
        if m["abstract"]:
            print(f"    its abstract: {m['abstract']}")
        print(f"    evidence: {k['evidence']}   runner-up: {k['runner_up']!r}\n")
    return 0


def record(pool: str, text: str, by: str = "claude-opus-5") -> int:
    audit.record(LABELS, _pool(pool), pool, band, text, VALID, by)
    return 0


def score(pool: str | None) -> int:
    labels = {r["cid"]: r for r in read_labels()}
    if not labels:
        print("no labels yet — run --sample, read the cases, and record them")
        return 0
    members = {name: {c["id"] for c in _pool(name)} for name in POOLS}
    for p in (sorted(POOLS) if pool is None else [pool]):
        rows = _pool(p)
        read = [(c, labels[c["id"]]) for c in rows if c["id"] in labels and not stale(c, labels[c["id"]])]
        dropped = sum(1 for c in rows if c["id"] in labels and stale(c, labels[c["id"]]))
        if not read:
            continue
        print(f"\n## pool '{p}' — {POOLS[p][0]}")
        print(f"   {len(read)} of {len(rows)} rows read by hand"
              + (f" ({dropped} labels set aside: the match changed since they were read)" if dropped else "") + "\n")
        matrix: dict[str, dict] = defaultdict(lambda: {"n": 0, "right": 0, "wrong": 0, "unclear": 0, "pool": 0})
        for c in rows:
            matrix[band(c)]["pool"] += 1
        for c, l in read:
            m = matrix[band(c)]
            m["n"] += 1
            m[l["label"]] += 1
        order = sorted(matrix, key=lambda b: -matrix[b]["pool"])
        print(f"   {'band':<34} {'in pool':>7} {'read':>5} {'right':>6}  {'precision':>9}  95% interval   unclear")
        for b in order:
            m = matrix[b]
            if not m["n"]:
                print(f"   {b:<34} {m['pool']:>7} {'—':>5}")
                continue
            lo, hi = audit.wilson(m["right"], m["n"])
            print(f"   {b:<34} {m['pool']:>7} {m['n']:>5} {m['right']:>6}  {m['right'] / m['n']:>8.0%}   "
                  f"{lo:.0%}–{hi:.0%}   {m['unclear']}")
        audit.unreached(rows, labels, members, band)
        _shippable(matrix)
    return 0


def _shippable(matrix: dict[str, dict]) -> None:
    """How much of this pool sits in a band that has been read and held up.

    The threshold is not a house style: a card whose original is wrong is wrong in the one place a player looks
    after answering. 90% read-right is the line the pages already use, and it is stated here rather than assumed.
    """
    good = {b: m for b, m in matrix.items() if m["n"] and m["right"] / m["n"] >= 0.9}
    read_any = {b: m for b, m in matrix.items() if m["n"]}
    total = sum(m["pool"] for m in matrix.values())
    unread = sum(m["pool"] for b, m in matrix.items() if not m["n"])
    if not read_any or not total:
        return
    print(f"\n   {sum(m['pool'] for m in good.values())} of {total} rows sit in a band read at 90% or better"
          f"; {unread} sit in a band nobody has read")


def run(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pipeline originals", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", type=int, metavar="N", help="print N unlabelled cases to read")
    ap.add_argument("--pool", choices=sorted(POOLS), default="card", help="which rows to draw from")
    ap.add_argument("--band", help="draw only this link band, e.g. reference_scan/low")
    ap.add_argument("--seed", default="2026-09-21", help="the draw is deterministic given this")
    ap.add_argument("--json", action="store_true", help="print the sample as JSON instead of text")
    ap.add_argument("--by", default="claude-opus-5", help="who read these cases; recorded with each label")
    ap.add_argument("--record", action="store_true",
                    help="read 'cid<TAB>label<TAB>note' lines from stdin and add them to the label file")
    ap.add_argument("--score", action="store_true", help="report accuracy from the labels recorded so far")
    ap.add_argument("--all-pools", action="store_true", help="score every pool, not just --pool")
    a = ap.parse_args(argv if argv is not None else sys.argv[1:])
    if a.record:
        return record(a.pool, sys.stdin.read(), a.by)
    if a.sample:
        return sample(a.pool, a.sample, a.seed, a.json, a.band)
    if a.score:
        return score(None if a.all_pools else a.pool)
    ap.print_help()
    return 0


def audit_summary(pool: str, candidates: list[dict]) -> dict | None:
    """The hand-read link audit as numbers a page can print, so no page states an accuracy the labels do not.

    Returns per-band counts plus a pooled figure over the bands in that pool, and None when nothing in the pool
    has been read. `unclear` labels stay in the denominator: a link a careful reader cannot confirm is not a link
    a reader should be told is right.
    """
    labels = {r["cid"]: r for r in read_labels()}
    rows = _pool(pool, candidates)
    read = [(c, labels[c["id"]]) for c in rows if c["id"] in labels and not stale(c, labels[c["id"]])]
    if not read:
        return None
    by: dict[str, dict] = defaultdict(lambda: {"n": 0, "right": 0, "in_pool": 0})
    for c in rows:
        by[band(c)]["in_pool"] += 1
    for c, l in read:
        by[band(c)]["n"] += 1
        by[band(c)]["right"] += l["label"] == "right"
    n = sum(b["n"] for b in by.values())
    k = sum(b["right"] for b in by.values())
    return {"n_read": n, "right": k, "n_pool": len(rows),
            "share": round(k / n, 3) if n else None,
            "unread_bands": sorted(b for b, v in by.items() if v["in_pool"] and not v["n"]),
            "by_band": {b: dict(v, precision=round(v["right"] / v["n"], 3)) for b, v in sorted(by.items()) if v["n"]}}
