"""Review queue: machine-found replication candidates that are not yet in FORRT's curated data.

Two sources, kept apart and labelled:
  forrt_flora_extractor  FORRT's own extractor output (public CSV, LLM-extracted, never human-reviewed);
  retested_discovery     our keyword and citation searches, screened by DeepSeek and linked to an original here.

Every row keeps review_state='machine' until a human decides; nothing here is shown as validated. Rows whose
original is already in the wiki are also shown on that effect/finding page, marked unverified and pending review.
"""
from __future__ import annotations

from .ids import norm_doi

# which triage verdicts reach the queue at all, and which pile they go in
GROUP = {
    ("replication", "psychology"): "replication",
    ("reproduction", "psychology"): "replication",
    ("replication", "other_behavioural"): "other_behavioural",
    ("reproduction", "other_behavioural"): "other_behavioural",
    ("registration_only", "psychology"): "registration",
    ("registration_only", "other_behavioural"): "registration",
}
GROUP_LABEL = {
    "replication": "Psychology replication",
    "other_behavioural": "Other behavioural science",
    "registration": "Registered protocol, no results yet",
}


def build(extracted: list[dict], g: dict) -> list[dict]:
    """FORRT's own flora-extractor rows."""
    known_pairs = {(a["doi_o"], a["doi_r"]) for a in g["attempts"].values() if a["doi_r"]}
    known_reps = {a["doi_r"] for a in g["attempts"].values() if a["doi_r"]}
    effect_of = _effect_of(g)
    out, seen = [], set()
    for r in extracted:
        doi_o, doi_r = norm_doi(r.get("doi_o")), norm_doi(r.get("doi_r"))
        if not doi_r or (doi_o, doi_r) in seen:
            continue
        seen.add((doi_o, doi_r))
        if (doi_o, doi_r) in known_pairs:
            continue
        eff = effect_of.get(doi_o)
        out.append({
            "id": r.get("pair_id") or f"{doi_o}|{doi_r}",
            "doi_r": doi_r, "title_r": r.get("title_r"), "year_r": _int(r.get("year_r")), "journal_r": r.get("journal_r"),
            "doi_o": doi_o, "title_o": r.get("title_o"), "year_o": _int(r.get("year_o")),
            "outcome": (r.get("outcome") or "").lower() or None,
            "outcome_quote": r.get("outcome_phrase"),
            "outcome_confidence": r.get("outcome_confidence"),
            "link_confidence": r.get("link_confidence"),
            "type": r.get("type"),
            "rep_already_known": doi_r in known_reps,
            "original_in_wiki": bool(doi_o and doi_o in g["findings"]),
            "effect": {"slug": eff[0], "name": eff[1]} if eff else None,
            "abstract": (r.get("abstract_r") or "")[:700] or None,
            "models": [m for m in (r.get("classify_llm_model"), r.get("link_llm_model"), r.get("outcome_llm_model")) if m],
            "origin": "forrt_flora_extractor",
            "group": "replication",
            "review_state": "machine",
        })
    out.sort(key=lambda c: (not c["original_in_wiki"], -(c["year_r"] or 0)))
    return out


def build_retested(triaged: list[dict], links: dict, g: dict) -> list[dict]:
    """Our own finds: one row per discovered paper DeepSeek judged a replication, a reproduction or a registered
    protocol, carrying its verdict, its grounded quote, and how its original was resolved."""
    known_pairs = {(a["doi_o"], a["doi_r"]) for a in g["attempts"].values() if a["doi_r"]}
    known_reps = {a["doi_r"] for a in g["attempts"].values() if a["doi_r"]}
    effect_of = _effect_of(g)
    P = g["papers"]
    out = []
    for r in triaged:
        t = r["triage"]
        group = GROUP.get((t.get("kind"), t.get("field")))
        if not group:
            continue
        doi_r = norm_doi(r.get("doi_r"))
        link = links.get(r["cid"])
        doi_o = t.get("original_doi") or (link or {}).get("doi_o")
        if doi_r and doi_o and (doi_o, doi_r) in known_pairs:
            continue                                      # FORRT already records this exact pair
        named = t.get("original") or {}
        in_wiki = bool(doi_o and doi_o in g["findings"])
        eff = effect_of.get(doi_o)
        out.append({
            "id": r["cid"],
            "doi_r": doi_r, "title_r": r.get("title_r"), "year_r": r.get("year_r"), "journal_r": r.get("venue"),
            "authors_r": r.get("authors_r"),
            "doi_o": doi_o,
            "title_o": (P.get(doi_o) or {}).get("title") if in_wiki else (link or {}).get("title_o"),
            "year_o": (P.get(doi_o) or {}).get("year") if in_wiki else (link or {}).get("year_o"),
            "outcome": t.get("outcome") if t.get("outcome") != "not_reported" else None,
            "outcome_quote": t.get("outcome_quote"),
            "outcome_confidence": t.get("confidence"),
            # a DOI read out of the replication's own reference list is as good as a link gets
            "link_confidence": ("high" if t.get("original_doi") else (link or {}).get("confidence")),
            "link_method": "cited by this paper" if t.get("original_doi") else (link or {}).get("method"),
            "link_evidence": {k: link.get(k) for k in ("score", "text_sim", "authors_matched", "year_delta", "runner_up")}
                             if link and not t.get("original_doi") else None,
            "original_named": {"authors": named.get("authors"), "year": named.get("year"),
                               "description": named.get("description")} if named.get("authors") or named.get("description") else None,
            "type": "reproduction" if t.get("kind") == "reproduction" else ("registration" if group == "registration" else "replication"),
            "field": t.get("field"),
            "group": group,
            "evidence_tier": "preprint" if r.get("type") == "preprint" else ("published" if doi_r else "no doi"),
            "found_by": r.get("found_by") or [],
            "rep_already_known": bool(doi_r and doi_r in known_reps),
            "original_in_wiki": in_wiki,
            "effect": {"slug": eff[0], "name": eff[1]} if eff else None,
            "abstract": (r.get("abstract") or "")[:700] or None,
            "models": [t["model"]] if t.get("model") else [],
            "screen_reason": t.get("reason"),
            "origin": "retested_discovery",
            "review_state": "machine",
        })
    out.sort(key=lambda c: (not c["original_in_wiki"], c["group"] != "replication", -(c["year_r"] or 0)))
    return out


def pending(candidates: list[dict], g: dict) -> dict:
    """Our linked finds, grouped for the pages that show them as unverified, pending review.

    Only rows whose original already has a page, and only replications: a registered protocol has no result yet,
    and an economics experiment is not part of a psychology effect's record. FORRT's own extractor candidates stay
    in the queue alone — putting someone else's unreviewed list on a page is their editorial call, not ours."""
    by_finding: dict[str, list[dict]] = {}
    by_effect: dict[str, list[dict]] = {}
    for c in candidates:
        if c["origin"] == "retested_discovery" and c["original_in_wiki"] and c["group"] == "replication":
            by_finding.setdefault(c["doi_o"], []).append(c)
    for doi_o, rows in by_finding.items():
        for eid in g["findings"][doi_o].get("effects") or []:
            by_effect.setdefault(eid, []).extend(rows)
    order = {"high": 0, "medium": 1, "low": 2}
    for d in (by_finding, by_effect):
        for rows in d.values():
            rows.sort(key=lambda c: (order.get(c.get("link_confidence"), 3), -(c["year_r"] or 0)))
    return {"by_finding": by_finding, "by_effect": by_effect}


def _effect_of(g: dict) -> dict:
    out: dict[str, tuple[str, str]] = {}
    for e in g["effects"].values():
        for d in e["originals"]:
            out.setdefault(d, (e["slug"], e["name"]))
    return out


def _int(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None
