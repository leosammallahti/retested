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
    # Rows that were matched to an original and then thrown away by a machine. They are not junk: the
    # discarding was done by `pipeline verify` and by band averages, and 900 hand reads say how often each of
    # those was wrong to discard - a verifier rejection is mistaken about 3 times in 10, a verifier `unclear`
    # row is right about 4 times in 10, and a row it confirmed inside an overruled band is right about 9 times
    # in 10. Reading them is the cheapest way to grow the pool, because the matching work is already done.
    "rescue": ("finds matched to an original that nothing currently trusts - the recoverable pile",
               lambda c: c.get("field") == "psychology" and c.get("doi_o") and not _shows(c)),
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


RUBRIC = audit.ROOT / "docs" / "READING_RUBRIC.md"
BATCH_DIR = audit.ROOT / "data" / "cache" / "reading"


def batches(pool: str, n_batches: int, size: int, only: str | None) -> int:
    """Write N batch files of unread links, worst first, each carrying the rubric.

    Reading is no longer an audit that samples a band to judge it; it is the decision procedure, because a
    label decides its own row and a reader costs nothing. That changes what a draw should optimise for. A
    stratified sample spreads effort evenly so that every band gets measured; this spends it where the wrong
    rows actually are, which is a different thing — an unread row's chance of being wrong is estimated from the
    read rows that share BOTH its band and the route that admitted it, and the worst cells go out first.
    """
    from collections import Counter
    from .queue import _read_label
    rows = [c for c in _pool(pool)
            if _read_label(c) not in ("right", "wrong") and only in (None, band(c))]
    ships = {c["id"] for c in _pool("page")}
    rows.sort(key=lambda c: (-flip_chance(c, c["id"] in ships), c["id"]))
    picked = rows[:n_batches * size]
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    rubric = RUBRIC.read_text(encoding="utf-8") if RUBRIC.exists() else ""
    for i in range(n_batches):
        chunk = picked[i * size:(i + 1) * size]
        if not chunk:
            break
        f = BATCH_DIR / f"{pool}-{i + 1:02d}.txt"
        body = "\n".join(_render(j, c) for j, c in enumerate(chunk, 1))
        f.write_text(f"{rubric}\n\n---\n\n# {len(chunk)} link cases, pool {pool!r}\n\n{body}",
                     encoding="utf-8")
        print(f"  wrote {f} · {len(chunk)} cases · "
              f"{Counter(band(c) for c in chunk).most_common(1)[0][0]} and others")
    print(f"  {len(rows)} unread rows in pool {pool!r}; {len(picked)} written, worst-estimated first")
    print(f"  give each reader {RUBRIC} and one batch file; record with "
          f"`originals --record --pool {pool}`")
    return 0


_CELLS: dict | None = None


def cell(c: dict) -> tuple:
    """The population a row belongs to for estimating whether it is right: its band and its machine verdict.

    Band alone is too coarse and was measured to be, badly. Inside `reference_scan/high` - a band read at 96% -
    the rows `pipeline verify` declined to confirm read 6 right of 24, because a band's average is dominated by
    the rows the verifier confirmed. Band and verdict together is the finest split the labels can support.
    """
    from .queue import _verified
    return (band(c), _verified().get((c["id"], c.get("doi_o"))) or "never judged")


def right_chance(c: dict) -> float | None:
    """How often rows like this one turn out to be right, from the hand labels. None if nothing comparable."""
    global _CELLS
    if _CELLS is None:
        from collections import defaultdict
        from .queue import rate
        idx = audit.index(read_labels())
        tal: dict = defaultdict(lambda: [0, 0])
        for x in _pool("linked"):
            l = audit.label_for(idx, x["id"], x.get("doi_o"))
            if l and not stale(x, l) and l["label"] in ("right", "wrong"):
                t = tal[cell(x)]
                t[0] += l["label"] == "right"
                t[1] += l["label"] == "wrong"
        _CELLS = {k: rate(*v) for k, v in tal.items() if sum(v) >= 8}
    return _CELLS.get(cell(c))


def flip_chance(c: dict, ships: bool) -> float:
    """The chance that reading this row changes what happens to it — the only reason to read it first.

    For a row on a page that is the chance it is wrong; for a row in the discard pile it is the chance it is
    right. One rule, because they are the same question asked from opposite sides, and it replaces the even
    stratified draw that made sense when the sample WAS the product rather than the decision.
    """
    pr = right_chance(c)
    if pr is None:
        return 1.0                      # nothing comparable has been read: worth reading most of all
    return 1 - pr if ships else pr


def _render(i: int, c: dict) -> str:
    k = _case(c)
    m = k["matched_to"]
    out = [f"--- {i}. {k['cid']}   BAND: {k['band']}",
           f"    replication: {k['title_r']} ({k['year_r']})",
           f"    abstract:    {k['abstract_r']}"]
    if k["circular"]:
        out.append("    !! the model wrote the description below AFTER picking the paper - it is not evidence")
    out += [f"    says it replicated: {k['says_it_replicated']}",
            f"    matched to:  {m['authors']} ({m['year']}) {m['title']!r} - {m['journal']}",
            f"    its abstract: {m['abstract']}",
            f"    evidence: {k['evidence']}   runner-up: {k['runner_up']!r}", ""]
    return "\n".join(out)


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
    idx = audit.index(read_labels())
    labels = {c["id"]: l for c in audit.candidates()
              if (l := audit.label_for(idx, c["id"], c.get("doi_o")))}
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
        # For a pool defined by what ships, "rows in a band read at 90% or better" is now trivially all of them:
        # a read row ships only if it was read as `right`. `residual` asks the question that is still open.
        if p in ("page", "shown"):
            residual(rows)
        else:
            _shippable(matrix)
    return 0


def residual(rows: list[dict]) -> None:
    """How much of this pool is still a guess, and how wrong that guess is likely to be.

    Since a hand label decides its own row, "precision of the rows a page shows" is no longer a question worth
    asking: every read row that ships was read as `right`, so the answer is 100% by construction and means
    nothing. The live question is about the rows nobody has read, and it has to be asked of the population they
    are actually in — same band AND same admission route. Estimating an unread verifier-confirmed row from all
    reads in its band mixes in rows the verifier rejected, which never ship and are disproportionately wrong;
    that put the estimate at 8.4% where the matched populations put it at 3.3%.
    """
    from collections import Counter, defaultdict
    from .queue import _read_label, _verified, rate
    ver = _verified()
    def route(c):
        return "verifier" if ver.get((c["id"], c.get("doi_o"))) == "right" else "band rule"
    idx = audit.index(read_labels())
    tal: dict = defaultdict(lambda: [0, 0])
    for c in _pool("linked"):
        l = audit.label_for(idx, c["id"], c.get("doi_o"))
        if l and not stale(c, l) and l["label"] in ("right", "wrong"):
            t = tal[(band(c), route(c))]
            t[0] += l["label"] == "right"
            t[1] += l["label"] == "wrong"
    unread = [c for c in rows if _read_label(c) not in ("right", "wrong")]
    exp, unknown = 0.0, 0
    for (b, rt), n in Counter((band(c), route(c)) for c in unread).items():
        pr = rate(*tal.get((b, rt), [0, 0]))
        if pr is None:
            unknown += n
        else:
            exp += n * (1 - pr)
    print()
    print(f"   {len(rows) - len(unread)} of {len(rows)} rows were read one at a time and are decided by that"
          f" reading; {len(unread)} still rest on their band")
    print(f"   expected wrong rows among them: about {exp:.0f}, so roughly {1 - exp / max(len(rows), 1):.0%}"
          f" of this pool is right" + (f" ({unknown} rows have nothing comparable to estimate from)" if unknown else ""))


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
    ap.add_argument("--batches", type=int, metavar="N",
                    help="write N batch files of unread links, worst-estimated first, each with the rubric")
    ap.add_argument("--size", type=int, default=40, help="cases per batch file")
    ap.add_argument("--score", action="store_true", help="report accuracy from the labels recorded so far")
    ap.add_argument("--all-pools", action="store_true", help="score every pool, not just --pool")
    a = ap.parse_args(argv if argv is not None else sys.argv[1:])
    if a.record:
        return record(a.pool, sys.stdin.read(), a.by)
    if a.batches:
        return batches(a.pool, a.batches, a.size, a.band)
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
    idx = audit.index(read_labels())
    rows = _pool(pool, candidates)
    labels = {c["id"]: l for c in rows if (l := audit.label_for(idx, c["id"], c.get("doi_o")))}
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
