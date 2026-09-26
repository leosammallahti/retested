"""Write the build bundle (data/build) and the client payloads (site/public/generated)."""
from __future__ import annotations

import json
import shutil
from datetime import date, timedelta
from hashlib import sha256
from pathlib import Path

from .game import context_ready
from .load import ROOT
from .stats import finding_context_tier

BUILD = ROOT / "data" / "build"
PUBLIC = ROOT / "site" / "public" / "generated"


def _dump(path: Path, obj, pretty: bool = False) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(obj, ensure_ascii=False, indent=1 if pretty else None, separators=None if pretty else (",", ":"),
                     default=_default)
    path.write_text(txt, encoding="utf-8")
    return len(txt)


def _default(o):
    if isinstance(o, (set, tuple)):
        return list(o)
    if hasattr(o, "item"):
        return o.item()
    raise TypeError(type(o))


def has_local_page(f: dict) -> bool:
    """Every addressable finding gets a local page and prediction interaction.

    Thin records used to link straight to the FORRT Atlas.  That saved duplicate
    pages, but it also meant only a subset of findings offered Retested's core
    guess-before-reveal experience.  Sparse and unresolved records are useful
    answers in their own right as long as the page labels them honestly.
    """

    return bool(f.get("slug"))


def _finding_reveal(f: dict) -> dict:
    """Return the answer-only payload fetched after a finding prediction.

    Finding pages are static, so this is a casual anti-spoiler boundary rather
    than access control.  Keeping these fields out of the initial HTML and
    hydration props still makes the intended guess-before-reveal interaction
    honest for ordinary visitors and mirrors the main game's payload split.
    """

    record = f["lenses"]["record"]
    return {
        "schema_version": 1,
        "record": {
            key: record[key]
            for key in ("code", "label", "n_attempts", "successful", "mixed", "failed")
        },
    }


def _daily_decks(items: list[dict], reveals: dict) -> dict[str, list[str]]:
    """Precompute one opaque 8-study/2-famous, 5/5 deck for each calendar day.

    The browser receives only IDs in ``daily.json``. Outcome labels remain solely in each card's
    separately fetched reveal JSON; this function is the one build-time boundary that can inspect
    both payloads. A month/day schedule repeats annually so a date means the same deck to every
    player, without putting answer-derived metadata on individual card records.
    """
    by_tier_answer: dict[tuple[str, str], list[dict]] = {}
    for tier in ("study", "famous"):
        for answer in ("successful", "failed"):
            rows = [item for item in items if item["tier"] == tier and item.get("context_ready")
                    and context_ready(item)
                    and reveals[item["id"]].get("answer") == answer]
            by_tier_answer[tier, answer] = rows
    quotas = {("study", "successful"): 4, ("study", "failed"): 4,
              ("famous", "successful"): 1, ("famous", "failed"): 1}
    missing = [f"{tier}/{answer}: {len(by_tier_answer[tier, answer])} < {n}"
               for (tier, answer), n in quotas.items() if len(by_tier_answer[tier, answer]) < n]
    if missing:
        raise ValueError("cannot build a fair daily game deck: " + "; ".join(missing))

    def ordered(rows: list[dict], key: str) -> list[dict]:
        return sorted(rows, key=lambda item: sha256(f"{key}|{item['id']}".encode()).hexdigest())

    decks: dict[str, list[str]] = {}
    day = date(2000, 1, 1)  # leap year: includes every month/day, including February 29.
    for _ in range(366):
        key = day.strftime("%m-%d")
        picked = [item for (tier, answer), n in quotas.items()
                  for item in ordered(by_tier_answer[tier, answer], f"{key}|{tier}|{answer}")[:n]]
        decks[key] = [item["id"] for item in ordered(picked, f"{key}|order")]
        day += timedelta(days=1)
    return decks


def write(g: dict, items: list[dict], reveals: dict, candidates: list[dict], pending: dict, stats: dict, citation: str) -> dict:
    if BUILD.exists():
        shutil.rmtree(BUILD)
    if PUBLIC.exists():
        shutil.rmtree(PUBLIC)
    A, F, E, P = g["attempts"], g["findings"], g["effects"], g["papers"]
    for f in F.values():
        f["page"] = has_local_page(f)

    used = set(F)
    for a in A.values():
        if a["doi_r"]:
            used.add(a["doi_r"])
    papers = {d: p for d, p in P.items() if d in used}

    sizes = {
        "effects.json": _dump(BUILD / "effects.json", sorted(E.values(), key=lambda e: e["name"].lower())),
        "findings.json": _dump(BUILD / "findings.json", F),
        "attempts.json": _dump(BUILD / "attempts.json", A),
        "papers.json": _dump(BUILD / "papers.json", papers),
        "stats.json": _dump(BUILD / "stats.json", stats, pretty=True),
        "game-items.json": _dump(BUILD / "game-items.json", items),
        "citation.json": _dump(BUILD / "citation.json", {"forrt": citation}),
        "candidates.json": _dump(BUILD / "candidates.json", candidates),
        "pending.json": _dump(BUILD / "pending.json", pending),
    }

    # --- client payloads (only what the browser needs; answers kept apart from cards/pages)
    _dump(PUBLIC / "game" / "items.json", items)
    _dump(PUBLIC / "game" / "daily.json", _daily_decks(items, reveals))
    for gid, rv in reveals.items():
        _dump(PUBLIC / "game" / "r" / f"{gid}.json", rv)
    sizes["finding-reveals"] = sum(
        _dump(PUBLIC / "finding" / "r" / f"{f['slug']}.json", _finding_reveal(f))
        for f in F.values()
    )
    _dump(PUBLIC / "queue" / "candidates.json", candidates)
    search = [{"t": "effect", "s": e["slug"], "n": e["name"], "a": e["aliases"][:6], "d": e.get("discipline"),
               "k": e["lenses"]["record"]["k"]} for e in E.values()]
    for f in F.values():
        p = P.get(f["doi_o"], {})
        search.append({"t": "finding", "s": f["slug"], "n": p.get("title") or f["doi_o"], "doi": f["doi_o"],
                       "au": p.get("authors"), "y": p.get("year"), "k": f["lenses"]["record"]["k"],
                       # Context quality is answer-blind and lets readers find
                       # the genuinely source-finished explanation pages.
                       "ctx": finding_context_tier(g, f["doi_o"], f)})
    sizes["search.json"] = _dump(PUBLIC / "search.json", search)
    return sizes
