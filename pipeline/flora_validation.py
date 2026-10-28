"""FLoRA's validation files: pairs FORRT has read and validated, some of them not yet in FLoRA's export.

    feeds/flora-validation_flora_entry_sheets.csv   FORRT's validation entry sheets
    feeds/flora-validation_validated_export.csv     FORRT's validated export

The registry (pipeline/registry.py) adds a validated pair that no other FORRT file carries, as FLoRA data with its
outcome and quote, so a pair FORRT has validated is never missing from the site. The FORRT ledger accounts for the rest.
"""
from __future__ import annotations

import pandas as pd

from .ids import norm_doi
from .load import FORRT

FILES = (("flora-validation_flora_entry_sheets.csv", "FLoRA validation sheets"),
         ("flora-validation_validated_export.csv", "FLoRA validated export"))


def rows() -> list[dict]:
    out = []
    for name, label in FILES:
        p = FORRT / "feeds" / name
        if not p.exists():
            continue
        for i, r in enumerate(pd.read_csv(p, dtype=str, keep_default_na=False).to_dict("records"), 1):
            rep = norm_doi(r.get("doi_r")) or norm_doi(r.get("alt_identifier_r")) or (r.get("alt_identifier_r") or "").strip() or (r.get("url_r") or "").strip()
            out.append({"file": label, "row": i, "doi_o": norm_doi(r.get("doi_o")), "rep_key": rep or None,
                        "type": r.get("type") or None, "outcome": r.get("outcome") or None,
                        "outcome_quote": r.get("outcome_quote") or None, "outcome_quote_source": r.get("outcome_quote_source") or None,
                        "ref_o": r.get("ref_o") or None, "ref_r": r.get("ref_r") or None, "title_r": r.get("title_r") or None,
                        "year_r": r.get("year_r") or None, "abstract_r": r.get("abstract_r") or None})
    return out
