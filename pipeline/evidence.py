"""The three lenses as computations.

1. Record  - what replication authors reported (FLoRA > FReD > legacy), rolled up with explicit count rules.
2. Numbers - random-effects pooling of replication effect sizes (Pearson r via Fisher z) and FORRT's seven criteria.
3. Design  - closeness, preregistration, independence (carried through as fields, not scored).

Never collapse these into one score.
"""
from __future__ import annotations

import math
from collections import Counter

# ---------------------------------------------------------------- outcome vocabulary

OUTCOMES = ("successful", "failed", "mixed", "inconclusive", "not_coded")

_FLORA = {
    "successful": "successful",
    "failed": "failed",
    "mixed": "mixed",
    "statistically successful but flawed": "mixed",
    "descriptive only": "inconclusive",
    "uninformative": "inconclusive",
}
_LEGACY_RESULT = {
    "success": "successful",
    "sucess": "successful",
    "informative failure to replicate": "failed",
    "practical failure to replicate": "failed",
    "inconclusive": "inconclusive",
}


def norm_outcome(raw) -> str:
    """Map FLoRA/FReD outcome strings onto our five-value vocabulary."""
    if raw is None:
        return "not_coded"
    s = str(raw).strip().lower()
    if s in _FLORA:
        return _FLORA[s]
    if s.startswith("computationally reproducible"):
        return "successful"
    if s.startswith("computational issues"):
        return "failed"
    return "not_coded"


def legacy_outcome(result, lebel) -> str:
    """Legacy 2.4.1: 'result' column first, then LeBel et al. signal/consistency coding."""
    if result is not None:
        return _LEGACY_RESULT.get(str(result).strip().lower(), "not_coded")
    if lebel is None:
        return "not_coded"
    s = str(lebel).lower()
    if s.startswith("signal"):
        return "failed" if "opposite" in s else "successful"
    if s.startswith("no signal - inconsistent"):
        return "failed"
    if s.startswith("no signal - consistent"):
        return "inconclusive"
    return "not_coded"


# ---------------------------------------------------------------- lens 1: the record

RECORD_LABELS = {
    "replicated": "Replicated",
    "largely_replicated": "Largely replicated",
    "contested": "Contested",
    "largely_failed": "Largely failed",
    "failed": "Failed to replicate",
    "reversed": "Reversed",
    "single_success": "Replicated once",
    "single_failure": "Failed once",
    "single_mixed": "Mixed (one attempt)",
    "unclear": "No clear verdict",
    "untested": "No linked attempts yet",
}
# ordering used for the colour scale and sorting (most robust first)
RECORD_ORDER = list(RECORD_LABELS)


def record_status(outcomes: list[str], curated_reversed: bool = False) -> dict:
    """Roll up attempt-level author verdicts.

    Rules (k = attempts with a successful/failed/mixed verdict):
      k = 0                       -> unclear (attempts exist but none gave a verdict) / untested
      k = 1                       -> single_{success,failure,mixed}
      k >= 2, all successful      -> replicated
      k >= 2, all failed          -> failed
      k >= 2, (successes + mixed/2) / k >= .75 -> largely_replicated
      k >= 2, (failures + mixed/2) / k >= .75  -> largely_failed
      otherwise                   -> contested
    A 'mixed' attempt counts half each way and blocks both unanimous labels. Reversed is curated-only.
    """
    c = Counter(outcomes)
    s, f, m = c["successful"], c["failed"], c["mixed"]
    k = s + f + m
    if curated_reversed:
        code = "reversed"
    elif not outcomes:
        code = "untested"
    elif k == 0:
        code = "unclear"
    elif k == 1:
        code = "single_success" if s else ("single_failure" if f else "single_mixed")
    elif s == k:
        code = "replicated"
    elif f == k:
        code = "failed"
    elif (s + m / 2) / k >= 0.75:
        code = "largely_replicated"
    elif (f + m / 2) / k >= 0.75:
        code = "largely_failed"
    else:
        code = "contested"
    return {
        "code": code,
        "label": RECORD_LABELS[code],
        "k": k,
        "n_attempts": len(outcomes),
        "successful": s,
        "failed": f,
        "mixed": m,
        "inconclusive": c["inconclusive"],
        "not_coded": c["not_coded"],
    }


# ---------------------------------------------------------------- lens 2: the numbers

def _fz(r: float) -> float:
    r = max(min(r, 0.9999), -0.9999)
    return 0.5 * math.log((1 + r) / (1 - r))


def _iz(z: float) -> float:
    return math.tanh(z)


def dl_pool(ests: list[tuple[float, float]]) -> dict | None:
    """DerSimonian-Laird random-effects pool of (z, var) pairs. Returns z-scale results."""
    ests = [(z, v) for z, v in ests if v and v > 0 and math.isfinite(z)]
    k = len(ests)
    if k == 0:
        return None
    if k == 1:
        z, v = ests[0]
        return {"z": z, "se": math.sqrt(v), "tau2": 0.0, "i2": None, "k": 1, "pi": None}
    w = [1 / v for _, v in ests]
    zf = sum(wi * z for wi, (z, _) in zip(w, ests)) / sum(w)
    q = sum(wi * (z - zf) ** 2 for wi, (z, _) in zip(w, ests))
    c = sum(w) - sum(wi * wi for wi in w) / sum(w)
    tau2 = max(0.0, (q - (k - 1)) / c) if c > 0 else 0.0
    ws = [1 / (v + tau2) for _, v in ests]
    z = sum(wi * zi for wi, (zi, _) in zip(ws, ests)) / sum(ws)
    se = math.sqrt(1 / sum(ws))
    i2 = max(0.0, (q - (k - 1)) / q) if q > 0 else 0.0
    pi = None
    if k >= 3:
        # t-quantile approximation for the prediction interval (df = k - 2)
        t = {1: 12.71, 2: 4.30, 3: 3.18, 4: 2.78, 5: 2.57, 6: 2.45, 7: 2.36, 8: 2.31, 9: 2.26, 10: 2.23}.get(k - 2, 2.0)
        half = t * math.sqrt(tau2 + se * se)
        pi = (z - half, z + half)
    return {"z": z, "se": se, "tau2": tau2, "i2": i2, "k": k, "pi": pi}


def pool_replications(rows: list[dict]) -> dict | None:
    """Two-level pooling: rows within one replication paper first (sites/sub-studies), then across papers.

    rows: dicts with attempt_id, r_r, n_r, r_o. Pooling on r only; rows lacking r_r or n_r > 3 are skipped.
    """
    by_attempt: dict[str, list[tuple[float, float]]] = {}
    r_os = []
    for r in rows:
        rr, nr = r.get("r_r"), r.get("n_r")
        if rr is None or nr is None or nr <= 3 or not math.isfinite(rr):
            continue
        by_attempt.setdefault(r["attempt_id"], []).append((_fz(rr), 1 / (nr - 3)))
        if r.get("r_o") is not None:
            r_os.append(r["r_o"])
    if not by_attempt:
        return None
    level1 = [dl_pool(v) for v in by_attempt.values()]
    top = dl_pool([(p["z"], p["se"] ** 2) for p in level1 if p])
    if not top:
        return None
    lo, hi = top["z"] - 1.96 * top["se"], top["z"] + 1.96 * top["se"]
    r_o = sorted(r_os)[len(r_os) // 2] if r_os else None
    out = {
        "r": round(_iz(top["z"]), 3),
        "ci": [round(_iz(lo), 3), round(_iz(hi), 3)],
        "pi": [round(_iz(top["pi"][0]), 3), round(_iz(top["pi"][1]), 3)] if top["pi"] else None,
        "tau": round(math.sqrt(top["tau2"]), 3),
        "i2": round(top["i2"], 2) if top["i2"] is not None else None,
        "k_papers": top["k"],
        "k_rows": sum(len(v) for v in by_attempt.values()),
        "r_original": round(r_o, 3) if r_o is not None else None,
        "ratio": None,
    }
    if r_o is not None and abs(r_o) >= 0.05:
        out["ratio"] = round(out["r"] / r_o, 2)
    out["label"] = numeric_label(out)
    return out


NUMERIC_LABELS = {
    "robust": "Holds at similar size",
    "smaller": "Holds, but smaller",
    "negligible": "Near zero",
    "reversed": "Opposite direction",
    "inconclusive": "Too imprecise to say",
}


def numeric_label(p: dict) -> dict:
    """Graded label from the pooled replication estimate relative to the original."""
    lo, hi = p["ci"]
    r_o = p["r_original"]
    sign = 1 if (r_o is None or r_o >= 0) else -1
    lo_s, hi_s = sorted((lo * sign, hi * sign))
    est = p["r"] * sign
    if hi_s < 0:
        code = "reversed"
    elif lo_s > 0:
        code = "robust" if (p["ratio"] is not None and p["ratio"] >= 0.67) or r_o is None else "smaller"
    elif hi_s < 0.1:
        code = "negligible"
    else:
        code = "inconclusive" if (hi_s - lo_s) > 0.2 else ("negligible" if abs(est) < 0.1 else "inconclusive")
    return {"code": code, "label": NUMERIC_LABELS[code]}


CRITERIA = (
    "significance_r",
    "significance_agg",
    "consistency_ci",
    "consistency_pi",
    "homogeneity",
    "homogeneity_significance",
    "small_telescopes",
)
CRITERIA_LABELS = {
    "significance_r": "Replication significant, same direction",
    "significance_agg": "Original + replication pooled is significant",
    "consistency_ci": "Original inside replication's 95% CI",
    "consistency_pi": "Replication inside original's prediction interval",
    "homogeneity": "Original and replication statistically consistent",
    "homogeneity_significance": "Consistent and jointly significant",
    "small_telescopes": "Replication rules out a tiny effect (small telescopes)",
}


def criteria_tally(rows: list[dict]) -> dict:
    """Per-criterion success/failure counts over FReD rows (FORRT's own computations)."""
    out = {}
    for c in CRITERIA:
        vals = [str((r.get("criteria") or {}).get(c) or "").lower() for r in rows]
        s = sum(v == "success" for v in vals)
        f = sum(v == "failure" for v in vals)
        out[c] = {"success": s, "failure": f, "na": len(vals) - s - f}
    return out


def lenses_disagree(record: dict, numeric: dict | None) -> bool:
    if not numeric:
        return False
    rc, nc = record["code"], numeric["label"]["code"]
    positive = rc in ("replicated", "largely_replicated", "single_success")
    negative = rc in ("failed", "largely_failed", "single_failure")
    return (positive and nc in ("negligible", "reversed")) or (negative and nc in ("robust",))
