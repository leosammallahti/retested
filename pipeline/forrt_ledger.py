"""Where everything FORRT publishes went, and what Retested added: one line per source row, rebuilt by every build.

Every row of every FORRT file the project holds gets exactly one outcome:

    on the site                       its (original, replication) pair is an attempt on the site
    on the site under another original  the replication paper is on the site, linked to a different original
    waiting to be read                its pair is in the review queue (found by a machine, not yet read)
    not yet read                      cited by FORRT's Replications & Reversals list; whether it is a replication
                                      and what it found is decided only by reading it
    names an effect                   the row carries no pair but names an effect (and says whether that effect has
                                      a replication on the site)
    left out                          it cannot become an attempt; the reason is FORRT's own (its filter logs, its
                                      'not a replication' marks, its unconfirmed links) or a stated missing identifier
    MISSING                           none of the above: the build stops (pipeline/__main__.py)

Retested's own rows are listed the same way (reviewed pairs on the site, finds in the queue). The summary is the
three-part count: what FORRT has, what of it the site carries, what Retested added.
"""
from __future__ import annotations

from collections import Counter, defaultdict

import pandas as pd

from .ids import norm_doi, norm_name
from .load import FORRT
from .registry import _aid

FEEDS = FORRT / "feeds"
FILTER_LOG = FORRT / "fred-data" / "output_flora_filter_log.csv"
EXPORT_LOG = FORRT / "fred-data" / "output_flora_export_log.csv"
UNCONFIRMED = {  # FORRT's extractor feeds whose links FORRT itself has not confirmed
    "flora-extractor_target_pending.csv": "FORRT's extractor has not yet identified the original",
    "flora-extractor_no_original_found.csv": "FORRT's extractor found no original for it",
    "flora-extractor_unidentified_original.csv": "FORRT's extractor could not identify the original",
    "flora-extractor_search_link_unconfirmed.csv": "FORRT's extractor has not confirmed its link to the original",
    "flora-extractor_keyed_link_disputed.csv": "FORRT's extractor marks its link to the original as disputed",
}


def _csv(path):
    return pd.read_csv(path, dtype=str, keep_default_na=False).to_dict("records") if path.exists() else []


def build(g: dict, candidates: list[dict], rr_rows: list[dict], famous: list[dict], extractor: list[dict]) -> dict:
    A, E = g["attempts"], g["effects"]
    folds = g.get("doi_folds") or {}
    fold = lambda d: folds.get(d, d) if d else d  # noqa: E731
    owners = defaultdict(list)
    for e in E.values():
        for aid in e["attempts"]:
            owners[aid].append(e["slug"])
    eff_by_key = {k: e for k, e in E.items()}
    for e in E.values():
        for n in [e["name"], *e["aliases"]]:
            eff_by_key.setdefault(norm_name(n), e)
    by_rep = defaultdict(list)
    for aid, a in A.items():
        if a["doi_r"]:
            by_rep[a["doi_r"]].append(aid)
    queue = {}
    for c in candidates:
        for rk in (c.get("doi_r"), c.get("landing_page"), c.get("id")):
            if rk:
                queue.setdefault((c.get("doi_o"), rk), c["id"])
    queue_reps = {c["doi_r"]: c["id"] for c in candidates if c.get("doi_r")}
    filt = {}
    for r in _csv(FILTER_LOG) + _csv(EXPORT_LOG):
        o, rp = norm_doi(r.get("doi_o")), norm_doi(r.get("doi_r")) or r.get("doi_r") or r.get("url_r")
        filt.setdefault((o, rp), f"FORRT's own FLoRA export left it out ({r.get('reason')})")

    def pair(o, rk):
        """Outcome of an (original, replication) pair, or None when it is nowhere."""
        o, rk = fold(norm_doi(o) or o), fold(norm_doi(rk) or rk) if rk else rk
        if o and rk:
            aid = _aid(o, rk)
            if aid in (g.get("merged_into") or {}):
                keep = g["merged_into"][aid]
                return {"outcome": "on the site", "attempt": keep, "effects": owners.get(keep, []), "note": "the same study as another record; counted once"}
            if aid in (g.get("relinked") or {}):
                new = g["relinked"][aid]
                return {"outcome": "on the site under another original", "attempt": new, "effects": owners.get(new, []),
                        "note": "filed under the original reading showed it replicates"}
            if aid in (g.get("set_aside") or {}):
                return {"outcome": "left out", "why": "set aside after reading: " + g["set_aside"][aid]["set_aside_because"]}
            if aid in A:
                return {"outcome": "on the site", "attempt": aid, "effects": owners.get(aid, [])}
            if (o, rk) in queue:
                return {"outcome": "waiting to be read", "queue": queue[(o, rk)]}
        if rk and by_rep.get(rk):
            return {"outcome": "on the site under another original", "attempt": by_rep[rk][0]}
        if rk and rk in queue_reps:
            return {"outcome": "waiting to be read", "queue": queue_reps[rk]}
        if (o, rk) in filt:
            return {"outcome": "left out", "why": filt[(o, rk)]}
        return None

    def effect_note(key):
        e = eff_by_key.get(key) if key else None
        if not e:
            return None
        return {"outcome": "names an effect", "effect": e["slug"],
                "effect_has_replication": bool(e["attempts"])}

    lines: list[dict] = []

    def add(file, row, res, **extra):
        lines.append({"file": file, "row": row, **(res or {"outcome": "MISSING"}), **extra})

    # FLoRA, FReD, the FReD 2.4.1 data sheet, the Replications & Reversals sheet, Retested's reviewed pairs
    rr_at = {(r["file"], r["row"]): r for r in rr_rows}
    for t in g.get("trace") or []:
        f = t["file"]
        if t.get("why_not"):
            add(f, t["row"], {"outcome": "left out", "why": t["why_not"]})
            continue
        named = effect_note(t.get("effect_key"))
        if f == "Replications & Reversals sheet":
            res = (pair(t["doi_o"], t["rep_key"]) if t["doi_o"] and t["rep_key"] else None) \
                or _rr_outcome(rr_at.get((f, t["row"])), named, g.get("read_index"))
        elif t.get("doi_o") and t.get("rep_key"):
            res = pair(t["doi_o"], t["rep_key"])        # a pair FORRT coded must be on the site: else MISSING
        elif t.get("rep_key"):
            res = pair(None, t["rep_key"]) or named or {"outcome": "left out", "why": "the row names no original paper"}
        else:
            res = named or {"outcome": "left out", "why": "the row names no replication paper and no effect"}
        add(f, t["row"], res)

    # the Replications & Reversals list file (the sheet's rows came through the trace above)
    for r in rr_rows:
        if r["file"] != "Replications & Reversals list file":
            continue
        res = pair(r["doi_o"], r["doi_r"]) if r["doi_r"] else None
        add(r["file"], r["row"], res or _rr_outcome(r, effect_note(norm_name(r["effect"]) if r["effect"] else None), g.get("read_index")))

    # FORRT's Replications & Reversals text (the famous list): each entry is an effect page
    slug_to_effect = {e["slug"]: e for e in E.values()}
    for i, f in enumerate(famous, 1):
        e = slug_to_effect.get((g.get("famous_effect") or {}).get(norm_name(f.get("name") or "")))
        add("Replications & Reversals text", i,
            {"outcome": "names an effect", "effect": e["slug"], "effect_has_replication": bool(e["attempts"])} if e else None,
            name=f.get("name"))

    # FORRT's extractor: what it linked, and what it has not
    for i, r in enumerate(extractor, 1):
        rk = norm_doi(r.get("doi_r")) or (r.get("url_r") or "").strip() or r.get("pair_id")
        add("FLoRA extractor (machine-found)", i, pair(r.get("doi_o"), rk))
    for name, why in UNCONFIRMED.items():
        for i, r in enumerate(_csv(FEEDS / name), 1):
            rk = norm_doi(r.get("doi_r")) or (r.get("url_r") or "").strip() or None
            res = pair(r.get("doi_o"), rk) if rk else None
            add(f"FLoRA extractor: {why}", i, res or {"outcome": "left out", "why": why})
    for name, label in (("flora-validation_flora_entry_sheets.csv", "FLoRA validation sheets"),
                        ("flora-validation_validated_export.csv", "FLoRA validated export")):
        for i, r in enumerate(_csv(FEEDS / name), 1):
            rk = norm_doi(r.get("doi_r")) or norm_doi(r.get("alt_identifier_r")) or r.get("alt_identifier_r") or r.get("url_r")
            res = pair(r.get("doi_o"), rk) if rk else {"outcome": "left out", "why": "the row has no replication identifier"}
            if not res and not norm_doi(r.get("doi_o")):
                res = {"outcome": "left out", "why": "FORRT's validation row names no original paper"}
            add(label, i, res)

    # Retested's own finds still in the queue
    for c in candidates:
        if c.get("origin") == "retested_discovery":
            add("Retested finds (machine-found)", c["id"], {"outcome": "waiting to be read", "queue": c["id"]})

    return {"lines": lines, "summary": summarise(lines, g)}


def _rr_outcome(r: dict | None, named: dict | None, read: dict | None = None) -> dict | None:
    read = read or {}
    if r is None:
        return named
    if r.get("forrt_excluded"):
        return {"outcome": "left out", "why": f"FORRT marks it: {r['forrt_excluded']}"}
    eff = {"effect": named["effect"]} if named else {}
    if r.get("doi_o") and r.get("doi_r"):
        done = read.get(f"{r['doi_o']}|{r['doi_r']}")
        if done:
            return {"outcome": "not yet read" if done.startswith("not readable") else "left out", "why": done, **eff}
        return {"outcome": "not yet read", "why": "cited by FORRT's Replications & Reversals list; not yet read", **eff}
    if r.get("ref_r"):
        done = read.get(f"ref|{r.get('doi_o')}|{(r['ref_r'] or '')[:200]}")
        if done:
            return {"outcome": "on the site" if done == "a replication of this finding" else
                    "not yet read" if done.startswith("not readable") else "left out", "why": done, **eff}
        return {"outcome": "not yet read", "why": "the list names the later paper only by reference, without a DOI", **eff}
    return named or {"outcome": "left out", "why": "the row names no later paper"}


def summarise(lines: list[dict], g: dict) -> dict:
    by_file, why = defaultdict(Counter), defaultdict(Counter)
    for l in lines:
        o = l["outcome"]
        if o == "names an effect":
            o = "names an effect that has a replication" if l.get("effect_has_replication") else "names an effect without a replication"
        by_file[l["file"]][o] += 1
        if l.get("why"):
            why[l["file"]][f"{o}: {l['why']}"] += 1
    A, E = g["attempts"], g["effects"]
    ours = [a for a in A.values() if set(a["sources"]) - {"read"} == {"retested"}]
    # FORRT's: coded in its files, or a replication its Replications & Reversals list cites (read for Retested)
    forrt_attempts = [a for a in A.values() if set(a["sources"]) & {"flora", "fred", "legacy"} or a.get("listed_by")]
    return {
        "by_file": {f: dict(c) for f, c in by_file.items()},
        "reasons": {f: dict(c.most_common()) for f, c in why.items()},
        "missing": sum(1 for l in lines if l["outcome"] == "MISSING"),
        "site": {
            "attempts": len(A), "from_forrt": len(forrt_attempts), "added_by_retested": len(ours),
            "effects_with_replication": sum(1 for e in E.values() if e["attempts"]),
            "effects_named_without_replication": sum(1 for e in E.values() if not e["attempts"]),
            "effects_only_retested_named": sum(1 for e in E.values() if e["attempts"] and e.get("name_sources") == ["retested"]),
            "findings": len(g["findings"]),
            "findings_only_retested": sum(1 for f in g["findings"].values()
                                          if all(set(A[x]["sources"]) - {"read"} == {"retested"} for x in f["attempts"])),
        },
    }
