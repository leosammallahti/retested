"""The wiki story: what a reader of an effect or finding page is told, assembled from the Store with a source for every part.

    python -m pipeline wiki [--release | --all | --slug SLUG ...] [--posts PATH]

Reads data/build/{effects,findings,attempts,papers}.json (so run `python -m pipeline build` first) and the curated posts,
and writes data/build/wiki.json: one "story" per page, which the Astro pages render. Nothing here calls a model and
nothing is invented: every sentence is either a template filled with counts the Store holds, or text written
elsewhere (the post, the replicators' own words, a reviewer's note), shown with where it came from. Two curated files
hold text an AI model wrote for the wiki: data/curated/wiki_explanations.json (per attempt, "what they did" and "what
they found", from that attempt's own abstract and words only, checked mechanically and by a second model, then read
against the sources by Claude whether or not the check flagged it) and data/curated/wiki_scenes.json (the scene of a
finding that has no post, from the original paper's abstract, checked and then read against its card the same way).
An entry with no `read_on` was not read and the page says so. The page says what each was written from
and how it was checked. Text that is not ready is left out and the page says so; it is never replaced by a guess.

A story has these parts (all optional except the verdict):
  scene     what people did, then what the original found (a reviewed post); answer-blind, safe before a prediction
  original  the paper, its own words, who took part and what was measured where a source review holds them
  verdict   the record in plain words with counts
  attempts  each later attempt: who, when, what they said in their own words, size, design flags, links
  sure      facts that say how much weight the record can bear
  numbers   pooled and original effect size in plain words
  why       differences between the original and the attempts that a source states or the data shows
  sources   where each part came from
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from . import posts as _posts
from .load import ROOT

BUILD = ROOT / "data" / "build"
CURATED = ROOT / "data" / "curated"
DISCOVERY = ROOT / "data" / "discovery"
SCHEMA = 1

# a source's own coding note is not the replicators' words (same list the feed uses)
CODING_NOTE = re.compile(r"^(\[?coded |subjective replication success rating|replicated = (yes|no)|(ticked|crossed) in |"
                         r"rep\d+ (s|study)|\[in supplementary)|the row is recorded as|binary (success )?indicator|"
                         r"\bnot both columns\b|^NB:\s", re.I)
# sentences in a reviewer's note that are bookkeeping about how the pair was found, not about the studies
ADMIN = re.compile(r"openalex|\bW\d{7,}\b|cov index|cached|primary[_ ]topic|primary psychology|official anonymous|"
                   r"retested|candidate|replaces one|no new counted|existing page|curated|\blink(ed|s)?\b|correct(ion|ed)|"
                   r"verified|page\b|\bpool\b|\bFORRT\b|\bFLoRA\b|\bFReD\b|dedup|duplicate|sibling|same[- ]work|"
                   r"scopus|crossref|doi\b|landing|full ?text|paywall|abstract[- ]only|source[- ]review|"
                   r"type article|field display|\bnode\b|not a new pair|counted|"
                   r"publisher|pubmed|\bcitation|support(s)? the pair|record lacks|do not generali[sz]e|claim is restricted|"
                   r"\bpair\b|\bcite[sd]?\b|\breference\b|\bsource\b|\bmetadata|\bindexed|"
                   r"co-?author|disjoint|\bauthors?\b.*\b(overlap|recur|participate|joined)|\boverlap|abstract (names|reports|states)|"
                   r"\bthe (original|later) (abstract|record|article|publication|primary)\b.*\b(supports?|names|reports|identifies)\b", re.I)

# sentences that explain how the reviewer scored the pair or when it was published, not what the studies did
META = re.compile(r"\bscoped?\b|\bsuccessful (is|refers|verdict)|\bmixed (reflects|outcome|verdict)|\b(failed|successful|mixed) (is|refers)\b|"
                  r"\bverdict\b|\boutcome (is|was|label)\b|\bthis row\b|\bthe count\b|\bis limited to\b|\bnot proof\b|\bdoes not establish\b|"
                  r"\bso the (effect|outcome|result) is\b|\breceives a\b|published online|\bissue( year)?\b|online \d{4}\b|"
                  r"\bdo not\b.*\b(treat|count)\b|\bnarrowly\b|\bexplicitly call|"
                  r"authored both|\bon both\b|appears? on both|\bshared (original )?authors?\b|\bsame (first |two |four |three )?authors?\b|"
                  r"\blabel\b|\bcoded\b|\bcoding (concerns|is|here)\b|outcome mixed|\bfull[- ]study\b|\bmeans no\b|applies only to|\bnot causal\b|not a causal|"
                  r"\bdescriptive, not\b|abstract (explicitly|contains|additionally)|accessible records|10\.\d{4,}|\bNCT\d+|\bOSF\b|"
                  r"appeared online|\bprint (volume |issue )?years?\b|\bnot a claim\b|\ba failure of the\b|\bfailure of the original\b|"
                  r"original[- ]paper author|original authors? (among|recur)|^\d{4}\b|^later:|\bn(ame)?d? in the later abstract\b|\bis (the )?target\b|\bthe target (is|here)\b|\bexact target\b", re.I)

HEADLINE = {
    "replicated": "Every later attempt with a clear verdict found it.",
    "largely_replicated": "Most later attempts found it.",
    "contested": "Later attempts disagree with one another.",
    "largely_failed": "Most later attempts did not find it.",
    "failed": "No later attempt found it.",
    "reversed": "Later work points the other way, or to a different cause.",
    "single_success": "The one later attempt found it.",
    "single_failure": "The one later attempt did not find it.",
    "single_mixed": "The one later attempt found part of it.",
    "unclear": "Later attempts exist, but none has a clear verdict yet.",
    "untested": "No later attempt is in the record yet.",
}
VERDICT_WORD = {"successful": "found it", "failed": "did not find it", "mixed": "found part of it",
                "inconclusive": "was inconclusive", "not_coded": "has no clear verdict yet"}


# ---------------------------------------------------------------- text hygiene

def _vocab(attempts: dict) -> Counter:
    """Words as they appear whole in the corpus, to tell 'con- trol' (a line break) from 'ego- depletion' (a hyphen)."""
    c: Counter = Counter()
    for a in attempts.values():
        for t in (a.get("quote"), (a.get("retested_review") or {}).get("outcome_quote"),
                  (a.get("retested_review") or {}).get("original_claim_quote")):
            if t:
                c.update(w.lower() for w in re.findall(r"[A-Za-z]{4,}", t.replace("-\n", "")))
    return c


def tidy(s: str | None, vocab: Counter) -> str:
    """One line, outer quotes off, line-break hyphens healed. Never changes a word otherwise."""
    if not s:
        return ""
    t = re.sub(r"\s+", " ", str(s).replace("​", "")).strip()
    pairs = {'"': '"', "'": "'", "“": "”", "‘": "’"}
    if len(t) > 1 and pairs.get(t[0]) == t[-1]:
        t = t[1:-1].strip()

    def heal(m: re.Match) -> str:
        a, b = m.group(1), m.group(2)
        joined = (a + b).lower()
        if vocab.get(joined, 0) >= 1 and vocab.get(f"{a}-{b}".lower(), 0) == 0 and b[0].islower():
            return a + b
        return f"{a}-{b}"
    t = re.sub(r"([A-Za-z]{2,})- ([a-z][A-Za-z]*)", heal, t)
    return t


def cut(s: str, n: int) -> str:
    """Shorten at a sentence end if possible, else a word end, and say so with an ellipsis."""
    if len(s) <= n:
        return s
    head = s[:n]
    m = list(re.finditer(r"[.!?][\"”’)]*\s", head))
    if m and m[-1].end() > n * 0.55:
        return head[:m[-1].end()].strip()
    return head.rsplit(" ", 1)[0].rstrip(",;:") + " …"


def review_sentences(note: str | None) -> list[str]:
    """The sentences of a reviewer's note that describe the studies, as written; bookkeeping sentences are dropped."""
    if not note:
        return []
    out = []
    for s in _posts.sentences(re.sub(r"\s+", " ", note).strip()):
        if ADMIN.search(s) or META.search(s) or len(s) < 45:
            continue
        out.append(s)
    return out


# ---------------------------------------------------------------- facts

def _n_of(a: dict) -> int | None:
    """Participants in the attempt, only where the record's number is one a reader can trust.

    A multi-site project is coded as many rows (and the old legacy file as one small row), so a size taken from
    several rows or from the legacy file can be a single site's size. Those attempts show no size; a reviewer's note
    may carry the real one and is shown as written.
    """
    est = a.get("est") or {}
    if est.get("n") and est.get("k_rows", 1) == 1 and not est.get("legacy"):
        return int(est["n"])
    rows = a.get("rows", [])
    ns = {r.get("n_r") for r in rows if r.get("n_r")}
    if len(ns) == 1 and len(rows) <= 2:
        return int(next(iter(ns)))
    return None


def dedupe_quote(q: str | None) -> str:
    """An attempt's quote is its rows' quotes joined with ' || '; keep each distinct passage once, longest wins."""
    if not q:
        return ""
    parts = []
    for p in (x.strip() for x in q.split("||")):
        p = re.sub(r"\s+", " ", p)
        if p and p not in parts:
            parts.append(p)
    parts = [p for p in parts if not any(p != o and o.startswith(p) for o in parts)]
    return parts[0] if len(parts) == 1 else " … ".join(parts[:2])


def _title(t: str | None) -> str | None:
    """A title as the record holds it, without the footnote asterisks some publishers leave in."""
    return re.sub(r"\s*\*+\s*$", "", t).replace("*", "") if t else t


def short_authors(s: str | None) -> str | None:
    """'Xiaomeng Xu, Kathryn E. Demos, Tricia M. Leahey, ... 2014' -> 'Xu et al.' (the record sometimes lists everyone)."""
    if not s or s.count(",") < 3 or " et al" in s:
        return s
    first = s.split(",")[0].strip().split()
    return f"{first[-1]} et al." if first else s


def _n_orig(attempts: list[dict]) -> int | None:
    for a in attempts:
        e = a.get("est") or {}
        if e.get("n_o"):
            return int(e["n_o"])
        for r in a.get("rows", []):
            if r.get("n_o"):
                return int(r["n_o"])
    return None


def _studies(a: dict) -> list[str]:
    return sorted({str(r["study_o"]).strip() for r in a.get("rows", []) if r.get("study_o") not in (None, "")})


def _fr(x: float) -> str:
    return ("−" if x < 0 else "") + f"{abs(x):.2f}".lstrip("0")


DIFFERS_CORE = re.compile(r"differ|conceptual|not any exact|more reliable|instead|rather than|unlike|modif|adapt|different (task|measure|sample|population|version)", re.I)
DIFFERS_WIDE = re.compile(r"differ|conceptual|not any exact|more reliable|instead|rather than|unlike|modif|adapt|different (task|measure|sample|population|version)|\boriginal\b.*\b(later|replication)\b|\b(later|replication)\b.*\boriginal\b|\bnew (participants|sample|group|cohort|population)\b", re.I)
REASON = re.compile(r"\bnot due to\b|\bbecause\b|\bexplained by\b|\bmoderated by\b|\bmay be due\b|\bmight be that\b|\bdue to\b", re.I)
RESULT_BITS = re.compile(r"pooled|\bCI\b|\bd ?= ?-?\d|\br ?= ?-?\.?\d|\bp ?[<=>] ?\.?\d|no (depletion|effect)", re.I)


def _surnames(authors: str | None) -> set[str]:
    """Surnames in an author string like 'Kidd & Castano' or 'Panero et al.' (only the names it lists)."""
    if not authors:
        return set()
    t = re.sub(r"\bet al\.?", "", authors)
    out = set()
    for chunk in re.split(r"\s*(?:&|,| and )\s*", t):
        w = re.findall(r"[A-Za-zÀ-ɏ\-']+", chunk)
        if w:
            out.add(w[-1].lower())
    return out


def shares_author(a: dict, orig: dict | None) -> bool:
    """True only when two or more listed surnames of the attempt are among the original's (one common surname proves nothing)."""
    sn = _surnames(a.get("authors_r"))
    on = set((orig or {}).get("surnames") or [])
    return len(sn) >= 2 and sn <= on


_OA: dict | None = None


def oa_links() -> dict:
    """Legal free copies and real paper pages from OpenAlex's open-access record (data/discovery/replication_oa_links.json,
    written by /root/wiki-scratch/oa_links.py); empty when the file is absent."""
    global _OA
    if _OA is None:
        p = DISCOVERY / "replication_oa_links.json"
        _OA = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"by_doi": {}, "by_openalex_id": {}}
    return _OA


def links_for(a: dict) -> tuple[str | None, str | None, str | None]:
    """(paper page, free copy, free copy's version) for an attempt: the record's own links first, OpenAlex's after."""
    oa = oa_links()
    rec = (oa["by_doi"].get((a.get("doi_r") or "").lower()) or {}) if a.get("doi_r") else {}
    url = a.get("url_r")
    m = re.match(r"https?://openalex\.org/(W\d+)", url or "")
    if m:                       # a catalogue entry, not the paper: link the paper's own page when OpenAlex names one
        rec = oa["by_openalex_id"].get(m.group(1)) or rec
        url = rec.get("paper_url") or url
    if a.get("oa_url_r"):
        return url, a["oa_url_r"], None
    return url, rec.get("free_url"), rec.get("free_version")


def explanation_for(a: dict, explanations: dict) -> dict | None:
    """The written "what they did / what they found" for an attempt, if one was written for this very paper.

    Each entry records the later paper's DOI it was written from; if the attempt has since been matched to another
    paper the entry no longer applies and is not shown."""
    e = explanations.get(a["id"])
    if not e or (e.get("doi_r") or None) != (a.get("doi_r") or None) or not (e.get("did") and e.get("found")):
        return None
    return e


def attempt_story(a: dict, vocab: Counter, lines: dict, orig: dict | None, explanations: dict | None = None) -> dict:
    est = a.get("est") or {}
    rv = a.get("retested_review") or {}
    q = tidy(rv.get("outcome_quote") or dedupe_quote(a.get("quote")), vocab)
    if q and CODING_NOTE.search(q):
        q = ""
    ov = a.get("author_overlap_pct")
    independent = (ov == 0) if ov is not None else (False if shares_author(a, orig) else None)
    ex = explanation_for(a, explanations or {})
    line = None if ex else (lines.get(a["id"]) or {}).get("line")
    sentences = [tidy(s, vocab) for s in review_sentences(rv.get("review_note"))]
    why = [{"text": s, "kind": "design", "from": "reviewer’s note", "who": None} for s in sentences if (DIFFERS_CORE if (line or ex) else DIFFERS_WIDE).search(s) and not RESULT_BITS.search(s)]
    raw_q = tidy(dedupe_quote(a.get("quote")), vocab)
    if raw_q and not CODING_NOTE.search(raw_q) and REASON.search(raw_q):
        why.append({"text": cut(raw_q, 420), "kind": "their reasons", "from": "the authors’ own words", "who": None})
    return {
        "id": a["id"], "type": a["type"], "authors": short_authors(a.get("authors_r")), "year": int(a["year_r"]) if a.get("year_r") else None,
        "journal": a.get("journal_r"), "title": _title(a.get("title_r")), "doi": a.get("doi_r"),
        "open_url": links_for(a)[1], "open_version": links_for(a)[2], "url": links_for(a)[0],
        "outcome": a["outcome"], "sources_disagree": bool(a.get("sources_disagree")),
        "outcomes_by_source": a.get("outcomes_by_source") or {},
        "line": line,
        "did": ex["did"] if ex else None,
        "found": ex["found"] if ex else None,
        "written_from": ex.get("basis") if ex else None,
        # "read": an AI model other than the writer (Claude) read this text against its sources; "sampled": it passed the
        # automatic checks and a random sample of the run it came from was read, not this text itself
        "written_check": ("read" if ex.get("read_on") else "sampled") if ex else None,
        "their_words": cut(q, 420) if q else "",
        "their_words_from": rv.get("outcome_quote_source") if rv.get("outcome_quote") else a.get("quote_source"),
        "tested_study": _studies(a),
        "tested_paper": a.get("doi_o"),
        "n": _n_of(a),
        "r": est.get("r"), "ci": est.get("ci"),
        "preregistered": {"yes": True, "no": False}.get(a.get("preregistration_status")),
        "independent": independent,
        "reviewer_sentences": [] if (line or ex) else sentences,
        "why": why,
        "reviewed_on": rv.get("reviewed_on"),
        "reviewer_links": {"original": rv.get("original_source_url"), "replication": rv.get("replication_source_url")} if rv else None,
        "in": a.get("sources"),
    }


def verdict_story(rec: dict, atts: list[dict]) -> dict:
    s, m, f = rec["successful"], rec["mixed"], rec["failed"]
    unclear = rec["inconclusive"] + rec["not_coded"]
    n = len(atts)
    parts = []
    if s: parts.append(f"{s} found it")
    if m: parts.append(f"{m} found part of it")
    if f: parts.append(f"{f} did not find it")
    line = ""
    if n > 1 and parts:
        tail = (f"; {unclear} {'has' if unclear == 1 else 'have'} no clear verdict yet." if unclear else ".")
        line = f"Of {n} later attempts, " + ", ".join(parts) + tail
    headline = HEADLINE.get(rec["code"], "")
    if rec["code"].startswith("single_") and n > 1:
        headline = headline.replace("The one later attempt", "The one later attempt with a clear verdict")
    return {"code": rec["code"], "label": rec["label"], "headline": headline, "detail": line,
            "counts": {"successful": s, "mixed": m, "failed": f, "unclear": unclear}, "n_attempts": n}


def sure_facts(atts: list[dict], lens: dict) -> list[dict]:
    out = []
    reps = [a for a in atts if a["type"] == "replication"]
    papers = len({a.get("doi") or a["id"] for a in reps})
    years = [a["year"] for a in reps if a["year"]]
    span = f", {min(years)}–{max(years)}" if years and min(years) != max(years) else (f", {years[0]}" if years else "")
    if reps:
        out.append({"text": f"{len(reps)} later attempt{'s' if len(reps) != 1 else ''}, reported in {papers} paper{'s' if papers != 1 else ''}{span}.", "from": "the record"})
    known = [a for a in reps if a["preregistered"] is not None]
    yes = sum(1 for a in known if a["preregistered"])
    rest = len(reps) - len(known)
    if known:
        what = ("was" if yes == 1 else "were") if yes == len(known) else None
        head = (f"{yes} attempt{'s' if yes != 1 else ''} {what} preregistered (the plan was filed before the data came in)" if what
                else f"Of the {len(known)} attempts with a recorded answer, {yes} {'was' if yes == 1 else 'were'} preregistered (the plan was filed before the data came in)")
        out.append({"text": head + (f"; for the other {rest} it is not recorded." if rest else "."), "from": "FLoRA / FReD"})
    ind = [a for a in reps if a["independent"] is not None]
    if ind:
        same = sum(1 for a in ind if a["independent"])
        out.append({"text": (f"Author lists let us check {len(ind)} of {len(reps)} attempts: {same} {'was' if same == 1 else 'were'} run by "
                             f"{'a team' if same == 1 else 'teams'} sharing no author with the original"
                             + (f", {len(ind) - same} shared authors." if len(ind) - same else ".")), "from": "FLoRA author check"})
    dis = [a for a in reps if a["sources_disagree"]]
    if dis:
        out.append({"text": f"The coding sources disagree on {len(dis)} attempt{'s' if len(dis) != 1 else ''}; those are marked below.", "from": "the record"})
    if len(reps) == 1:
        out.append({"text": "One attempt is a thin record.", "from": "the record"})
    return out


def numbers_story(lens: dict) -> dict | None:
    num = lens.get("numeric")
    if not num:
        return None
    ratio = num.get("ratio")
    if ratio is None:
        rt = None
    elif ratio <= 0:
        rt = "no effect, or the opposite direction"
    else:
        rt = f"{round(min(ratio, 9.99) * 100)}% of the original’s size"
    return {"pooled_r": num["r"], "ci": num["ci"], "original_r": num.get("r_original"), "ratio_text": rt,
            "k_papers": num["k_papers"], "k_rows": num["k_rows"], "label": num["label"]["label"], "label_code": num["label"]["code"],
            "text": (f"Pooled across the attempts that report an effect size, the effect is r = {_fr(num['r'])} "
                     f"(95% range {_fr(num['ci'][0])} to {_fr(num['ci'][1])})"
                     + (f", against a typical original of r = {_fr(num['r_original'])}" if num.get("r_original") is not None else "")
                     + (f": {rt}." if rt else "."))}


# ---------------------------------------------------------------- scene

def _gid(doi: str, study: str) -> str:
    return "g" + hashlib.md5(f"{doi}|{study}".encode()).hexdigest()[:9]


def _fid(key: str) -> str:
    return "f" + hashlib.md5(key.encode()).hexdigest()[:9]


def clean_original_quote(q: str) -> str:
    """FReD stores the original's words as quoted fragments joined by [...]; show them as one passage of whole sentences."""
    q = re.sub(r'"\s*\[\.\.\.\]\s*"', " … ", q)
    q = re.sub(r"\s+", " ", q.replace('"', "").replace("[...]", " … ")).strip()
    q = re.sub(r"\s*\((?:Table|Figure|Fig\.)[^)]*\)", "", q)
    pieces = [p.strip() for p in q.split(" … ")]
    keep = [p for p in pieces if p[:1].isupper()]
    return " … ".join(keep or pieces)


def _original_words(doi: str, f: dict, attempts: dict, study: str | None, vocab: Counter) -> str:
    """The original authors' own words for this study, from the rows that name it (any row when the scene is the whole paper)."""
    for aid in f["attempts"]:
        for r in attempts[aid].get("rows", []):
            s = str(r.get("study_o") or "").strip().lower() or "-"
            q = r.get("claim_text_o")
            if q and len(q) > 30 and (study is None or s == study):
                return cut(tidy(clean_original_quote(q), vocab), 300)
    if study is None:
        for aid in f["attempts"]:
            q = (attempts[aid].get("retested_review") or {}).get("original_claim_quote")
            if q and len(q) > 30:
                return cut(tidy(q, vocab), 300)
    return ""


def scene_sources(posts: dict, scenes: dict) -> dict:
    """Every account a page may show as "what people did", by card id: the reviewed posts, and for a card with no post
    the wiki scene written for it (data/curated/wiki_scenes.json). A post always wins. A wiki scene is marked so the page
    can say how it was checked: read one by one, or checked automatically with a sample read."""
    out = {k: dict(v, check="read", written_from=None) for k, v in scenes.items() if k not in posts}
    for k in out:
        out[k]["check"] = "read" if scenes[k].get("read_on") else "sampled"
        out[k]["written_from"] = scenes[k].get("written_from")
    out.update({k: dict(v, check="read", written_from=None) for k, v in posts.items()})
    return out


def _scene(pid: str, posts: dict, label: str | None, quote: str = "", study: str | None = None) -> dict:
    rec = posts[pid]
    did, found = _posts.split(rec["post"])
    return {"id": pid, "label": label, "study": study, "quote": quote, "did": did, "found": found, "level": rec.get("source_level"),
            "writer": rec.get("writer"), "written_on": rec.get("written_on"), "check": rec.get("check", "read"),
            "written_from": rec.get("written_from")}


def finding_scenes(doi: str, f: dict, attempts: dict, posts: dict, holds: set, vocab: Counter) -> list[dict]:
    studies = set()
    for aid in f["attempts"]:
        for r in attempts[aid].get("rows", []):
            studies.add(str(r.get("study_o") or "").strip().lower() or "-")
    out = []
    for s in sorted(studies):
        pid = _gid(doi, s)
        if pid in posts and pid not in holds:
            out.append(_scene(pid, posts, None if s == "-" else f"Study {s}",
                              _original_words(doi, f, attempts, None if s == "-" else s, vocab), None if s == "-" else s))
    pid = _posts.paper_id(doi)
    if pid in posts and pid not in holds:
        out.append(_scene(pid, posts, None, _original_words(doi, f, attempts, None, vocab)))
    if len(out) == 1:
        out[0]["label"] = None
    return out


def paper_story(p: dict | None, doi: str) -> dict:
    p = p or {}
    return {"doi": doi, "title": _title(p.get("title")), "authors": p.get("authors"), "year": int(p["year"]) if p.get("year") else None,
            "journal": p.get("journal"), "cited_by": (p.get("openalex") or {}).get("cited_by"),
            "retracted": bool((p.get("openalex") or {}).get("is_retracted")), "ref": p.get("ref")}


def original_quote(atts: list[dict], rows_src: list[dict], vocab: Counter) -> str:
    for a in rows_src:
        for r in a.get("rows", []):
            q = r.get("claim_text_o")
            if q and len(q) > 30:
                return cut(tidy(q, vocab), 320)
    for a in rows_src:
        q = (a.get("retested_review") or {}).get("original_claim_quote")
        if q and len(q) > 30:
            return cut(tidy(q, vocab), 320)
    return ""


# ---------------------------------------------------------------- build

def _group_why(raw: list[dict], atts: list[dict]) -> list[dict]:
    """Differences between one original and the attempts at it that the record states or the numbers show."""
    out = []
    ns = [a["n"] for a in atts if a["n"] and a["type"] == "replication"]
    ons = {int(r["n_o"]) for a in raw for r in a.get("rows", []) if r.get("n_o")} | {int((a.get("est") or {})["n_o"]) for a in raw if (a.get("est") or {}).get("n_o")}
    on = next(iter(ons)) if len(ons) == 1 else None       # several studies, several sizes: no single "the original tested N"
    if on and ns:
        span = f"{min(ns):,}" if min(ns) == max(ns) else f"{min(ns):,} to {max(ns):,}"
        who = "the attempt" if len(ns) == 1 else "every attempt"
        if all(n > on for n in ns):
            text = f"The original tested {on:,} people; {who} with a recorded size tested more ({span})."
        elif all(n < on for n in ns):
            text = f"The original tested {on:,} people; {who} with a recorded size tested fewer ({span})."
        else:
            text = f"The original tested {on:,} people; the attempts with a recorded size tested between {min(ns):,} and {max(ns):,}."
        out.append({"text": text, "kind": "size", "from": "FReD", "who": None})
    for a in atts:
        for w in a["why"]:
            out.append({**w, "who": f"{a['authors']} {a['year']}" if a["year"] else a["authors"]})
    return out


def build(slugs: set[str] | None, posts_path: Path | None = None) -> dict:
    eff = json.loads((BUILD / "effects.json").read_text(encoding="utf-8"))
    fnd = json.loads((BUILD / "findings.json").read_text(encoding="utf-8"))
    att = json.loads((BUILD / "attempts.json").read_text(encoding="utf-8"))
    pap = json.loads((BUILD / "papers.json").read_text(encoding="utf-8"))
    posts = json.loads((posts_path or CURATED / "posts.json").read_text(encoding="utf-8"))["posts"]
    sp = CURATED / "wiki_scenes.json"
    posts = scene_sources(posts, json.loads(sp.read_text(encoding="utf-8")).get("scenes", {}) if sp.exists() else {})
    hp = CURATED / "card_holds.json"
    holds = set(json.loads(hp.read_text(encoding="utf-8")).get("holds", {})) if hp.exists() else set()
    lp = CURATED / "wiki_lines.json"
    lines = json.loads(lp.read_text(encoding="utf-8")).get("lines", {}) if lp.exists() else {}
    ep = CURATED / "wiki_explanations.json"
    explanations = json.loads(ep.read_text(encoding="utf-8")).get("explanations", {}) if ep.exists() else {}
    vocab = _vocab(att)
    fby = {f["slug"]: (d, f) for d, f in fnd.items()}
    out = {"schema_version": SCHEMA, "effects": {}, "findings": {}}

    def common(atts_raw: list[dict], lens: dict, originals: list[str]) -> dict:
        ordered = sorted(atts_raw, key=lambda a: (a.get("year_r") or 9999, a["id"]))
        atts = [attempt_story(a, vocab, lines, pap.get(a.get("doi_o")), explanations) for a in ordered]
        raw_by_id = {a["id"]: a for a in ordered}
        multi = len(originals) > 1
        groups = []
        for d in sorted(originals, key=lambda d: ((pap.get(d) or {}).get("year") or 9999, d)):
            ga = [a for a in atts if a["tested_paper"] == d]
            if not ga:
                continue
            graw = [raw_by_id[a["id"]] for a in ga]
            groups.append({"original": paper_story(pap.get(d), d), "original_quote": original_quote(ga, graw, vocab),
                           "scenes": finding_scenes(d, fnd[d], att, posts, holds, vocab) if multi and d in fnd else [],
                           "attempts": ga, "why": _group_why(graw, ga)})
        # an attempt filed under no listed original is never dropped
        listed = {a["id"] for g in groups for a in g["attempts"]}
        rest = [a for a in atts if a["id"] not in listed]
        if rest:
            groups.append({"original": None, "original_quote": "", "scenes": [], "attempts": rest, "why": []})
        return {"verdict": verdict_story(lens["record"], atts), "attempts_n": len(atts), "groups": groups,
                "sure": sure_facts(atts, lens), "numbers": numbers_story(lens), "multi_original": multi,
                "same_paper_twice": sorted({a["doi"] for a in atts if a["doi"] and sum(1 for b in atts if b["doi"] == a["doi"]) > 1})}

    for e in eff:
        if slugs is not None and e["slug"] not in slugs:
            continue
        own = [att[i] for i in e["attempts"]]
        s = common(own, e["lenses"], e["originals"])
        scenes, scene_from = [], None
        pid = _fid(e["key"])
        if pid in posts and pid not in holds:
            scenes, scene_from = [_scene(pid, posts, None)], "the famous effect"
        elif len(e["originals"]) == 1 and e["originals"][0] in fnd:
            scenes = finding_scenes(e["originals"][0], fnd[e["originals"][0]], att, posts, holds, vocab)
            scene_from = "the original paper" if scenes else None
        s.update(kind="effect", slug=e["slug"], name=e["name"], scenes=scenes, scene_from=scene_from)
        out["effects"][e["slug"]] = s

    for slug, (doi, f) in fby.items():
        if slugs is not None and slug not in slugs:
            continue
        own = [att[i] for i in f["attempts"]]
        s = common(own, f["lenses"], [doi])
        expl = f.get("explanation")
        s.update(kind="finding", slug=slug, doi=doi, scenes=finding_scenes(doi, f, att, posts, holds, vocab),
                 explanation=({"claim": expl["original"]["claim"], "method": expl["original"]["method"],
                               "population": expl["original"]["population"], "measure": expl["original"]["outcome_measure"],
                               "source_url": expl["source"]["url"], "reviewed_on": expl["review"]["reviewed_on"]} if expl else None),
                 game_contexts=f.get("game_contexts") or [], effects=f.get("effects") or [])
        out["findings"][slug] = s
    return out


def released(doc: dict) -> dict:
    """The pages that carry the new template: those with a reviewed plain account of the experiment (a post).

    A page without one keeps its old layout until it has one: the story needs 'what people did' to read as a story,
    and nothing is written to fill the gap. The rule is the only gate, so a page joins the moment its post is imported.
    """
    return {"schema_version": doc["schema_version"],
            "effects": {k: v for k, v in doc["effects"].items() if v["scenes"] or any(g["scenes"] for g in v["groups"])},
            "findings": {k: v for k, v in doc["findings"].items() if v["scenes"]}}


def write_release(posts_path: Path | None = None) -> tuple[int, int]:
    doc = released(build(None, posts_path))
    (BUILD / "wiki.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return len(doc["effects"]), len(doc["findings"])


def main(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="pipeline wiki")
    ap.add_argument("--release", action="store_true", help="every page that has a reviewed post (what the build writes)")
    ap.add_argument("--all", action="store_true", help="every effect and finding story, released or not (for audits)")
    ap.add_argument("--slug", action="append", default=[], help="only this page (repeatable)")
    ap.add_argument("--posts", type=Path, help="read posts from this file instead of data/curated/posts.json")
    ap.add_argument("--out", type=Path, default=BUILD / "wiki.json")
    a = ap.parse_args(argv)
    if not (a.all or a.slug or a.release):
        ap.error("name pages with --slug, or use --release or --all")
    doc = build(None if (a.all or a.release) else set(a.slug), a.posts)
    if a.release:
        doc = released(doc)
    a.out.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    print(f"wiki: {len(doc['effects'])} effect stories, {len(doc['findings'])} finding stories -> {a.out}")
    return 0
