"""Download the raw sources the build needs, as recorded in data/raw/forrt/MANIFEST.json.

    python -m pipeline fetch            # download missing files, verify sha256
    python -m pipeline fetch --refresh  # re-download everything from upstream (FORRT updates FLoRA several times a week)

Raw files are never edited. A refresh records the new hash in the manifest, so every build states exactly what it used.
"""
from __future__ import annotations

import hashlib
import gzip
import json
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

from .load import FORRT, ROOT, SOURCES

MANIFEST = FORRT / "MANIFEST.json"
UA = {"User-Agent": "Retested/0.1 (+https://github.com/; mailto:leosammallahti@gmail.com)"}

# Files the pipeline reads, relative to data/raw/forrt/. Everything else in the manifest is reference material.
REQUIRED = [str(p.relative_to(FORRT)).replace("\\", "/") for k, p in SOURCES.items() if str(p).startswith(str(FORRT))]
COMPARISON_INPUTS = "comparison_inputs"


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def frozen_snapshot_bytes(entry: dict[str, Any], assets_root: Path | None = None) -> tuple[bytes | None, str | None]:
    """Return a verified raw payload from a committed gzip snapshot, if declared.

    The original upstream URL remains the source provenance.  This fallback is
    deliberately only for a historical public payload whose moving upstream
    ref can no longer reproduce the declared bytes.
    """

    assets_root = assets_root or ROOT
    rel = entry.get("frozen_snapshot")
    if not rel:
        return None, None
    if not isinstance(rel, str) or not isinstance(entry.get("frozen_snapshot_sha256"), str):
        return None, "frozen snapshot metadata is incomplete"
    snapshot = (assets_root / rel).resolve()
    try:
        snapshot.relative_to(assets_root.resolve())
    except ValueError:
        return None, "frozen snapshot path escapes the project root"
    if not snapshot.is_file():
        return None, f"frozen snapshot is missing: {rel}"
    blob = snapshot.read_bytes()
    if _sha(blob) != entry["frozen_snapshot_sha256"]:
        return None, f"frozen snapshot hash mismatch: {rel}"
    try:
        raw = gzip.decompress(blob)
    except OSError:
        return None, f"frozen snapshot is not a valid gzip payload: {rel}"
    if _sha(raw) != entry.get("sha256"):
        return None, f"frozen snapshot raw hash mismatch: {rel}"
    return raw, None


def required_paths(manifest: dict[str, Any]) -> list[str]:
    """Return every raw file the normal build and frozen comparison consume."""

    paths = list(REQUIRED)
    for path in manifest.get(COMPARISON_INPUTS, []):
        if path not in paths:
            paths.append(path)
    # Kept for compatibility with the first pinned registry snapshot.  New
    # comparison files belong in ``comparison_inputs`` above.
    for entry in manifest.get("files", []):
        path = entry.get("path")
        if entry.get("purpose") == "forrt_comparison_snapshot" and path not in paths:
            paths.append(path)
    return paths


def input_problems(manifest: dict[str, Any], root: Path = FORRT) -> list[str]:
    """Check that every required input exists and matches its manifest hash."""

    entries = {entry.get("path"): entry for entry in manifest.get("files", [])}
    problems: list[str] = []
    for rel in required_paths(manifest):
        entry = entries.get(rel)
        if not entry:
            problems.append(f"required input absent from manifest: {rel}")
            continue
        if not str(entry.get("source_url", "")).startswith("http"):
            problems.append(f"required input has no source URL: {rel}")
            continue
        expected = entry.get("sha256")
        if not isinstance(expected, str) or len(expected) != 64:
            problems.append(f"required input has no SHA-256: {rel}")
            continue
        _, snapshot_problem = frozen_snapshot_bytes(entry)
        if snapshot_problem:
            problems.append(f"required input {snapshot_problem}")
        path = root / rel
        if not path.exists():
            problems.append(f"required input is missing: {rel}")
        elif _sha(path.read_bytes()) != expected:
            problems.append(f"required input hash mismatch: {rel}")
    return problems


def validate_inputs(root: Path = FORRT, manifest_path: Path = MANIFEST) -> list[str]:
    return input_problems(json.loads(manifest_path.read_text(encoding="utf-8")), root)


def run(refresh: bool = False) -> int:
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = {e["path"]: e for e in man["files"]}
    required = required_paths(man)
    bad = 0
    for rel in required:
        e = entries.get(rel)
        if not e or not str(e.get("source_url", "")).startswith("http"):
            print(f"  ! {rel}: no source URL in manifest")
            bad += 1
            continue
        path = FORRT / rel
        # A frozen snapshot is an integrity-checked recovery asset for an
        # unrecoverable historical public payload.  Do not let --refresh turn
        # that declared historical input into a different moving-HEAD file.
        if e.get("frozen_snapshot"):
            data, snapshot_problem = frozen_snapshot_bytes(e)
            if snapshot_problem or data is None:
                print(f"  ! {rel}: {snapshot_problem or 'frozen snapshot has no payload'}")
                bad += 1
                continue
            if path.exists():
                ok = _sha(path.read_bytes()) == e["sha256"]
                print(f"  {'ok ' if ok else 'CHANGED'} {rel} (frozen snapshot source)")
                bad += 0 if ok else 1
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            print(f"  restored {rel} from frozen snapshot ({len(data) / 1e6:.1f} MB)")
            continue
        if path.exists() and not refresh:
            ok = _sha(path.read_bytes()) == e["sha256"]
            print(f"  {'ok ' if ok else 'CHANGED'} {rel}")
            bad += 0 if ok else 1
            continue
        url = e["source_url"].split()[0]
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
        new = _sha(data)
        changed = new != e.get("sha256")
        if changed and not refresh:
            # A missing file used to overwrite the declared hash here, turning
            # upstream drift into a successful ordinary fetch.  Keep the
            # manifest authoritative unless the caller explicitly refreshes.
            print(f"  CHANGED {rel} (download hash differs; not saved without --refresh)")
            bad += 1
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        if refresh:
            e.update(sha256=new, bytes=len(data), retrieved_on=str(date.today()))
        print(f"  {'updated' if changed else 'same   '} {rel} ({len(data) / 1e6:.1f} MB)")
    if refresh:
        MANIFEST.write_text(json.dumps(man, indent=2, ensure_ascii=False), encoding="utf-8")
    if bad:
        print(f"{bad} file(s) missing a URL or differing from the manifest. Run with --refresh to accept upstream changes.")
    return 1 if bad else 0
