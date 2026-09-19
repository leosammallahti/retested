"""Readers for the pinned raw sources. Every reader returns plain Python records; nothing here decides semantics."""
from __future__ import annotations

import json
import pickle
import re
from pathlib import Path

import pandas as pd

from .ids import is_na, norm_doi

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
FORRT = RAW / "forrt"
CACHE = ROOT / "data" / "cache"

SOURCES = {
    "flora": FORRT / "fred-data" / "output_flora.csv",
    "fred_explorer": FORRT / "feeds" / "fred-apps_explorer-data.json",
    "fred_output": FORRT / "fred-data" / "output_FReD.xlsx",
    "fred_legacy": FORRT / "osf" / "version-history" / "FReD_2.4.1_2025-06-25.xlsx",
    "famous": RAW / "local" / "docx_parsed_entries.json",
    "openalex": RAW / "local" / "openalex_original_enrichment.json",
    "extractor": FORRT / "feeds" / "flora-extractor_extracted.csv",
    "extractor_pending": FORRT / "feeds" / "flora-extractor_target_pending.csv",
    "citation": FORRT / "fred-data" / "output_citation.txt",
}


def _cached(name: str, src: Path, fn):
    """Pickle cache keyed by source mtime+size; the raw file stays the source of truth."""
    CACHE.mkdir(parents=True, exist_ok=True)
    st = src.stat()
    key = f"{st.st_mtime_ns}-{st.st_size}"
    p = CACHE / f"{name}.pkl"
    if p.exists():
        with p.open("rb") as f:
            k, val = pickle.load(f)
        if k == key:
            return val
    val = fn()
    with p.open("wb") as f:
        pickle.dump((key, val), f)
    return val


def clean(x):
    if is_na(x):
        return None
    if isinstance(x, str):
        s = x.strip()
        return s or None
    if isinstance(x, float) and x.is_integer():
        return int(x)
    return x


def short_authors(raw) -> str | None:
    """'Family', 'Family & Family', or 'Family et al.' from FLoRA's JSON-ish author field."""
    if is_na(raw):
        return None
    fams = re.findall(r"['\"]family['\"]\s*:\s*['\"]([^'\"]+)['\"]", str(raw))
    if not fams:
        return None
    if len(fams) == 1:
        return fams[0]
    if len(fams) == 2:
        return f"{fams[0]} & {fams[1]}"
    return f"{fams[0]} et al."


def to_int(x):
    try:
        v = int(float(x))
        return v if 1800 < v < 2100 or v > 0 else None
    except (TypeError, ValueError):
        return None


def load_flora() -> list[dict]:
    df = pd.read_csv(SOURCES["flora"], dtype=str, keep_default_na=False)
    out = []
    for r in df.to_dict("records"):
        out.append({k: clean(v) for k, v in r.items()})
    return out


def load_fred() -> list[dict]:
    """FReD effect rows: fred-apps explorer-data (r-scale ES + 7 criteria) joined row-wise to output_FReD (bibliographic + quotes)."""

    def build():
        ex = json.loads(SOURCES["fred_explorer"].read_text(encoding="utf-8"))["studies"]
        out = pd.read_excel(SOURCES["fred_output"])
        assert len(ex) == len(out), "explorer-data and output_FReD are no longer row-aligned"
        rows = []
        for s, o in zip(ex, out.to_dict("records")):
            assert (norm_doi(s["doi_o"]) or "") == (norm_doi(o["doi_o"]) or ""), "row alignment broken"
            rows.append({
                "row": s["id"],
                "fred_id": clean(o.get("fred_id")),
                "doi_o": norm_doi(s["doi_o"]),
                "doi_r": norm_doi(s["doi_r"]) or norm_doi(s.get("url_r")),
                "url_r": clean(s.get("url_r")),
                "study_o": clean(s.get("study_o")),
                "study_r": clean(s.get("study_r")),
                "description": clean(s.get("description")),
                "claim_text_o": clean(s.get("claim_text_o")),
                "discipline": clean(s.get("discipline")),
                "tags": clean(s.get("tags")),
                "r_o": s.get("es_o"),
                "r_r": s.get("es_r"),
                "es_type_o": clean(s.get("es_type_o")),
                "n_o": s.get("n_o"),
                "n_r": s.get("n_r"),
                "ci_o": [s.get("ci_lower_o"), s.get("ci_upper_o")],
                "ci_r": [s.get("ci_lower_r"), s.get("ci_upper_r")],
                "p_o": s.get("p_o"),
                "p_r": s.get("p_r"),
                "power_r": s.get("power_r"),
                "criteria": {k: (v or {}).get("outcome") for k, v in (s.get("outcomes") or {}).items()},
                "reported_success": clean(s.get("reported_success")),
                "quote": clean(o.get("reported_success_quote")),
                "quote_source": clean(o.get("reported_success_quote_source")),
                "author_overlap_pct": clean(o.get("author_overlap_pct")),
                "prereg_r": clean(o.get("prereg_r")),
                "title_o": clean(o.get("title_o")),
                "journal_o": clean(o.get("journal_o")),
                "year_o": to_int(o.get("year_o")),
                "title_r": clean(o.get("title_r")),
                "journal_r": clean(o.get("journal_r")),
                "year_r": to_int(o.get("year_r")),
                "ref_o": clean(o.get("ref_o")),
                "ref_r": clean(o.get("ref_r")),
                "author_o": short_authors(o.get("author_o")),
                "author_r": short_authors(o.get("author_r")),
            })
        return rows

    return _cached("fred", SOURCES["fred_explorer"], build)


def _legacy_sheet(sheet: str) -> list[dict]:
    df = pd.read_excel(SOURCES["fred_legacy"], sheet_name=sheet, skiprows=[1, 2])
    return [{k: clean(v) for k, v in r.items()} for r in df.to_dict("records")]


def load_legacy() -> dict[str, list[dict]]:
    """Legacy crowdsourced FReD 2.4.1: the 'Data' sheet and FORRT's Replications & Reversals sheet."""
    return _cached("legacy", SOURCES["fred_legacy"], lambda: {
        "data": _legacy_sheet("Data"),
        "rr": _legacy_sheet("FORRT R&R (editable)"),
    })


def load_famous() -> list[dict]:
    return json.loads(SOURCES["famous"].read_text(encoding="utf-8"))


def load_openalex() -> dict[str, dict]:
    def build():
        raw = json.loads(SOURCES["openalex"].read_text(encoding="utf-8"))
        out = {}
        for doi, rec in raw.items():
            d = (rec or {}).get("data") or {}
            if not d:
                continue
            topics = d.get("topics") or []
            out[norm_doi(doi)] = {
                "title": d.get("title"),
                "year": d.get("publication_year"),
                "cited_by": d.get("cited_by_count"),
                "counts_by_year": {int(c["year"]): c["cited_by_count"] for c in (d.get("counts_by_year") or [])},
                "is_retracted": d.get("is_retracted"),
                "topic": topics[0]["display_name"] if topics else None,
                "subfield": topics[0]["subfield"]["display_name"] if topics else None,
                "field": topics[0]["field"]["display_name"] if topics else None,
            }
        return out

    return _cached("openalex", SOURCES["openalex"], build)


def load_extractor() -> list[dict]:
    df = pd.read_csv(SOURCES["extractor"], dtype=str, keep_default_na=False)
    return [{k: clean(v) for k, v in r.items()} for r in df.to_dict("records")]


def load_citation() -> str:
    return SOURCES["citation"].read_text(encoding="utf-8").strip()


def load_merges() -> list[dict]:
    """Curated effect merges: data/curated/merges.yaml -> [{into: name, from: [names], reason: str}]."""
    import yaml
    p = ROOT / "data" / "curated" / "merges.yaml"
    if not p.exists():
        return []
    return yaml.safe_load(p.read_text(encoding="utf-8")) or []
