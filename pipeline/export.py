"""Write the build bundle (data/build) and the client payloads (site/public/generated)."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from .load import ROOT

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


def promoted(f: dict, game_findings: set[str]) -> bool:
    """A finding gets its own page only when it adds something the FORRT atlas page does not."""
    L = f["lenses"]
    return L["record"]["n_attempts"] >= 2 or L["numeric"] is not None or bool(f.get("effects")) or f["slug"] in game_findings


def write(g: dict, items: list[dict], reveals: dict, candidates: list[dict], pending: dict, stats: dict, citation: str) -> dict:
    if BUILD.exists():
        shutil.rmtree(BUILD)
    if PUBLIC.exists():
        shutil.rmtree(PUBLIC)
    A, F, E, P = g["attempts"], g["findings"], g["effects"], g["papers"]
    game_findings = {r["finding"] for r in reveals.values() if r.get("finding")}
    for f in F.values():
        f["page"] = promoted(f, game_findings)

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

    # --- client payloads (only what the browser needs; answers kept apart from cards)
    _dump(PUBLIC / "game" / "items.json", items)
    for gid, rv in reveals.items():
        _dump(PUBLIC / "game" / "r" / f"{gid}.json", rv)
    _dump(PUBLIC / "queue" / "candidates.json", candidates)
    search = [{"t": "effect", "s": e["slug"], "n": e["name"], "a": e["aliases"][:6], "d": e.get("discipline"),
               "c": e["lenses"]["record"]["code"], "k": e["lenses"]["record"]["k"]} for e in E.values()]
    for f in F.values():
        p = P.get(f["doi_o"], {})
        search.append({"t": "finding", "s": f["slug"], "n": p.get("title") or f["doi_o"], "doi": f["doi_o"],
                       "au": p.get("authors"), "y": p.get("year"), "c": f["lenses"]["record"]["code"],
                       "k": f["lenses"]["record"]["k"], "pg": f["page"]})
    sizes["search.json"] = _dump(PUBLIC / "search.json", search)
    return sizes
