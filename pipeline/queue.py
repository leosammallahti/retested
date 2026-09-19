"""Review queue: machine-found replication candidates that are not yet in FORRT's curated data.

Day-one source: FORRT's own flora-extractor output (public CSV, LLM-extracted, never human-reviewed).
Every row keeps review_state='machine' until a human decides; nothing here is shown as validated.
"""
from __future__ import annotations

from .ids import norm_doi


def build(extracted: list[dict], g: dict) -> list[dict]:
    known_pairs = {(a["doi_o"], a["doi_r"]) for a in g["attempts"].values() if a["doi_r"]}
    known_reps = {a["doi_r"] for a in g["attempts"].values() if a["doi_r"]}
    effect_of = {}
    for e in g["effects"].values():
        for d in e["originals"]:
            effect_of.setdefault(d, (e["slug"], e["name"]))
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
            "review_state": "machine",
        })
    out.sort(key=lambda c: (not c["original_in_wiki"], -(c["year_r"] or 0)))
    return out


def _int(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None
