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
    from .load import load_reread, load_curated_multi_original_links
    reread = load_reread()
    multi_originals = load_curated_multi_original_links()
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
        source_link = bool(link and link.get("method") == "source-backed citation")
        using_cited = bool(t.get("original_doi") and not source_link)
        doi_o = (link or {}).get("doi_o") if source_link else (t.get("original_doi") or (link or {}).get("doi_o"))
        if doi_r and doi_o and (doi_o, doi_r) in known_pairs:
            continue                                      # FORRT already records this exact pair
        named = t.get("original") or {}
        in_wiki = bool(doi_o and doi_o in g["findings"])
        eff = effect_of.get(doi_o)
        out.append({
            "id": r["cid"],
            "doi_r": doi_r, "title_r": r.get("title_r"), "year_r": r.get("year_r"), "journal_r": r.get("venue"),
            "authors_r": r.get("authors_r"),
            "doi_o": doi_o, "original_studies": multi_originals.get(r["cid"]),
            # OpenAlex first for originals we do not hold: for 1,127 of the card candidates the wiki has nothing
            # but a DOI, and the link's own title is whatever the matcher happened to score against
            "title_o": ((P.get(doi_o) or {}).get("title") if in_wiki else None)
                       or (original_authors.get(doi_o) or {}).get("title") or (link or {}).get("title_o"),
            "year_o": ((P.get(doi_o) or {}).get("year") if in_wiki else None)
                      or (original_authors.get(doi_o) or {}).get("year") or (link or {}).get("year_o"),
            "authors_o": (P.get(doi_o) or {}).get("authors") or (original_authors.get(doi_o) or {}).get("authors"),
            "journal_o": (P.get(doi_o) or {}).get("journal") or (original_authors.get(doi_o) or {}).get("journal"),
            "cited_by_o": (original_authors.get(doi_o) or {}).get("cited_by"),
            "retracted_o": (original_authors.get(doi_o) or {}).get("is_retracted"),
            "abstract_o": (original_authors.get(doi_o) or {}).get("abstract"),
            # The screen reads the abstract. Where the abstract does not say how the replication turned out,
            # `pipeline reread` reads the text that does — the OSF wiki the team wrote, the Results section of
            # the open-access paper — and that answer is used ONLY where the screen had none. It never overrides
            # the screen: two readings of different sources disagreeing is a thing to measure, not to silently
            # resolve, and the screen's reading is the one with 224 hand labels behind it.
            "outcome": (t.get("outcome") if t.get("outcome") != "not_reported" else None)
                       or (reread.get(r["cid"]) or {}).get("outcome"),
            "outcome_quote": t.get("outcome_quote") or (reread.get(r["cid"]) or {}).get("quote"),
            "outcome_confidence": t.get("confidence") if t.get("outcome") != "not_reported"
                                  else (reread.get(r["cid"]) or {}).get("confidence"),
            "outcome_source": "abstract" if t.get("outcome") not in (None, "not_reported")
                              else ((reread.get(r["cid"]) or {}).get("source") if reread.get(r["cid"]) else None),
            # A DOI the model picked out of the citation list carries no score of its own — the model writes its
            # account of the original AFTER choosing it, so nothing about the pair can be compared. So it says
            # "unscored" rather than borrowing high/medium/low, which mean a score elsewhere. How often it is
            # right is a question for the audit, not for a band: 72 of 84 read, 86%, which is the most-read band
            # there is and still short of the 90% a page requires.
            "link_confidence": ("unscored" if using_cited else (link or {}).get("confidence")),
            "link_method": "cited by this paper" if using_cited else (link or {}).get("method"),
            "link_evidence": {k: link.get(k) for k in ("score", "text_sim", "authors_matched", "year_delta",
                                                       "margin", "n_references", "runner_up", "source_url", "evidence") if k in (link or {})}
                             if link and not using_cited else None,
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


_TITLEKEY = re.compile(r"[^a-z0-9]")
_OSF_VERSION = re.compile(r"^([a-z0-9]{5})(?:_v\d+)?$", re.I)


def _dedupe_key(c: dict) -> str | None:
    """What makes two records the same piece of work.

    One replication reaches us several times: an OSF preprint and its own later versions (ck4st, ck4st_v2,
    ck4st_v5), a preprint DOI and the published DOI, a Zenodo deposit re-minted, or a DOI record and a bare
    OpenAlex record for the same paper. 286 of 3,897 finds were redundant this way. It matters most at the export:
    FORRT would have received seven rows for one study.
    """
    t = _TITLEKEY.sub("", (c.get("title_r") or "").lower())[:70]
    if len(t) > 25:
        return "t:" + t
    if c.get("osf_id") and (m := _OSF_VERSION.match(c["osf_id"])):
        return "o:" + m.group(1).lower()
    return None


def _completeness(c: dict) -> tuple:
    """Prefer the published record, then one with a DOI, then whichever carries the most."""
    return (c.get("evidence_tier") == "published", bool(c.get("doi_r")), bool(c.get("outcome")),
            bool(c.get("outcome_quote")), bool(c.get("doi_o")), sum(1 for v in c.values() if v not in (None, "", [], {})))


def dedupe(candidates: list[dict]) -> list[dict]:
    """Collapse repeats of one piece of work, keeping the fullest record and noting what it absorbed."""
    groups: dict[str, list[dict]] = {}
    out: list[dict] = []
    for c in candidates:
        k = _dedupe_key(c) if c["origin"] == "retested_discovery" else None
        if k is None:
            out.append(c)
        else:
            groups.setdefault(k, []).append(c)
    for k, rows in groups.items():
        rows.sort(key=_completeness, reverse=True)
        best, rest = rows[0], rows[1:]
        if rest:
            best = {**best, "duplicates": [r["id"] for r in rest],
                    # when the copies were linked to different originals they disagree with themselves; say so
                    "duplicate_originals_disagree": len({r["doi_o"] for r in rows if r["doi_o"]}) > 1}
        out.append(best)
    return out


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


# Which link bands may stand beside a verdict on a page, decided by the reading rather than by a list somebody
# maintains. A band qualifies when at least MIN_READ of its links have been read one by one and at least
# MIN_RIGHT of those pointed at the right original — the rule this project stated when it first gated pages
# ("the strata measured above 90%"), now applied uniformly instead of case by case.
#
# It is applied from data/curated/original_audit.csv on every build, because a hand-kept list goes stale in both
# directions and did: `reference_scan` high sat in the trusted set on a claimed 89% and reads 80% over 40 cases;
# `cited by this paper` was promoted on 34 of 36 and reads 86% over 84; `openalex_author_year` medium was kept
# out on 2 of 4 and reads 91% over 33. A point estimate near the line at n≈30 is not stable, so expect bands to
# move as reading accumulates — that is the mechanism working, and `pipeline originals --score` shows why.
MIN_READ, MIN_RIGHT = 20, 0.90

# What a reader's third answer means when a rate is computed. `right` and `wrong` are findings; `unclear` is the
# reader declining to judge — a bare title on one side, a plausible match nothing confirms — and it is not
# evidence the match is wrong. The harm this bar exists to prevent is a WRONG original sitting under a card, so
# the rate is right/(right+wrong) and unclear rows are set aside and counted separately.
#
# This file used right/n and the verifier's calibration used right/(right+wrong), which is one convention too
# many: on 2026-09-22 the two differed by 146 cards on the same labels, purely in how three "can't tell" reads
# were treated. One rule now, stated here, and both callers use it. Where unclear rows are numerous enough to
# matter, `originals --score` prints them in their own column so the choice stays visible rather than buried.
def rate(right: int, wrong: int) -> float | None:
    return right / (right + wrong) if right + wrong else None


def trusted_links() -> set[tuple[str, str]]:
    from . import audit
    from .originals import read_labels, _pool, band, stale
    idx = audit.index(read_labels())
    labels = {c["id"]: l for c in _pool("linked")
              if (l := audit.label_for(idx, c["id"], c.get("doi_o")))}
    tally: dict[tuple[str, str], list[int]] = {}
    for c in _pool("linked"):
        # A label whose row has since been rematched describes a different paper, so it says nothing about the
        # band the row is in now. The scorer already knew this; the gate that decides what ships did not, and
        # was reading reference_author/high as 31 right of 42 where the live labels say 28 of 30.
        if c["id"] in labels and not stale(c, labels[c["id"]]):
            k = (c.get("link_method"), c.get("link_confidence"))
            t = tally.setdefault(k, [0, 0])
            t[0] += labels[c["id"]]["label"] == "right"
            t[1] += labels[c["id"]]["label"] == "wrong"
    return {k for k, (right, wrong) in tally.items()
            if right + wrong >= MIN_READ and (rate(right, wrong) or 0) >= MIN_RIGHT}


TRUSTED_LINKS = trusted_links()


# Whether ONE link may stand beside a verdict on a page, which is not the same question as whether its band may.
#
# A band score judges a row by the company it keeps, and that is its limit: inside `reference_scan` low, measured
# at 29% over 34 reads, sit links that are plainly right and links that are plainly wrong, and the band cannot
# tell them apart. `pipeline verify` asks about the row instead - here is the replication, here is the paper we
# matched it to, is this the one it re-tested - and was scored against 401 links a person had already read:
#
#   of the links it confirms, 260 of 264 were confirmed by the reader too - 98% (95%: 96-99%)
#   of the links it rejects outright, 52 of 65 the reader also called wrong - 80%
#   of the links it calls unclear, the reader called 39 of 54 right - about the average of the pool
#
# So the verdict is used where it is strong and not where it is weak. "right" admits the row whatever band it
# came from; "wrong" excludes it whatever band it came from, which costs 13 good rows per 65 and removes 52 bad
# ones.
#
# "unclear" used to fall back to the band rule, and on 2026-09-22 that fallback was measured and removed. It
# was the worst thing on the site. A band's 90% is an average dominated by rows the verifier confirmed, and the
# rows inside it that the verifier DECLINED to confirm are a different population: read out, a verifier-unclear
# link is right 18 times in 44, and within `reference_scan/high` — a trusted band — 6 times in 24. The band
# score was being carried to a population it was never measured on, which is the error this project keeps
# finding in new clothes. A row nobody sent to the verifier was admitted the same way and was right 0 of 3.
#
# So a link now appears beside a verdict only if a reader confirmed it or the verifier confirmed it. The band
# rule keeps the two jobs it is genuinely good at: ordering the matchers in `load.merged_links`, and standing
# in for unread rows when `originals --score` estimates how much of the pool is still a guess.
# Above all of that sits the reading. A hand label is a careful judgement about THIS pairing, and it is the
# evidence every other instrument here is calibrated against — the verifier's 98% is 98% agreement with these
# labels. Using it only to score a band, and then letting the band score overrule it on the very row it was
# made about, is backwards: until now a row a reader had read and called `right` was dropped whenever its band
# was overruled, and a row read as `wrong` stayed on the page if its band held up. A label now decides its own
# row, and the band rule keeps the job it is actually good for — standing in for rows nobody has read.
#
# `unclear` decides nothing, for the reason it never has: a reader declining to judge is not a finding.
def _link_trusted(c: dict) -> bool:
    l = _read_label(c)
    if l in ("right", "wrong"):
        return l == "right"
    # Looked up by (find, paper): a verdict about a paper this find no longer points at simply is not found.
    v = _verified().get((c["id"], c.get("doi_o")))
    return v == "right" and band(c) not in _overruled()


def band(c: dict) -> str:
    return f"{c.get('link_method')}/{c.get('link_confidence')}"


_OVERRULED: set[str] | None = None


def _overruled() -> set[str]:
    """Bands where the verdict does not get to override the band rule, because it has been read and does not hold.

    The verifier is let past the band gate because it measures 98% against links a person had read. That is an
    average over every band, and it is not the same everywhere. Read 55 rows of `reference_scan/medium` that the
    verifier had confirmed and 47 are right — 85%, under the bar, on a sample big enough to mean it. An average
    that clears a bar does not license every part of it, which is the same mistake as carrying a calibration to
    a population it was not measured on.

    So a band is overruled once at least MIN_READ of ITS SHIPPED rows have been read and fewer than MIN_RIGHT of
    them hold. Computed from the labels like everything else, so it turns itself off if more reading clears the
    band, and on if a band that ships starts failing.
    """
    global _OVERRULED
    if _OVERRULED is None:
        from . import audit
        from .originals import read_labels, stale
        from .audit import candidates
        idx = audit.index(read_labels())
        labels = {c["id"]: l for c in candidates()
                  if (l := audit.label_for(idx, c["id"], c.get("doi_o")))}
        tally: dict[str, list[int]] = {}
        for c in candidates():
            l = labels.get(c["id"])
            if not c.get("doi_o") or not l or stale(c, l):
                continue
            if _verified().get((c["id"], c.get("doi_o"))) != "right":
                continue                       # only rows the verdict is what admits
            t = tally.setdefault(band(c), [0, 0])
            t[0] += l["label"] == "right"
            t[1] += l["label"] == "wrong"
        _OVERRULED = {b for b, (right, wrong) in tally.items()
                      if right + wrong >= MIN_READ and (rate(right, wrong) or 1) < MIN_RIGHT}
    return _OVERRULED


_LABELS: dict | None = None


def _read_label(c: dict) -> str | None:
    """What a reader said about this exact pairing, or None if nobody has read it."""
    global _LABELS
    if _LABELS is None:
        from . import audit
        from .originals import read_labels
        _LABELS = audit.index(read_labels())
    from . import audit
    l = audit.label_for(_LABELS, c["id"], c.get("doi_o"))
    if not l:
        return None
    from .originals import stale
    return None if stale(c, l) else l.get("label")


_VERIFIED: dict[tuple[str, str], str] | None = None


def _verified() -> dict[tuple[str, str], str]:
    global _VERIFIED
    if _VERIFIED is None:
        from .load import load_verified_matches
        _VERIFIED = load_verified_matches()
    return _VERIFIED


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
