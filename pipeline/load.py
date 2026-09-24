"""Readers for the pinned raw sources. Every reader returns plain Python records; nothing here decides semantics."""
from __future__ import annotations

import csv
import json
import pickle
import re
import unicodedata
from pathlib import Path

import pandas as pd

from .ids import is_na, norm_doi

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
FORRT = RAW / "forrt"
CACHE = ROOT / "data" / "cache"
# Discovery and triage results live outside data/build, which `build` wipes on every run.
DISCOVERY = ROOT / "data" / "discovery"

SOURCES = {
    "flora": FORRT / "fred-data" / "output_flora.csv",
    "fred_explorer": FORRT / "feeds" / "fred-apps_explorer-data.json",
    "fred_output": FORRT / "fred-data" / "output_FReD.xlsx",
    "fred_legacy": FORRT / "osf" / "version-history" / "FReD_2.4.1_2025-06-25.xlsx",
    "famous": RAW / "local" / "docx_parsed_entries.json",
    "openalex": RAW / "local" / "openalex_original_enrichment.json",
    "extractor": FORRT / "feeds" / "flora-extractor_extracted.csv",
    "extractor_pending": FORRT / "feeds" / "flora-extractor_target_pending.csv",
    "citation": FORRT / "fred-data" / "output_citation.txt",
}


def _cached(name: str, src: Path, fn):
    """Pickle cache keyed by source size+mtime and the Python/pandas versions; any read error just rebuilds it.
    The raw file stays the source of truth."""
    import sys
    CACHE.mkdir(parents=True, exist_ok=True)
    st = src.stat()
    key = f"{st.st_mtime_ns}-{st.st_size}-py{sys.version_info[:2]}-pd{pd.__version__}"
    p = CACHE / f"{name}.pkl"
    if p.exists():
        try:
            with p.open("rb") as f:
                k, val = pickle.load(f)
            if k == key:
                return val
        except Exception:  # noqa: BLE001 - stale or foreign cache (other OS / pandas version): rebuild
            pass
    val = fn()
    with p.open("wb") as f:
        pickle.dump((key, val), f)
    return val


def clean(x):
    if x is pd.NaT or is_na(x):
        return None
    if isinstance(x, (pd.Timestamp,)) or hasattr(x, "isoformat"):
        return x.isoformat()[:10]
    if isinstance(x, str):
        s = x.strip()
        return s or None
    if isinstance(x, float) and x.is_integer():
        return int(x)
    return x


def short_authors(raw) -> str | None:
    """'Family', 'Family & Family', or 'Family et al.' from FLoRA's JSON-ish author field."""
    if is_na(raw):
        return None
    fams = re.findall(r"['\"]family['\"]\s*:\s*['\"]([^'\"]+)['\"]", str(raw))
    if not fams:
        return None
    if len(fams) == 1:
        return fams[0]
    if len(fams) == 2:
        return f"{fams[0]} & {fams[1]}"
    return f"{fams[0]} et al."


def all_surnames(raw) -> list[str]:
    """Every family name in FLoRA's JSON-ish author field, lower-cased, for author-overlap checks.

    FLoRA already carries author_overlap_pct, but only for the pairs FORRT coded (20% of findings). Our finds have
    no such coding, and overlap is the strongest predictor in the whole dataset — 70% of replications sharing an
    author with the original succeed against 38% of independent ones — so it is worth deriving ourselves.
    """
    if is_na(raw):
        return []
    fams = re.findall(r"['\"]family['\"]\s*:\s*['\"]([^'\"]+)['\"]", str(raw))
    out, seen = [], set()
    for f in fams:
        t = unicodedata.normalize("NFKD", f).encode("ascii", "ignore").decode().lower().strip()
        t = re.sub(r"[^a-z' -]", "", t)
        if len(t) > 1 and t not in seen:
            seen.add(t); out.append(t)
    return out


def to_int(x):
    try:
        v = int(float(x))
        return v if 1800 < v < 2100 or v > 0 else None
    except (TypeError, ValueError):
        return None


def load_flora() -> list[dict]:
    df = pd.read_csv(SOURCES["flora"], dtype=str, keep_default_na=False)
    out = []
    for r in df.to_dict("records"):
        out.append({k: clean(v) for k, v in r.items()})
    return out


def load_fred() -> list[dict]:
    """FReD effect rows: fred-apps explorer-data (r-scale ES + 7 criteria) joined row-wise to output_FReD (bibliographic + quotes)."""

    def build():
        ex = json.loads(SOURCES["fred_explorer"].read_text(encoding="utf-8"))["studies"]
        out = pd.read_excel(SOURCES["fred_output"])
        assert len(ex) == len(out), "explorer-data and output_FReD are no longer row-aligned"
        rows = []
        for s, o in zip(ex, out.to_dict("records")):
            assert (norm_doi(s["doi_o"]) or "") == (norm_doi(o["doi_o"]) or ""), "row alignment broken"
            rows.append({
                "row": s["id"],
                "fred_id": clean(o.get("fred_id")),
                "doi_o": norm_doi(s["doi_o"]),
                "doi_r": norm_doi(s["doi_r"]) or norm_doi(s.get("url_r")),
                "url_r": clean(s.get("url_r")),
                "study_o": clean(s.get("study_o")),
                "study_r": clean(s.get("study_r")),
                "description": clean(s.get("description")),
                "claim_text_o": clean(s.get("claim_text_o")),
                "discipline": clean(s.get("discipline")),
                "tags": clean(s.get("tags")),
                "r_o": s.get("es_o"),
                "r_r": s.get("es_r"),
                "es_type_o": clean(s.get("es_type_o")),
                "n_o": s.get("n_o"),
                "n_r": s.get("n_r"),
                "ci_o": [s.get("ci_lower_o"), s.get("ci_upper_o")],
                "ci_r": [s.get("ci_lower_r"), s.get("ci_upper_r")],
                "p_o": s.get("p_o"),
                "p_r": s.get("p_r"),
                "power_r": s.get("power_r"),
                "criteria": {k: (v or {}).get("outcome") for k, v in (s.get("outcomes") or {}).items()},
                "reported_success": clean(s.get("reported_success")),
                "quote": clean(o.get("reported_success_quote")),
                "quote_source": clean(o.get("reported_success_quote_source")),
                "author_overlap_pct": clean(o.get("author_overlap_pct")),
                "prereg_r": clean(o.get("prereg_r")),
                "title_o": clean(o.get("title_o")),
                "journal_o": clean(o.get("journal_o")),
                "year_o": to_int(o.get("year_o")),
                "title_r": clean(o.get("title_r")),
                "journal_r": clean(o.get("journal_r")),
                "year_r": to_int(o.get("year_r")),
                "ref_o": clean(o.get("ref_o")),
                "ref_r": clean(o.get("ref_r")),
                "author_o": short_authors(o.get("author_o")),
                "author_r": short_authors(o.get("author_r")),
            })
        return rows

    return _cached("fred", SOURCES["fred_explorer"], build)


def _legacy_sheet(sheet: str) -> list[dict]:
    df = pd.read_excel(SOURCES["fred_legacy"], sheet_name=sheet, skiprows=[1, 2])
    return [{k: clean(v) for k, v in r.items()} for r in df.to_dict("records")]


def load_legacy() -> dict[str, list[dict]]:
    """Legacy crowdsourced FReD 2.4.1: the 'Data' sheet and FORRT's Replications & Reversals sheet."""
    return _cached("legacy", SOURCES["fred_legacy"], lambda: {
        "data": _legacy_sheet("Data"),
        "rr": _legacy_sheet("FORRT R&R (editable)"),
    })


def load_famous() -> list[dict]:
    return json.loads(SOURCES["famous"].read_text(encoding="utf-8"))


def load_openalex() -> dict[str, dict]:
    def build():
        raw = json.loads(SOURCES["openalex"].read_text(encoding="utf-8"))
        out = {}
        for doi, rec in raw.items():
            d = (rec or {}).get("data") or {}
            if not d:
                continue
            topics = d.get("topics") or []
            out[norm_doi(doi)] = {
                "title": d.get("title"),
                "year": d.get("publication_year"),
                "cited_by": d.get("cited_by_count"),
                "counts_by_year": {int(c["year"]): c["cited_by_count"] for c in (d.get("counts_by_year") or [])},
                "is_retracted": d.get("is_retracted"),
                "topic": topics[0]["display_name"] if topics else None,
                "subfield": topics[0]["subfield"]["display_name"] if topics else None,
                "field": topics[0]["field"]["display_name"] if topics else None,
            }
        return out

    return _cached("openalex", SOURCES["openalex"], build)


def load_extractor() -> list[dict]:
    df = pd.read_csv(SOURCES["extractor"], dtype=str, keep_default_na=False)
    return [{k: clean(v) for k, v in r.items()} for r in df.to_dict("records")]


def load_citation() -> str:
    return SOURCES["citation"].read_text(encoding="utf-8").strip()


def load_merges() -> list[dict]:
    """Curated effect merges: data/curated/merges.yaml -> [{into: name, from: [names], reason: str}]."""
    import yaml
    p = ROOT / "data" / "curated" / "merges.yaml"
    if not p.exists():
        return []
    return yaml.safe_load(p.read_text(encoding="utf-8")) or []


def load_reference_author_links() -> dict[str, dict]:
    """Matches made by finding the named author and year inside the paper's own reference list."""
    p = DISCOVERY / "reference_author_links.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def merged_links() -> dict[str, dict]:
    """One original per find, choosing between the two matchers by how accurate each has been measured to be.

    Three matchers propose an original and they disagree. For a long time the author-and-year answer simply won
    because it was merged last; that was replaced by two pairwise rules about which band may displace which,
    and on 2026-09-22 those rules broke under their own weight. Adding 1,169 fresh author-and-year links let an
    `openalex_author_year/medium` link (measured 91%) displace a `reference_author/high` one (measured 93%),
    and let `openalex_author_year/low` (17-33%) win every find where nothing better already sat — the
    reference_author/high band fell from 225 links to 20 and the deck lost 48 cards.

    So the choice is made the way the docstring always claimed it was: **by how accurate each band has been
    measured to be**, read off data/curated/original_audit.csv rather than written into a rule here. A band with
    fewer than 20 reads is treated as unknown and loses to every band that has been read, ordered high above
    medium above low among themselves. Adding a matcher can no longer quietly demote a better-measured one.
    """
    refs, auth, byauth = load_reference_links(), load_links(), load_reference_author_links()
    out: dict[str, dict] = {}
    for src in (refs, auth, byauth):
        for cid, link in src.items():
            cur = out.get(cid)
            if cur is None or _band_score(link) > _band_score(cur):
                out[cid] = link
    # The second choices are NOT merged in. `verify --runners` judges the paper each matcher ranked second for
    # finds whose first choice failed, and the judge confirmed 180 of 1,189. Read by hand, 18 of those drawn at
    # random are right 14 times — 78%, against a 90% bar. The failures have a shape the judge cannot see without
    # an abstract: a review of the field instead of the study it reviews, a methodological critique of a scale
    # instead of the paper that used it, and the wrong paper by the right author.
    #
    # The judge was let past the band gate at all because it measures 98% ON FIRST CHOICES. That number is about
    # first choices. A second choice is a different population — it is, by construction, a paper some matcher
    # already ranked below one that turned out to be wrong — and the same instrument reads 78% there. Carrying a
    # calibration across populations is the error this file exists to prevent.
    #
    # So the work is kept, the measurement is written down, and nothing ships: data/discovery/runner_up_links.json
    # and the 18 labels in original_audit.csv are what a later reader needs to settle it. Roughly 36 cards turn
    # on this. If reading more of them clears 90%, merge them here.
    # A checked citation in the replication's own source text is about an exact pairing and takes precedence
    # over machine matchers. The pairing and its source are recorded in data/curated/original_links.csv.
    out.update(load_curated_original_links())
    return out


def load_curated_original_links() -> dict[str, dict]:
    """Pairing-specific original citations verified from a find's own source text."""
    p = ROOT / "data" / "curated" / "original_links.csv"
    if not p.exists():
        return {}
    out: dict[str, dict] = {}
    with p.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            cid, doi = r["cid"].strip(), norm_doi(r["doi_o"])
            if not cid or not doi or cid in out:
                raise ValueError(f"invalid or duplicate curated original link: {cid!r}")
            out[cid] = {"doi_o": doi, "title_o": r["title_o"],
                        "year_o": int(r["year_o"]) if r["year_o"] else None,
                        "method": "source-backed citation", "confidence": "reviewed",
                        "source_url": r["source_url"], "evidence": r["evidence"]}
    return out



def load_curated_multi_original_links() -> dict[str, list[dict]]:
    """All explicitly identified originals when one replication retests several papers."""
    p = ROOT / "data" / "curated" / "multi_original_links.csv"
    if not p.exists():
        return {}
    out: dict[str, list[dict]] = {}
    seen: set[tuple[str, str]] = set()
    with p.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            cid, doi = r["cid"].strip(), norm_doi(r["doi_o"])
            if not cid or not doi or (cid, doi) in seen:
                raise ValueError(f"invalid or duplicate multi-original link: {cid!r}, {doi!r}")
            seen.add((cid, doi))
            out.setdefault(cid, []).append({"doi_o": doi, "title_o": r["title_o"],
                                              "year_o": int(r["year_o"]) if r["year_o"] else None,
                                              "source_url": r["source_url"], "evidence": r["evidence"]})
    if any(len(rows) < 2 for rows in out.values()):
        raise ValueError("multi-original links require at least two originals per find")
    return out

def load_confirmed_runners() -> dict[str, dict]:
    """find id -> the second-choice paper the judge confirmed. Empty until `verify --runners` has run."""
    p = DISCOVERY / "runner_up_links.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


# How accurate each band has been measured to be, read off the hand labels rather than written down here, so
# the merge and the page gate cannot drift apart. A band nobody has read enough of scores below every band that
# has been read, which is the conservative reading of "we do not know".
_BAND_SCORES: dict[tuple[str, str], float] | None = None
_UNREAD = {"high": 0.05, "medium": 0.03, "low": 0.01}      # ordered among themselves, below anything measured


def _band_score(link: dict) -> float:
    global _BAND_SCORES
    if _BAND_SCORES is None:
        # Tallied by the band RECORDED WITH THE LABEL, not the band the row sits in now. A reader who judged a
        # `reference_author/high` link and called it right measured that band, and the measurement holds whether
        # or not re-matching later moved that row somewhere else. Keying on the current band instead makes a
        # band eat itself: re-matching invalidates its labels, it falls below 20 reads, it counts as unmeasured,
        # it loses the merge, and fewer rows remain in it. That is what took reference_author/high from 225
        # links to 17 within one run. (`originals.score` correctly uses the current band and the stale check —
        # it answers a different question, namely how good the rows in a band are RIGHT NOW.)
        from .originals import read_labels
        tally: dict[str, list[int]] = {}
        for r in read_labels():
            if not r.get("recorded") or r.get("label") not in ("right", "wrong"):
                continue
            t = tally.setdefault(r["recorded"], [0, 0])
            t[0] += 1
            t[1] += r["label"] == "right"
        _BAND_SCORES = {k: right / n for k, (n, right) in tally.items() if n >= 20}
    key = f"{link.get('method')}/{link.get('confidence')}"
    return _BAND_SCORES.get(key, _UNREAD.get(link.get("confidence"), 0.0))


def load_claims() -> dict[str, dict]:
    """The written game-card claims, keyed by card id. Empty until `python -m pipeline claims --all` has run."""
    p = DISCOVERY / "claims.json"
    if not p.exists():
        return {}
    return {r["id"]: r for r in json.loads(p.read_text(encoding="utf-8")) if r.get("ok")}


def load_refused_claims() -> set[str]:
    """Cards the claim writer looked at and said could not be made into a card.

    Its refusals are reasoned and mostly right: "The inability of individuals to account for inflation" is a
    definition of money illusion rather than a finding, "poor self-esteem results in a decrease in
    self-appreciation" is true by what the words mean, "Dyslexia). Adults who stutter show similar scores…" is a
    fragment of a database field. The deck used to fall back to that same database text whenever a claim was
    missing, which put all 58 of them back in front of players — the deck's fallback silently overruling the
    only check that had read them. A refusal now stands.
    """
    p = DISCOVERY / "claims.json"
    if not p.exists():
        return set()
    return {r["id"] for r in json.loads(p.read_text(encoding="utf-8"))
            if r.get("insufficient") or r.get("absence_written_positive")}


def load_verified_links() -> dict[str, str]:  # noqa: D401 — see load_verified_matches for the paper-aware form
    """The model's per-link verdict, keyed by find id: "right", "wrong" or "unclear".

    Empty until `python -m pipeline verify --all` has run. Measured against 401 links a person had already read
    one at a time: of the links it confirms, 98% (96-99%) were confirmed by the reader too. That is what lets a
    single row stand on its own evidence instead of on the average accuracy of the method that found it.

    A verdict without a `doi_o` is dropped. It was written before the file recorded WHICH paper the verdict was
    about, so there is no way to tell whether the find has since been re-matched to a different one — and a
    verdict about a match nobody is making any more is the same error as measuring a band over rows it was never
    computed on. `queue._link_trusted` checks the recorded paper against the current one.
    """
    p = DISCOVERY / "verified_links.json"
    if not p.exists():
        return {}
    return {r["id"]: r["verdict"] for r in json.loads(p.read_text(encoding="utf-8")) if r.get("doi_o")}


def load_verified_matches() -> dict[tuple[str, str], str]:
    """(find id, paper doi) -> verdict.

    Keyed by the PAIR, because the verdict is about a pairing and a find can have more than one pairing judged.
    That is not hypothetical: every matcher records the paper it ranked second, and 1,189 finds whose first
    choice was rejected have a second choice nobody ever looked at. Judging those means holding two verdicts for
    one find, which a dict keyed on the find alone cannot do.
    """
    p = DISCOVERY / "verified_links.json"
    if not p.exists():
        return {}
    return {(r["id"], r["doi_o"]): r["verdict"]
            for r in json.loads(p.read_text(encoding="utf-8")) if r.get("doi_o")}


def load_reread() -> dict[str, dict]:
    """Outcomes read out of text the abstract never carried — OSF wikis, Europe PMC Results sections.

    Empty until `python -m pipeline fulltext` and `python -m pipeline reread` have run. Only answers whose
    verbatim quote was found in the source they were read from are kept; `reread` drops the rest at the point of
    reading, and this is a second refusal in case that ever changes. See pipeline/reread.py for why the quote
    check is not optional on this population: "the text does not say" is the correct answer 72% of the time.
    """
    p = DISCOVERY / "reread.json"
    if not p.exists():
        return {}
    return {r["id"]: r for r in json.loads(p.read_text(encoding="utf-8"))
            if r.get("outcome") in ("successful", "failed", "mixed") and r.get("quote_checked")}


def load_triaged() -> list[dict]:
    """Screened finds, plus source-reviewed Psychology finds from the alternative search.

    The t3 screen was measured on high and medium rule tiers. Its answers on the low tier are a different
    population, so screening that tier fills the cache without automatically adding its guesses to the queue.
    Reviewed decisions and alternative-search evidence live in curated files and survive another paid screen.
    """
    f = DISCOVERY / "triaged.json"
    review = ROOT / "data" / "curated" / "low_tier_review.csv"
    accepted: set[str] = set()
    if review.exists():
        with review.open(encoding="utf-8", newline="") as fh:
            accepted = {r["cid"] for r in csv.DictReader(fh) if r.get("decision") == "accept"}
    generated = json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
    rows = [r for r in generated if r.get("tier") != "low" or r["cid"] in accepted]

    alternative = ROOT / "data" / "curated" / "psychology_alternative_finds.json"
    if not alternative.exists():
        return rows
    extra = json.loads(alternative.read_text(encoding="utf-8"))
    if not isinstance(extra, list):
        raise ValueError("psychology_alternative_finds.json must be a list")
    seen = {r["cid"] for r in generated}
    for r in extra:
        cid = r.get("cid")
        if (not cid or cid in seen or cid not in (r.get("doi_r"), r.get("openalex_id"))
                or r.get("triage", {}).get("kind") != "replication"
                or r["triage"].get("field") != "psychology"
                or not r.get("source_url") or not r.get("source_quote")
                or r["source_quote"] not in (r.get("abstract") or "")):
            raise ValueError(f"Invalid or duplicate alternative Psychology find: {cid}")
        seen.add(cid)
    return rows + extra


def load_osf() -> dict[str, dict]:
    """OSF token -> what OSF says the object is. Empty until `python -m pipeline osf` has run."""
    f = DISCOVERY / "osf.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def load_reference_links() -> dict[str, dict]:
    """cid -> original found in the replication's own reference list. Empty until `pipeline references` has run."""
    f = DISCOVERY / "reference_links.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def load_original_authors() -> dict[str, dict]:
    """DOI -> {ids, surnames} for originals OpenAlex knows. Empty until `python -m pipeline authors` has run."""
    f = DISCOVERY / "original_authors.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def load_links() -> dict[str, dict]:
    """cid -> resolved original. Empty until `python -m pipeline link` has run."""
    f = DISCOVERY / "links.json"
    return json.loads(f.read_text(encoding="utf-8"))["links"] if f.exists() else {}


# Any column in any FORRT file that holds the identifier of a REPLICATION paper. A DOI appearing in one of these
# means FORRT already has the paper, whether curated, extracted or merely queued for checking.
_REP_COLS = {"doi_r", "doi_replication", "alt_identifier_r", "url_r", "doi_r_published", "replication_doi"}
# a raw OpenAlex search dump is not evidence that FORRT recorded anything
_NOT_A_RECORD = {"repos/fred-litsearch/openalex_results_10000.csv"}


def load_known_replication_dois() -> set[str]:
    """Every replication identifier FORRT has anywhere, not just in the four files discovery used to check.

    Checking only the curated tables and two feed files let 275 papers FORRT already had reach our queue, some as
    "new" finds: an OSF project id recorded in FLoRA's alt_identifier_r column, and papers already carried as doi_r
    in flora-validation's dated extractor snapshots. Absence has to be proved against everything they hold.
    """

    def build():
        out: set[str] = set()
        for p in sorted(FORRT.rglob("*")):
            rel = str(p.relative_to(FORRT))
            if not p.is_file() or rel in _NOT_A_RECORD or "node_modules" in rel:
                continue
            try:
                if p.suffix.lower() == ".csv":
                    frames = [pd.read_csv(p, dtype=str, keep_default_na=False, low_memory=False)]
                elif p.suffix.lower() == ".xlsx":
                    frames = list(pd.read_excel(p, sheet_name=None, dtype=str).values())
                else:
                    continue
            except Exception:      # a corrupt or non-tabular file proves nothing either way
                continue
            for df in frames:
                for c in df.columns:
                    if str(c).strip().lower() in _REP_COLS:
                        out |= {d for d in (norm_doi(x) for x in df[c].astype(str)) if d}
        return out

    return _cached("forrt_known_reps", SOURCES["flora"], build)


def load_known_osf_ids() -> set[str]:
    """OSF project tokens appearing anywhere in FORRT's files.

    Most of our DOI-less finds are OSF student and class replications, and an OSF page can be cited as a bare
    osf.io link, a 10.17605 DOI or a 10.31234 preprint DOI. The five-character token is the one part common to all
    three, so absence is proved against the token rather than against a guessed DOI prefix."""

    def build():
        out: set[str] = set()
        for p in FORRT.rglob("*"):
            rel = str(p.relative_to(FORRT))
            if not p.is_file() or "node_modules" in rel or p.suffix.lower() not in (".csv", ".json", ".txt"):
                continue
            text = p.read_text(encoding="utf-8", errors="ignore").lower()
            out |= set(re.findall(r"osf\.io/([a-z0-9]{5})(?:[/?#\"',\s]|$)", text))
        return out

    return _cached("forrt_known_osf", SOURCES["flora"], build)


def osf_token(url: str | None) -> str | None:
    """'https://osf.io/fdfwc/#!' -> 'fdfwc'."""
    m = re.search(r"osf\.io/([a-z0-9]{5})(?:[/?#]|$)", str(url or ""), re.I)
    return m.group(1).lower() if m else None


# a surname this common carries almost no evidence that two papers share a person (top ~1%: median is 1, p99 is 30)
COMMON_SURNAME = 25


def load_surname_frequency() -> dict[str, int]:
    """How many discovered papers carry each author surname, as a base rate for author-overlap claims."""

    def build():
        from collections import Counter
        f: Counter[str] = Counter()
        for mode in ("keyword", "cites"):
            p = DISCOVERY / f"discovered-{mode}.json"
            if not p.exists():
                continue
            for c in json.loads(p.read_text(encoding="utf-8"))["candidates"]:
                for sn in set(c.get("author_surnames_r") or []):
                    f[sn] += 1
        return dict(f)

    return _cached("surname_freq", SOURCES["flora"], build)
