"""The written post for each feed card: a short plain account of the experiment, ending with what was found.

A post is two to four short sentences, about 40 words and never more than 70. It starts with what was done, never with a head-count or an age, and its last
sentence is the finding the player bets on. It never mentions a later study, authors, years or statistics.

Posts are written in packets (by a model, from the original paper's own abstract or Methods text) and imported here with
the same fairness test the build applies to a card, so a post that leaks the answer or reads like a methods section never
reaches the feed:

    python -m pipeline posts-import packet.json [packet.json ...] [--writer claude-sonnet-5-5] [--check]

A packet is a JSON array of {"id": ..., "post": ..., "source_level": "procedure" | "design_only"}. Merging is by id; a
later import replaces an earlier post for the same id. Output: data/curated/posts.json.

Card ids: "g..." is one original study (doi + study number), "f..." a famous effect, and "p..." (see `paper_id`) one
original paper whose replication pairs carry no study-level rows.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

from .load import ROOT

PATH = ROOT / "data" / "curated" / "posts.json"
SCHEMA = 1
MIN_CHARS, MAX_CHARS = 80, 420
MIN_SENTENCES, MAX_SENTENCES, MAX_SENTENCE_WORDS, MAX_WORDS = 2, 4, 32, 70
LEVELS = {"procedure", "design_only"}

_END = re.compile(r"(?<=[.!?])[\"”’)]*\s+(?=[A-Z0-9“\"(])")
_STATS = re.compile(r"\b[pF]\s*[<=>]|\bp\s*[<=>]\s*\.?\d|η|Cohen|\bCI\b|\bSD\b|effect size|significan|degrees of freedom", re.I)
_CITATION = re.compile(r"\bet al\b|\(\s*(?:19|20)\d\d\s*\)|\b(?:19|20)\d\d\)")
_OPENER = re.compile(r"^\s*(in this study|in the study|this study|a study of|the study (looked|examined|tested)|"
                     r"researchers (looked|examined|studied)|this (is a|chapter|paper))\b", re.I)


def paper_id(doi: str) -> str:
    """Card id for an original paper that has no study-level rows."""
    return "p" + hashlib.md5(doi.encode()).hexdigest()[:9]


def sentences(post: str) -> list[str]:
    return [s.strip() for s in _END.split(post.strip()) if s.strip()]


def split(post: str) -> tuple[str, str]:
    """(the account of what was done, the finding): the finding is the last sentence."""
    parts = sentences(post)
    return " ".join(parts[:-1]), parts[-1] if parts else ""


def problems(rec: dict) -> list[str]:
    """Why this record may not be imported; empty when it is fine."""
    from .game import LEAK       # imported here: game imports this module
    out = []
    pid, post = rec.get("id"), rec.get("post")
    if not isinstance(pid, str) or not pid:
        return ["record has no id"]
    if not isinstance(post, str):
        return [f"{pid}: post is missing"]
    post = post.strip()
    if not MIN_CHARS <= len(post) <= MAX_CHARS:
        out.append(f"{pid}: {len(post)} characters, outside {MIN_CHARS}-{MAX_CHARS}")
    parts = sentences(post)
    if not MIN_SENTENCES <= len(parts) <= MAX_SENTENCES:
        out.append(f"{pid}: {len(parts)} sentences, outside {MIN_SENTENCES}-{MAX_SENTENCES}")
    if any(len(s.split()) > MAX_SENTENCE_WORDS for s in parts):
        out.append(f"{pid}: a sentence runs past {MAX_SENTENCE_WORDS} words")
    if len(post.split()) > MAX_WORDS:
        out.append(f"{pid}: {len(post.split())} words, past {MAX_WORDS}; a post is short")
    if post[:1].isdigit() or _OPENER.search(post):
        out.append(f"{pid}: opens with a head-count or 'In this study'; start with what was done")
    if LEAK.search(post):
        out.append(f"{pid}: leaks the answer or mentions a later study: {LEAK.search(post).group(0)!r}")
    if _STATS.search(post):
        out.append(f"{pid}: carries a statistic: {_STATS.search(post).group(0)!r}")
    if _CITATION.search(post):
        out.append(f"{pid}: cites authors or a year")
    if rec.get("source_level") not in (None, *LEVELS):
        out.append(f"{pid}: source_level must be one of {sorted(LEVELS)}")
    return out


def load() -> dict[str, dict]:
    """Card id -> {post, writer, written_on, source_level?}. Empty until `posts-import` has run."""
    if not PATH.exists():
        return {}
    return json.loads(PATH.read_text(encoding="utf-8")).get("posts", {})


def load_unusable() -> dict[str, dict]:
    """Card id -> why the writer said it does not belong in the feed (a book chapter, a review, another field)."""
    if not PATH.exists():
        return {}
    return json.loads(PATH.read_text(encoding="utf-8")).get("unusable", {})


def run(packets: list[Path], writer: str, check: bool = False) -> int:
    incoming: dict[str, dict] = {}
    unusable: dict[str, dict] = {}
    bad: list[str] = []
    stamp = {"writer": writer, "written_on": date.today().isoformat()}
    for packet in packets:
        for rec in json.loads(Path(packet).read_text(encoding="utf-8")):
            if rec.get("usable") is False:       # the writer says this paper is not an empirical finding for the feed
                unusable[rec["id"]] = {"note": rec.get("note", ""), **stamp}
                continue
            found = problems(rec)
            if found:
                bad += found
                continue
            incoming[rec["id"]] = {k: rec[k] for k in ("post", "source_level") if rec.get(k)} | {
                "writer": rec.get("writer") or writer, "written_on": stamp["written_on"]}
    merged = {**load(), **incoming}
    kept_unusable = {**load_unusable(), **unusable}
    print(f"{len(incoming)} posts accepted, {len(unusable)} marked not for the feed, {len(bad)} refused; {len(merged)} posts in all")
    for line in bad[:40]:
        print("  -", line)
    if bad or check:
        return 1 if bad else 0
    PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"schema_version": SCHEMA, "posts": merged, "unusable": kept_unusable},
                              ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    tmp.replace(PATH)
    print(f"wrote {PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(run([Path(p) for p in sys.argv[1:]], "unspecified"))
