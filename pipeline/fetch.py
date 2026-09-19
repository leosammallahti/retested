"""Download the raw sources the build needs, as recorded in data/raw/forrt/MANIFEST.json.

    python -m pipeline fetch            # download missing files, verify sha256
    python -m pipeline fetch --refresh  # re-download everything from upstream (FORRT updates FLoRA several times a week)

Raw files are never edited. A refresh records the new hash in the manifest, so every build states exactly what it used.
"""
from __future__ import annotations

import hashlib
import json
import urllib.request
from datetime import date

from .load import FORRT, SOURCES

MANIFEST = FORRT / "MANIFEST.json"
UA = {"User-Agent": "Retested/0.1 (+https://github.com/; mailto:leosammallahti@gmail.com)"}

# Files the pipeline reads, relative to data/raw/forrt/. Everything else in the manifest is reference material.
REQUIRED = [str(p.relative_to(FORRT)).replace("\\", "/") for k, p in SOURCES.items() if str(p).startswith(str(FORRT))]


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def run(refresh: bool = False) -> int:
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = {e["path"]: e for e in man["files"]}
    bad = 0
    for rel in REQUIRED:
        e = entries.get(rel)
        if not e or not str(e.get("source_url", "")).startswith("http"):
            print(f"  ! {rel}: no source URL in manifest")
            bad += 1
            continue
        path = FORRT / rel
        if path.exists() and not refresh:
            ok = _sha(path.read_bytes()) == e["sha256"]
            print(f"  {'ok ' if ok else 'CHANGED'} {rel}")
            bad += 0 if ok else 1
            continue
        url = e["source_url"].split()[0]
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        new = _sha(data)
        changed = new != e.get("sha256")
        e.update(sha256=new, bytes=len(data), retrieved_on=str(date.today()))
        print(f"  {'updated' if changed else 'same   '} {rel} ({len(data) / 1e6:.1f} MB)")
    MANIFEST.write_text(json.dumps(man, indent=2, ensure_ascii=False), encoding="utf-8")
    if bad:
        print(f"{bad} file(s) missing a URL or differing from the manifest. Run with --refresh to accept upstream changes.")
    return 1 if bad else 0
