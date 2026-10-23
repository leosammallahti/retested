"""Later papers' own abstracts, harvested from the caches already on disk (no network, no cost).

    python -m pipeline rep-abstracts      # writes data/discovery/replication_abstracts.json

For every attempt's later paper (doi_r) this looks through the cached OpenAlex and Europe PMC answers, keeps the longest
abstract, and keeps it only if the cached record's own title matches the title the attempt carries (so an abstract that
belongs to another paper is never attached). Each kept abstract records where it came from. A paper with no cached abstract
is simply absent; nothing is guessed or fetched.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from .load import ROOT

CACHE = ROOT / "data" / "cache"
OUT = ROOT / "data" / "discovery" / "replication_abstracts.json"
SCHEMA = 1
_WORDS = re.compile(r"[a-z0-9]{3,}")
_BOILER = re.compile(r"\(PsycINFO Database Record(?: \(c\))?[^)]*\)\.?|©\s*\d{4}[^.]*\.?\s*$", re.I)


def _rebuild(inv: dict) -> str:
    pos = [(p, w) for w, ps in inv.items() for p in ps]
    return " ".join(w for _, w in sorted(pos))


def _tokens(s: str | None) -> set[str]:
    return set(_WORDS.findall((s or "").lower()))


def title_matches(a: str | None, b: str | None) -> bool:
    """Same paper if most of the shorter title's words are in the other (titles differ in punctuation, subtitles and case)."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return False
    return len(ta & tb) / min(len(ta), len(tb)) >= 0.7


def clean(text: str) -> str:
    t = re.sub(r"<[^>]+>", " ", text)
    t = _BOILER.sub("", t)
    return re.sub(r"\s+", " ", t).strip()


def harvest() -> dict:
    att = json.loads((ROOT / "data" / "build" / "attempts.json").read_text(encoding="utf-8"))
    want: dict[str, str | None] = {}
    for a in att.values():
        d = (a.get("doi_r") or "").lower().replace("https://doi.org/", "")
        if d:
            want.setdefault(d, a.get("title_r"))
    found: dict[str, dict] = {}
    rejected = Counter()
    for sub in ("openalex", "fulltext"):
        for p in sorted((CACHE / sub).rglob("*.json")):
            s = p.read_text(encoding="utf-8")
            if "abstract_inverted_index" not in s and "abstractText" not in s:
                continue
            try:
                j = json.loads(s)
            except ValueError:
                continue
            works = j.get("results") if isinstance(j, dict) else None
            if works is None and isinstance(j, dict):
                works = (j.get("resultList") or {}).get("result")
            for w in works or []:
                if not isinstance(w, dict):
                    continue
                d = (w.get("doi") or "").lower().replace("https://doi.org/", "")
                if d not in want:
                    continue
                if w.get("abstract_inverted_index"):
                    ab, src, title = _rebuild(w["abstract_inverted_index"]), "openalex", w.get("title") or w.get("display_name")
                elif w.get("abstractText"):
                    ab, src, title = w["abstractText"], "europepmc", w.get("title")
                else:
                    continue
                ab = clean(ab)
                if len(ab) < 200:
                    rejected["too short"] += 1
                    continue
                if not title_matches(title, want[d]):
                    rejected["title does not match"] += 1
                    continue
                if d not in found or len(ab) > len(found[d]["abstract"]):
                    found[d] = {"abstract": ab, "source": src, "title_in_source": title}
    return {"schema_version": SCHEMA, "papers": len(want), "kept": len(found), "rejected": dict(rejected), "abstracts": found}


def main(argv: list[str]) -> int:
    doc = harvest()
    OUT.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    print(f"rep-abstracts: {doc['kept']} of {doc['papers']} later papers have a cached abstract whose title matches; rejected {doc['rejected']} -> {OUT}")
    return 0
