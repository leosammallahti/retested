"""The parts every hand-read audit in this project shares.

There are two of them and they ask different questions — `outcomes` asks whether the verdict was read right,
`originals` asks whether the find was matched to the right earlier paper — but the machinery is the same one
every time, and it is the machinery that keeps the answers honest:

* **A pool is a stated set of rows.** Every figure is only about the rows it was computed over. Twice this
  project has been sent down a dead end by an intermediate built from the wrong population, so a pool carries a
  plain-English description and the scorer prints it above the numbers.
* **The draw is deterministic and stratified.** Stratified because the question is almost always whether one
  stratum can be trusted more than another, and a flat draw spends the reading wherever the rows happen to pile
  up. Deterministic because a sample you cannot redraw is a sample nobody can check.
* **Labels are written down, keyed by candidate id.** An earlier outcome audit read 20 cases, recorded only the
  summary, and when a later session wanted to extend it there was nothing to extend — it had to start again, and
  the second answer contradicted the first. Labels here survive rebuilds and accumulate.

`python -m pipeline outcomes --help` and `python -m pipeline originals --help` are the entry points.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

from .load import ROOT

BUILD = ROOT / "data" / "build" / "candidates.json"
CURATED = ROOT / "data" / "curated"
COLUMNS = ["cid", "pool", "recorded", "label", "note", "labelled_by", "labelled_on"]


def candidates() -> list[dict]:
    if not BUILD.exists():
        raise SystemExit(f"{BUILD} is missing — run `python -m pipeline build` first")
    return json.loads(BUILD.read_text(encoding="utf-8"))


def pool(pools: dict, name: str, rows: list[dict] | None = None) -> list[dict]:
    """Our own psychology replication finds, narrowed by the named pool's own rule and sorted for a stable draw."""
    keep = pools[name][1]
    out = [c for c in (candidates() if rows is None else rows)
           if c.get("origin") == "retested_discovery" and c.get("group") == "replication" and keep(c)]
    out.sort(key=lambda c: c["id"])
    return out


def read_labels(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return [r for r in csv.DictReader(fh) if r.get("label")]


def write_labels(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        for r in sorted(rows, key=lambda r: (r["pool"], r["cid"])):
            w.writerow({k: r.get(k, "") for k in COLUMNS})


def add(path: Path, cid: str, pool_name: str, recorded: str, label: str, note: str, by: str, valid) -> None:
    if label not in valid:
        raise SystemExit(f"label must be one of {tuple(valid)}")
    rows = [r for r in read_labels(path) if r["cid"] != cid]
    rows.append({"cid": cid, "pool": pool_name, "recorded": recorded, "label": label, "note": note,
                 "labelled_by": by, "labelled_on": date.today().isoformat()})
    write_labels(path, rows)


def record(path: Path, rows: list[dict], pool_name: str, stratum, text: str, valid, by: str) -> int:
    """Take labels in bulk: one 'cid<TAB>label<TAB>note' line each, from a session that has just read them."""
    by_id = {c["id"]: c for c in rows}
    n, missing = 0, []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        cid, label, note = (line.rstrip("\n").split("\t") + ["", ""])[:3]
        if cid not in by_id:
            # A row can leave a pool between the draw and the label — a rebuild folds a DOI, a dedupe collapses
            # a deposit. Named, never dropped quietly: a label with nowhere to go is a case somebody read for
            # nothing, and the next draw will hand it to them again.
            missing.append(cid)
            continue
        add(path, cid, pool_name, stratum(by_id[cid]), label, note, by, valid)
        n += 1
    print(f"recorded {n} labels in {path}")
    if missing:
        print(f"  {len(missing)} labels had no row in pool {pool_name!r} and were NOT recorded: "
              + ", ".join(missing[:8]) + ("…" if len(missing) > 8 else ""))
    return n


def draw(rows: list[dict], done: set[str], n: int, seed: str, stratum, only: str | None = None) -> list[dict]:
    """n unlabelled rows, spread evenly over the strata, in an order fixed by the seed."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for c in rows:
        s = stratum(c)
        if c["id"] not in done and only in (None, s):
            groups[s].append(c)
    per = max(1, n // max(1, len(groups)))
    picked = []
    for _, group in sorted(groups.items()):
        group.sort(key=lambda c: hashlib.md5(f"{seed}|{c['id']}".encode()).hexdigest())
        picked += group[:per]
    return picked


def wilson(k: int, n: int) -> tuple[float, float]:
    from .stats import wilson as w
    return tuple(w(k, n) or (0.0, 1.0))


def table(matrix: dict, order=None, right_label: str = "right") -> None:
    """One line per stratum: how many were read, how many the machine got right, and how wide that still is."""
    print(f"   {'machine said':<34} {'n':>4}  {right_label:>6}  {'precision':>9}  95% interval")
    for key in (order or sorted(matrix)):
        n, k = matrix[key]["n"], matrix[key]["right"]
        if not n:
            continue
        lo, hi = wilson(k, n)
        print(f"   {key:<34} {n:>4}  {k:>6}  {k / n:>8.0%}   {lo:.0%}–{hi:.0%}")


def unreached(rows: list[dict], labels: dict, members: dict, stratum) -> None:
    """Rows in this pool that no draw has sampled from, named by stratum.

    Borrowing a stratum's precision for rows that were never in the urn is the same error as `link --check`:
    a number measured on the easy half and quoted over the whole.
    """
    drawn_from: dict[str, set] = defaultdict(set)
    for r in labels.values():
        drawn_from[r["recorded"]].add(r["pool"])
    gaps: dict[str, int] = defaultdict(int)
    for c in rows:
        pools = drawn_from.get(stratum(c))
        if pools and not any(c["id"] in members[q] for q in pools):
            gaps[stratum(c)] += 1
    if gaps:
        print("   not reached by any draw: " + ", ".join(f"{v} rows in '{k}'" for k, v in sorted(gaps.items())))
