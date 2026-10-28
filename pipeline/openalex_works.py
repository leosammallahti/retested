"""OpenAlex's record (title, year, authors) for each DOI on the site: data/raw/local/openalex_paper_metadata.json,
fetched 2026-10-28 from the public OpenAlex API (see its 'source' field). The registry uses it only to replace a title
parsed out of a reference string, or a missing title, year or author list."""
from __future__ import annotations

import json

from .load import RAW

FILE = RAW / "local" / "openalex_paper_metadata.json"


def load() -> dict[str, dict]:
    return json.loads(FILE.read_text(encoding="utf-8"))["works"] if FILE.exists() else {}


LATER = RAW / "local" / "later_paper_records.json"


def later_records() -> dict[str, dict]:
    """Records of later papers OpenAlex does not hold, keyed by the attempt's rep_key: OSF's public API for OSF pages
    and OSF DOIs, the DOI registry (doi.org) for other DOIs; fetched 2026-10-28 (pipeline/repair/details/
    fetch_osf_registry.py). Used only to fill a missing title, author list or year."""
    return {k: v for k, v in json.loads(LATER.read_text(encoding="utf-8"))["records"].items() if v} if LATER.exists() else {}
