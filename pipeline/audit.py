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
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

from .load import ROOT

BUILD = ROOT / "data" / "build" / "candidates.json"
CURATED = ROOT / "data" / "curated"
_WARNED = False
COLUMNS = ("cid", "pool", "recorded", "matched_to", "label", "note", "labelled_by", "labelled_on")


def candidates() -> list[dict]:
    """The rows the last build wrote. Note the tense: this is the PREVIOUS build's output.

    `queue.TRUSTED_LINKS` and `queue._overruled` are computed from it, so a build that runs straight after new
    labels are recorded gates on the bands as they stood before them, and the build after that gates on the new
    ones. The two disagree, and the first is wrong. On 2026-09-22 that reported a deck of 1,151 cards which the
    next build, with nothing changed in between, put at 1,096 — and the half hour spent looking for what had
    changed is the reason this warning exists. Run the build twice after recording labels, or read the second
    number.
    """
    if not BUILD.exists():
        raise SystemExit(f"{BUILD} is missing — run `python -m pipeline build` first")
    global _WARNED
    for f in (() if _WARNED else (CURATED / "original_audit.csv", CURATED / "outcome_audit.csv")):
        if f.exists() and f.stat().st_mtime > BUILD.stat().st_mtime:
            print(f"  ! {f.name} is newer than the last build: the link gate is computed from {BUILD.name},"
                  f" so this run still uses the previous labels. Build again to settle.", file=sys.stderr)
            _WARNED = True
            break
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
        for r in sorted(rows, key=lambda r: (r["pool"], r["cid"], r.get("matched_to") or "")):
            w.writerow({k: r.get(k, "") for k in COLUMNS})


def add(path: Path, cid: str, pool_name: str, recorded: str, label: str, note: str, by: str, valid,
        matched_to: str = "") -> None:
    """One label. `matched_to` is the paper the row pointed at when it was read.

    Without it a label cannot be checked against the match in force. `recorded` holds the BAND, and a band is
    too coarse: after the reference titles were completed on 2026-09-22, many rows kept the band
    `reference_scan/medium` while moving to a different paper inside it, so 32 labels about superseded matches
    went on being counted — the band read 81% on those and 95% on twenty fresh reads of the same band. Labels
    written before that date have this column empty and cannot be checked, which is itself worth seeing.
    """
    if label not in valid:
        raise SystemExit(f"label must be one of {tuple(valid)}")
    # Replaced by the PAIRING, not by the find. A find can be matched to more than one paper worth judging —
    # the matcher's first choice and its runner-up — and keying on the find alone means the second reading
    # silently deletes the first. That happened on 2026-09-22: recording 45 runner-up labels overwrote six
    # band labels, five of them `wrong` verdicts that were holding weak bands down, and the page gate and the
    # deck moved by about 55 cards with nothing in the file to say why.
    rows = [r for r in read_labels(path)
            if not (r["cid"] == cid and (r.get("matched_to") or "") == (matched_to or ""))]
    rows.append({"cid": cid, "pool": pool_name, "recorded": recorded, "matched_to": matched_to, "label": label,
                 "note": note, "labelled_by": by, "labelled_on": date.today().isoformat()})
    write_labels(path, rows)


def record(path: Path, rows: list[dict], pool_name: str, stratum, text: str, valid, by: str,
           matched=lambda c: c.get("doi_o") or "") -> int:
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
        add(path, cid, pool_name, stratum(by_id[cid]), label, note, by, valid, matched(by_id[cid]))
        n += 1
    print(f"recorded {n} labels in {path}")
    if missing:
        print(f"  {len(missing)} labels had no row in pool {pool_name!r} and were NOT recorded: "
              + ", ".join(missing[:8]) + ("…" if len(missing) > 8 else ""))
    return n


def index(labels: list[dict]) -> dict[str, dict[str, dict]]:
    """find id -> {the paper that was judged: label}.

    Two labels on one find are not a contradiction: one reader judged the paper the matcher chose, another
    judged the paper it ranked second. Only the one about the paper in force says anything about what ships.
    """
    out: dict[str, dict[str, dict]] = defaultdict(dict)
    for r in labels:
        out[r["cid"]][r.get("matched_to") or ""] = r
    return out


def label_for(idx: dict, cid: str, matched_to: str | None) -> dict | None:
    """The label that judged THIS pairing, or an older one that did not record which paper it judged."""
    d = idx.get(cid)
    return (d.get(matched_to or "") or d.get("")) if d else None


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
