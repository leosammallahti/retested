"""Build the entity graph: papers, attempts (original x replication pairs), findings (one per original), effects (named).

Grain:
  attempt  = one (original paper, replication/reproduction paper) pair. Sources merged: FLoRA > FReD > legacy 2.4.1.
  finding  = one original paper with all of its attempts. Every original with >= 1 attempt has a finding.
  effect   = a named phenomenon (e.g. 'Elderly priming') spanning one or more originals.
"""
from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict

from rapidfuzz import fuzz

from . import evidence as ev
from .ids import EffectLedger, doi_slug, is_na, norm_doi, norm_name, slugify

CLOSENESS = ("instructions", "measures", "stimuli", "procedure", "location", "renumeration",
             "participants", "exclusions", "language", "nationality")


def _aid(doi_o: str, rep_key: str) -> str:
    return "at_" + hashlib.md5(f"{doi_o}|{rep_key}".encode()).hexdigest()[:10]


def _num(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def _first(*xs):
    for x in xs:
        if x is not None and not is_na(x):
            return x
    return None


def _majority(vals: list[str]) -> str:
    vals = [v for v in vals if v != "not_coded"]
    if not vals:
        return "not_coded"
    c = Counter(vals)
    if len(c) > 1 and {"successful", "failed"} <= set(c):
        return "mixed"
    return c.most_common(1)[0][0]


def build(src: dict, ledger: EffectLedger) -> dict:
    flora, fred, legacy, famous, oa = src["flora"], src["fred"], src["legacy"], src["famous"], src["openalex"]
    papers: dict[str, dict] = {}
    attempts: dict[str, dict] = {}
    log: list[str] = []

    def paper(doi, **kw):
        if not doi:
            return
        p = papers.setdefault(doi, {"doi": doi, "slug": doi_slug(doi)})
        for k, v in kw.items():
            if v is not None and p.get(k) is None:
                p[k] = v

    def attempt(doi_o, rep_key, **kw) -> dict:
        aid = _aid(doi_o, rep_key)
        a = attempts.get(aid)
        if a is None:
            a = attempts[aid] = {
                "id": aid, "doi_o": doi_o, "rep_key": rep_key, "doi_r": norm_doi(rep_key),
                "type": "replication", "sources": [], "outcomes_by_source": {},
                "rows": [], "legacy_rows": [], "projects": [],
            }
        for k, v in kw.items():
            if v is not None and a.get(k) is None:
                a[k] = v
        return a

    # ---------------------------------------------------------------- FLoRA (paper pairs, author verdict + quote)
    for r in flora:
        doi_o = norm_doi(r.get("doi_o"))
        rep_key = norm_doi(r.get("doi_r")) or norm_doi(r.get("alt_identifier_r")) or r.get("alt_identifier_r") or r.get("url_r")
        if not doi_o or not rep_key:
            log.append(f"flora row skipped (no doi_o or replication id): {r.get('title_r')}")
            continue
        paper(doi_o, title=r.get("title_o"), year=_num(r.get("year_o")), journal=r.get("journal_o"),
              authors=_short(r.get("author_o")), ref=r.get("apa_ref_o"), oa_url=r.get("oa_url_o"))
        if norm_doi(rep_key):
            paper(norm_doi(rep_key), title=r.get("title_r"), year=_num(r.get("year_r")), journal=r.get("journal_r"),
                  authors=_short(r.get("author_r")), ref=r.get("apa_ref_r"), oa_url=r.get("oa_url_r"))
        a = attempt(doi_o, rep_key, title_r=r.get("title_r"),
                    year_r=_num(r.get("year_r")), journal_r=r.get("journal_r"), authors_r=_short(r.get("author_r")),
                    url_r=r.get("url_r") if not norm_doi(rep_key) else None, oa_url_r=r.get("oa_url_r"),
                    quote=r.get("outcome_quote"), quote_source=r.get("outcome_quote_source"))
        if str(r.get("type") or "").lower().startswith("reproduc"):
            a["type"] = "reproduction"
        a["sources"].append("flora")
        a["outcomes_by_source"]["flora"] = ev.norm_outcome(r.get("outcome"))
        a["outcome_raw"] = a.get("outcome_raw") or r.get("outcome")
        if r.get("source"):
            a["flora_source"] = r["source"]

    # ---------------------------------------------------------------- FReD (effect rows: numbers + 7 criteria)
    for r in fred:
        doi_o = r["doi_o"]
        rep_key = r["doi_r"] or r.get("url_r")
        if not doi_o or not rep_key:
            log.append(f"fred row {r['row']} skipped (no doi pair)")
            continue
        paper(doi_o, title=r["title_o"], year=r["year_o"], journal=r["journal_o"], authors=r["author_o"], ref=r["ref_o"])
        if r["doi_r"]:
            paper(r["doi_r"], title=r["title_r"], year=r["year_r"], journal=r["journal_r"], authors=r["author_r"], ref=r["ref_r"])
        a = attempt(doi_o, rep_key, title_r=r["title_r"], year_r=r["year_r"], journal_r=r["journal_r"],
                    authors_r=r["author_r"], quote=r["quote"], quote_source=r["quote_source"])
        if "fred" not in a["sources"]:
            a["sources"].append("fred")
        a["rows"].append({
            "row": r["row"], "study_o": r["study_o"], "study_r": r["study_r"], "description": r["description"],
            "claim_text_o": r["claim_text_o"], "discipline": r["discipline"], "tags": r["tags"],
            "r_o": r["r_o"], "r_r": r["r_r"], "n_o": r["n_o"], "n_r": r["n_r"], "p_o": r["p_o"], "p_r": r["p_r"],
            "es_type_o": r["es_type_o"], "ci_o": r["ci_o"], "ci_r": r["ci_r"], "power_r": r["power_r"],
            "criteria": r["criteria"], "reported_success": ev.norm_outcome(r["reported_success"]),
            "quote": r["quote"], "prereg_r": r["prereg_r"],
        })
        if r.get("author_overlap_pct") is not None:
            a["author_overlap_pct"] = r["author_overlap_pct"]

    for a in attempts.values():
        if a["rows"]:
            a["outcomes_by_source"]["fred"] = _majority([x["reported_success"] for x in a["rows"]])

    # ---------------------------------------------------------------- legacy FReD 2.4.1 (names, projects, closeness, legacy-only pairs)
    labels: dict[tuple[str, str | None], set[str]] = defaultdict(set)   # (doi_o, doi_r) -> effect names
    name_rows: dict[str, list[dict]] = defaultdict(list)                  # effect key -> rows that name it

    for sheet in ("data", "rr"):
        for r in legacy[sheet]:
            doi_o = norm_doi(r.get("doi_original"))
            doi_r = norm_doi(r.get("doi_replication"))
            name = r.get("effect")
            if name and not is_na(name) and str(name).strip() not in ("#", "?"):
                key = norm_name(name)
                name_rows[key].append({"name": str(name).strip(), "doi_o": doi_o, "doi_r": doi_r, "sheet": sheet,
                                       "discipline": r.get("discipline"), "description": r.get("description")})
                if doi_o:
                    labels[(doi_o, doi_r)].add(key)
            if sheet != "data" or not doi_o or not doi_r:
                continue
            paper(doi_o, ref=r.get("ref_original"), journal=r.get("orig_journal"))
            paper(doi_r, ref=r.get("ref_replication"))
            aid = _aid(doi_o, doi_r)
            is_new = aid not in attempts
            a = attempt(doi_o, doi_r)
            if is_new:
                a["legacy_only"] = True
            if "legacy" not in a["sources"]:
                a["sources"].append("legacy")
            a["legacy_rows"].append({
                "effect": name, "r_o": _num(r.get("es_original")), "r_r": _num(r.get("es_replication")),
                "n_o": _num(r.get("n_original")), "n_r": _num(r.get("n_replication")),
                "outcome": ev.legacy_outcome(r.get("result"), r.get("outcome")),
                "result_raw": r.get("result") or r.get("outcome"),
                "closeness": {c: r.get(f"closeness_{c}") for c in CLOSENESS if r.get(f"closeness_{c}") is not None},
                "preregistration": r.get("preregistration"), "power": _num(r.get("power")),
                "validated": r.get("validated"), "osf_link": r.get("osf_link"),
            })
            if r.get("source") and r["source"] not in a["projects"]:
                a["projects"].append(str(r["source"]))

    for a in attempts.values():
        if a["legacy_rows"]:
            a["outcomes_by_source"]["legacy"] = _majority([x["outcome"] for x in a["legacy_rows"]])
        # author verdict priority: FLoRA > FReD > legacy
        obs = a["outcomes_by_source"]
        a["outcome"] = next((obs[s] for s in ("flora", "fred", "legacy") if obs.get(s, "not_coded") != "not_coded"), "not_coded")
        a["sources_disagree"] = len({v for v in obs.values() if v != "not_coded"}) > 1

    # ---------------------------------------------------------------- fill gaps from APA reference strings (legacy rows carry only 'ref')
    for p in papers.values():
        if p.get("ref") and (not p.get("authors") or not p.get("year") or not p.get("title")):
            au, yr, ti = parse_apa(p["ref"])
            p.setdefault("authors", None); p.setdefault("year", None); p.setdefault("title", None)
            p["authors"] = p["authors"] or au
            p["year"] = p["year"] or yr
            p["title"] = p["title"] or ti
    for a in attempts.values():
        rp = papers.get(a["doi_r"]) if a["doi_r"] else None
        if rp:
            for src_k, dst_k in (("authors", "authors_r"), ("year", "year_r"), ("title", "title_r"), ("journal", "journal_r")):
                if a.get(dst_k) is None and rp.get(src_k) is not None:
                    a[dst_k] = rp[src_k]

    # ---------------------------------------------------------------- findings: one per original with attempts
    by_orig: dict[str, list[str]] = defaultdict(list)
    for aid, a in attempts.items():
        by_orig[a["doi_o"]].append(aid)

    findings: dict[str, dict] = {}
    for doi_o, aids in by_orig.items():
        p = papers.get(doi_o, {})
        o = oa.get(doi_o)
        if o:
            paper(doi_o, title=o["title"], year=o["year"])
            p = papers[doi_o]
            p["openalex"] = {k: o[k] for k in ("cited_by", "counts_by_year", "is_retracted", "topic", "subfield", "field")}
        findings[doi_o] = {"doi_o": doi_o, "slug": p.get("slug") or doi_slug(doi_o), "attempts": sorted(aids)}

    # ---------------------------------------------------------------- effects: named phenomena
    famous_by_key = {}
    for f in famous:
        if f.get("name"):
            famous_by_key.setdefault(norm_name(f["name"]), f)
    named_keys = set(name_rows)
    # famous names that only differ trivially from a data-backed name attach to it (conservative fuzzy)
    fam_map: dict[str, str] = {}
    for fk in famous_by_key:
        if fk in named_keys:
            fam_map[fk] = fk
            continue
        best = max(named_keys, key=lambda k: fuzz.ratio(fk, k))
        if fuzz.ratio(fk, best) >= 95:
            fam_map[fk] = best
            log.append(f"famous '{fk}' -> '{best}' (fuzzy {fuzz.ratio(fk, best):.0f})")
        else:
            fam_map[fk] = fk  # curated-only effect, no linked data yet

    keys = named_keys | set(fam_map.values())

    # --- merge near-duplicate names that describe the same original(s): 'power pose' ~ 'power posing',
    #     'anchoring' ~ 'anchoring effect'. A parenthetical qualifier blocks a merge
    #     ('moral priming (cleanliness)' stays apart from 'moral priming'). Curated merges.yaml wins over both.
    canon = {k: k for k in keys}

    def find(k):
        while canon[k] != k:
            canon[k] = canon[canon[k]]
            k = canon[k]
        return k

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        # the survivor is the name used by more rows
        if len(name_rows.get(ra, [])) < len(name_rows.get(rb, [])):
            ra, rb = rb, ra
        canon[rb] = ra

    def _wordform(w: str) -> str:
        for suf in ("ism", "ing", "ed", "es", "s", "e"):
            if w.endswith(suf) and len(w) - len(suf) >= 3:
                return w[: -len(suf)]
        return w

    def stem(k):
        return [_wordform(w) for w in re.sub(r"(effects?|the|of|on|in|and|a|an)", " ", k.replace("-", " ")).split()]

    def same_name(a: str, b: str) -> bool:
        """Only spelling / word-form variants merge ('colour'~'color', 'pose'~'posing', 'pre-cognition'~'precognition').
        Any substantive word difference ('pure' vs 'mixed', 'warmth' vs 'competence') keeps them apart."""
        ta, tb = stem(a), stem(b)
        if "".join(ta) == "".join(tb):
            return True
        da, db = sorted(set(ta) - set(tb)), sorted(set(tb) - set(ta))
        if not da or len(da) != len(db) or len(da) > 2:
            return False
        return all(max(fuzz.ratio(x, y) for y in db) >= 85 for x in da)

    dois_of = {k: {r["doi_o"] for r in name_rows.get(k, []) if r["doi_o"]} for k in keys}
    by_doi = defaultdict(set)
    for k, ds in dois_of.items():
        for d in ds:
            by_doi[d].add(k)
    for ks in by_doi.values():
        ks = sorted(ks)
        for i, a in enumerate(ks):
            for b in ks[i + 1:]:
                if ("(" in a) != ("(" in b):
                    continue
                if same_name(a, b):
                    log.append(f"merged name '{b}' ~ '{a}' (shared original, similar name)")
                    union(a, b)
    for m in src.get("merges") or []:
        into = norm_name(m["into"])
        for other in m.get("from", []):
            o = norm_name(other)
            if into in canon and o in canon:
                ri, ro = find(into), find(o)
                if ri != ro:
                    canon[ro] = ri
                if ri != into:          # the curated name becomes the group's canonical name
                    canon[into] = into
                    canon[ri] = into
                log.append(f"merges.yaml: '{other}' -> '{m['into']}'")
            else:
                log.append(f"merges.yaml: unknown name '{other}' or '{m['into']}'")
    groups = defaultdict(set)
    for k in keys:
        groups[find(k)].add(k)
    for root, members in groups.items():
        for mk in members - {root}:
            name_rows[root].extend(name_rows.pop(mk, []))
            for (d, r), labs in labels.items():
                if mk in labs:
                    labs.discard(mk)
                    labs.add(root)
            for fk, k in list(fam_map.items()):
                if k == mk:
                    fam_map[fk] = root
    keys = set(groups)
    orig_to_effects: dict[str, set[str]] = defaultdict(set)
    for key in keys:
        for nr in name_rows.get(key, []):
            if nr["doi_o"] and nr["doi_o"] in findings:
                orig_to_effects[nr["doi_o"]].add(key)

    effects: dict[str, dict] = {}
    slugs: set[str] = set()
    for key in sorted(keys):
        rows = name_rows.get(key, [])
        fam_key = next((fk for fk, k in fam_map.items() if k == key), None)
        fam = famous_by_key.get(fam_key) if fam_key else None
        name = Counter(r["name"] for r in rows).most_common(1)[0][0] if rows else fam["name"]
        name = re.sub(r"\s+", " ", name).replace(". (", " (").strip().rstrip(".")  # \s also folds non-breaking spaces
        originals = sorted({r["doi_o"] for r in rows if r["doi_o"] and r["doi_o"] in findings})
        own, shared = [], []
        for doi_o in originals:
            for aid in findings[doi_o]["attempts"]:
                a = attempts[aid]
                lab = labels.get((doi_o, a["doi_r"]))
                if lab:
                    (own if key in lab else shared).append(aid)
                elif len(orig_to_effects[doi_o]) == 1:
                    own.append(aid)
                else:
                    shared.append(aid)
        slug = slugify(name)
        if slug in slugs:
            slug = f"{slug}-{hashlib.md5(key.encode()).hexdigest()[:4]}"
        slugs.add(slug)
        disc = Counter(r["discipline"] for r in rows if r.get("discipline")).most_common(1)
        desc = next((r["description"] for r in rows if r.get("description") and len(str(r["description"])) > 25), None)
        effects[key] = {
            "id": ledger.get(key), "key": key, "slug": slug, "name": name,
            "aliases": sorted({r["name"] for r in rows} - {name}),
            # FORRT's own sheets first: the docx parse mislabels some disciplines (e.g. 'Parapsychology')
            "discipline": _canon_disc(disc[0][0] if disc else (fam or {}).get("discipline")),
            "description": desc,
            "famous": _famous(fam) if fam else None,
            "originals": originals,
            "attempts": sorted(set(own)),
            "shared_attempts": sorted(set(shared) - set(own)),
        }

    for doi_o, keys_ in orig_to_effects.items():
        findings[doi_o]["effects"] = sorted(effects[k]["id"] for k in keys_)

    return {"papers": papers, "attempts": attempts, "findings": findings, "effects": effects, "log": log}


def _short(raw):
    from .load import short_authors
    return short_authors(raw)


_STATUS = {
    "replicated": "replicated", "not replicated": "not_replicated", "mixed": "mixed", "reversed": "reversed",
}


def _famous(f: dict) -> dict:
    raw = str(f.get("status") or "").strip().lower().rstrip(".")
    status = next((v for k, v in _STATUS.items() if raw.startswith(k)), None)
    op = f.get("original_paper") or ""
    year = re.search(r"\b(19|20)\d{2}\b", op)
    return {
        "status": status, "status_raw": f.get("status"), "description": f.get("description"),
        "original_paper": op or None, "original_year": int(year.group(0)) if year else None,
        "critiques": f.get("critiques"), "original_es": f.get("original_es"), "replication_es": f.get("replication_es"),
        "gs_citations": _gs(op),
    }


def _gs(text: str) -> int | None:
    m = re.search(r"citations\s*=\s*([\d,]+)", text or "")
    return int(m.group(1).replace(",", "")) if m else None


_APA = re.compile(r"^\s*(?P<au>.+?)\s*\((?P<yr>(?:19|20)\d{2})[a-z]?[^)]*\)\.?\s*(?P<ti>[^.?!]+[.?!]?)")


def parse_apa(ref: str) -> tuple[str | None, int | None, str | None]:
    """'Smith, J., Jones, K., & Lee, M. (2014). Title here. Journal...' -> ('Smith et al.', 2014, 'Title here')."""
    m = _APA.match(str(ref))
    if not m:
        return None, None, None
    au = m.group("au")
    fams = [x.strip() for x in re.findall(r"(?:^|&|,)\s*([A-Z][A-Za-z'À-ſ\- ]+?),\s*(?:[A-Z]\.|[A-Z][a-z]+)", au)]
    fams = [f for f in fams if len(f) > 1]
    if not fams:
        who = au.split(",")[0].strip() or None
    elif len(fams) == 1:
        who = fams[0]
    elif len(fams) == 2:
        who = f"{fams[0]} & {fams[1]}"
    else:
        who = f"{fams[0]} et al."
    title = m.group("ti").strip().rstrip(".") or None
    return who, int(m.group("yr")), title


_DISC_FIX = {
    "jdm": "Judgment and Decision Making",
    "judgment and decision-making": "Judgment and Decision Making",
    "judgement and decision making": "Judgment and Decision Making",
    "judgement and decision making/behavioural economics": "Judgment and Decision Making",
    "neuroscience (humans": "Neuroscience",
    "neuroscience (humans)": "Neuroscience",
    "pyschology": "Psychology",
    "psychiatry/mental health": "Psychiatry",
    "animal psychology": "Comparative Psychology",
}


def _canon_disc(d):
    """'Evolutionary psychology' / 'Evolutionary Psychology' -> one spelling (title case on each word except 'and/of')."""
    if not d or is_na(d):
        return None
    s = re.sub(r"\s+", " ", str(d)).strip()
    if s.lower() in _DISC_FIX:
        return _DISC_FIX[s.lower()]
    return " ".join(w if w.lower() in ("and", "of", "in") else (w[0].upper() + w[1:]) for w in s.split(" "))
