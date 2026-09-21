"""Review queue: machine-found replication candidates that are not yet in FORRT's curated data.

Two sources, kept apart and labelled:
  forrt_flora_extractor  FORRT's own extractor output (public CSV, LLM-extracted, never human-reviewed);
  retested_discovery     our keyword and citation searches, screened by DeepSeek and linked to an original here.

Every row keeps review_state='machine' until a human decides; nothing here is shown as validated. Rows whose
original is already in the wiki are also shown on that effect/finding page, marked unverified and pending review.
"""
from __future__ import annotations

import re

from .ids import norm_doi
from .load import osf_token

# which triage verdicts reach the queue at all, and which pile they go in
GROUP = {
    ("replication", "psychology"): "replication",
    ("reproduction", "psychology"): "replication",
    ("replication", "other_behavioural"): "other_behavioural",
    ("reproduction", "other_behavioural"): "other_behavioural",
    ("registration_only", "psychology"): "registration",
    ("registration_only", "other_behavioural"): "registration",
}
GROUP_LABEL = {
    "replication": "Psychology replication",
    "other_behavioural": "Other behavioural science",
    "registration": "Registered protocol, no results yet",
}


def build(extracted: list[dict], g: dict) -> list[dict]:
    """FORRT's own flora-extractor rows."""
    known_pairs = {(a["doi_o"], a["doi_r"]) for a in g["attempts"].values() if a["doi_r"]}
    known_reps = {a["doi_r"] for a in g["attempts"].values() if a["doi_r"]}
    effect_of = _effect_of(g)
    out, seen = [], set()
    for r in extracted:
        doi_o, doi_r = norm_doi(r.get("doi_o")), norm_doi(r.get("doi_r"))
        if not doi_r or (doi_o, doi_r) in seen:
            continue
        seen.add((doi_o, doi_r))
        if (doi_o, doi_r) in known_pairs:
            continue
        eff = effect_of.get(doi_o)
        out.append({
            "id": r.get("pair_id") or f"{doi_o}|{doi_r}",
            "doi_r": doi_r, "title_r": r.get("title_r"), "year_r": _int(r.get("year_r")), "journal_r": r.get("journal_r"),
            "doi_o": doi_o, "title_o": r.get("title_o"), "year_o": _int(r.get("year_o")),
            "outcome": (r.get("outcome") or "").lower() or None,
            "outcome_quote": r.get("outcome_phrase"),
            "outcome_confidence": r.get("outcome_confidence"),
            "link_confidence": r.get("link_confidence"),
            "type": r.get("type"),
            "rep_already_known": doi_r in known_reps,
            "original_in_wiki": bool(doi_o and doi_o in g["findings"]),
            "effect": {"slug": eff[0], "name": eff[1]} if eff else None,
            "abstract": (r.get("abstract_r") or "")[:700] or None,
            "models": [m for m in (r.get("classify_llm_model"), r.get("link_llm_model"), r.get("outcome_llm_model")) if m],
            "origin": "forrt_flora_extractor",
            "group": "replication",
            "review_state": "machine",
        })
    out.sort(key=lambda c: (not c["original_in_wiki"], -(c["year_r"] or 0)))
    return out


def build_retested(triaged: list[dict], links: dict, g: dict, forrt_known: set[str] | None = None,
                   forrt_osf: set[str] | None = None, surname_freq: dict[str, int] | None = None,
                   osf_records: dict[str, dict] | None = None,
                   original_authors: dict[str, dict] | None = None) -> list[dict]:
    """Our own finds: one row per discovered paper DeepSeek judged a replication, a reproduction or a registered
    protocol, carrying its verdict, its grounded quote, and how its original was resolved."""
    known_pairs = {(a["doi_o"], a["doi_r"]) for a in g["attempts"].values() if a["doi_r"]}
    known_reps = {a["doi_r"] for a in g["attempts"].values() if a["doi_r"]}
    effect_of = _effect_of(g)
    P = g["papers"]
    forrt_known, forrt_osf = forrt_known or set(), forrt_osf or set()
    osf_records, original_authors = osf_records or {}, original_authors or {}
    out, already = [], 0
    for r in triaged:
        t = r["triage"]
        group = GROUP.get((t.get("kind"), t.get("field")))
        if not group:
            continue
        doi_r = norm_doi(r.get("doi_r"))
        osf = osf_token(r.get("landing_page"))
        if (doi_r and doi_r in forrt_known) or (osf and osf in forrt_osf):
            already += 1                                  # FORRT has this paper somewhere; it is not our find
            continue
        link = links.get(r["cid"])
        doi_o = t.get("original_doi") or (link or {}).get("doi_o")
        if doi_r and doi_o and (doi_o, doi_r) in known_pairs:
            continue                                      # FORRT already records this exact pair
        named = t.get("original") or {}
        in_wiki = bool(doi_o and doi_o in g["findings"])
        eff = effect_of.get(doi_o)
        out.append({
            "id": r["cid"],
            "doi_r": doi_r, "title_r": r.get("title_r"), "year_r": r.get("year_r"), "journal_r": r.get("venue"),
            "authors_r": r.get("authors_r"),
            "doi_o": doi_o,
            "title_o": (P.get(doi_o) or {}).get("title") if in_wiki else (link or {}).get("title_o"),
            "year_o": (P.get(doi_o) or {}).get("year") if in_wiki else (link or {}).get("year_o"),
            "outcome": t.get("outcome") if t.get("outcome") != "not_reported" else None,
            "outcome_quote": t.get("outcome_quote"),
            "outcome_confidence": t.get("confidence"),
            # A DOI the model picked out of the citation list is NOT a strong link: read one by one, 6 of 11 were
            # right (docs/LINK_AUDIT_20260919.md). It cannot be scored either, because the model writes its account
            # of the original after choosing it. So it says "unchecked" rather than borrowing a band it never earned.
            "link_confidence": ("unchecked" if t.get("original_doi") else (link or {}).get("confidence")),
            "link_method": "cited by this paper" if t.get("original_doi") else (link or {}).get("method"),
            "link_evidence": {k: link.get(k) for k in ("score", "text_sim", "authors_matched", "year_delta", "runner_up")}
                             if link and not t.get("original_doi") else None,
            "original_named": {"authors": named.get("authors"), "year": named.get("year"),
                               "description": named.get("description")} if named.get("authors") or named.get("description") else None,
            "type": "reproduction" if t.get("kind") == "reproduction" else ("registration" if group == "registration" else "replication"),
            "field": t.get("field"),
            "group": group,
            "evidence_tier": "preprint" if r.get("type") == "preprint" else ("published" if doi_r else "no doi"),
            # a DOI-less OSF deposit is identified by its page; absence from FORRT is proved on that token
            "identifier": doi_r or (f"osf.io/{osf}" if osf else r.get("landing_page")),
            "search_tier": r.get("tier"), "rule_score": r.get("score"),
            "landing_page": r.get("landing_page"), "osf_id": osf,
            "declared_design": declared_design(r.get("title_r"), r.get("abstract")),
            # OSF answers this outright: a registration is a registration. No inference, no reading.
            "preregistered": _prereg(osf_records.get(osf)),
            "independence": independence(
                r.get("author_surnames_r"),
                (P.get(doi_o) or {}).get("surnames") or (original_authors.get(doi_o) or {}).get("surnames"),
                surname_freq, r.get("author_ids_r"), (original_authors.get(doi_o) or {}).get("ids")),
            "found_by": r.get("found_by") or [],
            "rep_already_known": bool(doi_r and doi_r in known_reps),
            "original_in_wiki": in_wiki,
            "effect": {"slug": eff[0], "name": eff[1]} if eff else None,
            "abstract": (r.get("abstract") or "")[:700] or None,
            "models": [t["model"]] if t.get("model") else [],
            "screen_reason": t.get("reason"),
            "origin": "retested_discovery",
            "review_state": "machine",
        })
    out.sort(key=lambda c: (not c["original_in_wiki"], c["group"] != "replication", -(c["year_r"] or 0)))
    if already:
        print(f"    dropped {already} finds FORRT already records somewhere")
    return out


def consequences(candidates: list[dict], g: dict) -> None:
    """Annotate each candidate with what accepting it would do to the record it belongs to.

    A reviewer deciding on a row is not filing paperwork; they are deciding whether an effect currently labelled
    "Replicated once" becomes "Contested". 84% of our linked finds attach to a finding with no more than one coded
    replication, which is exactly where one more verdict moves the label, so the consequence is usually real and
    worth showing before the decision rather than after it.

    Computed one row at a time, because that is how the decision is made. Rows with no stated outcome cannot move
    a record and get nothing.
    """
    from .evidence import record_status
    A = g["attempts"]
    current: dict[str, list[str]] = {}
    for c in candidates:
        if not (c.get("outcome") and c.get("original_in_wiki")):
            continue
        doi = c["doi_o"]
        if doi not in current:
            f = g["findings"][doi]
            current[doi] = [A[a]["outcome"] for a in f["attempts"] if A[a]["type"] == "replication"]
        before = record_status(current[doi])
        after = record_status(current[doi] + [c["outcome"]])
        c["if_accepted"] = {"from": before["code"], "from_label": before["label"],
                            "to": after["code"], "to_label": after["label"],
                            "changes": before["code"] != after["code"],
                            "k_before": before["k"], "k_after": after["k"]}


def pending(candidates: list[dict], g: dict) -> dict:
    """Our linked finds, grouped for the pages that show them as unverified, pending review.

    A page gets a row only when every step behind it has been measured and held up. Screening: high tier only, whose
    screen was right 86% of the time against the owner's 70 hand labels, against 50% for the medium tier. Linking:
    only the two sources that survived reading 65 links one by one — a library match at high or medium confidence
    (24/25 right) and an OpenAlex match at high confidence (10/11). Citation-derived links (6/11), medium OpenAlex
    (2/4) and low library matches (5/14) do not qualify; before this rule 53% of what pages showed pointed at the
    wrong original. See docs/LINK_AUDIT_20260919.md.

    Everything that does not qualify stays in the review queue, which is the right home for a claim that needs a
    person. Also queue-only: registered protocols, which have no result to put beside a record, other behavioural
    sciences, which are not part of a psychology effect's record, and FORRT's own extractor candidates, because
    publishing someone else's unreviewed list on a page is their editorial call, not ours."""
    by_finding: dict[str, list[dict]] = {}
    by_effect: dict[str, list[dict]] = {}
    for c in candidates:
        if (c["origin"] == "retested_discovery" and c["original_in_wiki"] and c["group"] == "replication"
                and c["search_tier"] == "high" and _link_trusted(c)):
            by_finding.setdefault(c["doi_o"], []).append(c)
    for doi_o, rows in by_finding.items():
        for eid in g["findings"][doi_o].get("effects") or []:
            by_effect.setdefault(eid, []).extend(rows)
    order = {"high": 0, "medium": 1, "low": 2}

    for d in (by_finding, by_effect):
        for rows in d.values():
            rows.sort(key=lambda c: (order.get(c.get("link_confidence"), 3), -(c["year_r"] or 0)))
    # what the record would say if every row shown on that page were accepted -- the per-candidate if_accepted
    # answers a different question (this row alone), and taking one of them would misreport a page with several
    from .evidence import record_status
    A = g["attempts"]
    verdicts = {}
    for doi, rows in by_finding.items():
        outs = [r["outcome"] for r in rows if r.get("outcome")]
        if not outs:
            continue
        cur = [A[a]["outcome"] for a in g["findings"][doi]["attempts"] if A[a]["type"] == "replication"]
        before, after = record_status(cur), record_status(cur + outs)
        verdicts[doi] = {"from": before["code"], "from_label": before["label"], "to": after["code"],
                         "to_label": after["label"], "changes": before["code"] != after["code"],
                         "n_accepted": len(outs), "k_before": before["k"], "k_after": after["k"]}
    eff_verdicts = {}
    for eid, rows in by_effect.items():
        outs = [r["outcome"] for r in rows if r.get("outcome")]
        if not outs:
            continue
        e = next((x for x in g["effects"].values() if x["id"] == eid), None)
        if not e:
            continue
        cur = [A[a]["outcome"] for a in e["attempts"] if A[a]["type"] == "replication"]
        before, after = record_status(cur), record_status(cur + outs)
        eff_verdicts[eid] = {"from": before["code"], "from_label": before["label"], "to": after["code"],
                             "to_label": after["label"], "changes": before["code"] != after["code"],
                             "n_accepted": len(outs), "k_before": before["k"], "k_after": after["k"]}
    return {"by_finding": by_finding, "by_effect": by_effect, "verdict_if_accepted": verdicts,
            "effect_verdict_if_accepted": eff_verdicts}


# How close to the original did the authors say they were? This is FORRT's `same_design` / closeness question,
# which they coded for 4-10% of entries. Authors state it themselves far more often than anyone codes it, and the
# word they choose is their own claim rather than our inference. "Conceptual" is the one that matters: it means a
# different operationalisation, so a failure is much weaker evidence against the original.
_KIND = re.compile(r"\b(direct|close|exact|literal|conceptual|systematic|approximate|paradigmatic)[a-z]*\s+"
                   r"(?:and\s+\w+\s+)?replicat", re.I)
_HIGH_FIDELITY = {"direct", "close", "exact", "literal"}


def declared_design(title: str | None, abstract: str | None) -> dict | None:
    """The replication type the authors claim, taken verbatim from their own title or abstract."""
    m = _KIND.search(f"{title or ''}. {abstract or ''}")
    if not m:
        return None
    word = m.group(1).lower()
    return {"word": word,
            "fidelity": "high" if word in _HIGH_FIDELITY else "low" if word == "conceptual" else "unclear",
            "said_in": "title" if _KIND.search(title or "") else "abstract"}


def _prereg(rec: dict | None) -> dict | None:
    if not rec or rec.get("kind") is None:
        return None
    return {"is_registration": bool(rec.get("registration")), "date": rec.get("date_registered"),
            "osf_kind": rec.get("kind"), "source": "osf_api"}


def independence(rep_surnames: list[str] | None, orig_surnames: list[str] | None,
                 freq: dict[str, int] | None = None,
                 rep_ids: list[str] | None = None, orig_ids: list[str] | None = None) -> dict | None:
    """Does the replication team share an author with the original?

    This is FORRT's author_overlap, which is the strongest thing in their data: replications sharing an author with
    the original report success 70% of the time, independent ones 38%. FORRT has it coded for 20% of findings and
    for none of ours, but both author lists are already here, so it can simply be computed.

    A shared surname is not proof of a shared person, and the base rate says so loudly: across 171,000 author slots
    the median surname appears once, the 99th percentile is 30, and "chen" appears 832 times. So a match on common
    names only is reported as possible_shared_name, not as overlap. "dekay" matching on a DeKay replication means
    something; "kim" does not. Absent either author list it says nothing rather than guessing independence.
    """
    from .load import COMMON_SURNAME
    freq = freq or {}
    # OpenAlex author ids settle the question; fall back to surnames only when one side has no ids
    if rep_ids and orig_ids:
        shared_ids = sorted(set(rep_ids) & set(orig_ids))
        return {"verdict": "shares_author" if shared_ids else "independent", "basis": "openalex_author_id",
                "shared": shared_ids, "distinctive": shared_ids,
                "n_replication_authors": len(rep_ids), "n_original_authors": len(orig_ids)}
    if not rep_surnames or not orig_surnames:
        return None
    shared = sorted(set(rep_surnames) & set(orig_surnames))
    distinctive = [n for n in shared if freq.get(n, 0) < COMMON_SURNAME]
    verdict = "independent" if not shared else ("shares_author" if distinctive else "possible_shared_name")
    return {"verdict": verdict, "basis": "surname", "shared": shared, "distinctive": distinctive,
            "shared_frequency": {n: freq.get(n, 0) for n in shared},
            "n_replication_authors": len(rep_surnames), "n_original_authors": len(orig_surnames)}


# (link method, confidence) pairs that read correctly often enough to stand beside a verdict unreviewed
TRUSTED_LINKS = {("library_author_year", "high"), ("library_author_year", "medium"), ("openalex_author_year", "high")}


def _link_trusted(c: dict) -> bool:
    return (c.get("link_method"), c.get("link_confidence")) in TRUSTED_LINKS


def _effect_of(g: dict) -> dict:
    out: dict[str, tuple[str, str]] = {}
    for e in g["effects"].values():
        for d in e["originals"]:
            out.setdefault(d, (e["slug"], e["name"]))
    return out


def _int(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None
