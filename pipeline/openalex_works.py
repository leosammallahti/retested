"""OpenAlex's record (title, year, authors) for each DOI on the site: data/raw/local/openalex_paper_metadata.json,
fetched 2026-10-28 from the public OpenAlex API (see its 'source' field). The registry uses it only to replace a title
parsed out of a reference string, or a missing title, year or author list."""
from __future__ import annotations

import json

from .load import RAW

FILE = RAW / "local" / "openalex_paper_metadata.json"


def load() -> dict[str, dict]:
    return json.loads(FILE.read_text(encoding="utf-8"))["works"] if FILE.exists() else {}
