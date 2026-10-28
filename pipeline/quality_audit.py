"""Quality audit of the built site: the questions a reader should never have to ask.

    python -m pipeline quality-audit        # after `python -m pipeline build`; writes data/build/quality_audit.json

Coverage of FORRT's files is the FORRT ledger's job (pipeline/forrt_ledger.py, which stops the build). This audit
reads what the build produced and lists, by kind, every item that still needs a decision:

  * attempts: the original listed as its own replication; a replication titled like a review, meta-analysis,
    commentary or reply (a keyword only picks these for reading); dated before its original; no title, authors or
    year; no result coded;
  * effects: two or more with exactly the same replications (unless data/curated/effects_kept_apart.csv records
    that reading kept them apart); a broken name; a description starting mid-sentence; one description shared by
    differently named effects;
  * lists: an effect without a replication in any list.

Nothing here changes data. Each answered question becomes a reviewed input in data/curated/ (see
docs/SOURCES_AND_LEDGER.md), and the next audit no longer lists it.
"""
from __future__ import annotations

import collections
import csv
import json
import re

from rapidfuzz import fuzz

from .ids import norm_name
from .load import ROOT

BUILD = ROOT / "data" / "build"
NON_REPLICATION_TITLE = re.compile(r"meta-?analy|systematic review|\breview\b|commentary|\breply\b|comment on|rejoinder|erratum|corrigendum", re.I)


def _short(t, n=110):
    return re.sub(r"\s+", " ", str(t or ""))[:n]


def run() -> dict:
    ld = lambda f: json.loads((BUILD / f).read_text(encoding="utf-8"))  # noqa: E731
    A, E, P, S = ld("attempts.json"), ld("effects.json"), ld("papers.json"), ld("stats.json")
    out: dict[str, list] = collections.OrderedDict()

    def flag(kind, item):
        out.setdefault(kind, []).append(item)

    checked = set()
    f = ROOT / "data" / "curated" / "same_title_checked.csv"
    if f.exists():
        checked = {(r["doi_o"], r["rep_key"]) for r in csv.DictReader(f.open(encoding="utf-8"))}
    for aid, a in A.items():
        po = P.get(a["doi_o"], {})
        rec = {"attempt": aid, "doi_o": a["doi_o"], "rep_key": a["rep_key"], "replication": _short(a.get("title_r")),
               "sources": a["sources"], "outcome": a["outcome"]}
        t_r, t_o = a.get("title_r"), po.get("title")
        if a["doi_r"] and a["doi_r"] == a["doi_o"]:
            flag("attempt: the original is listed as its own replication", rec)
        elif t_r and t_o and fuzz.ratio(str(t_r).lower(), str(t_o).lower()) >= 95 and (a["doi_o"], a["rep_key"]) not in checked:
            flag("attempt: replication title equals the original's (check it is a later study)", rec)
        if po.get("year") and a.get("year_r") and float(a["year_r"]) < float(po["year"]):
            flag("attempt: replication dated before its original", rec)
        if not t_r or str(t_r).startswith("http"):
            flag("attempt: no replication title", rec)
        if not a.get("authors_r"):
            flag("attempt: no replication authors", rec)
        if not a.get("year_r"):
            flag("attempt: no replication year", rec)
        if t_r and NON_REPLICATION_TITLE.search(str(t_r)) and not a.get("read"):
            flag("attempt: titled like a review, meta-analysis, commentary or reply (needs reading)", rec)
        if a["outcome"] == "not_coded":
            flag("attempt: no result coded", rec)

    apart = set()
    p = ROOT / "data" / "curated" / "effects_kept_apart.csv"
    if p.exists():
        for r in csv.DictReader(p.open(encoding="utf-8")):
            names = [norm_name(n) for n in r["effects"].split(";")]
            apart.update(frozenset({x, y}) for x in names for y in names if x != y)
    by_set = collections.defaultdict(list)
    for e in E:
        if e["attempts"]:
            by_set[tuple(e["attempts"])].append(e["name"])
    for reps, names in by_set.items():
        pairs = [(x, y) for i, x in enumerate(names) for y in names[i + 1:]]
        if len(names) > 1 and not all(frozenset({norm_name(x), norm_name(y)}) in apart for x, y in pairs):
            flag("effects: the same replications under two or more names", {"effects": names, "attempts": len(reps)})
    desc_users = collections.defaultdict(list)
    for e in E:
        n, d = e["name"], e.get("description") or ""
        if len(n) < 4 or n.count("(") != n.count(")") or "**" in n or n.endswith((" (vs", "(e.g")):
            flag("effects: broken name", {"effect": e["slug"], "name": n})
        if e["attempts"] and d and (d[0] in ").,;:" or d[:1].islower() or "**" in d):
            flag("effects: description starts mid-sentence or carries stray marks", {"effect": e["slug"], "description": _short(d, 160)})
        if d and len(d) > 40:
            desc_users[d.strip().lower()].append(n)
    for d, names in desc_users.items():
        if len({norm_name(x) for x in names}) > 1:
            flag("effects: one description shared by differently named effects", {"effects": names, "description": _short(d)})

    for lst, cards in S["lists"].items():
        for c in cards:
            if c["record"]["n_attempts"] == 0:
                flag(f"lists: '{lst}' shows an effect without a replication", {"effect": c["slug"]})

    doc = {"counts": {k: len(v) for k, v in out.items()}, "items": out}
    tmp = BUILD / "quality_audit.json.tmp"
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(BUILD / "quality_audit.json")
    return doc


def main(argv: list[str] | None = None) -> int:
    doc = run()
    for k, n in doc["counts"].items():
        print(f"{n:6d}  {k}")
    return 0
