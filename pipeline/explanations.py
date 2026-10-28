"""Curated, source-backed explanations of the *original* finding.

This is deliberately a small manually curated layer rather than another model
summary cache.  A finding explanation is useful on an effect page and as
pre-guess game context, so it may describe only the original study.  Later
replication results remain on attempt/reveal records.

``data/curated/finding_explanations.json`` is intentionally keyed by original
DOI. Keeping it separate from ``promoted_pairs.json`` lets one explanation
serve every later attempt. A Retested reviewed-pair anchor is useful when one
exists, but is optional: FORRT-only findings deserve the same source review.
"""
from __future__ import annotations

import copy
import json
import re
from datetime import date
from pathlib import Path
from typing import Mapping, Sequence
from urllib.parse import urlparse

from .ids import norm_doi

ROOT = Path(__file__).resolve().parent.parent
FILE = ROOT / "data" / "curated" / "finding_explanations.json"
HOLDS_FILE = ROOT / "data" / "curated" / "finding_explanation_review_holds_20260926.json"
SCHEMA_VERSION = 1
HOLD_STATES = {
    "held_source_unavailable",
    "held_source_insufficient",
    "held_nonempirical",
    "held_secondary_analysis",
    "held_source_mismatch",
}

# These phrases report or signal knowledge of a later attempt.  They are not
# allowed in displayable original-study context, where they would make the
# prediction game unfair and would conflate two different evidentiary claims.
LATER_OUTCOME_LEAK = re.compile(
    r"\b(?:replicat(?:e|ed|es|ing|ion)|reproduc(?:e|ed|es|ing|ibility)|retest(?:ed|ing)?|"
    r"later\s+(?:study|paper|experiment|result)|subsequent\s+(?:study|paper|experiment|result)|"
    r"did\s+not\s+replicat|failed\s+to\s+replicat|successful\s+(?:replicat|retest))\b",
    re.I,
)

# A display claim must say what the original study observed.  A recurrent
# packet error was to copy an abstract's objective ("the study examined
# whether ...") into the claim field.  Method and outcome fields already
# preserve what was tested; accepting an aim-only claim would leave the user
# without the original result they are being asked to predict about.
AIM_ONLY_CLAIM = re.compile(
    r"^(?:this|the)\s+(?:study|research|experiment|article|paper|survey)\s+"
    r"(?:aim(?:ed|s)?|examin(?:e|ed|es|ing)|evaluat(?:e|ed|es|ing)|"
    r"investigat(?:e|ed|es|ing)|test(?:ed|s|ing)|assess(?:ed|es|ing)|"
    r"explor(?:e|ed|es|ing)|surveyed|compar(?:e|ed|es|ing)|analy[sz](?:e|ed|es|ing))\b",
    re.I,
)


class ExplanationValidationError(ValueError):
    """A curated explanation cannot safely enter the built finding payload."""


def _text(value: object, where: str, minimum: int = 1) -> str:
    if not isinstance(value, str) or value != value.strip() or len(value) < minimum:
        raise ExplanationValidationError(f"{where}: expected a trimmed string of at least {minimum} characters")
    return value


def _https(value: object, where: str) -> str:
    text = _text(value, where, 12)
    parsed = urlparse(text)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ExplanationValidationError(f"{where}: expected a public HTTPS URL")
    return text


def _day(value: object, where: str) -> str:
    text = _text(value, where, 10)
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise ExplanationValidationError(f"{where}: expected YYYY-MM-DD") from exc
    if parsed.isoformat() != text:
        raise ExplanationValidationError(f"{where}: expected YYYY-MM-DD")
    return text


def _doi(value: object, where: str) -> str:
    text = _text(value, where, 8)
    if norm_doi(text) != text:
        raise ExplanationValidationError(f"{where}: expected a normalized bare DOI")
    return text


def _display_text(value: object, where: str, minimum: int = 12) -> str:
    text = _text(value, where, minimum)
    if LATER_OUTCOME_LEAK.search(text):
        raise ExplanationValidationError(f"{where}: must describe only the original study, not a later outcome")
    return text


def _promoted_index(rows: Sequence[Mapping[str, object]] | None) -> dict[tuple[str, str], Mapping[str, object]]:
    return {
        (str(row["doi_o"]), str(row["doi_r"])): row
        for row in (rows or [])
        if row.get("doi_o") and row.get("doi_r")
    }


def validate_document(document: object, promoted_rows: Sequence[Mapping[str, object]] | None = None) -> dict[str, dict]:
    """Validate and canonicalize the committed explanation document.

    ``promoted_pair_doi_r`` is an optional provenance anchor, never display
    context. When supplied, it must identify an existing source-reviewed pair
    for the same original and reuse that pair's reviewed original URL. In
    particular, no later outcome text is copied from the promoted row.
    """
    if not isinstance(document, dict):
        raise ExplanationValidationError(f"{FILE}: expected an object")
    if set(document) != {"schema_version", "findings"}:
        raise ExplanationValidationError(f"{FILE}: expected only schema_version and findings")
    if document.get("schema_version") != SCHEMA_VERSION:
        raise ExplanationValidationError(f"{FILE}: unsupported schema_version")
    raw_findings = document.get("findings")
    if not isinstance(raw_findings, dict):
        raise ExplanationValidationError(f"{FILE}: findings must be an object keyed by original DOI")

    promoted = _promoted_index(promoted_rows)
    out: dict[str, dict] = {}
    for raw_doi in sorted(raw_findings):
        doi_o = _doi(raw_doi, f"{FILE.name} finding key")
        record = raw_findings[raw_doi]
        where = f"{FILE.name} {doi_o}"
        if not isinstance(record, dict):
            raise ExplanationValidationError(f"{where}: expected an object")
        if set(record) != {"original", "source", "review", "provenance"}:
            raise ExplanationValidationError(f"{where}: expected original, source, review, and provenance")

        original = record["original"]
        if not isinstance(original, dict) or set(original) != {"claim", "method", "population", "outcome_measure"}:
            raise ExplanationValidationError(f"{where}: original needs claim, method, population, and outcome_measure")
        clean_original = {
            "claim": _display_text(original["claim"], f"{where} original.claim", 20),
            "method": _display_text(original["method"], f"{where} original.method", 20),
            "population": _display_text(original["population"], f"{where} original.population", 8),
            "outcome_measure": _display_text(original["outcome_measure"], f"{where} original.outcome_measure", 8),
        }
        if AIM_ONLY_CLAIM.search(clean_original["claim"]):
            raise ExplanationValidationError(
                f"{where} original.claim: must state an observed original result, not only a research aim"
            )

        source = record["source"]
        if not isinstance(source, dict) or set(source) != {"url", "evidence"}:
            raise ExplanationValidationError(f"{where}: source needs url and evidence")
        source_url = _https(source["url"], f"{where} source.url")
        evidence = source["evidence"]
        if not isinstance(evidence, list) or not evidence:
            raise ExplanationValidationError(f"{where}: source.evidence must be a nonempty list")
        supported: set[str] = set()
        clean_evidence = []
        for index, item in enumerate(evidence, 1):
            item_where = f"{where} source.evidence[{index}]"
            if not isinstance(item, dict) or set(item) != {"location", "quote", "supports"}:
                raise ExplanationValidationError(f"{item_where}: needs location, quote, and supports")
            supports = item["supports"]
            if (not isinstance(supports, list) or not supports
                    or any(field not in clean_original for field in supports)
                    or len(set(supports)) != len(supports)):
                raise ExplanationValidationError(
                    f"{item_where}: supports must be distinct original field names"
                )
            clean_evidence.append({
                "location": _text(item["location"], f"{item_where} location", 3),
                "quote": _display_text(item["quote"], f"{item_where} quote", 12),
                "supports": sorted(supports),
            })
            supported.update(supports)
        missing_support = sorted(set(clean_original) - supported)
        if missing_support:
            raise ExplanationValidationError(
                f"{where}: source.evidence does not support {', '.join(missing_support)}"
            )
        clean_source = {
            "url": source_url,
            # Evidence order does not change what it supports. Canonicalizing
            # it makes identical parallel packets merge as no-ops.
            "evidence": sorted(clean_evidence, key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True)),
        }

        review = record["review"]
        if not isinstance(review, dict) or set(review) != {"state", "reviewed_by", "reviewed_on"}:
            raise ExplanationValidationError(f"{where}: review needs state, reviewed_by, and reviewed_on")
        if review["state"] != "source_reviewed":
            raise ExplanationValidationError(f"{where}: only source_reviewed explanations may enter the build")
        clean_review = {
            "state": "source_reviewed",
            "reviewed_by": _text(review["reviewed_by"], f"{where} review.reviewed_by", 3),
            "reviewed_on": _day(review["reviewed_on"], f"{where} review.reviewed_on"),
        }

        provenance = record["provenance"]
        if not isinstance(provenance, dict) or set(provenance) != {"kind", "promoted_pair_doi_r"}:
            raise ExplanationValidationError(f"{where}: provenance needs kind and promoted_pair_doi_r")
        if provenance["kind"] != "manual_source_review":
            raise ExplanationValidationError(f"{where}: provenance.kind must be manual_source_review")
        raw_doi_r = provenance["promoted_pair_doi_r"]
        if raw_doi_r is not None and not isinstance(raw_doi_r, str):
            raise ExplanationValidationError(f"{where}: provenance.promoted_pair_doi_r must be a DOI or null")
        doi_r = _doi(raw_doi_r, f"{where} provenance.promoted_pair_doi_r") if raw_doi_r is not None else None
        if doi_r:
            source_pair = promoted.get((doi_o, doi_r))
            if promoted_rows is not None and source_pair is None:
                raise ExplanationValidationError(f"{where}: provenance pair is not a reviewed promoted pair")
            if source_pair and source_pair.get("original_source_url") != source_url:
                raise ExplanationValidationError(f"{where}: source.url must match the anchored promoted-pair original source")

        out[doi_o] = {
            "original": clean_original,
            "source": clean_source,
            "review": clean_review,
            "provenance": {"kind": "manual_source_review", "promoted_pair_doi_r": doi_r},
        }
    return out


def load(path: Path = FILE, promoted_rows: Sequence[Mapping[str, object]] | None = None) -> dict[str, dict]:
    """Load the versioned, manually curated explanation layer (an empty layer is valid)."""
    if not path.exists():
        return {}
    return validate_document(json.loads(path.read_text(encoding="utf-8")), promoted_rows)


def validate_holds(document: object, accepted: Mapping[str, dict]) -> list[dict]:
    """Validate the durable source-review hold queue.

    Holds preserve completed screening work without presenting it as finished
    explanation content.  A DOI cannot be both held and accepted: when a later
    reader obtains sufficient primary evidence, the accepted explanation is
    the durable record and the obsolete hold must leave this current queue.
    """
    if not isinstance(document, dict) or set(document) != {"schema_version", "reviewed_on", "scope", "holds"}:
        raise ExplanationValidationError(
            f"{HOLDS_FILE.name}: expected schema_version, reviewed_on, scope, and holds"
        )
    if document.get("schema_version") != SCHEMA_VERSION:
        raise ExplanationValidationError(f"{HOLDS_FILE.name}: unsupported schema_version")
    _day(document.get("reviewed_on"), f"{HOLDS_FILE.name} reviewed_on")
    _text(document.get("scope"), f"{HOLDS_FILE.name} scope", 20)
    raw_holds = document.get("holds")
    if not isinstance(raw_holds, list):
        raise ExplanationValidationError(f"{HOLDS_FILE.name}: holds must be a list")

    out, seen = [], set()
    for index, raw in enumerate(raw_holds, 1):
        where = f"{HOLDS_FILE.name} holds[{index}]"
        if not isinstance(raw, dict) or set(raw) != {"doi_o", "state", "reason", "source_url", "source_batches"}:
            raise ExplanationValidationError(
                f"{where}: expected doi_o, state, reason, source_url, and source_batches"
            )
        doi_o = _doi(raw.get("doi_o"), f"{where} doi_o")
        if doi_o in seen:
            raise ExplanationValidationError(f"{where}: duplicate held DOI {doi_o}")
        if doi_o in accepted:
            raise ExplanationValidationError(f"{where}: {doi_o} is already an accepted explanation")
        seen.add(doi_o)
        state = raw.get("state")
        if state not in HOLD_STATES:
            raise ExplanationValidationError(f"{where}: unsupported hold state {state!r}")
        source_url = raw.get("source_url")
        if source_url is not None:
            source_url = _https(source_url, f"{where} source_url")
        batches = raw.get("source_batches")
        if (not isinstance(batches, list) or not batches
                or any(not isinstance(batch, str) or not batch.strip() for batch in batches)
                or batches != sorted(set(batches))):
            raise ExplanationValidationError(f"{where}: source_batches must be a sorted nonempty unique string list")
        out.append({
            "doi_o": doi_o,
            "state": state,
            "reason": _text(raw.get("reason"), f"{where} reason", 20),
            "source_url": source_url,
            "source_batches": batches,
        })
    if [row["doi_o"] for row in out] != sorted(seen):
        raise ExplanationValidationError(f"{HOLDS_FILE.name}: holds must be sorted by doi_o")
    return out


def load_holds(accepted: Mapping[str, dict], path: Path = HOLDS_FILE) -> list[dict]:
    """Load and cross-check the current review holds; a missing queue is valid."""
    if not path.exists():
        return []
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExplanationValidationError(f"{path}: cannot read the explanation hold queue") from exc
    return validate_holds(document, accepted)


def attach(findings: Mapping[str, dict], explanations: Mapping[str, dict], doi_folds: Mapping[str, str] | None = None,
           withdrawn: Mapping[str, str] | None = None) -> list[str]:
    """Attach explanations to their built finding, failing on an orphaned DOI.

    ``withdrawn`` names originals whose every attempt was set aside after reading (data/curated/
    attempt_exclusions.csv), with the reason: their explanation is set aside too, and reported, not attached.

    The attached copy is intentionally limited to original-study material.  A
    future caller cannot accidentally turn provenance or a later verdict into
    pre-guess text by reusing a promoted-pair record.
    """
    folds = doi_folds or {}
    notes: list[str] = []
    for doi_o, explanation in explanations.items():
        canonical = folds.get(doi_o, doi_o)
        if canonical not in findings and canonical in (withdrawn or {}):
            notes.append(f"explanation for {doi_o} set aside: its only attempts were set aside ({withdrawn[canonical]})")
            continue
        if canonical not in findings:
            raise ExplanationValidationError(
                f"{FILE.name} {doi_o}: no built finding exists for this original DOI"
            )
        findings[canonical]["explanation"] = copy.deepcopy(explanation)
    return notes
