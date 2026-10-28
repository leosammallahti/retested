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
from . import explanations
from .ids import EffectLedger, doi_slug, is_na, norm_doi, norm_name, slugify

CLOSENESS = ("instructions", "measures", "stimuli", "procedure", "location", "renumeration",
             "participants", "exclusions", "language", "nationality")


def _aid(doi_o: str, rep_key: str) -> str:
    return "at_" + hashlib.md5(f"{doi_o}|{rep_key}".encode()).hexdigest()[:10]


def _oa_authors(names: list[str]) -> str | None:
    """OpenAlex display names -> 'Isen & Levin', 'Kruger et al.' (surname = the last word of each name)."""
    sur = [n.split()[-1] for n in names if n and n.split()]
    if not sur:
        return None
    return sur[0] if len(sur) == 1 else f"{sur[0]} & {sur[1]}" if len(sur) == 2 else f"{sur[0]} et al."


def _broken_authors(a) -> bool:
    """An author field that is not names: missing, 'None', raw citation data, an editor marker, stray quotes or braces,
    a mis-decoded accent ('KÃ¶bach'), a study label, or a title ('An Experimental Study of …')."""
    t = str(a or "").strip()
    if not t or t == "None":
        return True
    if re.search(r'[{}\[\]"]|\(Ed\.?\)|Ã|^Replications\b', t) or t[:1] in "(.,;:":
        return True
    words = t.rstrip(".").split()
    return t.endswith(".") and len(words) >= 3 and "&" not in t and "et al" not in t


def _broken_title(t) -> bool:
    """A title that is really a fragment of a reference: a link, a page number, a journal name with no words of a
    title, or a few characters."""
    t = str(t or "").strip()
    return (not t or t.lower().startswith(("http", "doi")) or t[:1] in ":,;.)" or len(t) < 12
            or bool(re.match(r"^(study \d|journal of|vol\.?|volume|pp)\b", t, re.I)) or bool(re.search(r"\bet al\.?$", t)))


def _shown(name: str) -> str:
    """An effect name as the site shows it: whitespace folded (\\s also folds non-breaking spaces), the famous list's
    'Name. (alias)' joined, and no trailing full stop."""
    return re.sub(r"\s+", " ", str(name)).replace(". (", " (").strip().rstrip(".")


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
    # where every source row went, for the FORRT ledger (pipeline/forrt_ledger.py): its pair, or why it has none
    trace: list[dict] = []
    stale: list[str] = []      # reviewed inputs that no longer match the data: the build stops on any of them

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
    for i, r in enumerate(flora, 1):
        doi_o = norm_doi(r.get("doi_o"))
        rep_key = norm_doi(r.get("doi_r")) or norm_doi(r.get("alt_identifier_r")) or r.get("alt_identifier_r") or r.get("url_r")
        trace.append({"file": "FLoRA", "row": i, "doi_o": doi_o, "rep_key": rep_key or None,
                      "why_not": None if doi_o and rep_key else "the row has no original DOI or no replication identifier"})
        if not doi_o or not rep_key:
            log.append(f"flora row skipped (no doi_o or replication id): {r.get('title_r')}")
            continue
        paper(doi_o, title=r.get("title_o"), year=_num(r.get("year_o")), journal=r.get("journal_o"),
              authors=_short(r.get("author_o")), surnames=_surnames(r.get("author_o")) or None,
              ref=r.get("apa_ref_o"), oa_url=r.get("oa_url_o"))
        if norm_doi(rep_key):
            paper(norm_doi(rep_key), title=r.get("title_r"), year=_num(r.get("year_r")), journal=r.get("journal_r"),
                  authors=_short(r.get("author_r")), surnames=_surnames(r.get("author_r")) or None,
                  ref=r.get("apa_ref_r"), oa_url=r.get("oa_url_r"))
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
        trace.append({"file": "FReD", "row": r["row"], "doi_o": doi_o or None, "rep_key": rep_key or None,
                      "why_not": None if doi_o and rep_key else "the row has no original DOI or no replication identifier"})
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
        for i, r in enumerate(legacy[sheet], 1):
            doi_o = norm_doi(r.get("doi_original"))
            doi_r = norm_doi(r.get("doi_replication"))
            name = r.get("effect")
            named = bool(name and not is_na(name) and str(name).strip() not in ("#", "?"))
            trace.append({"file": "FReD 2.4.1 data sheet" if sheet == "data" else "Replications & Reversals sheet",
                          "row": i, "doi_o": doi_o, "rep_key": doi_r,
                          "effect_key": norm_name(name) if named else None, "why_not": None})
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

    # ------------------------------------------------------------ Retested reviewed pairs
    # Only source-checked rows in data/curated/promoted_pairs.json enter the
    # counted graph. No discovery/triage result is promoted by a machine gate.
    for i, r in enumerate(src.get("promoted") or [], 1):
        doi_o, doi_r = r["doi_o"], r["doi_r"]
        trace.append({"file": "Retested reviewed pairs", "row": i, "doi_o": doi_o, "rep_key": doi_r, "why_not": None})
        paper(doi_o, title=r["original_title"], year=r["original_year"],
              journal=r.get("original_journal"), authors=_names(r["original_authors"]),
              source_url=r["original_source_url"])
        paper(doi_r, title=r["replication_title"], year=r["replication_year"],
              journal=r.get("replication_journal"), authors=_names(r["replication_authors"]),
              source_url=r["replication_source_url"])
        a = attempt(doi_o, doi_r, title_r=r["replication_title"],
                    year_r=r["replication_year"], journal_r=r.get("replication_journal"),
                    authors_r=_names(r["replication_authors"]), quote=r["outcome_quote"],
                    quote_source=r["outcome_quote_source"])
        if "retested" not in a["sources"]:
            a["sources"].append("retested")
        a["outcomes_by_source"]["retested"] = r["outcome"]
        if r.get("outcome_adjudication"):
            a["outcome_adjudication"] = r["outcome_adjudication"]
        a["preregistration_status"] = r["preregistration_status"]
        a["retested_review"] = {
            "candidate_id": r["candidate_id"],
            "reviewed_by": r["reviewed_by"], "reviewed_on": r["reviewed_on"],
            "original_source_url": r["original_source_url"],
            "original_claim_quote": r["effect_claim_quote"],
            "original_source_type": r.get("original_source_type"),
            "replication_source_url": r["replication_source_url"],
            "replication_target_quote": r["replication_target_quote"],
            "outcome_quote": r["outcome_quote"],
            "outcome_quote_source": r["outcome_quote_source"],
            "review_note": r.get("review_note"),
        }
        key = norm_name(r["effect_name"])
        name_rows[key].append({
            "name": r["effect_name"], "doi_o": doi_o, "doi_r": doi_r,
            "sheet": "retested", "discipline": "Psychology",
            "description": r["effect_claim"],
        })
        labels[(doi_o, doi_r)].add(key)

    # ---------------------------------------------------------------- FLoRA validation files (pipeline/flora_validation.py)
    # A pair FORRT has validated but not yet exported to FLoRA is still FORRT's coding: it enters as FLoRA data.
    # A replication already on the site under another original keeps FLoRA's exported link; the ledger shows both.
    reps_known = {a["doi_r"] for a in attempts.values() if a["doi_r"]} | {a["rep_key"] for a in attempts.values()}
    for r in src.get("flora_validation") or []:
        doi_o, rep_key = r["doi_o"], r["rep_key"]
        if not doi_o or not rep_key or _aid(doi_o, rep_key) in attempts or rep_key in reps_known:
            continue
        paper(doi_o, ref=r["ref_o"])
        if norm_doi(rep_key):
            paper(norm_doi(rep_key), ref=r["ref_r"], title=r["title_r"], year=_num(r["year_r"]))
        a = attempt(doi_o, rep_key, title_r=r["title_r"], year_r=_num(r["year_r"]),
                    quote=r["outcome_quote"], quote_source=r["outcome_quote_source"])
        if str(r["type"] or "").lower().startswith("reproduc"):
            a["type"] = "reproduction"
        a["sources"].append("flora")
        a["outcomes_by_source"]["flora"] = ev.norm_outcome(r["outcome"])
        a["outcome_raw"] = r["outcome"]
        a["flora_source"] = f"{r['file']} (validated by FORRT, not yet in FLoRA's export)"

    # ---------------------------------------------------------------- reviewed links (pipeline/curated_links.py)
    links = src.get("links") or {}
    for r in links.get("effect_originals", []):
        name_rows[norm_name(r["effect"])].append({"name": r["effect"], "doi_o": r["doi_o"], "doi_r": None,
                                                  "sheet": "reviewed link", "discipline": None, "description": None})
    for r in links.get("attempt_effects", []):
        labels[(r["doi_o"], r["doi_r"])].add(norm_name(r["effect"]))
    for r in links.get("effect_original_exclusions", []):
        k = norm_name(r["effect"])
        kept = [x for x in name_rows.get(k, []) if x["doi_o"] != r["doi_o"]]
        if len(kept) == len(name_rows.get(k, [])):
            stale.append(f"reviewed exclusion not applied: effect '{r['effect']}' original {r['doi_o']}")
        else:
            name_rows[k] = kept
            for (o, _), labs in labels.items():
                if o == r["doi_o"]:
                    labs.discard(k)

    # ---------------------------------------------------------------- fill gaps from APA reference strings (legacy rows carry only 'ref')
    for p in papers.values():
        if p.get("ref") and (not p.get("authors") or not p.get("year") or not p.get("title")):
            au, yr, ti = parse_apa(p["ref"])
            p.setdefault("authors", None); p.setdefault("year", None); p.setdefault("title", None)
            p["authors"] = p["authors"] or au
            if not p["year"] and yr:
                p["year_from_ref"] = True
            p["year"] = p["year"] or yr
            if not p["title"] and ti:
                p["title_from_ref"] = True      # parsed out of a reference string: replaced below when OpenAlex has the DOI
            p["title"] = p["title"] or ti
    for a in attempts.values():
        rp = papers.get(a["doi_r"]) if a["doi_r"] else None
        if rp:
            for src_k, dst_k in (("authors", "authors_r"), ("year", "year_r"), ("title", "title_r"), ("journal", "journal_r")):
                if a.get(dst_k) is None and rp.get(src_k) is not None:
                    a[dst_k] = rp[src_k]

    doi_folds = _fold_doi_variants(papers, attempts, log)
    if doi_folds:
        # The paper and attempt IDs were folded; effect labels must use those
        # same canonical DOIs or a newly accepted original loses its effect.
        remapped: dict[tuple[str, str | None], set[str]] = defaultdict(set)
        for (doi_o, doi_r), names in labels.items():
            remapped[(doi_folds.get(doi_o, doi_o),
                      doi_folds.get(doi_r, doi_r) if doi_r else None)].update(names)
        labels = remapped
        for rows in name_rows.values():
            for row in rows:
                row["doi_o"] = doi_folds.get(row["doi_o"], row["doi_o"]) if row["doi_o"] else None
                row["doi_r"] = doi_folds.get(row["doi_r"], row["doi_r"]) if row["doi_r"] else None

    # ---------------------------------------------------------------- OpenAlex titles (data/raw/local/openalex_paper_metadata.json)
    # A title the site could only parse out of a reference string, or a missing one, is replaced by the title OpenAlex
    # holds for the DOI; a missing year or author list is filled the same way. Titles from FLoRA and FReD are kept
    # (they agree with OpenAlex for 99% of DOIs; the rest are listed in the identity check).
    works = (src.get("openalex_works") or {})
    replaced: dict[str, str | None] = {}
    for d, p in papers.items():
        w = works.get(d)
        if not w:
            continue
        if (not p.get("title") or p.get("title_from_ref") or _broken_title(p.get("title"))) and w.get("title") and not _broken_title(w["title"]):
            replaced[d] = p.get("title")
            p["title"], p["title_source"] = w["title"], "OpenAlex"
        if w.get("is_retracted"):
            # OpenAlex marks the paper retracted: every page shows it, not only the originals in the older enrichment
            p["openalex"] = {**(p.get("openalex") or {}), "is_retracted": True}
        if w.get("authors") and _broken_authors(p.get("authors")):
            p["authors"] = _oa_authors(w["authors"])
        if w.get("year") and (not p.get("year") or p.get("year_from_ref")):
            p["year"] = w["year"]
        if not p.get("authors") and w.get("authors"):
            p["authors"] = _oa_authors(w["authors"])
    for a in attempts.values():
        rp = papers.get(a["doi_r"]) if a["doi_r"] else None
        if not rp:
            continue
        if a["doi_r"] in replaced and (a.get("title_r") is None or a.get("title_r") == replaced[a["doi_r"]] or _broken_title(a.get("title_r"))):
            a["title_r"] = rp["title"]
        for src_k, dst_k in (("authors", "authors_r"), ("year", "year_r")):
            if a.get(dst_k) is None and rp.get(src_k) is not None:
                a[dst_k] = rp[src_k]
        if rp.get("year_from_ref") and rp.get("year"):
            a["year_r"] = rp["year"]
        if _broken_authors(a.get("authors_r")) and rp.get("authors") and not _broken_authors(rp["authors"]):
            a["authors_r"] = rp["authors"]

    # a title is one line: line breaks and repeated spaces from the source spreadsheets are folded
    for p in papers.values():
        if isinstance(p.get("title"), str):
            p["title"] = re.sub(r"\s+", " ", p["title"]).strip()
    for a in attempts.values():
        if isinstance(a.get("title_r"), str):
            a["title_r"] = re.sub(r"\s+", " ", a["title_r"]).strip()

    # one study listed twice under one original is merged into the record it duplicates: counted once, nothing lost
    merged_into: dict[str, str] = {}
    for r in (src.get("links") or {}).get("attempt_duplicates", []):
        o = doi_folds.get(r["doi_o"], r["doi_o"])
        drop, keep = _aid(o, doi_folds.get(r["rep_key"], r["rep_key"])), _aid(o, doi_folds.get(r["same_as"], r["same_as"]))
        if drop not in attempts or keep not in attempts:
            stale.append(f"reviewed duplicate not applied: {r['doi_o']} -> {r['rep_key']} (same as {r['same_as']})")
            continue
        gone = attempts.pop(drop)
        attempts[keep] = _merge_attempts(attempts[keep], gone)
        attempts[keep].setdefault("same_study_as", []).append({"rep_key": gone["rep_key"], "title_r": gone.get("title_r"), "why": r["reason"]})
        merged_into[drop] = keep
        labels[(o, attempts[keep]["doi_r"])].update(labels.get((o, gone["doi_r"]), set()))

    set_aside: dict[str, dict] = {}     # attempts set aside with the reason, never dropped

    # ---------------------------------------------------------------- papers read for Retested (pipeline/read_pairs.py)
    read_notes: list[dict] = []          # readings that disagree with FORRT's coding, listed for a person to read
    checked_pairs = {(doi_folds.get(r["doi_o"], r["doi_o"]), doi_folds.get(r["rep_key"], r["rep_key"])): r
                     for r in (src.get("links") or {}).get("attempts_checked", [])}
    read_index: dict[str, str] = {}      # "doi_o|later" or "ref|doi_o|reference" -> what the reading found, for the ledger
    read_retested_finds: dict[str, str] = {}   # "doi_o|later" -> queue id of a Retested find that was read, for the ledger
    from .read_pairs import FOUND_BY as READ_FOUND_BY, OUTCOME as READ_OUTCOME, REPLICATION as READ_REPLICATION
    for r in src.get("read_pairs") or []:
        o = doi_folds.get(r["doi_o"], r["doi_o"]) if r.get("doi_o") else None
        if not o:
            continue
        rk = doi_folds.get(r["rep_key"], r["rep_key"])
        if rk == o:
            # FORRT's list sometimes cites the original itself as its later paper: never a replication of itself
            read_index[f"{o}|{rk}"] = "the list cites the original paper itself"
            continue
        aid = _aid(o, rk)
        is_rep = r["kind"] in READ_REPLICATION and r["tests_this_finding"] == "YES" and (r.get("is_cited_paper") or "YES") == "YES"
        what = ("a replication of this finding" if is_rep else f"read: {r['kind'].lower().replace('_', ' ')}"
                + ("" if r["tests_this_finding"] == "YES" else ", not a test of this finding")
                + ("" if (r.get("is_cited_paper") or "YES") == "YES" else ", not the paper FORRT's reference names"))
        if r["kind"] == "CANNOT_TELL":
            what = "not readable from its title, and no abstract is available"
        read_index[f"{o}|{rk}"] = what
        if r.get("group") == "Retested machine search" and r.get("candidate"):
            read_retested_finds[f"{o}|{rk}"] = r["candidate"]
        if r.get("cited_ref"):
            read_index[f"ref|{o}|{r['cited_ref'][:200]}"] = what
        info = {"kind": r["kind"], "result": r.get("result"), "quote": r.get("result_quote") or r.get("kind_quote"),
                "decided_by": r["decided_by"], "read_on": r["read_on"]}
        if aid in attempts:
            a = attempts[aid]
            coded = any(v != "not_coded" for k, v in a["outcomes_by_source"].items() if k != "read")
            if is_rep:
                a["read"] = info
                if READ_OUTCOME.get(r.get("result")):
                    a["outcomes_by_source"]["read"] = READ_OUTCOME[r["result"]]
                    others = {v for k, v in a["outcomes_by_source"].items() if k != "read" and v != "not_coded"}
                    if others and READ_OUTCOME[r["result"]] not in others and READ_OUTCOME[r["result"]] != "not_coded":
                        # FORRT's coding stands; the reading that differs is listed for a person to read
                        if (o, rk) not in checked_pairs:
                            read_notes.append({"attempt": aid, **info, "tests_this_finding": r["tests_this_finding"],
                                               "differs_from": sorted(others)})
                if "read" not in a["sources"]:
                    a["sources"].append("read")
            elif r["kind"] not in READ_REPLICATION and r["kind"] != "CANNOT_TELL" and not coded:
                set_aside[aid] = {**attempts.pop(aid), "set_aside_because": f"Read: the later paper is {r['kind'].lower().replace('_', ' ')}, not a replication",
                                  "set_aside_evidence": f"{r['decided_by']}; {info['quote'] or ''}",
                                  "read_kind": r["kind"], "read_tests_this_finding": r["tests_this_finding"]}
            elif r["kind"] in READ_REPLICATION and r["tests_this_finding"] == "CANNOT_TELL" and r.get("result") == "NO_RESULT_STATED":
                pass        # a replication whose abstract names neither the exact finding nor a result: only the full text can say
            elif (o, rk) in checked_pairs:
                pass        # a reader checked this pair against the reading (data/curated/attempts_checked.csv)
            elif r["kind"] != "CANNOT_TELL" or r["tests_this_finding"] == "NO":
                read_notes.append({"attempt": aid, **info, "tests_this_finding": r["tests_this_finding"]})
        elif is_rep and r.get("group", "").split(" by ")[0] in READ_FOUND_BY:
            w = (src.get("openalex_works") or {}).get(norm_doi(rk) or "") or {}
            title, year, authors = w.get("title") or r.get("title_r"), w.get("year"), _oa_authors(w.get("authors") or [])
            if norm_doi(rk):
                paper(norm_doi(rk), title=title, year=year, authors=authors)
                if w.get("is_retracted"):
                    papers[norm_doi(rk)]["openalex"] = {**(papers[norm_doi(rk)].get("openalex") or {}), "is_retracted": True}
            wo = (src.get("openalex_works") or {}).get(o) or {}
            paper(o, title=wo.get("title"), year=wo.get("year"), authors=_oa_authors(wo.get("authors") or []))
            a = attempt(o, rk, title_r=title, year_r=year, authors_r=authors, quote=info["quote"], quote_source="abstract")
            a["sources"].append("read")
            a["read"] = info
            a["outcomes_by_source"]["read"] = READ_OUTCOME.get(r.get("result"), "not_coded")
            a["found_by"], a["listed_by"] = READ_FOUND_BY[r["group"].split(" by ")[0]]
            for name in r.get("effects") or []:
                labels[(o, a["doi_r"])].add(norm_name(name))

    # attempts a reader showed are not replications of this original (data/curated/attempt_exclusions.csv); after the
    # reading step, so a pair the reading added can be set aside too, and a reviewed reason replaces the reading's
    for r in (src.get("links") or {}).get("attempt_exclusions", []):
        aid = _aid(doi_folds.get(r["doi_o"], r["doi_o"]), doi_folds.get(r["rep_key"], r["rep_key"]))
        if aid in attempts:
            set_aside[aid] = {**attempts.pop(aid), "set_aside_because": r["reason"], "set_aside_evidence": r["evidence"]}
        elif aid in set_aside:
            set_aside[aid].update(set_aside_because=r["reason"], set_aside_evidence=r["evidence"], read_kind=None)
        else:
            stale.append(f"reviewed exclusion not applied: {r['doi_o']} -> {r['rep_key']}")
    read_notes[:] = [n for n in read_notes if n["attempt"] in attempts]   # a set-aside pair needs no further reading

    # a replication set aside as misfiled moves to the original reading showed it replicates
    relinked: dict[str, str] = {}
    for r in (src.get("links") or {}).get("attempt_relinks", []):
        old = _aid(doi_folds.get(r["doi_o_wrong"], r["doi_o_wrong"]), doi_folds.get(r["rep_key"], r["rep_key"]))
        if old not in set_aside:
            stale.append(f"reviewed relink not applied (not set aside as misfiled): {r['doi_o_wrong']} -> {r['rep_key']}")
            continue
        was = set_aside[old]
        w = (src.get("openalex_works") or {}).get(r["doi_o"]) or {}
        paper(r["doi_o"], title=w.get("title"), year=w.get("year"), authors=_oa_authors(w.get("authors") or []))
        existed = _aid(r["doi_o"], was["rep_key"]) in attempts
        a = attempt(r["doi_o"], was["rep_key"], title_r=was.get("title_r"), year_r=was.get("year_r"),
                    journal_r=was.get("journal_r"), authors_r=was.get("authors_r"), quote=was.get("quote"),
                    quote_source=was.get("quote_source"))
        a["relinked_from"] = {"doi_o": was["doi_o"], "because": was["set_aside_because"], "evidence": r["evidence"],
                              "outcomes_there": was.get("outcomes_by_source")}
        relinked[old] = a["id"]
        if existed:
            # the right pair is already on record: its own coding stands; a code given under the wrong original does not
            continue
        a["type"] = was.get("type", "replication")
        a["sources"] = sorted(set(a["sources"]) | set(was["sources"]))
        for k, v in (was.get("outcomes_by_source") or {}).items():
            a["outcomes_by_source"].setdefault(k, v)

    # a later paper's details looked up by hand where no catalogue has them (data/curated/paper_details.csv)
    for r in (src.get("links") or {}).get("paper_details", []):
        rk = doi_folds.get(norm_doi(r["rep_key"]) or r["rep_key"], norm_doi(r["rep_key"]) or r["rep_key"])
        hits = [a for a in attempts.values() if a["rep_key"] == rk]
        if not hits:
            stale.append(f"reviewed paper details do not match an attempt: {r['rep_key']}")
        for a in hits:
            a["details_before"] = {k: a.get(k) for k in ("title_r", "authors_r", "year_r")}
            a["title_r"], a["authors_r"] = r["title"], r["authors"]
            a["year_r"] = int(r["year"]) if r["year"] else a.get("year_r")
            a["details_from"] = r["evidence"]

    # a result reviewed against the replication's own abstract (data/curated/attempt_results.csv) is shown first,
    # with the coding it corrects kept beside it
    from .read_pairs import OUTCOME as _RESULT
    for r in (src.get("links") or {}).get("attempt_results", []):
        aid = _aid(doi_folds.get(r["doi_o"], r["doi_o"]), doi_folds.get(r["rep_key"], r["rep_key"]))
        if aid not in attempts or r["result"] not in _RESULT:
            stale.append(f"reviewed result not applied: {r['doi_o']} -> {r['rep_key']}")
            continue
        a = attempts[aid]
        a["result_review"] = {"result": _RESULT[r["result"]], "reason": r["reason"], "evidence": r["evidence"],
                              "coded_before": {k: v for k, v in a["outcomes_by_source"].items() if v != "not_coded"}}
        a["outcomes_by_source"]["reviewed"] = _RESULT[r["result"]]
        if "reviewed" not in a["sources"]:
            a["sources"].append("reviewed")
    read_notes[:] = [n for n in read_notes if not attempts[n["attempt"]].get("result_review")]   # settled by review

    # Compute outcomes after folding: two DOI spellings can merge an overlay
    # attempt with a FORRT attempt, and FORRT's verdict must still take priority.
    for a in attempts.values():
        if a["legacy_rows"]:
            a["outcomes_by_source"]["legacy"] = _majority([x["outcome"] for x in a["legacy_rows"]])
        obs = a["outcomes_by_source"]
        # A source-reviewed, documented adjudication can supersede a stale
        # paper-level label for this exact original/replication pair.
        priority = ("reviewed", "retested", "flora", "fred", "legacy", "read") if a.get("outcome_adjudication") else ("reviewed", "flora", "fred", "legacy", "retested", "read")
        a["outcome"] = next((obs[source] for source in priority
                             if obs.get(source, "not_coded") != "not_coded"), "not_coded")
        a["sources_disagree"] = len({v for v in obs.values() if v != "not_coded"}) > 1

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
            was_retracted = bool((p.get("openalex") or {}).get("is_retracted"))
            p["openalex"] = {k: o[k] for k in ("cited_by", "counts_by_year", "is_retracted", "topic", "subfield", "field")}
            p["openalex"]["is_retracted"] = bool(p["openalex"]["is_retracted"]) or was_retracted
        findings[doi_o] = {"doi_o": doi_o, "slug": p.get("slug") or doi_slug(doi_o), "attempts": sorted(aids)}

    # This layer is deliberately attached after DOI folds and after every
    # finding exists.  It can therefore neither create a phantom finding nor
    # silently attach source-backed prose to a different original paper.
    withdrawn = {a["doi_o"]: a["set_aside_because"] for a in set_aside.values() if a["doi_o"] not in findings}
    log.extend(explanations.attach(findings, src.get("explanations") or {}, doi_folds, withdrawn))

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
    # a merge may name an effect as the site shows it (cleaned of the source's stray spaces and full stops)
    by_shown = {norm_name(_shown(k)): k for k in keys}
    chosen_name: dict[str, str] = {}
    for m in src.get("merges") or []:
        into = by_shown.get(norm_name(m["into"]), norm_name(m["into"]))
        for other in m.get("from", []):
            o = by_shown.get(norm_name(other), norm_name(other))
            if into not in canon or o not in canon:
                # a reviewed merge that no longer matches the data is a stale input: stop, never skip it
                raise ValueError(f"merges.yaml: unknown name {other!r} or {m['into']!r}")
            ri, ro = find(into), find(o)
            if ri != ro:
                canon[ro] = ri
            if ri != into:          # the curated name becomes the group's canonical name
                canon[into] = into
                canon[ri] = into
            log.append(f"merges.yaml: '{other}' -> '{m['into']}'")
        chosen_name[into] = _shown(m["into"])
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
        # a reviewed merge names the effect; otherwise the name most of its source rows use
        name = chosen_name.get(key) or (Counter(r["name"] for r in rows).most_common(1)[0][0] if rows else fam["name"])
        name = _shown(name)
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
        desc_source = next((r["description"] for r in rows if r.get("description") and len(str(r["description"])) > 25), None)
        desc = _clean_description(desc_source)
        effects[key] = {
            "id": ledger.get(key), "key": key, "slug": slug, "name": name,
            "aliases": sorted({r["name"] for r in rows} - {name}),
            # the name keys folded into this effect, so material filed under a folded name still finds it
            "merged_keys": sorted(groups.get(key, {key}) - {key}),
            "name_sources": sorted(({"retested" if r["sheet"] == "retested" else "forrt" for r in rows})
                                   | ({"forrt"} if fam else set())),
            # FORRT's own sheets first: the docx parse mislabels some disciplines (e.g. 'Parapsychology')
            "discipline": _canon_disc(disc[0][0] if disc else (fam or {}).get("discipline")),
            "description": desc, "description_as_in_source": desc_source if desc != desc_source else None,
            "famous": _famous(fam) if fam else None,
            "originals": originals,
            "attempts": sorted(set(own)),
            "shared_attempts": sorted(set(shared) - set(own)),
        }

    for doi_o, keys_ in orig_to_effects.items():
        findings[doi_o]["effects"] = sorted(effects[k]["id"] for k in keys_)

    # every reviewed link must have taken effect; one that did not is reported, never dropped quietly
    by_name = {norm_name(e["name"]): e for e in effects.values()}
    for k, e in effects.items():
        for a in e["aliases"]:
            by_name.setdefault(norm_name(a), e)
    for r in links.get("effect_originals", []):
        e = by_name.get(norm_name(r["effect"]))
        if not e or r["doi_o"] not in e["originals"]:
            stale.append(f"reviewed link not applied: effect '{r['effect']}' original {r['doi_o']}")
    for r in links.get("attempt_effects", []):
        e = by_name.get(norm_name(r["effect"]))
        aid = _aid(doi_folds.get(r["doi_o"], r["doi_o"]), doi_folds.get(r["doi_r"], r["doi_r"]))
        if not e or aid not in e["attempts"]:
            stale.append(f"reviewed link not applied: effect '{r['effect']}' attempt {r['doi_o']} -> {r['doi_r']}")

    # each entry of FORRT's Replications & Reversals text -> the effect page it became (after merges)
    famous_effect = {fk: effects[find(k)]["slug"] for fk, k in fam_map.items() if find(k) in effects}
    for r in links.get("effect_description_exclusions", []):
        e = by_name.get(norm_name(r["effect"]))
        if not e or not e.get("description"):
            stale.append(f"reviewed description exclusion not applied: effect '{r['effect']}'")
            continue
        e["description_set_aside"] = {"text": e["description"], "because": r["reason"]}
        e["description"] = None
    for (o, rk), r in checked_pairs.items():
        if _aid(o, rk) not in attempts and _aid(o, rk) not in set_aside:
            stale.append(f"reviewed check does not match an attempt on the site: {r['doi_o']} -> {r['rep_key']}")
    if stale:
        raise ValueError("reviewed inputs that no longer match the data:\n  " + "\n  ".join(stale))
    # effect keys in the trace follow the merges, so a row that names a folded name points at the effect it joined
    for t in trace:
        if t.get("effect_key"):
            t["effect_key"] = find(t["effect_key"]) if t["effect_key"] in canon else t["effect_key"]
    # meta-analyses and reviews of an effect's original finding, which reading set aside as not replications: still
    # evidence about the effect, so each effect lists them apart from its replications
    for e in effects.values():
        own = set(e["originals"])
        e["related_papers"] = sorted(
            ({"rep_key": x["rep_key"], "doi": x.get("doi_r"), "title": x.get("title_r"), "year": x.get("year_r"),
              "authors": x.get("authors_r"), "original": x["doi_o"],
              "kind": "meta-analysis" if x["read_kind"] == "META_ANALYSIS" else "review or commentary"}
             for x in set_aside.values()
             if x["doi_o"] in own and x.get("read_kind") in ("META_ANALYSIS", "REVIEW_OR_COMMENTARY")
             and x.get("read_tests_this_finding") == "YES"),
            key=lambda x: (-(x["year"] or 0), x["title"] or ""))
    return {"papers": papers, "attempts": attempts, "findings": findings, "effects": effects, "trace": trace, "famous_effect": famous_effect, "set_aside": set_aside, "merged_into": merged_into, "relinked": relinked, "read_notes": read_notes, "read_index": read_index, "read_retested_finds": read_retested_finds,
            "doi_folds": doi_folds, "log": log}


# A group tag listed as an author ("[SCORE]" in FLoRA's SCORE rows) is not a name; it is dropped before shortening, so
# the page names the first real author instead of "[SCORE] et al.".
_GROUP_TAG = re.compile(r"\{[^{}]*['\"]family['\"]\s*:\s*['\"]\[[^'\"\]]*\]['\"][^{}]*\},?\s*")


def _short(raw):
    from .load import short_authors
    if raw is not None and not is_na(raw):
        raw = _GROUP_TAG.sub("", str(raw))
    return short_authors(raw)


def _names(raw):
    """A reviewed record's author field as the page shows it: a plain string stays as written; an author list in
    CrossRef form ({"given", "family"} entries) is shortened like FLoRA's, never shown as raw data."""
    if raw is None or is_na(raw):
        return None
    return _short(raw) if re.search(r"['\"]family['\"]\s*:", str(raw)) else raw


def _surnames(raw):
    from .load import all_surnames
    return all_surnames(raw)


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


_TITLE_KEY = re.compile(r"[^a-z0-9]")


def _fold_doi_variants(papers: dict, attempts: dict, log: list) -> dict[str, str]:
    """One study, two DOIs: fold a malformed DOI into the real one, in place.

    The sources carry DOIs that were cut short somewhere upstream — "10.1016/j" for
    "10.1016/j.obhdp.2006.10.001", "10.1126/science.745568" for "...7455683" — and APA's legacy double-slash
    form. Each one mints a second paper with its own page and splits one study's record across the two:
    Tversky and Kahneman's framing paper carried seven attempts on one page and a stranded eighth on the other.

    A fold needs BOTH conditions. One DOI is a strict prefix of the other, or differs from it only by the
    doubled slash; AND the two carry the same normalised title. Either test alone would be unsafe — a real DOI
    can sit inside another real DOI, and two different papers can share a title — and together they have not
    produced a wrong fold in the twelve cases on record, each of which was read.
    """
    by_title: dict[str, list[str]] = defaultdict(list)
    for doi, p in papers.items():
        if p.get("title"):
            by_title[_TITLE_KEY.sub("", p["title"].lower())].append(doi)
    fold: dict[str, str] = {}
    for group in by_title.values():
        for a in group:
            for b in group:
                if a == b:
                    continue
                if b.startswith(a) and len(b) > len(a) and b[len(a)] in "?#":
                    fold[b] = a     # a link's tracking tail ('?utm_campaign=…') is not part of the DOI: keep the clean one
                elif (b.startswith(a) and len(b) > len(a)) or ("//" in a and a.replace("//", "/") == b):
                    fold[a] = b
    if not fold:
        return fold

    for bad, good in fold.items():
        p = papers.pop(bad, None)
        if p:
            keep = papers.setdefault(good, {"doi": good, "slug": doi_slug(good)})
            for k, v in p.items():
                if k not in ("doi", "slug") and v is not None and keep.get(k) is None:
                    keep[k] = v

    for aid in list(attempts):
        a = attempts[aid]
        doi_o, rep_key = fold.get(a["doi_o"], a["doi_o"]), fold.get(a["rep_key"], a["rep_key"])
        if (doi_o, rep_key) == (a["doi_o"], a["rep_key"]):
            continue
        del attempts[aid]
        a.update(doi_o=doi_o, rep_key=rep_key, doi_r=norm_doi(rep_key), id=_aid(doi_o, rep_key))
        kept = attempts.get(a["id"])
        attempts[a["id"]] = _merge_attempts(kept, a) if kept else a
    log.append(f"folded {len(fold)} malformed DOI variants into the paper they belong to: "
               + ", ".join(f"{b} -> {g}" for b, g in sorted(fold.items())))
    return fold


def _clean_description(t: str | None) -> str | None:
    """FORRT's description as a reader should see it: the list's formatting marks and a heading run into the text
    are taken out, and the first letter is a capital. The words are FORRT's; the source text is kept beside it."""
    if not t:
        return t
    t = " ".join(str(t).split())
    head = max(t.rfind("**.", 0, 250), t.rfind("**:", 0, 250))
    if head >= 0:                                   # "Effect name (detail)**. The claim ..." : the heading repeats the name
        t = t[head + 3:]
    elif t[:1].islower() and ")." in t[:200] and t[:t.index(").")].count("(") == 0:
        t = t[t.index(").") + 2:]                   # the tail of a heading cut mid-parenthesis
    t = t.replace("**", "").replace("__", "")
    t = re.sub(r"(?<![\w])_([^_]+)_(?![\w])", r"\1", t)
    t = t.strip(" ).,;:")
    return (t[:1].upper() + t[1:]) if t else None


def _merge_attempts(keep: dict, other: dict) -> dict:
    """Two records of the same replication, reached through two spellings of the original's DOI."""
    for k in ("rows", "legacy_rows", "projects"):
        keep[k] = keep.get(k, []) + other.get(k, [])
    keep["sources"] = sorted(set(keep.get("sources", []) + other.get("sources", [])))
    for src, out in (other.get("outcomes_by_source") or {}).items():
        keep["outcomes_by_source"].setdefault(src, out)
    for k, v in other.items():
        if k not in keep or keep.get(k) is None:
            if v is not None:
                keep[k] = v
    return keep
