"""Build deterministic text records for Retested-to-FORRT pair matching.

This module deliberately does no semantic matching and writes nothing under
``data/build``.  It turns the source text that already exists in Retested and
the pinned FORRT snapshot into two collections:

* ``query_records``: the source-reviewed rows in ``promoted_pairs.json``;
* ``corpus_records``: every FORRT row with a usable later-paper identity,
  grouped by stable original/later keys while retaining every source row.

The text used to identify an effect is kept separate from the text reporting
the later result.  The former may therefore be embedded without silently
turning a success/failure quote into the matching target.

Run with::

    .venv/bin/python -m pipeline.pair_summaries

The default output is ``data/discovery/pair_match_summaries.json``.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import os
import re
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence
from urllib.parse import unquote, urlsplit, urlunsplit

from .ids import is_na, norm_doi

ROOT = Path(__file__).resolve().parent.parent
PROMOTED = ROOT / "data" / "curated" / "promoted_pairs.json"
FORRT_ROOT = ROOT / "data" / "raw" / "forrt"
OUTPUT = ROOT / "data" / "discovery" / "pair_match_summaries.json"
LIVE_ROOT = Path("/tmp")
SCHEMA_VERSION = 1


@dataclass(frozen=True)
class SourceBatch:
    """Rows from one source with a shared, explicit provenance status."""

    source: str
    status: str
    path: str
    rows: Sequence[Mapping[str, object]]
    sha256: str | None = None


# Field aliases are ordered only to make the output easy to inspect.  All
# populated aliases are retained and attributed; none silently overwrites
# another source's wording.
COMPONENT_FIELDS: dict[str, tuple[str, ...]] = {
    "effect_claim": ("effect_claim",),
    "description": ("description",),
    "original_claim_quote": (
        "effect_claim_quote",
        "claim_text_o",
        "claim_text_orig",
        "claim_text_original",
    ),
    "replication_target": (
        "replication_target_quote",
        "target_quote",
        "replication_target",
    ),
    "original_title": ("original_title", "title_o", "title_original"),
    "replication_title": ("replication_title", "title_r", "title_replication"),
    "original_abstract": ("original_abstract", "abstract_o", "abstract_original"),
    "replication_abstract": ("replication_abstract", "abstract_r", "abstract_replication"),
    "observed_result": (
        "outcome_quote",
        "outcome_phrase",
        "reported_success_quote",
        "quote",
    ),
}

IDENTITY_COMPONENTS = (
    "effect_claim",
    "description",
    "original_claim_quote",
    "replication_target",
    "original_title",
    "replication_title",
    "original_abstract",
    "replication_abstract",
)

IDENTITY_LABELS = {
    "effect_claim": "Effect claim",
    "description": "Description",
    "original_claim_quote": "Original claim text",
    "replication_target": "Replication target",
    "original_title": "Original title",
    "replication_title": "Replication title",
    "original_abstract": "Original abstract",
    "replication_abstract": "Replication abstract",
}

OUTCOME_FIELDS = ("outcome", "reported_success", "result", "result_raw")

ORIGINAL_DOI_FIELDS = ("doi_o", "original_doi", "doi_original", "alt_identifier_o")
REPLICATION_DOI_FIELDS = (
    "doi_r",
    "doi_r_published",
    "replication_doi",
    "doi_replication",
    "alt_identifier_r",
)
ORIGINAL_URL_FIELDS = ("url_o", "original_url", "oa_url_o", "alt_identifier_o")
REPLICATION_URL_FIELDS = (
    "url_r",
    "replication_url",
    "oa_url_r",
    "alt_identifier_r",
)
ORIGINAL_OPENALEX_FIELDS = ("oa_work_id_o", "openalex_id_o", "original_openalex_id")
REPLICATION_OPENALEX_FIELDS = ("oa_work_id_r", "openalex_id_r", "replication_openalex_id", "work_id")

# Crossref's older SICI DOI syntax uses literal ``<`` and ``>`` around the
# article identifier (for example ``...24:2<125::AID-EAT2>3.0.CO;2-G``).
# Excluding angle brackets silently shortened those identifiers and prevented
# them from joining back to the promoted-pair audit.  Keep the matcher bounded
# to DOI-safe ASCII punctuation instead of treating the brackets as markup.
_DOI = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9+<>%]+", re.I)
_OPENALEX = re.compile(r"(?:https?://openalex\.org/)?(W\d+)$", re.I)
_HTML_ENTITY = re.compile(r"&(?:#\d+|#x[0-9a-f]+|[a-z]+);?", re.I)
_STATUS_RANK = {
    "source_reviewed": 0,
    "validated": 10,
    "published": 20,
    "extractor": 30,
    "pending_original_unresolved": 40,
    "unconfirmed": 50,
    "disputed": 60,
    "unresolved": 70,
    "historical": 80,
    "diagnostic": 85,
    "local": 90,
}

# An explicit membership-evidence allowlist.  In particular, do not broaden
# this to ``rglob('*.csv')``: the FORRT repository snapshot also contains
# literature-search results, keyword screens, model samples, and export logs.
# Those files may propose a paper but do not show that FORRT records a pair.
_CSV_SOURCE_RULES = (
    ("feeds/flora-extractor_extracted.csv", "extractor"),
    ("feeds/flora-extractor_keyed_link_disputed.csv", "disputed"),
    ("feeds/flora-extractor_no_original_found.csv", "unresolved"),
    ("feeds/flora-extractor_search_link_unconfirmed.csv", "unconfirmed"),
    ("feeds/flora-extractor_target_pending.csv", "pending_original_unresolved"),
    ("feeds/flora-extractor_unidentified_original.csv", "unresolved"),
    ("feeds/flora-validation_flora_entry_sheets.csv", "validated"),
    ("feeds/flora-validation_validated_export.csv", "validated"),
    ("fred-data/output_flora.csv", "published"),
    ("fred-data/output_flora_filtered.csv", "published"),
    ("fred-data/output_dup_outcome_conflicts.csv", "diagnostic"),
    ("fred-data/archive/additional_subjective_coding_with_ai.csv", "historical"),
    ("fred-data/archive/libre2.csv", "historical"),
    ("fred-data/archive/subj_coding_Roksana.csv", "historical"),
    ("fred-data/cos_score_integration_cos_test_set_phase1.csv", "historical"),
    ("osf/flora_osf_2026-03-21.csv", "historical"),
    ("repos/flora-pubpeer/data/flora.csv", "historical"),
    ("repos/flora-validation/data/extracted_*.csv", "historical"),
    ("repos/flora-validation/data/needs_manual_refs.csv", "unresolved"),
    ("repos/flora-validation/data/validated_export.csv", "historical"),
    ("repos/flora-validation/extracted.csv", "historical"),
    ("repos/flora-validation/output/flora_entry_sheets.csv", "historical"),
    # Immutable current-official comparison snapshot.  These replace the old
    # optional /tmp inputs for any reproducible overlap claim.
    ("snapshots/2026-09-26/flora-extractor_extracted.csv", "extractor"),
    ("snapshots/2026-09-26/flora-extractor_target_pending.csv", "pending_original_unresolved"),
    ("snapshots/2026-09-26/flora-validation_validated_export.csv", "validated"),
    ("snapshots/2026-09-26/fred-data_output_flora.csv", "published"),
    ("snapshots/2026-09-26/fred-data_output_flora_filtered.csv", "published"),
)


def canonical_dois(value: object) -> tuple[str, ...]:
    """Return every canonical DOI visible in a cell, not just the first one."""

    if is_na(value):
        return ()
    # HTML entities are export artefacts, not valid DOI content.  Remove them
    # before ``html.unescape`` can turn ``&amp;`` into a plausible suffix ampersand.
    raw = html.unescape(unquote(_HTML_ENTITY.sub("", str(value)))).strip()
    # A few exports concatenate identifiers with a semicolon or pipe.  Insert
    # a boundary only where the next token is visibly another DOI.
    raw = re.sub(
        r"[,;|](?=\s*(?:(?:https?://)?(?:dx\.)?doi\.org/|doi:\s*)?10\.\d{4,9}/)",
        " ",
        raw,
        flags=re.I,
    )
    found: list[str] = []
    for match in _DOI.finditer(raw):
        doi = norm_doi(match.group(0))
        if not doi:
            continue
        doi = re.sub(r"^(10\.\d{4,9})/+", r"\1/", doi)
        doi = doi.rstrip(".,;:)]}")
        if doi and doi not in found:
            found.append(doi)
    # ``norm_doi`` also understands a bare resolver prefix that the broad
    # matcher above can occasionally miss after unusual punctuation.
    if not found:
        doi = norm_doi(raw)
        if doi:
            found.append(re.sub(r"^(10\.\d{4,9})/+", r"\1/", doi))
    return tuple(found)


def canonical_doi(value: object) -> str | None:
    """The first canonical DOI in ``value`` (for callers needing one)."""

    values = canonical_dois(value)
    return values[0] if values else None


def _clean_text(value: object) -> str | None:
    if is_na(value):
        return None
    text = html.unescape(str(value))
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _title_key(value: object) -> tuple[str, str] | None:
    text = _clean_text(value)
    if not text:
        return None
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()
    normalized = " ".join(re.findall(r"[a-z0-9]+", normalized))
    if not normalized:
        return None
    digest = hashlib.sha256(normalized.encode()).hexdigest()
    return f"title-sha256:{digest}", text


def _canonical_url(value: object) -> str | None:
    text = _clean_text(value)
    if not text or not re.match(r"^https?://", text, re.I):
        return None
    try:
        parts = urlsplit(text)
    except ValueError:
        return None
    if not parts.netloc:
        return None
    path = re.sub(r"/+", "/", parts.path).rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def _openalex_key(value: object) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    match = _OPENALEX.fullmatch(text)
    return f"openalex:{match.group(1).upper()}" if match else None


def _values_by_field(row: Mapping[str, object], fields: Iterable[str]) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {}
    for field in fields:
        for doi in canonical_dois(row.get(field)):
            values.setdefault(doi, []).append(field)
    return values


def _identity_options(row: Mapping[str, object], side: str) -> list[dict]:
    """Identity alternatives for one side of a row, in evidence order.

    Every explicit DOI becomes an indexed option, allowing a preprint and its
    ``doi_r_published`` value to remain findable.  Non-DOI fallbacks produce a
    single stable option to avoid multiplying title/URL aliases into spurious
    pairs.
    """

    if side == "original":
        doi_fields = ORIGINAL_DOI_FIELDS
        url_fields = ORIGINAL_URL_FIELDS
        openalex_fields = ORIGINAL_OPENALEX_FIELDS
        title_fields = COMPONENT_FIELDS["original_title"]
    else:
        doi_fields = REPLICATION_DOI_FIELDS
        url_fields = REPLICATION_URL_FIELDS
        openalex_fields = REPLICATION_OPENALEX_FIELDS
        title_fields = COMPONENT_FIELDS["replication_title"]

    dois = _values_by_field(row, doi_fields)
    if dois:
        return [
            {"key": f"doi:{doi}", "kind": "doi", "value": doi, "fields": sorted(fields), "doi": doi}
            for doi, fields in sorted(dois.items())
        ]

    for field in url_fields:
        url = _canonical_url(row.get(field))
        if url:
            return [{"key": f"url:{url}", "kind": "url", "value": url, "fields": [field], "doi": None}]
        value = _clean_text(row.get(field))
        if value and field.startswith("alt_identifier"):
            normalized = value.casefold()
            return [{"key": f"alt:{normalized}", "kind": "alt_identifier", "value": value, "fields": [field], "doi": None}]

    for field in openalex_fields:
        key = _openalex_key(row.get(field))
        if key:
            return [{"key": key, "kind": "openalex", "value": key.split(":", 1)[1], "fields": [field], "doi": None}]

    for field in title_fields:
        found = _title_key(row.get(field))
        if found:
            key, text = found
            return [{"key": key, "kind": "title", "value": text, "fields": [field], "doi": None}]
    return []


def _source_row(row: Mapping[str, object], ordinal: int) -> object:
    value = row.get("_source_row")
    return value if value is not None else ordinal


def _row_sort_key(value: object) -> tuple[int, object]:
    if isinstance(value, int):
        return (0, value)
    text = str(value)
    return (0, int(text)) if text.isdigit() else (1, text)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def _provenance_sort_key(provenance: Mapping[str, object]) -> tuple:
    return (
        _STATUS_RANK.get(str(provenance["status"]), 999),
        str(provenance["source"]),
        str(provenance["path"]),
        _row_sort_key(provenance["row"]),
        str(provenance["id"]),
    )


def _record_id(original_key: str | None, replication_key: str) -> str:
    digest = hashlib.sha256(f"{original_key or '-'}\n{replication_key}".encode()).hexdigest()[:20]
    return f"ps_{digest}"


def _provenance_id(batch: SourceBatch, row_number: object, original: dict | None, replication: dict) -> str:
    raw = json.dumps(
        {
            "source": batch.source,
            "status": batch.status,
            "path": batch.path,
            "row": row_number,
            "original_key": original["key"] if original else None,
            "replication_key": replication["key"],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return "pv_" + hashlib.sha256(raw.encode()).hexdigest()[:20]


def _new_accumulator(original: dict | None, replication: dict) -> dict:
    return {
        "record_id": _record_id(original["key"] if original else None, replication["key"]),
        "record_kind": "pair" if original else "later_paper_status",
        "original_key": original["key"] if original else None,
        "replication_key": replication["key"],
        "doi_o": original.get("doi") if original else None,
        "doi_r": replication.get("doi"),
        "provenance": {},
        "identifiers": {"original": {}, "replication": {}},
        "components": {name: {} for name in COMPONENT_FIELDS},
        "outcome_labels": {},
    }


def _add_identifier(acc: dict, side: str, identifier: dict, provenance_id: str) -> None:
    key = (identifier["kind"], identifier["value"])
    item = acc["identifiers"][side].setdefault(
        key,
        {
            "kind": identifier["kind"],
            "value": identifier["value"],
            "fields": set(),
            "provenance_ids": set(),
        },
    )
    item["fields"].update(identifier["fields"])
    item["provenance_ids"].add(provenance_id)


def _add_component(acc: dict, name: str, text: str, provenance_id: str) -> None:
    item = acc["components"][name].setdefault(text, set())
    item.add(provenance_id)


def _component_sort_key(item: tuple[str, set[str]], provenance_by_id: Mapping[str, dict]) -> tuple:
    text, provenance_ids = item
    best = min((_provenance_sort_key(provenance_by_id[p]) for p in provenance_ids), default=(999,))
    return best, text.casefold(), text


_ABBREVIATIONS = {
    "al.", "approx.", "dr.", "e.g.", "etc.", "fig.", "i.e.", "mr.", "mrs.", "ms.", "prof.", "vs.",
}


def _first_sentence(text: str) -> str:
    """Take one readable source sentence without trying to rewrite it."""

    for match in re.finditer(r"[.!?](?=\s|$)", text):
        end = match.end()
        token = text[:end].rsplit(" ", 1)[-1].casefold()
        if token in _ABBREVIATIONS:
            continue
        return text[:end].strip()
    return text.strip().rstrip(";") + "."


def _title_sentence(label: str, text: str) -> str:
    return f"{label}: {_first_sentence(text)}"


def _match_summary(components: Mapping[str, list[dict]]) -> tuple[str | None, list[dict]]:
    """Select at most two source-derived sentences, never the observed result."""

    chosen: list[tuple[str, dict, str]] = []
    for name in ("effect_claim", "description", "original_claim_quote", "original_abstract"):
        if components[name]:
            item = components[name][0]
            chosen.append((name, item, _first_sentence(item["text"])))
            break
    if not chosen and components["original_title"]:
        item = components["original_title"][0]
        chosen.append(("original_title", item, _title_sentence("Original report", item["text"])))

    for name in ("replication_target",):
        if components[name]:
            item = components[name][0]
            chosen.append((name, item, _first_sentence(item["text"])))
            break
    else:
        if components["replication_title"]:
            item = components["replication_title"][0]
            chosen.append(("replication_title", item, _title_sentence("Later report", item["text"])))
        elif not chosen and components["replication_abstract"]:
            item = components["replication_abstract"][0]
            chosen.append(("replication_abstract", item, _first_sentence(item["text"])))

    # A repeated title/claim adds no information and would make a one-sentence
    # record look artificially complete.
    unique: list[tuple[str, dict, str]] = []
    seen: set[str] = set()
    for item in chosen:
        key = item[2].casefold()
        if key not in seen:
            seen.add(key)
            unique.append(item)
    if not unique:
        return None, []
    return " ".join(item[2] for item in unique[:2]), [
        {"component": name, "provenance_ids": list(component["provenance_ids"])}
        for name, component, _ in unique[:2]
    ]


def _finish_accumulator(acc: dict) -> dict:
    provenance = sorted(acc["provenance"].values(), key=_provenance_sort_key)
    provenance_by_id = {item["id"]: item for item in provenance}

    components: dict[str, list[dict]] = {}
    for name in COMPONENT_FIELDS:
        items = sorted(acc["components"][name].items(), key=lambda item: _component_sort_key(item, provenance_by_id))
        components[name] = [
            {"text": text, "provenance_ids": sorted(ids)}
            for text, ids in items
        ]

    identifiers: dict[str, list[dict]] = {}
    for side in ("original", "replication"):
        values = []
        for item in acc["identifiers"][side].values():
            values.append(
                {
                    "kind": item["kind"],
                    "value": item["value"],
                    "fields": sorted(item["fields"]),
                    "provenance_ids": sorted(item["provenance_ids"]),
                }
            )
        identifiers[side] = sorted(values, key=lambda item: (item["kind"], str(item["value"]).casefold()))

    identity_lines: list[str] = []
    seen_identity_text: set[str] = set()
    for name in IDENTITY_COMPONENTS:
        if not components[name]:
            continue
        text = components[name][0]["text"]
        key = text.casefold()
        if key in seen_identity_text:
            continue
        seen_identity_text.add(key)
        identity_lines.append(f"{IDENTITY_LABELS[name]}: {text}")

    outcomes = []
    for label, ids in acc["outcome_labels"].items():
        best = min((_provenance_sort_key(provenance_by_id[p]) for p in ids), default=(999,))
        outcomes.append((best, str(label).casefold(), str(label), sorted(ids)))
    outcomes.sort()

    match_summary, match_summary_components = _match_summary(components)

    missing = [name for name in COMPONENT_FIELDS if not components[name]]
    if not identity_lines:
        missing.append("identity_text")
    if not match_summary:
        missing.append("match_summary")
    if acc["original_key"] is None:
        missing.append("original_identity")

    return {
        "record_id": acc["record_id"],
        "record_kind": acc["record_kind"],
        "original_key": acc["original_key"],
        "replication_key": acc["replication_key"],
        "doi_o": acc["doi_o"],
        "doi_r": acc["doi_r"],
        "identity_text": "\n".join(identity_lines) if identity_lines else None,
        "match_summary": match_summary,
        "match_summary_components": match_summary_components,
        "observed_result": components["observed_result"][0]["text"] if components["observed_result"] else None,
        "outcome_labels": [
            {"label": label, "provenance_ids": ids}
            for _, _, label, ids in outcomes
        ],
        "identifiers": identifiers,
        "components": components,
        "missing_components": missing,
        "provenance": provenance,
    }


def _build_records(batches: Sequence[SourceBatch]) -> tuple[list[dict], list[dict]]:
    accumulators: dict[tuple[str | None, str], dict] = {}
    source_stats: list[dict] = []

    for batch in sorted(batches, key=lambda item: (item.source, item.status, item.path)):
        rows_with_record = 0
        pair_references = 0
        later_status_references = 0
        for ordinal, row in enumerate(batch.rows, 1):
            original_options = _identity_options(row, "original")
            replication_options = _identity_options(row, "replication")
            if not replication_options:
                continue
            rows_with_record += 1
            original_choices: list[dict | None] = original_options or [None]
            row_number = _source_row(row, ordinal)
            for original in original_choices:
                for replication in replication_options:
                    key = (original["key"] if original else None, replication["key"])
                    acc = accumulators.setdefault(key, _new_accumulator(original, replication))
                    provenance_id = _provenance_id(batch, row_number, original, replication)
                    provenance = {
                        "id": provenance_id,
                        "source": batch.source,
                        "status": batch.status,
                        "path": batch.path,
                        "row": row_number,
                        "original_identifier_fields": original["fields"] if original else [],
                        "replication_identifier_fields": replication["fields"],
                    }
                    acc["provenance"][provenance_id] = provenance
                    if original:
                        _add_identifier(acc, "original", original, provenance_id)
                    _add_identifier(acc, "replication", replication, provenance_id)

                    # Preserve aliases that did not become this record's key.
                    for alias in original_options:
                        _add_identifier(acc, "original", alias, provenance_id)
                    for alias in replication_options:
                        _add_identifier(acc, "replication", alias, provenance_id)

                    for component, fields in COMPONENT_FIELDS.items():
                        for field in fields:
                            text = _clean_text(row.get(field))
                            if text:
                                _add_component(acc, component, text, provenance_id)
                    for field in OUTCOME_FIELDS:
                        label = _clean_text(row.get(field))
                        if label:
                            acc["outcome_labels"].setdefault(label, set()).add(provenance_id)
                    if original:
                        pair_references += 1
                    else:
                        later_status_references += 1

        source_stats.append(
            {
                "source": batch.source,
                "status": batch.status,
                "path": batch.path,
                "sha256": batch.sha256,
                "rows_read": len(batch.rows),
                "rows_indexed": rows_with_record,
                "rows_without_later_identity": len(batch.rows) - rows_with_record,
                "pair_references": pair_references,
                "later_status_references": later_status_references,
            }
        )

    records = [_finish_accumulator(acc) for acc in accumulators.values()]
    records.sort(key=lambda item: (item["record_id"], item["original_key"] or "", item["replication_key"]))
    return records, source_stats


def build_document(
    promoted_rows: Sequence[Mapping[str, object]],
    forrt_batches: Sequence[SourceBatch],
    *,
    promoted_path: str = "data/curated/promoted_pairs.json",
    promoted_sha256: str | None = None,
) -> dict:
    """Build the complete deterministic query/corpus document from in-memory rows."""

    query_batch = SourceBatch(
        source="retested_promoted",
        status="source_reviewed",
        path=promoted_path,
        rows=promoted_rows,
        sha256=promoted_sha256,
    )
    query_records, query_stats = _build_records([query_batch])
    corpus_records, corpus_stats = _build_records(forrt_batches)

    exact_corpus = {
        (record["doi_o"], record["doi_r"]): record["record_id"]
        for record in corpus_records
        if record["record_kind"] == "pair" and record["doi_o"] and record["doi_r"]
    }
    for record in query_records:
        record["exact_corpus_record_id"] = exact_corpus.get((record["doi_o"], record["doi_r"]))

    return {
        "schema_version": SCHEMA_VERSION,
        "query_records": query_records,
        "corpus_records": corpus_records,
        "sources": sorted(query_stats + corpus_stats, key=lambda item: (item["source"], item["path"])),
    }


def _has_pair_columns(fields: Sequence[str] | None) -> bool:
    if not fields:
        return False
    names = set(fields)
    original = set(ORIGINAL_DOI_FIELDS + ORIGINAL_URL_FIELDS + ORIGINAL_OPENALEX_FIELDS + COMPONENT_FIELDS["original_title"])
    replication = set(
        REPLICATION_DOI_FIELDS
        + REPLICATION_URL_FIELDS
        + REPLICATION_OPENALEX_FIELDS
        + COMPONENT_FIELDS["replication_title"]
    )
    # A later-only pending source is still part of the paper-status corpus.
    return bool(names & replication) and bool(names & (original | set(COMPONENT_FIELDS["replication_abstract"])))


def _load_csv_batch(path: Path, source: str, status: str, provenance_path: str) -> SourceBatch | None:
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        if not _has_pair_columns(reader.fieldnames):
            return None
        rows: list[dict] = []
        for row_number, row in enumerate(reader, 2):
            row["_source_row"] = row_number
            rows.append(row)
    return SourceBatch(source=source, status=status, path=provenance_path, rows=rows, sha256=_file_sha256(path))


def load_csv_batches(forrt_root: Path = FORRT_ROOT) -> list[SourceBatch]:
    """Load allowlisted FORRT pair tables, never generic search outputs."""

    batches: list[SourceBatch] = []
    paths: dict[Path, str] = {}
    for pattern, status in _CSV_SOURCE_RULES:
        for path in sorted(forrt_root.glob(pattern)):
            previous = paths.setdefault(path, status)
            if previous != status:
                raise ValueError(f"conflicting pair-source statuses for {path}: {previous}, {status}")
    for path, status in sorted(paths.items(), key=lambda item: item[0].as_posix()):
        relative = path.relative_to(forrt_root)
        batch = _load_csv_batch(
            path,
            source="forrt_csv:" + relative.with_suffix("").as_posix(),
            status=status,
            provenance_path=(Path("data/raw/forrt") / relative).as_posix(),
        )
        if batch:
            batches.append(batch)
    return batches


_LIVE_FILES = {
    "retested_live_forrt_extractor.csv": ("forrt_live:flora_extractor", "extractor"),
    "retested_live_forrt_pending.csv": ("forrt_live:flora_extractor_pending", "pending_original_unresolved"),
    "retested_live_forrt_validated.csv": ("forrt_live:flora_validation", "validated"),
    "retested_live_forrt_flora.csv": ("forrt_live:fred_flora", "published"),
    "retested_live_forrt_flora_filtered.csv": ("forrt_live:fred_flora_filtered", "published"),
}


def load_live_batches(live_root: Path = LIVE_ROOT) -> list[SourceBatch]:
    """Load current official snapshots fetched by ``pipeline.forrt_provenance``.

    They are optional because a fresh checkout may not have run the live audit;
    their presence and row counts are explicit in the output's source manifest.
    """

    batches = []
    for filename, (source, status) in _LIVE_FILES.items():
        path = live_root / filename
        if not path.exists():
            continue
        batch = _load_csv_batch(path, source=source, status=status, provenance_path=str(path))
        if batch:
            batches.append(batch)
    return batches


def load_default_batches(forrt_root: Path = FORRT_ROOT, live_root: Path | None = None) -> list[SourceBatch]:
    """Load CSV snapshots plus FReD effect/legacy rows carrying claim text."""

    batches = load_csv_batches(forrt_root)
    if live_root is not None:
        batches.extend(load_live_batches(live_root))
    if forrt_root.resolve() != FORRT_ROOT.resolve():
        return batches

    # These readers join the JSON/XLSX representations used by the main
    # pipeline and expose FReD's description and original-claim fields.
    from .load import load_fred, load_legacy

    fred_rows = []
    for ordinal, row in enumerate(load_fred(), 1):
        item = dict(row)
        item["_source_row"] = item.get("row") or ordinal
        fred_rows.append(item)
    batches.append(
        SourceBatch(
            source="forrt_fred_effect_rows",
            status="published",
            path="data/raw/forrt/fred-data/output_FReD.xlsx",
            rows=fred_rows,
            sha256=_file_sha256(forrt_root / "fred-data" / "output_FReD.xlsx"),
        )
    )

    legacy = load_legacy()
    for sheet in ("data", "rr"):
        rows = []
        for ordinal, row in enumerate(legacy[sheet], 1):
            item = dict(row)
            item["_source_row"] = item.get("rowid") or item.get("id") or ordinal
            rows.append(item)
        batches.append(
            SourceBatch(
                source=f"forrt_fred_legacy_{sheet}",
                status="historical",
                path="data/raw/forrt/osf/version-history/FReD_2.4.1_2025-06-25.xlsx",
                rows=rows,
                sha256=_file_sha256(forrt_root / "osf" / "version-history" / "FReD_2.4.1_2025-06-25.xlsx"),
            )
        )
    return batches


def write_document(document: Mapping[str, object], output: Path = OUTPUT) -> None:
    """Atomically write stable JSON; no timestamp is added to deterministic data."""

    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    fd, temporary = tempfile.mkstemp(prefix=output.name + ".", dir=output.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
        os.chmod(temporary, 0o644)
        Path(temporary).replace(output)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--promoted", type=Path, default=PROMOTED)
    parser.add_argument("--forrt-root", type=Path, default=FORRT_ROOT)
    parser.add_argument("--live-root", type=Path, default=LIVE_ROOT)
    parser.add_argument(
        "--include-ephemeral-live", action="store_true",
        help="also include optional /tmp live files; never use this for a frozen comparison",
    )
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)

    from .promoted import load as load_promoted

    promoted_rows = load_promoted(args.promoted)
    document = build_document(
        promoted_rows,
        load_default_batches(args.forrt_root, args.live_root if args.include_ephemeral_live else None),
        promoted_path=_display_path(args.promoted),
        promoted_sha256=_file_sha256(args.promoted),
    )
    write_document(document, args.output)
    later_statuses = sum(record["record_kind"] == "later_paper_status" for record in document["corpus_records"])
    exact = sum(bool(record["exact_corpus_record_id"]) for record in document["query_records"])
    print(
        f"WROTE {args.output} queries={len(document['query_records'])} "
        f"corpus={len(document['corpus_records'])} later_status={later_statuses} exact_query_pairs={exact}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
