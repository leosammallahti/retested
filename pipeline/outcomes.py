"""Did the model read the replication's outcome correctly?

Every other accuracy figure in this project is about *linking* — whether a find was matched to the right original
(docs/LINK_AUDIT_20260919.md). This one is about the verdict itself, which is the error that decides whether a game
card scores a player right or wrong.

It is measured the only way anything here is measured: by reading cases one at a time. `--sample` draws a
deterministic stratified sample and prints each case as the replication's own full abstract — not the
700-character copy the queue carries for the browser, which usually stops before the results sentence — plus the
quote the model rested its verdict on. A person, or a session, reads them and writes a label back through
`--record`. `--score` turns the labels into a confusion matrix, per-verdict precision with Wilson intervals, the
base rate the pool would have if every verdict were read the way the labels were, and the same rate at the grain
the game deals in.

The labels live in data/curated/outcome_audit.csv and are keyed by candidate id, so they survive rebuilds and
accumulate: a later session samples what is not labelled yet and the interval tightens. The file records which pool
each row was drawn from, because an accuracy figure means nothing without the population it was computed over —
this project has twice been sent down a dead end by an intermediate built from the wrong rows.

    python -m pipeline outcomes --sample 40                      # print unlabelled cases to read
    python -m pipeline outcomes --sample 24 --verdict mixed      # one stratum only
    python -m pipeline outcomes --record < labels.tsv            # cid<TAB>label<TAB>note, one per line
    python -m pipeline outcomes --score --all-pools              # what the labels say so far

LABELS (what the replication itself reports about the original finding):
    successful      the original effect was found again
    failed          it was not
    mixed           partly: some outcomes held, others did not
    not_established the abstract does not settle it — no comparison with the original, results not reported,
                    or the paper is not a replication at all. For a card this is as unusable as a wrong answer.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import date

from .load import ROOT

LABELS = ROOT / "data" / "curated" / "outcome_audit.csv"
BUILD = ROOT / "data" / "build" / "candidates.json"
COLUMNS = ["cid", "pool", "recorded", "label", "note", "labelled_by", "labelled_on"]
VERDICTS = ("successful", "failed", "mixed")          # what the model can say
VALID = VERDICTS + ("not_established",)               # what a reader can say back

# Which rows each pool is: stated plainly, because every figure below is only about the rows it was computed over.
POOLS = {
    "card": ("psychology finds with a binary verdict and a linked original — the game-card pool",
             lambda c: c.get("field") == "psychology" and c.get("outcome") in ("successful", "failed") and c.get("doi_o")),
    "page": ("card-pool rows whose link is good enough to appear on a page",
             lambda c: c.get("field") == "psychology" and c.get("outcome") in ("successful", "failed") and c.get("doi_o")
             and _page_grade(c)),
    # exactly what stats.uncounted() counts: a linked psychology find carrying any verdict, mixed included
    "uncounted": ("linked psychology finds carrying any verdict — the population behind /uncounted/",
                  lambda c: c.get("field") == "psychology" and c.get("outcome") and c.get("doi_o")),
}
PAGE_GRADE = {("library_author_year", "high"), ("library_author_year", "medium"), ("openalex_author_year", "high"),
              ("reference_scan", "high")}


def _wilson(k: int, n: int):
    from .stats import wilson
    return wilson(k, n)


def _page_grade(c: dict) -> bool:
    return (c.get("link_method"), c.get("link_confidence")) in PAGE_GRADE


def _pool(name: str, candidates: list[dict] | None = None) -> list[dict]:
    if candidates is None:
        if not BUILD.exists():
            raise SystemExit(f"{BUILD} is missing — run `python -m pipeline build` first")
        candidates = json.loads(BUILD.read_text(encoding="utf-8"))
    keep = POOLS[name][1]
    rows = [c for c in candidates
            if c.get("origin") == "retested_discovery" and c.get("group") == "replication" and keep(c)]
    rows.sort(key=lambda c: c["id"])
    return rows


def read_labels() -> list[dict]:
    if not LABELS.exists():
        return []
    with LABELS.open(encoding="utf-8", newline="") as fh:
        return [r for r in csv.DictReader(fh) if r.get("label")]


def write_labels(rows: list[dict]) -> None:
    LABELS.parent.mkdir(parents=True, exist_ok=True)
    with LABELS.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        for r in sorted(rows, key=lambda r: (r["pool"], r["cid"])):
            w.writerow({k: r.get(k, "") for k in COLUMNS})


def sample(pool: str, n: int, seed: str, as_json: bool, only: str | None = None) -> int:
    """A deterministic stratified draw of rows nobody has labelled yet.

    Stratified by the recorded verdict rather than drawn flat, because the question is whether "successful" and
    "failed" are equally trustworthy, and a flat draw of the card pool would spend 61% of the reading on one of them.
    """
    rows = _pool(pool)
    done = {r["cid"] for r in read_labels()}
    by_verdict: dict[str, list[dict]] = defaultdict(list)
    for c in rows:
        if c["id"] not in done and only in (None, c["outcome"]):
            by_verdict[c["outcome"]].append(c)
    per = max(1, n // max(1, len(by_verdict)))
    picked = []
    for verdict, group in sorted(by_verdict.items()):
        group.sort(key=lambda c: hashlib.md5(f"{seed}|{c['id']}".encode()).hexdigest())
        picked += group[:per]
    if as_json:
        print(json.dumps([_case(c, pool) for c in picked], indent=1, ensure_ascii=False))
        return 0
    print(f"# {len(picked)} unlabelled cases from pool '{pool}' ({POOLS[pool][0]}), seed {seed!r}\n"
          f"# {len(rows)} rows in the pool, {len(done)} already labelled\n")
    for i, c in enumerate(picked, 1):
        case = _case(c, pool)
        print(f"--- {i}. {case['cid']}   MODEL SAID: {case['recorded']}  (confidence {case['confidence']})")
        print(f"    title: {case['title_r']}")
        print(f"    quote: {case['quote']}")
        print(f"    abstract: {case['abstract']}")
        print(f"    replicating: {case['original']}\n")
    return 0


_ABSTRACTS: dict[str, str] | None = None


def _abstract(cid: str) -> str | None:
    """The whole abstract, from the triage file — not the 700-character copy the queue carries.

    The reader has to see what the model saw. A queue abstract is cut for the browser and the cut usually lands
    before the results sentence, which is the one sentence the verdict turns on.
    """
    global _ABSTRACTS
    if _ABSTRACTS is None:
        from .load import load_triaged
        _ABSTRACTS = {r["cid"]: r.get("abstract") for r in load_triaged() if r.get("abstract")}
    return _ABSTRACTS.get(cid)


def _case(c: dict, pool: str) -> dict:
    return {"cid": c["id"], "pool": pool, "recorded": c["outcome"], "confidence": c.get("outcome_confidence"),
            "title_r": c.get("title_r"), "quote": c.get("outcome_quote"),
            "abstract": _abstract(c["id"]) or c.get("abstract"),
            "original": (c.get("title_o") or (c.get("original_named") or {}).get("description")),
            "reason": c.get("screen_reason")}


def add(cid: str, pool: str, recorded: str, label: str, note: str, by: str) -> None:
    if label not in VALID:
        raise SystemExit(f"label must be one of {VALID}")
    rows = [r for r in read_labels() if r["cid"] != cid]
    rows.append({"cid": cid, "pool": pool, "recorded": recorded, "label": label, "note": note,
                 "labelled_by": by, "labelled_on": date.today().isoformat()})
    write_labels(rows)


def record(pool: str, text: str) -> int:
    """Take labels in bulk: one 'cid<TAB>label<TAB>note' line each, from a session that has just read them."""
    rows = {c["id"]: c for c in _pool(pool)}
    n = 0
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.rstrip("\n").split("\t")
        cid, label, note = (parts + ["", ""])[:3]
        if cid not in rows:
            raise SystemExit(f"{cid} is not in pool {pool!r} — label it against the pool it was drawn from")
        add(cid, pool, rows[cid]["outcome"], label, note, "claude-opus-5")
        n += 1
    print(f"recorded {n} labels in {LABELS}")
    return 0


def score(pool: str | None) -> int:
    """What the labels say, pool by pool.

    A label belongs to the row, not to the draw that produced it, so scoring a pool uses every label whose
    candidate is in that pool — the card-pool reads also measure those same rows inside the wider /uncounted/
    population. What they do not measure is the part of a pool no draw has ever reached, and that is printed
    explicitly rather than averaged away.
    """
    labels = {r["cid"]: r for r in read_labels()}
    if not labels:
        print("no labels yet — run --sample, read the cases, and record them")
        return 0
    members = {name: {c["id"] for c in _pool(name)} for name in POOLS}
    for p in (sorted(POOLS) if pool is None else [pool]):
        rows = _pool(p)
        here = [labels[c["id"]] for c in rows if c["id"] in labels]
        if not here:
            continue
        print(f"\n## pool '{p}' — {POOLS[p][0]}")
        print(f"   {len(here)} of {len(rows)} rows read by hand\n")
        matrix: dict[str, Counter] = defaultdict(Counter)
        for r in here:
            matrix[r["recorded"]][r["label"]] += 1
        print(f"   {'model said':<12} {'n':>4}  {'right':>6}  {'precision':>9}  95% interval     where the rest went")
        for recorded in sorted(matrix):
            c = matrix[recorded]
            n, k = sum(c.values()), c[recorded]
            lo, hi = _wilson(k, n) or (0.0, 1.0)
            rest = ", ".join(f"{v}× {kk}" for kk, v in c.most_common() if kk != recorded) or "—"
            print(f"   {recorded:<12} {n:>4}  {k:>6}  {k / n:>8.0%}   {lo:.0%}–{hi:.0%}        {rest}")
        _unreached(p, rows, labels, members)
        if p in ("card", "page"):                    # only these rows can become a card
            _card_safety(matrix)
        _corrected_rate(p, matrix)
        if p == "card":
            _deck_rate(rows, matrix)
    return 0


def _unreached(pool: str, rows: list[dict], labels: dict[str, dict], members: dict[str, set]) -> None:
    """Rows in this pool that no draw has sampled from, named by verdict.

    The card-pool draw can say nothing about a find with no linked original, because it never had one in the urn.
    Borrowing its precision for those rows would be the same error as `link --check`: a number measured on the
    easy half and quoted over the whole.
    """
    drawn_from: dict[str, set[str]] = defaultdict(set)
    for r in labels.values():
        drawn_from[r["recorded"]].add(r["pool"])
    gaps = Counter()
    for c in rows:
        pools = drawn_from.get(c["outcome"])
        if pools and not any(c["id"] in members[q] for q in pools):
            gaps[c["outcome"]] += 1
    if gaps:
        print("   not reached by any draw: " + ", ".join(f"{v} rows called '{k}'" for k, v in sorted(gaps.items())))


def _card_safety(matrix: dict[str, Counter]) -> None:
    """How often a card built from one of these rows would score a player against the wrong answer.

    Only rows the model gave a binary verdict can become a card, so only those are counted. A verdict read as the
    opposite of the truth is the worst case; "mixed" and "not_established" are not wrong answers so much as
    questions with no binary answer, which should never have been a card at all.
    """
    binary = {r: c for r, c in matrix.items() if r in ("successful", "failed")}
    n = sum(sum(c.values()) for c in binary.values())
    if not n:
        return
    flipped = binary.get("successful", Counter())["failed"] + binary.get("failed", Counter())["successful"]
    unplayable = sum(c["mixed"] + c["not_established"] for c in binary.values())
    print(f"\n   as cards: {n - flipped - unplayable}/{n} sound, {flipped} would score the player backwards, "
          f"{unplayable} have no binary answer")


def _deck_rate(rows: list[dict], matrix: dict[str, Counter]) -> None:
    """The same correction at the grain the game actually deals in: one card per original study.

    game.py plays one original, not one find, and drops an original whose finds disagree — so the deck's base
    rate is not the pool's. The existing FORRT deck sits at 53% successful; whether these cards can be shuffled
    into it or must stay a deck of their own turns on this number and not on the row count.
    """
    by_original: dict[str, set] = defaultdict(set)
    for c in rows:
        by_original[c["doi_o"]].add(c["outcome"])
    deck = Counter(next(iter(v)) for v in by_original.values() if len(v) == 1)
    n = sum(deck.values())
    if not n:
        return
    est: Counter = Counter()
    for recorded, c in matrix.items():
        m = sum(c.values())
        for true_label, k in c.items():
            est[true_label] += deck[recorded] * k / m
    binary = est["successful"] + est["failed"]
    print(f"\n   at the deck's grain: {n} cards from {len(by_original)} originals "
          f"({len(by_original) - n} dropped for disagreeing finds), {deck['successful'] / n:.1%} successful"
          + (f"; corrected {est['successful'] / binary:.1%} of {binary:.0f}" if binary else ""))


def _corrected_rate(pool: str, matrix: dict[str, Counter]) -> None:
    """The pool's success rate as recorded, and as the labels say it would come out if every row were read.

    Reweighting, not guessing: each recorded verdict contributes its own measured mix of true verdicts. Rows the
    reading found to have no binary answer leave the denominator, which is why the corrected figure is a rate over
    a smaller pool than the raw one.

    It refuses to print a corrected figure while any recorded verdict in the pool is unread. That is not caution
    for its own sake: reweighting two of three strata and leaving the third at its recorded value is a number
    computed over rows that were never measured, which is the mistake this project has made twice.
    """
    raw = Counter(c["outcome"] for c in _pool(pool))
    n = sum(raw[v] for v in VERDICTS)
    if not n:
        return
    print(f"   success rate as recorded: {raw['successful'] / n:.1%} of {n}"
          + (f" ({raw['mixed']} of them 'mixed', counted in the denominator as the site counts them)" if raw["mixed"] else ""))
    unread = [v for v in VERDICTS if raw[v] and v not in matrix]
    if unread:
        print("   no corrected rate: " + ", ".join(f"{raw[v]} rows the model called '{v}'" for v in unread)
              + " have not been read, and correcting only the strata that have been is a figure over the wrong rows")
        return
    est: Counter = Counter()
    for recorded, c in matrix.items():
        m = sum(c.values())
        for true_label, k in c.items():
            est[true_label] += raw[recorded] * k / m
    denom = est["successful"] + est["failed"] + est["mixed"]
    if denom:
        print(f"   after correction:         {est['successful'] / denom:.1%} of an estimated {denom:.0f} "
              f"still carrying a verdict ({est['not_established']:.0f} would drop out)")
    print("   (the correction is only as good as the sample above; it moves as more rows are read)")


def run(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pipeline outcomes", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", type=int, metavar="N", help="print N unlabelled cases to read")
    ap.add_argument("--pool", choices=sorted(POOLS), default="card", help="which rows to draw from")
    ap.add_argument("--seed", default="2026-09-21", help="the draw is deterministic given this")
    ap.add_argument("--verdict", choices=["successful", "failed", "mixed"],
                    help="draw only rows the model gave this verdict")
    ap.add_argument("--json", action="store_true", help="print the sample as JSON instead of text")
    ap.add_argument("--record", action="store_true",
                    help="read 'cid<TAB>label<TAB>note' lines from stdin and add them to the label file")
    ap.add_argument("--score", action="store_true", help="report accuracy from the labels recorded so far")
    ap.add_argument("--all-pools", action="store_true", help="score every pool, not just --pool")
    a = ap.parse_args(argv if argv is not None else sys.argv[1:])
    if a.record:
        return record(a.pool, sys.stdin.read())
    if a.sample:
        return sample(a.pool, a.sample, a.seed, a.json, a.verdict)
    if a.score:
        return score(None if a.all_pools else a.pool)
    ap.print_help()
    return 0


def audit_summary(pool: str, candidates: list[dict]) -> dict | None:
    """The hand-read audit as numbers the site can print, so no page states an accuracy the label file does not.

    Returns None when nothing in this pool has been read. Every figure carries the count it came from; the
    corrected share is withheld unless every verdict in the pool has been read, for the reason given in
    _corrected_rate.
    """
    labels = {r["cid"]: r for r in read_labels()}
    rows = _pool(pool, candidates)
    read = [labels[c["id"]] for c in rows if c["id"] in labels]
    if not read:
        return None
    matrix: dict[str, Counter] = defaultdict(Counter)
    for r in read:
        matrix[r["recorded"]][r["label"]] += 1
    raw = Counter(c["outcome"] for c in rows)
    n = sum(raw[v] for v in VERDICTS)
    out = {
        "n_read": len(read), "n_pool": len(rows),
        "by_verdict": {v: {"n": sum(c.values()), "right": c[v],
                           "precision": round(c[v] / sum(c.values()), 3)} for v, c in sorted(matrix.items())},
        "flipped": matrix.get("successful", Counter())["failed"] + matrix.get("failed", Counter())["successful"],
        "raw_success_share": round(raw["successful"] / n, 3) if n else None,
        "corrected_success_share": None,
    }
    if all(v in matrix for v in VERDICTS if raw[v]):
        est: Counter = Counter()
        for recorded, c in matrix.items():
            m = sum(c.values())
            for true_label, k in c.items():
                est[true_label] += raw[recorded] * k / m
        denom = sum(est[v] for v in VERDICTS)
        if denom:
            out["corrected_success_share"] = round(est["successful"] / denom, 3)
            out["corrected_n"] = round(denom)
    return out
