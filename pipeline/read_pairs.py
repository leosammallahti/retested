"""Papers read for Retested: data/curated/read_pairs.json.

Each reading answers, from the later paper's title and abstract, what the later paper is, whether it tests the earlier
finding, and what it found, with the words quoted from the abstract. A reading stands when two models agreed and every
quote was found word for word in the abstract, or when Claude (reading helpers, samples checked) decided a case
the models split on. The registry uses a reading three ways:

  * a pair FORRT's Replications & Reversals list cites becomes an attempt, labelled as read, only when the reading
    says it is a new-data replication (or a re-analysis) of that very finding;
  * an attempt on the site without a result gets the reading's result, under its own source label;
  * an attempt the reading shows is not a replication is set aside with the reason, only when FORRT coded no result
    for it; one FORRT did code is never overruled by a reading, it is listed for a person to read instead.
"""
from __future__ import annotations

import json

from .ids import norm_doi
from .load import ROOT

FILE = ROOT / "data" / "curated" / "read_pairs.json"
REPLICATION = {"NEW_DATA_REPLICATION", "REANALYSIS"}
OUTCOME = {"FOUND": "successful", "NOT_FOUND": "failed", "MIXED": "mixed", "NO_RESULT_STATED": "not_coded"}


def load() -> list[dict]:
    if not FILE.exists():
        return []
    out = []
    for r in json.loads(FILE.read_text(encoding="utf-8"))["readings"]:
        r = dict(r)
        r["doi_o"] = norm_doi(r.get("doi_o")) if r.get("doi_o") else None
        r["rep_key"] = norm_doi(r.get("rep_key")) or r.get("rep_key")
        out.append(r)
    return out
