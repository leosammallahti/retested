"""Integrity checks. The build fails loudly instead of silently shipping wrong or shrinking data."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .game import LEAK
from .ids import norm_doi
from .load import ROOT

BASELINE = ROOT / "data" / "curated" / "baseline" / "SUMMARY.json"
SECRET = re.compile(r"sk-or-v1-[A-Za-z0-9]{20,}|sk-proj-[A-Za-z0-9_-]{20,}|sk-ant-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{40,}")
SCAN_DIRS = ("pipeline", "site/src", "data/curated", "docs", "tests")
ROOT_ALLOW = {
    ".git", ".gitignore", ".gitattributes", ".github", ".claude", ".venv", ".mypy_cache", "__pycache__",
    "README.md", "pyproject.toml", "uv.lock", "package.json", "package-lock.json", "node_modules",
    "pipeline", "site", "data", "docs", "tests", "archive",
}


class Failure(Exception):
    pass


def run(g: dict, flora: list[dict], items: list[dict], reveals: dict, stats: dict, accept_baseline: bool) -> list[str]:
    problems: list[str] = []
    A, F, E = g["attempts"], g["findings"], g["effects"]

    # 1. every FLoRA pair is reachable through a finding
    reachable = {aid for f in F.values() for aid in f["attempts"]}
    lost = 0
    for r in flora:
        doi_o = norm_doi(r.get("doi_o"))
        rep = norm_doi(r.get("doi_r")) or norm_doi(r.get("alt_identifier_r")) or r.get("alt_identifier_r") or r.get("url_r")
        if doi_o and rep:
            from .registry import _aid
            if _aid(doi_o, rep) not in reachable:
                lost += 1
    if lost:
        problems.append(f"{lost} FLoRA pairs are not reachable from any finding")

    # 2. referential integrity and unique identifiers
    ids = [e["id"] for e in E.values()]
    slugs = [e["slug"] for e in E.values()]
    if len(set(ids)) != len(ids):
        problems.append("duplicate effect ids")
    if len(set(slugs)) != len(slugs):
        problems.append("duplicate effect slugs")
    fslugs = [f["slug"] for f in F.values()]
    if len(set(fslugs)) != len(fslugs):
        problems.append("duplicate finding slugs")
    eids = set(ids)
    for e in E.values():
        for aid in e["attempts"] + e["shared_attempts"]:
            if aid not in A:
                problems.append(f"effect {e['slug']} references missing attempt {aid}")
    for f in F.values():
        for eid in f.get("effects") or []:
            if eid not in eids:
                problems.append(f"finding {f['slug']} references missing effect {eid}")

    # 3. game fairness
    for it in items:
        if LEAK.search(it["claim"]):
            problems.append(f"game item {it['id']} leaks the answer: {it['claim'][:80]}")
        if it["id"] not in reveals:
            problems.append(f"game item {it['id']} has no reveal")
        if "answer" in it:
            problems.append(f"game item {it['id']} ships its answer in the card")
    study = [reveals[i["id"]]["answer"] for i in items if i["tier"] == "study"]
    if study:
        rate = sum(a == "successful" for a in study) / len(study)
        if not 0.35 <= rate <= 0.65:
            problems.append(f"game base rate {rate:.2f} outside [0.35, 0.65]")

    # 4. no secrets anywhere outside the archive
    for d in SCAN_DIRS:
        for p in (ROOT / d).rglob("*"):
            if p.is_file() and p.suffix in (".py", ".ts", ".tsx", ".astro", ".js", ".mjs", ".json", ".md", ".yaml", ".yml", ".css", ".env") \
                    and "generated" not in p.parts and "node_modules" not in p.parts and p.stat().st_size < 2_000_000:
                if SECRET.search(p.read_text(encoding="utf-8", errors="ignore")):
                    problems.append(f"secret-looking string in {p.relative_to(ROOT)}")

    # 5. repository root stays clean
    stray = sorted(p.name for p in ROOT.iterdir() if p.name not in ROOT_ALLOW and not p.name.endswith(".egg-info"))
    if stray:
        problems.append(f"unexpected entries in repo root (add to ROOT_ALLOW or move them): {stray}")

    # 6. counts never silently drop
    counts = stats["counts"]
    if BASELINE.exists() and not accept_baseline:
        base = json.loads(BASELINE.read_text(encoding="utf-8"))
        for k, v in base.items():
            now = counts.get(k)
            if now is not None and v and now < v * 0.99:
                problems.append(f"count '{k}' dropped from {v} to {now} (>1%). Re-run with --accept-baseline if intended.")
    if accept_baseline or not BASELINE.exists():
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(json.dumps(counts, indent=1), encoding="utf-8")
    return problems
