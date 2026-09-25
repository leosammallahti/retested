"""Source-checked Retested additions to the counted effect and attempt registry.

The file is deliberately separate from immutable FORRT raw data. One row is one
(original DOI, replication DOI, named effect) pair. The same replication may
appear in several rows when it retests several different original papers.
Nothing from discovery enters this layer without explicit source evidence.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from .ids import norm_doi, norm_name

FILE = Path(__file__).resolve().parent.parent / "data" / "curated" / "promoted_pairs.json"

REQUIRED_STRINGS = (
    "candidate_id", "doi_o", "doi_r", "effect_name", "effect_claim",
    "effect_claim_quote", "original_source_url", "original_title",
    "original_authors", "replication_title", "replication_authors",
    "replication_source_url", "replication_target_quote", "outcome",
    "outcome_quote", "outcome_quote_source", "reviewed_by", "reviewed_on",
)
REQUIRED_YEARS = ("original_year", "replication_year")
OPTIONAL = {
    "original_journal", "replication_journal", "original_date",
    "replication_date", "preregistration_status", "duplicate_candidate_ids", "review_note", "outcome_adjudication",
}
OUTCOMES = {"successful", "failed", "mixed"}
QUOTE_SOURCES = {"abstract", "full_text", "paper"}
PREREG = {"yes", "no", "unknown"}
ADJUDICATIONS = {"primary_result", "effect_scope"}
LEAK = re.compile(r"replicat|reproduc|debunk|retract|did not hold|holds? up", re.I)


def _https(value: str, where: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError(f"{where}: expected a public HTTPS source URL")


def _doi(value: str, where: str) -> None:
    if norm_doi(value) != value:
        raise ValueError(f"{where}: expected a normalized bare DOI")


def _day(value: str, where: str) -> date:
    try:
        result = date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{where}: expected YYYY-MM-DD") from exc
    if result.isoformat() != value:
        raise ValueError(f"{where}: expected YYYY-MM-DD")
    return result


def validate(rows: object) -> list[dict]:
    if not isinstance(rows, list):
        raise ValueError(f"{FILE}: expected a JSON list of reviewed pairs")
    pairs: set[tuple[str, str]] = set()
    effects: dict[tuple[str, str], str] = {}
    for n, row in enumerate(rows, 1):
        where = f"{FILE.name} row {n}"
        if not isinstance(row, dict):
            raise ValueError(f"{where}: expected an object")
        missing = (set(REQUIRED_STRINGS) | set(REQUIRED_YEARS)) - row.keys()
        extra = row.keys() - set(REQUIRED_STRINGS) - set(REQUIRED_YEARS) - OPTIONAL
        if missing or extra:
            raise ValueError(f"{where}: missing {sorted(missing)}, unexpected {sorted(extra)}")
        for field in REQUIRED_STRINGS:
            value = row[field]
            if not isinstance(value, str) or not value.strip() or value != value.strip():
                raise ValueError(f"{where}: {field} must be a nonempty, trimmed string")
        for field in REQUIRED_YEARS:
            value = row[field]
            if type(value) is not int or not 1800 <= value <= 2100:
                raise ValueError(f"{where}: {field} must be a plausible integer year")
        for field in OPTIONAL - {"duplicate_candidate_ids"}:
            if field in row and row[field] is not None and (
                not isinstance(row[field], str) or not row[field].strip()
                or row[field] != row[field].strip()
            ):
                raise ValueError(f"{where}: {field} must be a trimmed string or null")
        aliases = row.setdefault("duplicate_candidate_ids", [])
        if not isinstance(aliases, list) or any(not isinstance(x, str) or not x.strip() for x in aliases):
            raise ValueError(f"{where}: duplicate_candidate_ids must be a list of IDs")
        if len(set(aliases)) != len(aliases) or row["candidate_id"] in aliases:
            raise ValueError(f"{where}: duplicate candidate IDs must be distinct")
        _doi(row["doi_o"], f"{where} doi_o")
        _doi(row["doi_r"], f"{where} doi_r")
        cid = row["candidate_id"]
        candidate_doi = norm_doi(cid)
        if candidate_doi and candidate_doi != row["doi_r"]:
            raise ValueError(f"{where}: candidate_id DOI differs from doi_r")
        if not candidate_doi and not re.fullmatch(r"W[0-9]+", cid):
            raise ValueError(f"{where}: candidate_id must be a DOI or OpenAlex work id")
        if row["doi_o"] == row["doi_r"]:
            raise ValueError(f"{where}: original and replication are the same paper")
        pair = (row["doi_o"], row["doi_r"])
        if pair in pairs:
            raise ValueError(f"{where}: duplicate original/replication pair {pair}")
        pairs.add(pair)
        for field in ("original_source_url", "replication_source_url"):
            _https(row[field], f"{where} {field}")
        if row["outcome"] not in OUTCOMES:
            raise ValueError(f"{where}: outcome must be successful, failed, or mixed")
        if row["outcome_quote_source"] not in QUOTE_SOURCES:
            raise ValueError(f"{where}: outcome_quote_source must be abstract, full_text, or paper")
        if row.get("preregistration_status", "unknown") not in PREREG:
            raise ValueError(f"{where}: preregistration_status must be yes, no, or unknown")
        if row.get("outcome_adjudication"):
            if row["outcome_adjudication"] not in ADJUDICATIONS:
                raise ValueError(f"{where}: unknown outcome adjudication")
            if "FLoRA" not in (row.get("review_note") or ""):
                raise ValueError(f"{where}: outcome adjudication must explain the FLoRA disagreement")
        if LEAK.search(row["effect_claim"]):
            raise ValueError(f"{where}: effect_claim describes the retest rather than the original finding")
        if len(row["effect_claim"]) < 25 or len(row["effect_claim_quote"]) < 12:
            raise ValueError(f"{where}: original effect claim needs a specific, sourced result")
        if len(row["replication_target_quote"]) < 12 or len(row["outcome_quote"]) < 12:
            raise ValueError(f"{where}: replication target and outcome need source quotes")
        if not norm_name(row["effect_name"]):
            raise ValueError(f"{where}: missing effect name")
        _day(row["reviewed_on"], f"{where} reviewed_on")
        oy, ry = row["original_year"], row["replication_year"]
        if oy > ry:
            raise ValueError(f"{where}: the original cannot postdate the replication")
        if oy == ry:
            if not row.get("original_date") or not row.get("replication_date"):
                raise ValueError(f"{where}: same-year pair needs both publication dates")
            if _day(row["original_date"], f"{where} original_date") >= _day(
                row["replication_date"], f"{where} replication_date"
            ):
                raise ValueError(f"{where}: original must predate replication")
        for field, year in (("original_date", oy), ("replication_date", ry)):
            if row.get(field) and _day(row[field], f"{where} {field}").year != year:
                raise ValueError(f"{where}: {field} disagrees with year")
        # Within one original, an effect label must mean the same directional
        # claim in every accepted row. A different claim needs a different name.
        effect_key = (norm_name(row["effect_name"]), row["doi_o"])
        previous = effects.setdefault(effect_key, row["effect_claim"])
        if previous != row["effect_claim"]:
            raise ValueError(f"{where}: inconsistent claim for {effect_key}")
        row.setdefault("preregistration_status", "unknown")
    return rows


def load(path: Path = FILE) -> list[dict]:
    if not path.exists():
        return []
    rows = validate(json.loads(path.read_text(encoding="utf-8")))
    # Check the discovery identity when its source files are present. The
    # reviewed overlay remains independently rebuildable if caches vanish.
    root = path.resolve().parent.parent
    records = {}
    for source in (root / "discovery" / "triaged.json",
                   root / "curated" / "psychology_alternative_finds.json"):
        if source.exists():
            found = json.loads(source.read_text(encoding="utf-8"))
            if not isinstance(found, list):
                raise ValueError(f"{source}: expected a list")
            records.update({r.get("cid"): r for r in found if isinstance(r, dict) and r.get("cid")})
    for row in rows:
        cid = row["candidate_id"]
        candidate = records.get(cid)
        if candidate and norm_doi(candidate.get("doi_r")) != row["doi_r"]:
            raise ValueError(f"{FILE.name}: {cid} points at a different replication DOI in discovery")
        if not candidate and not norm_doi(cid):
            raise ValueError(f"{FILE.name}: OpenAlex candidate {cid} cannot be checked against discovery")
        title_key = re.sub(r"[^a-z0-9]", "", row["replication_title"].lower())
        for alias in row["duplicate_candidate_ids"]:
            other = records.get(alias)
            if not other:
                raise ValueError(f"{FILE.name}: duplicate candidate {alias} is absent from discovery")
            other_title = re.sub(r"[^a-z0-9]", "", (other.get("title_r") or "").lower())
            if (other_title != title_key or other.get("year_r") != row["replication_year"]
                    or norm_doi(other.get("doi_r")) not in (None, row["doi_r"])):
                raise ValueError(f"{FILE.name}: duplicate candidate {alias} is not the same study")
            if candidate:
                primary_authors = set(candidate.get("author_surnames_r") or [])
                alias_authors = set(other.get("author_surnames_r") or [])
                if primary_authors and alias_authors and (
                    2 * len(primary_authors & alias_authors) < min(len(primary_authors), len(alias_authors))
                ):
                    raise ValueError(f"{FILE.name}: duplicate candidate {alias} has different authors")
    return rows
