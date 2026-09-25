"""Inventory proposed later papers and exact pairs before source review.

The site graph merges FORRT's coded pairs with source-reviewed Retested overlays.
A later paper already on the site may still have a new original-paper pair;
the exact pair is the unit that must be checked.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from .ids import norm_doi
from .load import ROOT, load_known_replication_dois

ATTEMPTS = ROOT / "data" / "build" / "attempts.json"
PROMOTED = ROOT / "data" / "curated" / "promoted_pairs.json"


def _doi(value: str | None) -> str | None:
    normalized = norm_doi(value)
    return normalized.replace("//", "/") if normalized else None


def _title(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def inventory(dois: list[str], pairs: list[dict] | None = None) -> dict:
    if not ATTEMPTS.exists():
        raise FileNotFoundError(f"{ATTEMPTS}: build the site data first")
    if PROMOTED.exists() and ATTEMPTS.stat().st_mtime < PROMOTED.stat().st_mtime:
        raise RuntimeError("Built attempts are older than curated pairs; run python -m pipeline build first")
    attempts = json.loads(ATTEMPTS.read_text(encoding="utf-8"))
    by_rep: dict[str, list[dict]] = defaultdict(list)
    by_pair: dict[tuple[str, str], dict] = {}
    by_title: dict[str, list[dict]] = defaultdict(list)
    for attempt in attempts.values():
        doi_o, doi_r = _doi(attempt.get("doi_o")), _doi(attempt.get("doi_r"))
        if not doi_o or not doi_r:
            continue
        by_rep[doi_r].append(attempt)
        by_pair[(doi_o, doi_r)] = attempt
        title = _title(attempt.get("title_r"))
        if title:
            by_title[title].append(attempt)
    raw_known = {_doi(doi) for doi in load_known_replication_dois()}
    requested = {_doi(doi) for doi in dois}
    pair_rows = pairs or []
    requested.update(_doi(row.get("doi_r")) for row in pair_rows)
    requested.discard(None)
    papers = []
    for doi_r in sorted(requested):
        site_rows = by_rep.get(doi_r, [])
        papers.append({
            "doi_r": doi_r,
            "site_pair_count": len(site_rows),
            "forrt_raw_knows_later_paper": doi_r in raw_known,
            "site_originals": sorted({_doi(a["doi_o"]) for a in site_rows}),
            "site_forrt_pair_count": sum(
                any(source != "retested" for source in a.get("sources", []))
                for a in site_rows
            ),
        })
    checked_pairs = []
    for row in pair_rows:
        doi_o, doi_r = _doi(row.get("doi_o")), _doi(row.get("doi_r"))
        if not doi_o or not doi_r:
            raise ValueError("Each pair needs doi_o and doi_r")
        existing = by_pair.get((doi_o, doi_r))
        same_title = [
            a for a in by_title.get(_title(row.get("replication_title")), [])
            if _doi(a.get("doi_r")) != doi_r
        ] if row.get("replication_title") else []
        same_work = [
            a for a in same_title if _doi(a.get("doi_o")) == doi_o
        ]
        checked_pairs.append({
            "doi_o": doi_o,
            "doi_r": doi_r,
            "already_on_site": existing is not None,
            "site_sources": existing.get("sources", []) if existing else [],
            "same_title_site_versions": sorted({_doi(a["doi_r"]) for a in same_title}),
            "same_work_same_original_on_site": bool(same_work),
        })
    return {"papers": papers, "pairs": checked_pairs}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dois", nargs="*", help="Later-paper DOIs to inventory")
    parser.add_argument("--pairs", type=Path, help="JSON list of {doi_o, doi_r} rows to check")
    args = parser.parse_args()
    pair_rows = json.loads(args.pairs.read_text(encoding="utf-8")) if args.pairs else []
    if not isinstance(pair_rows, list):
        parser.error("--pairs must contain a JSON list")
    print(json.dumps(inventory(args.dois, pair_rows), indent=2))


if __name__ == "__main__":
    main()

