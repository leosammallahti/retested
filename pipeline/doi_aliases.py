"""Flag candidate DOI aliases of already curated replication articles.

This is a conservative pre-model screen: exact DOI, or the same later-paper
title, nearby year and original DOI. A title collision is flagged for human review,
never automatically added or removed from curated data.
"""
from __future__ import annotations

import argparse
from difflib import SequenceMatcher
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Iterable


def normalized_doi(value: Any) -> str:
    doi = str(value or "").strip().casefold()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi.startswith(prefix):
            doi = doi[len(prefix):]
    return doi


def normalized_title(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).casefold()
    return re.sub(r"[^a-z0-9]+", "", text)


def _near_year(first: Any, second: Any) -> bool:
    try:
        return abs(int(first) - int(second)) <= 5
    except (TypeError, ValueError):
        return False


def _read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def find_aliases(
    candidates: Iterable[dict[str, Any]],
    sources: Iterable[dict[str, Any]],
    curated: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return possible duplicate articles for pre-review filtering."""
    source_index: dict[str, dict[str, Any]] = {}
    for row in sources:
        for key in ("replication_doi", "replication_candidate_id", "candidate_id"):
            value = row.get(key)
            if value:
                source_index[normalized_doi(value)] = row

    exact_index: dict[str, dict[str, Any]] = {}
    title_index: dict[str, list[dict[str, Any]]] = {}
    original_index: dict[str, list[dict[str, Any]]] = {}
    for row in curated:
        doi = normalized_doi(row.get("doi_r"))
        if doi:
            exact_index[doi] = row
        title = normalized_title(row.get("replication_title"))
        if title:
            title_index.setdefault(title, []).append(row)
        original = normalized_doi(row.get("doi_o"))
        if original:
            original_index.setdefault(original, []).append(row)

    results = []
    for candidate in candidates:
        doi = normalized_doi(candidate.get("doi_r") or candidate.get("candidate_id"))
        source = source_index.get(doi, {})
        title = source.get("replication_title") or candidate.get("replication_title")
        year = source.get("replication_year") or candidate.get("replication_year")
        original = normalized_doi(candidate.get("doi_o") or source.get("original_doi"))
        exact = exact_index.get(doi)
        # Preprint and journal records for the same study commonly carry
        # different publication years. Exact title plus exact original DOI is
        # a conservative human-review flag across a small year window.
        aliases = [
            row for row in title_index.get(normalized_title(title), [])
            if _near_year(row.get("replication_year"), year)
            and normalized_doi(row.get("doi_o")) == original
        ] if title and year and original else []
        title_key = normalized_title(title)
        # Minor title edits between a preprint and journal article are common.
        # Flag only long, nearly identical titles tied to the same original,
        # and leave the final identity decision to source review.
        possible = [
            row for row in original_index.get(original, [])
            if title_key and len(title_key) >= 50
            and _near_year(row.get("replication_year"), year)
            and SequenceMatcher(None, title_key, normalized_title(row.get("replication_title"))).ratio() >= .95
        ] if original and year and not aliases else []
        match = exact or (aliases[0] if aliases else None) or (possible[0] if possible else None)
        results.append({
            "candidate_doi": doi,
            "candidate_title": title or "",
            "status": (
                "already_curated_exact_doi" if exact
                else "likely_doi_alias" if aliases
                else "possible_doi_alias" if possible
                else "unmatched"
            ),
            "curated_doi": match.get("doi_r") if match else None,
            "curated_original_doi": match.get("doi_o") if match else None,
        })
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidates", help="Candidate JSONL")
    parser.add_argument("sources", help="Quote-bearing source JSONL")
    parser.add_argument(
        "--curated",
        default="data/curated/promoted_pairs.json",
        help="Curated promotion manifest",
    )
    args = parser.parse_args()
    curated = json.loads(Path(args.curated).read_text(encoding="utf-8"))
    results = find_aliases(_read_jsonl(args.candidates), _read_jsonl(args.sources), curated)
    print(json.dumps({"n": len(results), "records": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
