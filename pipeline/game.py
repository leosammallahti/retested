"""'Did it replicate?' deck.

Unit of play = one original study (doi_o + study_o), never one FReD row: multi-site mega-papers
collapse to one card, so a player cannot learn a project's answer by pattern.
Answers never live in the card file; each card's reveal is a separate file fetched after lock-in.
"""
from __future__ import annotations

import hashlib
import re
from collections import defaultdict

from .ids import is_na

# Words that give away the answer or the premise of the game.
LEAK = re.compile(r"replicat|reproduc|fail|robust|did not hold|null effect|not significant|no effect|debunk|retract", re.I)


def _clean_claim(s: str | None, floor: int = 40) -> str | None:
    """The 40-character floor is there to throw out FReD's fragments — "effect of velocity", "main effect of
    condition". A written claim has already been through its own checks, so it gets a lower floor: "Oxytocin
    increases trust in strangers." is 38 characters and a better card than anything the floor was protecting us
    from."""
    if not s:
        return None
    t = re.sub(r"\s+", " ", str(s)).strip().strip('"“”').strip()
    t = re.sub(r"^(that|claim:)\s+", "", t, flags=re.I)
    if len(t) < floor or len(t) > 420 or LEAK.search(t):
        return None
    return t[0].upper() + t[1:]


def _clean_method(s: str | None) -> str | None:
    """How the study was run, shown under the claim. Held to the same leak test: it is on the card."""
    if not s:
        return None
    t = re.sub(r"\s+", " ", str(s)).strip()
    return None if len(t) < 20 or len(t) > 500 or LEAK.search(t) else t


def _p_bucket(p) -> str | None:
    try:
        p = float(p)
    except (TypeError, ValueError):
        return None
    if p != p:
        return None
    if p <= 0.001:
        return "p ≤ .001"
    if p <= 0.005:
        return ".001 < p ≤ .005"
    if p <= 0.05:
        return ".005 < p ≤ .05"
    return "p > .05"


def build(g: dict, written: dict[str, dict] | None = None,
          found: list[dict] | None = None) -> tuple[list[dict], dict[str, dict]]:
    A, F, P, E = g["attempts"], g["findings"], g["papers"], g["effects"]
    written = written or {}
    eff_by_id = {e["id"]: e for e in E.values()}
    groups: dict[tuple, list[tuple[dict, dict]]] = defaultdict(list)
    for a in A.values():
        if a["type"] != "replication":
            continue
        for r in a["rows"]:
            study = str(r.get("study_o") or "").strip().lower() or "-"
            groups[(a["doi_o"], study)].append((a, r))

    items, reveals = [], {}
    for (doi_o, study), pairs in groups.items():
        outs = {r["reported_success"] for _, r in pairs}
        if len(outs) != 1 or next(iter(outs)) not in ("successful", "failed"):
            continue
        gid = "g" + hashlib.md5(f"{doi_o}|{study}".encode()).hexdigest()[:9]
        # A written claim where one exists, the database's own description where it does not. FReD's descriptions
        # are what the deck dealt until now and most of them cannot be played — see pipeline/claims.py.
        w = written.get(gid) or {}
        claim = _clean_claim(w.get("claim"), 30) or next((c for _, r in pairs if (c := _clean_claim(r.get("description")))), None)
        if not claim:
            continue
        p = P.get(doi_o, {})
        year = p.get("year")
        if not year:
            continue
        r0 = pairs[0][1]
        f = F[doi_o]
        effect = eff_by_id.get((f.get("effects") or [None])[0]) if f.get("effects") else None
        items.append({
            "id": gid,
            "tier": "study",
            "claim": claim,
            "method": _clean_method(w.get("method")),
            "written": bool(w.get("claim")),
            "year": int(year),
            "journal": p.get("journal"),
            "discipline": r0.get("discipline"),
            "cues": {
                "n": _int(r0.get("n_o")),
                "p": _p_bucket(r0.get("p_o")),
                "r": _round(r0.get("r_o")),
                "cited_by": (p.get("openalex") or {}).get("cited_by"),
            },
        })
        reps = sorted({a["id"]: a for a, _ in pairs}.values(), key=lambda a: a.get("year_r") or 0)
        reveals[gid] = {
            "id": gid,
            "answer": next(iter(outs)),
            "title_o": p.get("title"), "authors_o": p.get("authors"),
            "replications": [{
                "authors": a.get("authors_r"), "year": _int(a.get("year_r")), "journal": a.get("journal_r"),
                "doi": a.get("doi_r"), "n": _int(max((r.get("n_r") or 0) for r in a["rows"]) or None),
                "r": _round(next((r.get("r_r") for r in a["rows"] if r.get("r_r") is not None), None)),
                "quote": a.get("quote"),
            } for a in reps[:4]],
            "finding": f["slug"],
            "effect": {"slug": effect["slug"], "name": effect["name"]} if effect else None,
            # the writer's own name for the phenomenon, shown only here — it may contain words the card may not
            "effect_label": w.get("effect_label"),
        }

    # famous-effects tier: curated verdicts (2021-22 list), clearly labelled as such in the reveal
    for e in E.values():
        fam = e.get("famous")
        if not fam or fam["status"] not in ("replicated", "not_replicated", "reversed"):
            continue
        claim = _clean_claim(fam.get("description"))
        if not claim and not (written.get("f" + hashlib.md5(e["key"].encode()).hexdigest()[:9]) or {}).get("claim"):
            continue
        gid = "f" + hashlib.md5(e["key"].encode()).hexdigest()[:9]
        w = written.get(gid) or {}
        claim = _clean_claim(w.get("claim"), 30) or claim
        items.append({
            "id": gid, "tier": "famous", "claim": claim, "effect_name": e["name"],
            "method": _clean_method(w.get("method")), "written": bool(w.get("claim")),
            "year": fam.get("original_year"), "journal": None, "discipline": e.get("discipline"),
            "cues": {"gs_citations": fam.get("gs_citations")},
        })
        reveals[gid] = {
            "id": gid, "answer": "successful" if fam["status"] == "replicated" else "failed",
            "curated_status": fam["status_raw"], "critiques": fam.get("critiques"),
            "effect_label": (written.get(gid) or {}).get("effect_label"),
            "original_paper": fam.get("original_paper"),
            "effect": {"slug": e["slug"], "name": e["name"]}, "finding": None, "replications": [],
        }
    _found_tier(items, reveals, written or {}, found or [])
    items.sort(key=lambda x: x["id"])
    return items, reveals


def _found_tier(items: list[dict], reveals: dict, written: dict, candidates: list[dict]) -> None:
    """Cards from replications this project found and FORRT does not record.

    These are not the record and the reveal says so. A card is dealt only when the find clears both hand-read
    audits — a link band measured at 90% or better and an outcome the model was confident about — when every
    find pointing at that original agrees on the answer, and when a claim could be written from the original's
    own abstract. That is what makes it a fair thing to score somebody against; the nine-word label these
    carried before was not.
    """
    from .queue import TRUSTED_LINKS
    by_original: dict[str, list[dict]] = defaultdict(list)
    for c in candidates:
        if (c.get("origin") == "retested_discovery" and c.get("group") == "replication"
                and c.get("field") == "psychology" and c.get("outcome") in ("successful", "failed")
                and c.get("doi_o") and c.get("abstract_o")
                and (c.get("link_method"), c.get("link_confidence")) in TRUSTED_LINKS
                and (c.get("outcome_confidence") or 0) >= 0.8):
            by_original[c["doi_o"]].append(c)
    for doi, cs in sorted(by_original.items()):
        outs = {c["outcome"] for c in cs}
        if len(outs) != 1:
            continue
        gid = "d" + hashlib.md5(doi.encode()).hexdigest()[:9]
        w = written.get(gid) or {}
        claim = _clean_claim(w.get("claim"), 30)
        if not claim:
            continue
        c0 = cs[0]
        items.append({
            "id": gid, "tier": "found", "claim": claim, "method": _clean_method(w.get("method")),
            "written": True, "year": _int(c0.get("year_o")), "journal": c0.get("journal_o"),
            "discipline": None,
            "cues": {"n": None, "p": None, "r": None, "cited_by": c0.get("cited_by_o")},
        })
        reveals[gid] = {
            "id": gid, "answer": next(iter(outs)),
            "title_o": c0.get("title_o"), "authors_o": c0.get("authors_o"),
            "replications": [{"authors": c.get("authors_r"), "year": _int(c.get("year_r")),
                              "journal": c.get("journal_r"), "doi": c.get("doi_r"), "n": None, "r": None,
                              "quote": c.get("outcome_quote")} for c in cs[:4]],
            "finding": None, "effect": None, "effect_label": w.get("effect_label"),
            # the card's whole provenance, in the reveal, because none of it is in FORRT's record
            "unverified": True,
            "how_found": "This replication is not in FORRT's curated record. Our own search of OpenAlex found it, "
                         "a language model read its abstract for the outcome, and its link to the original was "
                         "checked by hand for its matching method but not for this paper. Nobody has reviewed "
                         "this pair.",
        }


def _int(x):
    try:
        return None if x is None or is_na(x) else int(float(x))
    except (TypeError, ValueError):
        return None


def _round(x, d=2):
    try:
        return None if x is None else round(float(x), d)
    except (TypeError, ValueError):
        return None
