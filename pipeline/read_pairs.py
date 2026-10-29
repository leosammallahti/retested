"""Papers read for Retested: data/curated/read_pairs.json.

Each reading answers, from the later paper's title and abstract, what the later paper is, whether it tests the earlier
finding, and what it found, with the words quoted from the abstract. A reading stands when two models agreed and every
quote was found word for word in the abstract, or when Claude (reading helpers, samples checked) decided a case
the models split on. The registry uses a reading three ways:

  * a pair FORRT's Replications & Reversals list cites, or a pair a machine search found (the review queue), becomes
    an attempt, labelled as read, only when the reading says it is a new-data replication (or a re-analysis) of that
    very finding; a queue pair the reading shows is not one leaves the queue, with the reading as its reason;
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
# a pair not yet on the site becomes an attempt when a reading confirms it; what found the pair is kept with it:
# reading group -> (found_by, the words the site shows)
FOUND_BY = {
    "Replications & Reversals citation": ("forrt_list", "cited by FORRT's Replications & Reversals list"),
    "FORRT machine search": ("forrt_machine_search", "found by FORRT's machine search (the FLoRA extractor)"),
    "Retested machine search": ("retested_machine_search", "found by Retested's machine search"),
}
# which readings may add a pair to the counted record. A pair FORRT's famous-effects list cites was linked by FORRT's
# editors; a machine-found pair was linked by a machine, and two models agreeing that it is a replication of that
# original was measured wrong too often (12 of 200 read blind by Claude on 29 Oct 2026 replicate a different study),
# so such a pair stays in the review queue, read, until a reader has checked its link against both abstracts
# (data/curated/link_checks.csv, decision Y; pipeline/registry.py).
ADDS_TO_RECORD = {"Replications & Reversals citation"}
# sources that add evidence to a record without changing who put it there
EVIDENCE_ONLY = {"read", "reviewed"}


def forrt_record(a: dict) -> bool:
    """An attempt FORRT has: coded in its files, or a paper FORRT's list or machine search names, read for Retested."""
    return bool(set(a["sources"]) & {"flora", "fred", "legacy"}) or a.get("found_by", "").startswith("forrt")


def retested_addition(a: dict) -> bool:
    """An attempt only Retested has: a pair Retested's readers reviewed, or one Retested's search found and a reading
    confirmed."""
    own = set(a["sources"]) - EVIDENCE_ONLY
    return own == {"retested"} or (not own and a.get("found_by") == "retested_machine_search")


def load() -> list[dict]:
    if not FILE.exists():
        return []
    out = []
    for r in json.loads(FILE.read_text(encoding="utf-8"))["readings"]:
        r = dict(r)
        r["doi_o"] = norm_doi(r.get("doi_o")) if r.get("doi_o") else None
        r["rep_key"] = norm_doi(r.get("rep_key")) or r.get("rep_key")
        if (r.get("title_r") or "").strip().lower() in ("unknown", ""):
            r["title_r"] = None         # the reading item said "unknown" where no title was held
        out.append(r)
    return out
