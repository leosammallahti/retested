"""Attach the three lenses to findings and effects."""
from __future__ import annotations

import math
import statistics

from . import evidence as ev


def numeric_rows(attempts: dict, aids: list[str]) -> list[dict]:
    """Rows usable for pooling: FReD rows first; legacy rows only for attempts with no FReD numbers."""
    out = []
    for aid in aids:
        a = attempts[aid]
        if a["type"] != "replication":
            continue
        src = a["rows"] or [r for r in a["legacy_rows"] if r.get("r_r") is not None]
        for r in src:
            if r.get("r_r") is not None and r.get("n_r"):
                out.append({"attempt_id": aid, "r_r": r["r_r"], "n_r": r["n_r"], "r_o": r.get("r_o"),
                            "legacy": not a["rows"]})
    return out


def lenses(attempts: dict, aids: list[str], curated_reversed: bool = False) -> dict:
    reps = [attempts[a] for a in aids if attempts[a]["type"] == "replication"]
    record = ev.record_status([a["outcome"] for a in reps], curated_reversed)
    num_rows = numeric_rows(attempts, aids)
    numeric = ev.pool_replications(num_rows)
    fred_rows = [r for a in reps for r in a["rows"]]
    crit = ev.criteria_tally(fred_rows) if fred_rows else None
    closeness = {}
    for a in reps:
        for lr in a["legacy_rows"]:
            for k, v in (lr.get("closeness") or {}).items():
                closeness.setdefault(k, []).append(v)
    prereg = sum(1 for a in reps if any(is_prereg(r.get("prereg_r")) for r in a["rows"])
                 or any(is_prereg(lr.get("preregistration")) for lr in a["legacy_rows"]))
    independent = sum(1 for a in reps if a.get("author_overlap_pct") in (0, 0.0))
    overlap_known = sum(1 for a in reps if a.get("author_overlap_pct") is not None)
    years = sorted(y for a in reps if (y := a.get("year_r")))
    return {
        "record": record,
        "numeric": numeric,
        "criteria": crit,
        "disagree": ev.lenses_disagree(record, numeric),
        "design": {
            "preregistered": prereg,
            "independent": independent,
            "overlap_known": overlap_known,
            "closeness": {k: _mode(v) for k, v in closeness.items()} or None,
        },
        "n_reproductions": sum(1 for a in aids if attempts[a]["type"] == "reproduction"),
        "first_replication_year": int(years[0]) if years else None,
        "last_replication_year": int(years[-1]) if years else None,
        "total_replication_n": sum(n for a in reps if (n := attempt_n(a))) or None,
    }


def attempt_n(a: dict) -> int | None:
    """Largest reported replication N in an attempt (rows can be several effects on one sample, so never summed)."""
    ns = [r.get("n_r") for r in a["rows"] + a["legacy_rows"] if r.get("n_r")]
    return int(max(ns)) if ns else None


_NOT_PREREG = {"", "0", "no", "false", "na", "nan", "none", "null", "n/a", "-"}


def is_prereg(v) -> bool:
    """FORRT's codebook defines prereg_r as a LINK to the preregistration, not a flag.

    Reading the field as a yes/no flag made the site report zero preregistered replications while 1,173 FReD rows
    and 257 legacy rows carried an OSF link. A link counts, "embargoed" counts (the registration exists, it is just
    not public yet), and only an explicit negative or an empty cell does not.
    """
    t = str(v or "").strip().lower()
    return bool(t) and t not in _NOT_PREREG


def _mode(vals):
    from collections import Counter
    return Counter(str(v) for v in vals).most_common(1)[0][0]


def _ci(r: float, n) -> list[float] | None:
    if n is None or n <= 3:
        return None
    z, se = ev._fz(r), 1 / math.sqrt(n - 3)
    return [round(ev._iz(z - 1.96 * se), 3), round(ev._iz(z + 1.96 * se), 3)]


def attempt_estimate(a: dict) -> dict | None:
    """One point + CI per attempt for forest plots: sites/sub-studies inside a paper pooled first."""
    rows = [r for r in (a["rows"] or a["legacy_rows"]) if r.get("r_r") is not None and (r.get("n_r") or 0) > 3]
    if not rows:
        return None
    p = ev.dl_pool([(ev._fz(r["r_r"]), 1 / (r["n_r"] - 3)) for r in rows])
    ros = [r["r_o"] for r in rows if r.get("r_o") is not None]
    nos = [r["n_o"] for r in rows if r.get("n_o")]
    r_o = statistics.median(ros) if ros else None
    n_o = statistics.median(nos) if nos else None
    return {
        "r": round(ev._iz(p["z"]), 3),
        "ci": [round(ev._iz(p["z"] - 1.96 * p["se"]), 3), round(ev._iz(p["z"] + 1.96 * p["se"]), 3)],
        "k_rows": len(rows), "n": int(max(r["n_r"] for r in rows)),
        "r_o": round(r_o, 3) if r_o is not None else None,
        "ci_o": _ci(r_o, n_o) if r_o is not None else None,
        "n_o": int(n_o) if n_o else None,
        "legacy": not a["rows"],
    }


def score(g: dict) -> None:
    A = g["attempts"]
    for a in A.values():
        a["est"] = attempt_estimate(a)
    for f in g["findings"].values():
        f["lenses"] = lenses(A, f["attempts"])
    for e in g["effects"].values():
        rev = bool(e["famous"] and e["famous"]["status"] == "reversed")
        e["lenses"] = lenses(A, e["attempts"], curated_reversed=rev)
