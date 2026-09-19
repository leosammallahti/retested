"""Site-wide numbers, always with their denominator and grain."""
from __future__ import annotations

import math
import statistics
from collections import Counter, defaultdict

VERDICT = ("successful", "failed", "mixed")


def wilson(k: int, n: int, z: float = 1.96) -> list[float] | None:
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 3), round(c + h, 3)]


def _share(outs: list[str]) -> dict:
    c = Counter(o for o in outs if o in VERDICT)
    n = sum(c.values())
    return {"n": n, **{k: c[k] for k in VERDICT},
            "success_share": round(c["successful"] / n, 3) if n else None,
            "success_ci": wilson(c["successful"], n)}


def attempt_discipline(a: dict, g: dict) -> str | None:
    ds = Counter(r["discipline"] for r in a["rows"] if r.get("discipline"))
    if ds:
        return ds.most_common(1)[0][0]
    f = g["findings"].get(a["doi_o"], {})
    for eid in f.get("effects") or []:
        e = g["_eff_by_id"][eid]
        if e.get("discipline"):
            return e["discipline"]
    return None


def build(g: dict, game_items: list[dict], candidates: list[dict]) -> dict:
    A, F, E, P = g["attempts"], g["findings"], g["effects"], g["papers"]
    g["_eff_by_id"] = {e["id"]: e for e in E.values()}
    reps = [a for a in A.values() if a["type"] == "replication"]
    verdict = [a for a in reps if a["outcome"] in VERDICT]

    by_year = defaultdict(list)
    for a in reps:
        if a.get("year_r"):
            by_year[int(a["year_r"])].append(a["outcome"])
    by_decade = defaultdict(list)
    for a in reps:
        y = P.get(a["doi_o"], {}).get("year")
        if y:
            by_decade[f"{int(y) // 10 * 10}s"].append(a["outcome"])
    by_disc = defaultdict(list)
    for a in reps:
        d = attempt_discipline(a, g)
        if d:
            by_disc[d.strip()].append(a["outcome"])
    by_journal = defaultdict(list)
    for a in reps:
        j = P.get(a["doi_o"], {}).get("journal")
        if j:
            by_journal[j.strip()].append(a["outcome"])

    # p-value of the original as a predictor (FReD rows, one per original study)
    seen, p_low, p_mid = set(), [], []
    for a in reps:
        for r in a["rows"]:
            key = (a["doi_o"], r.get("study_o"))
            p, o = r.get("p_o"), r.get("reported_success")
            if key in seen or p is None or o not in ("successful", "failed"):
                continue
            seen.add(key)
            if p <= 0.005:
                p_low.append(o)
            elif p <= 0.05:
                p_mid.append(o)

    ratios = []
    for a in reps:
        for r in a["rows"]:
            ro, rr = r.get("r_o"), r.get("r_r")
            if ro is not None and rr is not None and abs(ro) >= 0.05:
                ratios.append(rr / ro)
    ratios.sort()

    indep, overlap = [], []
    for a in reps:
        pct = a.get("author_overlap_pct")
        if pct is None or a["outcome"] not in VERDICT:
            continue
        (indep if float(pct) == 0 else overlap).append(a["outcome"])

    rec_counts = Counter(e["lenses"]["record"]["code"] for e in E.values())
    fin_counts = Counter(f["lenses"]["record"]["code"] for f in F.values())

    def fame(e):
        fam = e.get("famous") or {}
        oa = max(((P.get(d, {}).get("openalex") or {}).get("cited_by") or 0 for d in e["originals"]), default=0)
        return max(fam.get("gs_citations") or 0, oa)

    def card(e):
        L = e["lenses"]
        return {"slug": e["slug"], "name": e["name"], "discipline": e.get("discipline"), "record": L["record"],
                "fame": fame(e), "numeric": L["numeric"] and {k: L["numeric"][k] for k in ("r", "ci", "ratio", "r_original", "label")},
                "famous_status": (e.get("famous") or {}).get("status")}

    failed_codes = {"failed", "largely_failed", "reversed", "single_failure"}
    ok_codes = {"replicated", "largely_replicated"}
    graveyard = sorted((e for e in E.values() if e["lenses"]["record"]["code"] in failed_codes and e["lenses"]["record"]["k"] >= 1),
                       key=lambda e: (-fame(e), e["name"]))
    def survived(e):
        code = e["lenses"]["record"]["code"]
        fam = (e.get("famous") or {}).get("status")
        return code in ok_codes or code == "single_success" or (fam == "replicated" and code not in failed_codes | {"contested"})

    survivors = sorted((e for e in E.values() if survived(e)), key=lambda e: (-fame(e), e["name"]))
    contested = sorted((e for e in E.values() if e["lenses"]["record"]["code"] == "contested"),
                       key=lambda e: (-e["lenses"]["record"]["k"], e["name"]))
    most_tested = sorted(E.values(), key=lambda e: (-e["lenses"]["record"]["k"], e["name"]))

    q = lambda xs, f: xs[int(f * (len(xs) - 1))] if xs else None  # noqa: E731
    return {
        "counts": {
            "effects": len(E),
            "effects_with_attempts": sum(1 for e in E.values() if e["attempts"]),
            "famous_effects": sum(1 for e in E.values() if e.get("famous")),
            "findings": len(F),
            "attempts": len(A),
            "replications": len(reps),
            "reproductions": len(A) - len(reps),
            "replications_with_verdict": len(verdict),
            "legacy_only_attempts": sum(1 for a in A.values() if a.get("legacy_only")),
            "attempts_with_numbers": sum(1 for a in reps if a["rows"]),
            "papers": len(P),
            "game_items": len(game_items),
            "game_items_study": sum(1 for i in game_items if i["tier"] == "study"),
            "game_items_famous": sum(1 for i in game_items if i["tier"] == "famous"),
            "candidates": len(candidates),
            "candidates_on_known_originals": sum(1 for c in candidates if c["original_in_wiki"]),
            "candidates_forrt": sum(1 for c in candidates if c["origin"] == "forrt_flora_extractor"),
            "candidates_retested": sum(1 for c in candidates if c["origin"] == "retested_discovery"),
            "retested_replications": sum(1 for c in candidates if c["origin"] == "retested_discovery" and c["group"] == "replication"),
            "retested_other_behavioural": sum(1 for c in candidates if c["origin"] == "retested_discovery" and c["group"] == "other_behavioural"),
            "retested_registrations": sum(1 for c in candidates if c["origin"] == "retested_discovery" and c["group"] == "registration"),
            "retested_with_original": sum(1 for c in candidates if c["origin"] == "retested_discovery" and c["doi_o"]),
            "retested_on_known_originals": sum(1 for c in candidates if c["origin"] == "retested_discovery" and c["original_in_wiki"]),
            "retested_preprints": sum(1 for c in candidates if c["origin"] == "retested_discovery" and c.get("evidence_tier") == "preprint"),
            "retested_high_tier": sum(1 for c in candidates if c["origin"] == "retested_discovery" and c.get("search_tier") == "high"),
            "retested_medium_tier": sum(1 for c in candidates if c["origin"] == "retested_discovery" and c.get("search_tier") == "medium"),
        },
        "overall": _share([a["outcome"] for a in reps]),
        "by_replication_year": {y: _share(v) for y, v in sorted(by_year.items()) if 2000 <= y <= 2030},
        "by_original_decade": {d: _share(v) for d, v in sorted(by_decade.items()) if _share(v)["n"] >= 20},
        "by_discipline": dict(sorted(((d, _share(v)) for d, v in by_disc.items() if _share(v)["n"] >= 25),
                                     key=lambda kv: -kv[1]["n"])),
        "by_journal": dict(sorted(((j, _share(v)) for j, v in by_journal.items() if _share(v)["n"] >= 20),
                                  key=lambda kv: -kv[1]["n"])),
        "predictors": {
            "p_le_005": _share(p_low), "p_005_05": _share(p_mid),
            "independent_team": _share(indep), "overlapping_authors": _share(overlap),
        },
        "shrinkage": {
            "n_rows": len(ratios),
            "median_ratio": round(statistics.median(ratios), 2) if ratios else None,
            "q25": round(q(ratios, 0.25), 2) if ratios else None,
            "q75": round(q(ratios, 0.75), 2) if ratios else None,
            "share_below_half": round(sum(r < 0.5 for r in ratios) / len(ratios), 3) if ratios else None,
            "share_sign_flip": round(sum(r < 0 for r in ratios) / len(ratios), 3) if ratios else None,
        },
        "effect_record_counts": dict(rec_counts),
        "finding_record_counts": dict(fin_counts),
        "lists": {
            "graveyard": [card(e) for e in graveyard[:80]],
            "survivors": [card(e) for e in survivors[:80]],
            "contested": [card(e) for e in contested[:60]],
            "most_tested": [card(e) for e in most_tested[:30]],
        },
    }
