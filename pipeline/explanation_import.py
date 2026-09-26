"""Fail-closed importer for parallel manual source-review explanation packets.

Packets use the exact committed ``finding_explanations.json`` schema.  They
are not a staging area for unchecked summaries: every packet is validated as
a source-reviewed explanation before it can be merged.  The importer accepts
only new records or byte-for-byte-equivalent canonical records for the same
original; competing prose for one DOI must be resolved by a curator first.
"""
from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from . import explanations, load, registry
from .ids import EffectLedger

LEDGER = load.ROOT / "data" / "curated" / "registry" / "effect_ids.csv"


@dataclass(frozen=True)
class MergeReport:
    added: tuple[str, ...]
    unchanged: tuple[str, ...]
    total: int


@contextmanager
def _curation_lock(target: Path, *, exclusive: bool):
    """Serialize imports sharing a curated directory on the primary Linux VM.

    Locking the directory, rather than a lockfile that might be replaced or
    accidentally committed, keeps the read--merge--atomic-write transaction on
    one inode. A check/dry-run takes a shared lock so it observes a complete
    import. The fallback keeps local non-POSIX development usable; the VM is
    the authoritative concurrent-writer environment.
    """
    try:
        import fcntl
    except ImportError:  # pragma: no cover - the production VM is POSIX.
        yield
        return
    descriptor = os.open(target.parent, os.O_RDONLY)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _document(records: Mapping[str, dict]) -> dict:
    """The sole on-disk shape, with a deterministic DOI order."""
    return {
        "schema_version": explanations.SCHEMA_VERSION,
        "findings": {doi: records[doi] for doi in sorted(records)},
    }


def _read(path: Path, promoted_rows: Sequence[Mapping[str, object]]) -> dict[str, dict]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise explanations.ExplanationValidationError(f"{path}: cannot read a JSON explanation packet") from exc
    return explanations.validate_document(raw, promoted_rows)


def _fold(doi: str, doi_folds: Mapping[str, str]) -> str:
    """Follow DOI aliases defensively; current registry folds are one hop."""
    seen = set()
    while doi in doi_folds and doi not in seen:
        seen.add(doi)
        doi = doi_folds[doi]
    return doi


def merge_records(
    existing: Mapping[str, dict],
    packets: Sequence[tuple[str, Mapping[str, dict]]],
    finding_dois: set[str],
    doi_folds: Mapping[str, str] | None = None,
) -> tuple[dict, MergeReport]:
    """Merge already schema-validated records, rejecting ambiguity and orphans.

    DOI aliases are canonicalized before comparison, so two parallel packets
    cannot create two explanations for the same built finding through a known
    malformed DOI spelling.
    """
    folds = doi_folds or {}
    merged: dict[str, dict] = {}
    owners: dict[str, str] = {}
    added, unchanged = [], []

    for label, records in [("existing curated layer", existing), *packets]:
        for doi in sorted(records):
            canonical = _fold(doi, folds)
            if canonical not in finding_dois:
                raise explanations.ExplanationValidationError(
                    f"{label} {doi}: no built finding exists for this original DOI"
                )
            record = records[doi]
            if canonical not in merged:
                merged[canonical] = record
                owners[canonical] = label
                if label != "existing curated layer":
                    added.append(canonical)
                continue
            if merged[canonical] != record:
                raise explanations.ExplanationValidationError(
                    f"conflicting explanations for {canonical}: {owners[canonical]} and {label}"
                )
            if label != "existing curated layer":
                unchanged.append(canonical)

    return _document(merged), MergeReport(
        added=tuple(sorted(set(added))),
        unchanged=tuple(sorted(set(unchanged))),
        total=len(merged),
    )


def _write_atomic(path: Path, document: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        handle.write(rendered)
        temporary = Path(handle.name)
    try:
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def import_packets(
    packet_paths: Sequence[Path],
    target: Path,
    promoted_rows: Sequence[Mapping[str, object]],
    finding_dois: set[str],
    doi_folds: Mapping[str, str] | None = None,
    *,
    write: bool = False,
) -> MergeReport:
    """Plan a packet merge and optionally atomically write it.

    ``write=False`` is used by both CLI check modes.  It follows exactly the
    same validation and merge path as a real import, so a successful dry run
    is meaningful rather than a shallow JSON syntax check.
    """
    target_resolved = target.resolve()
    if any(path.resolve() == target_resolved for path in packet_paths):
        raise explanations.ExplanationValidationError("an import packet cannot also be the target curated layer")
    with _curation_lock(target, exclusive=write):
        existing = _read(target, promoted_rows)
        packets = [(str(path), _read(path, promoted_rows)) for path in packet_paths]
        merged, report = merge_records(existing, packets, finding_dois, doi_folds)
        # A successful explicit import also canonicalizes key/evidence ordering.
        # Check and dry-run remain strictly non-mutating.
        if write:
            _write_atomic(target, merged)
        return report


def _built_findings(existing: Mapping[str, dict], promoted_rows: list[dict]) -> tuple[set[str], dict[str, str]]:
    """Build only the graph needed for the orphan gate; it never writes data."""
    src = {
        "flora": load.load_flora(), "fred": load.load_fred(), "legacy": load.load_legacy(),
        "famous": load.load_famous(), "openalex": load.load_openalex(), "merges": load.load_merges(),
        "promoted": promoted_rows, "explanations": dict(existing),
    }
    graph = registry.build(src, EffectLedger(LEDGER))
    return set(graph["findings"]), graph.get("doi_folds") or {}


def run(packet_paths: Sequence[Path], target: Path = explanations.FILE, *, check: bool = False, dry_run: bool = False) -> int:
    """CLI entry point. Check and dry-run validate fully but never write."""
    if check and dry_run:
        raise ValueError("--check and --dry-run cannot be used together")
    if not packet_paths:
        raise ValueError("at least one explanation packet is required")
    promoted_rows = load.load_promoted()
    existing = _read(target, promoted_rows)
    finding_dois, doi_folds = _built_findings(existing, promoted_rows)
    report = import_packets(
        packet_paths, target, promoted_rows, finding_dois, doi_folds,
        write=not (check or dry_run),
    )
    action = "checked" if check else "dry run" if dry_run else "imported"
    print(
        f"explanation {action}: added {len(report.added)}, unchanged {len(report.unchanged)}, "
        f"total {report.total}"
    )
    return 0
