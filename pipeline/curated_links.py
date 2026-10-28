"""Reviewed links that FORRT's files do not carry, each decided by reading and recorded with its evidence.

data/curated/effect_originals.csv  (effect, doi_o, evidence)
    The original paper of an effect that FORRT names only in prose: the famous list cites the paper by title, author
    and year, and the paper is already in the database with its replications.
data/curated/attempt_effects.csv   (doi_o, doi_r, effect, evidence)
    Which named effect a replication tested, when its original paper carries several named effects and FORRT's rows
    do not say. Without such a link the replication is shown on each of those effects only as a replication of the
    same paper.

data/curated/attempt_exclusions.csv (doi_o, rep_key, reason, evidence)
    An attempt that reading showed is not a replication at all (the original paper listed as its own replication,
    a preprint of the same study). It is set aside, not deleted: the FORRT ledger shows it with the reason.

data/curated/attempt_duplicates.csv (doi_o, rep_key, same_as, reason, evidence)
    One study listed twice under one original (a preprint and its article, two hosts of one report). The copy is merged
    into the record it duplicates, so its sources, numbers and result are kept and the study is counted once.
data/curated/attempt_relinks.csv (doi_o_wrong, rep_key, doi_o, evidence)
    A replication set aside as filed under the wrong original, filed under the original it really replicates (found by
    reading). Its result and the paper's details move with it; the original-side numbers of the wrong pairing do not.
data/curated/effect_original_exclusions.csv (effect, doi_o, reason, evidence)
    A source row that names an effect with the DOI of a different paper: that effect is not linked to that paper.

data/curated/effect_description_exclusions.csv (effect, reason, evidence)
    A source description that reading showed belongs to another claim, or is not a claim at all: it is not shown.

All are inputs to pipeline/registry.py; the build log reports any row that did not take effect.
"""
from __future__ import annotations

import csv

from .ids import norm_doi
from .load import ROOT

CURATED = ROOT / "data" / "curated"


def _rows(name: str, fields: tuple[str, ...]) -> list[dict]:
    p = CURATED / name
    if not p.exists():
        return []
    out, seen = [], set()
    with p.open(encoding="utf-8", newline="") as fh:
        for i, r in enumerate(csv.DictReader(fh), 2):
            row = {k: (r.get(k) or "").strip() for k in fields}
            if not all(row.values()):
                raise ValueError(f"{name} line {i}: every field is required ({', '.join(fields)})")
            for k in ("doi_o", "doi_r", "rep_key", "same_as", "doi_o_wrong"):
                if k in row:
                    # a replication without a DOI is identified by its address, as the registry keys it
                    row[k] = norm_doi(row[k]) or (row[k] if k in ("rep_key", "same_as") and row[k].startswith("http") else None)
                    if not row[k]:
                        raise ValueError(f"{name} line {i}: {k} is not a DOI")
            key = tuple(row[k] for k in fields if k != "evidence")
            if key in seen:
                raise ValueError(f"{name} line {i}: duplicate row {key}")
            seen.add(key)
            out.append(row)
    return out


def load() -> dict[str, list[dict]]:
    return {"effect_originals": _rows("effect_originals.csv", ("effect", "doi_o", "evidence")),
            "attempt_effects": _rows("attempt_effects.csv", ("doi_o", "doi_r", "effect", "evidence")),
            "attempt_exclusions": _rows("attempt_exclusions.csv", ("doi_o", "rep_key", "reason", "evidence")),
            "attempt_duplicates": _rows("attempt_duplicates.csv", ("doi_o", "rep_key", "same_as", "reason", "evidence")),
            "attempt_relinks": _rows("attempt_relinks.csv", ("doi_o_wrong", "rep_key", "doi_o", "evidence")),
            "effect_original_exclusions": _rows("effect_original_exclusions.csv", ("effect", "doi_o", "reason", "evidence")),
            "effect_description_exclusions": _rows("effect_description_exclusions.csv", ("effect", "reason", "evidence"))}
