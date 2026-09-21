"""Readers for the pinned raw sources. Every reader returns plain Python records; nothing here decides semantics."""
from __future__ import annotations

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


def load_triaged() -> list[dict]:
    """DeepSeek's screen of the discovered candidates. Empty until `python -m pipeline triage` has run."""
    f = DISCOVERY / "triaged.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []


def load_osf() -> dict[str, dict]:
    """OSF token -> what OSF says the object is. Empty until `python -m pipeline osf` has run."""
    f = DISCOVERY / "osf.json"
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
