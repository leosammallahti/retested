"""Identifier rules: DOI normalization, FORRT-compatible hashes, slugs, the effect-id ledger."""
from __future__ import annotations

import csv
import hashlib
import re
import unicodedata
from pathlib import Path

_DOI = re.compile(r"10\.\d{4,9}/\S+", re.I)
_ENTITY = re.compile(r"&(?:#\d+|#x[0-9a-f]+|[a-z]+);?", re.I)
_NA = {"", "na", "nan", "none", "null", "n/a"}


def is_na(x) -> bool:
    return x is None or (isinstance(x, float) and x != x) or str(x).strip().lower() in _NA


def norm_doi(x) -> str | None:
    """Lower-case bare DOI (no resolver prefix), or None."""
    if is_na(x):
        return None
    s = str(x).strip().lower()
    s = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", s)
    s = s.removeprefix("doi:").strip()
    # A DOI never contains an HTML entity. One arrives in the sources as "...352321&#8203" — a zero-width space
    # that survived a copy out of a web page — and mints a second paper for a study we already hold.
    s = _ENTITY.sub("", s)
    m = _DOI.search(s)
    return m.group(0).rstrip(".,;)") if m else None


def hash3(doi: str) -> str:
    """FORRT's privacy-preserving prefix: first 3 hex chars of md5(doi)."""
    return hashlib.md5(doi.lower().encode()).hexdigest()[:3]


def slugify(text: str, maxlen: int = 70) -> str:
    t = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t.lower()).strip("-")
    return (t[:maxlen].rstrip("-")) or "x"


def doi_slug(doi: str) -> str:
    """URL-safe, readable, collision-guarded slug for a DOI."""
    return slugify(doi, 80) + "-" + hashlib.md5(doi.encode()).hexdigest()[:4]


def norm_name(name: str) -> str:
    """Effect-name key. Keeps parentheticals: 'moral priming (cleanliness)' != 'moral priming'."""
    t = unicodedata.normalize("NFKC", str(name)).lower().strip()
    t = t.replace("’", "'").replace("–", "-").replace("—", "-")
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[.;:,]+$", "", t)
    return t


_B32 = "0123456789abcdefghjkmnpqrstvwxyz"


class EffectLedger:
    """Append-only mapping name-key -> opaque effect id. Ids are never reassigned or reused."""

    def __init__(self, path: Path):
        self.path = path
        self.ids: dict[str, str] = {}
        self.new: list[tuple[str, str]] = []
        if path.exists():
            with path.open(encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f):
                    self.ids[row["key"]] = row["effect_id"]

    def get(self, key: str) -> str:
        if key in self.ids:
            return self.ids[key]
        h = int(hashlib.sha256(key.encode()).hexdigest(), 16)
        taken = set(self.ids.values())
        while True:
            eid = "fx_" + "".join(_B32[(h >> (5 * i)) & 31] for i in range(8))
            if eid not in taken:
                break
            h //= 7
        self.ids[key] = eid
        self.new.append((key, eid))
        return eid

    def save(self) -> None:
        if not self.new:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        exists = self.path.exists()
        with self.path.open("a", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            if not exists:
                w.writerow(["key", "effect_id"])
            w.writerows(self.new)
        self.new = []
