"""FORRT's Replications & Reversals list, as FORRT keeps it in two files.

    the 'FORRT R&R (editable)' sheet of the FReD 2.4.1 workbook   (load.load_legacy()["rr"])
    osf/sub-datasets/231026_forrt_with_journals.xlsx              (one row per effect and cited later paper,
                                                                    with the later paper's abstract)

Each row names an effect, its original paper and a later paper the list cites about it. The list calls the later
papers "critiques": many are replications, others are reviews, meta-analyses or commentaries, and FORRT has coded
no result for most of them. So a pair from this list is not counted as a replication attempt until it has been read;
until then it waits in the queue (queue.build_rr). Rows FORRT itself marks as not a replication are kept and labelled.
"""
from __future__ import annotations

import re

import pandas as pd

from .ids import is_na, norm_doi
from .load import FORRT

LIST_FILE = FORRT / "osf" / "sub-datasets" / "231026_forrt_with_journals.xlsx"
_DOI = re.compile(r"10\.\d{4,9}/[^\s<>\"]+")


def _doi(*vals) -> str | None:
    """The first DOI in the given cells (a bare DOI, a doi.org link, or a DOI inside a reference)."""
    for v in vals:
        if v is None or is_na(v):
            continue
        m = _DOI.search(str(v))
        if m:
            d = norm_doi(m.group(0).rstrip(".,;>)"))
            if d:
                return d
    return None


def _text(v) -> str | None:
    return None if v is None or is_na(v) or not str(v).strip() else str(v).strip()


def rows(legacy_rr: list[dict]) -> list[dict]:
    """Every row of both files, in file order, with its identifiers: nothing is dropped here."""
    out = []
    for i, r in enumerate(legacy_rr, 1):
        ex = _text(r.get("exclusion"))
        out.append({
            "file": "Replications & Reversals sheet", "row": i, "effect": _text(r.get("effect")),
            "doi_o": norm_doi(r.get("doi_original")), "doi_r": norm_doi(r.get("doi_replication")),
            "ref_o": _text(r.get("ref_original")), "ref_r": _text(r.get("ref_replication")),
            "abstract_r": None, "critique": None,
            "forrt_excluded": ex if ex and re.search(r"not a replication|meta-analysis", ex, re.I) else None,
            "forrt_note": ex,
        })
    if LIST_FILE.exists():
        df = pd.read_excel(LIST_FILE, dtype=str)
        for i, r in enumerate(df.to_dict("records"), 1):
            out.append({
                "file": "Replications & Reversals list file", "row": i, "effect": _text(r.get("Effect")),
                "doi_o": _doi(r.get("Original_doi"), r.get("Original_doi_cr"), r.get("Original_doi_url"), r.get("Original_Link")),
                "doi_r": _doi(r.get("Critique_doi"), r.get("Critique_doi_parsed"), r.get("Critique_Link"), r.get("Critique_ref_apa")),
                "ref_o": _text(r.get("Original_ref_apa")) or _text(r.get("Original_Paper_title")),
                "ref_r": _text(r.get("Critique_ref_apa")) or _text(r.get("Critique_text")),
                "abstract_r": _text(r.get("Critique_Abstract")), "critique": _text(r.get("Critique_text")),
                "forrt_excluded": None, "forrt_note": None,
            })
    return out
