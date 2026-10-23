"""Keep the abstract of every original paper, with where it came from and when.

Earlier reviews read each original's page and kept only one quote and a link. The page text itself went into a
temporary folder and is gone. This step keeps the text, so a card or a review can be checked against it later.

Sources, tried in this order for each paper that still has no accepted abstract:

  1. what we already hold: data/discovery/original_authors.json and this file's earlier run
  2. OpenAlex, 50 DOIs a call (cached, costed)
  3. Europe PMC, by DOI (free)
  4. Crossref, by DOI (free)
  5. Semantic Scholar, by DOI (free, opt-in: it throttles unauthenticated callers and is slow)
  6. the original's page that a reviewer already used, read through its metadata tags only. A page that refuses
     automatic access (403) stays missing: nothing here works around a refusal.

Every text must pass one gate before it is kept: long enough to be an abstract, English, not a citation line or a
download counter, and, where the source gives a title, that title must match the title we hold for the DOI (a DOI that
resolves to a different paper is the commonest silent error). Rejected texts are recorded with the reason.

    python -m pipeline original-abstracts [--max-usd 0.10] [--semantic-scholar] [--no-pages]

Writes data/discovery/original_abstracts.json. Reads data/build/findings.json, papers.json and attempts.json, so run
`python -m pipeline build` first. Nothing here calls a language model.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from urllib.parse import quote, urlparse

from . import authors, fulltext, load
from .discover import MAILTO, USER_AGENT

OUT = load.DISCOVERY / "original_abstracts.json"
CACHE_DIR = load.CACHE / "original_abstracts"
BUILD = load.ROOT / "data" / "build"
UA = {"User-Agent": USER_AGENT}
MIN_CHARS = 300
_STOP = frozenset("the of and in to a that is was for with were as on by from this are be or at an which not".split())
_JUNK = re.compile(r"^\s*\[?\d+\]|downloads?\b|metrics|total citations|^abstract\s*$|view article|cite this", re.I)
PAGE_META = ["citation_abstract", "dc.description", "DC.Description", "og:description", "description", "twitter:description"]
PAGE_TITLE_META = ["citation_title", "og:title", "dc.title", "DC.Title"]


def clean(text: str | None) -> str:
    """Strip markup and a leading 'Abstract' label; collapse whitespace."""
    t = re.sub(r"<[^>]+>", " ", html.unescape(text or ""))
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"\s+([.,;:!?])", r"\1", t)          # a tag removed before a full stop leaves a stray space
    return re.sub(r"^(abstract|summary)\b[:.\s]*", "", t, flags=re.I)


def english(text: str) -> bool:
    words = re.findall(r"[A-Za-z]+", text.lower())
    return bool(words) and sum(1 for w in words if w in _STOP) / len(words) >= 0.18


def reject_reason(abstract: str, our_title: str | None = None, their_title: str | None = None,
                  min_overlap: float = 0.6) -> str | None:
    """Why this text is not an abstract of this paper, or None if it passes."""
    if len(abstract) < MIN_CHARS:
        return "too short"
    if _JUNK.search(abstract[:200]):
        return "not an abstract"
    if not english(abstract):
        return "not English"
    if our_title and their_title and authors._overlap(our_title, their_title) < min_overlap:
        return "title mismatch"
    return None


def _cached(kind: str, key: str, build, keep=lambda value: True):
    """Run `build` once per key and remember the answer. An answer `keep` refuses (a throttled request) is not stored."""
    f = CACHE_DIR / kind / (hashlib.sha256(key.encode()).hexdigest()[:24] + ".json")
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    value = build()
    if keep(value):
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return value


def _http(url: str, data: bytes | None = None, headers: dict | None = None, tries: int = 3, limit: int = 2_500_000):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers={**UA, **(headers or {})}), timeout=30) as r:
                return r.read(limit)
        except urllib.error.HTTPError as e:
            if e.code in (400, 403, 404, 410):
                return None
            time.sleep(3 * 2 ** k)
        except Exception:  # noqa: BLE001 - transient network error
            time.sleep(2 * 2 ** k)
    return None


# ---------------------------------------------------------------- the sources: each returns {doi: (text, their_title)}

def from_openalex(dois: list[str], max_usd: float) -> dict[str, tuple[str, str | None]]:
    got = authors.fetch(dois, max_usd)
    return {d: (r["abstract"], r.get("title")) for d, r in got.items() if r.get("abstract")}


def from_europepmc(dois: list[str]) -> dict[str, tuple[str, str | None]]:
    return {d: (h["abstract"], None) for d, h in fulltext.pmc_lookup(dois).items() if h.get("abstract")}


def from_crossref(dois: list[str]) -> dict[str, tuple[str, str | None]]:
    def one(doi: str):
        def build():
            raw = _http(f"https://api.crossref.org/works/{quote(doi, safe='/')}" + (f"?mailto={MAILTO}" if MAILTO else ""))
            msg = (json.loads(raw).get("message") if raw else None) or {}
            return {"abstract": msg.get("abstract"), "title": " ".join(msg.get("title") or [])}
        return doi, _cached("crossref", doi, build)
    with ThreadPoolExecutor(max_workers=5) as ex:
        return {d: (r["abstract"], r["title"]) for d, r in ex.map(one, dois) if r.get("abstract")}


def from_semantic_scholar(dois: list[str]) -> dict[str, tuple[str, str | None]]:
    out: dict[str, tuple[str, str | None]] = {}
    for i in range(0, len(dois), 100):
        chunk = dois[i:i + 100]

        def build():
            raw = _http("https://api.semanticscholar.org/graph/v1/paper/batch?fields=title,abstract",
                        data=json.dumps({"ids": ["DOI:" + d for d in chunk]}).encode(),
                        headers={"Content-Type": "application/json"}, tries=4)
            return json.loads(raw) if raw else []
        for d, rec in zip(chunk, _cached("semanticscholar", "|".join(chunk), build, keep=bool)):
            if rec and rec.get("abstract"):
                out[d] = (rec["abstract"], rec.get("title"))
        time.sleep(3)
    return out


def _meta(page: str, names: list[str]) -> list[str]:
    found = []
    for n in names:
        for pat in (r'<meta[^>]+(?:name|property)=["\']%s["\'][^>]*content=["\']([^"\']+)["\']',
                    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:name|property)=["\']%s["\']'):
            found += [html.unescape(m.group(1)) for m in re.finditer(pat % re.escape(n), page, re.I)]
    return found


def from_pages(jobs: list[tuple[str, str]], titles: dict[str, str]) -> dict[str, tuple[str, str | None, str]]:
    """The page a reviewer already used, read through its metadata tags. Returns {doi: (text, page title, url)}."""
    def one(job):
        doi, url = job

        def build():
            raw = _http(url)
            if raw is None:
                return {}
            page = raw.decode("utf-8", "replace")
            texts = [clean(c) for c in _meta(page, PAGE_META)]
            page_titles = _meta(page, PAGE_TITLE_META)
            return {"abstract": max(texts, key=len, default=""), "title": max(page_titles, key=len, default="")}
        return doi, url, _cached("page", url, build)
    out = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        for doi, url, rec in ex.map(one, jobs):
            if rec.get("abstract"):
                out[doi] = (rec["abstract"], rec.get("title"), url)
    return out


# ---------------------------------------------------------------- the driver

def _record(text: str, source: str, title_checked: bool, url: str | None = None) -> dict:
    rec = {"abstract": text[:4000], "source": source, "fetched_on": date.today().isoformat(),
           "sha256": hashlib.sha256(text.encode()).hexdigest()[:16], "title_checked": title_checked}
    if url:
        rec["url"] = url
    return rec


def run(max_usd: float = 0.10, semantic_scholar: bool = False, pages: bool = True) -> int:
    try:
        findings = json.loads((BUILD / "findings.json").read_text(encoding="utf-8"))
        paper_titles = {d: (p or {}).get("title") for d, p in json.loads((BUILD / "papers.json").read_text(encoding="utf-8")).items()}
        attempts = json.loads((BUILD / "attempts.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        print("data/build is missing: run `python -m pipeline build` first")
        return 1
    dois = sorted({f["doi_o"] for f in findings.values() if f.get("doi_o")})
    previous = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    wanted = set(dois)
    kept: dict[str, dict] = {d: r for d, r in previous.get("abstracts", {}).items() if d in wanted}
    rejected: dict[str, str] = {}

    def offer(source: str, found: dict, title_checked: bool = True) -> int:
        n = 0
        for d, val in found.items():
            if d in kept or d not in wanted:      # a lookup can return records for DOIs we did not ask about
                continue
            text, their_title = clean(val[0]), val[1]
            why = reject_reason(text, paper_titles.get(d), their_title, 0.5 if source == "saved page" else 0.6)
            if why:
                rejected[d] = f"{source}: {why}"
                continue
            kept[d] = _record(text, source, title_checked and bool(their_title), val[2] if len(val) > 2 else None)
            rejected.pop(d, None)
            n += 1
        print(f"  {source:<18} +{n:<5} kept {len(kept)} of {len(dois)}", flush=True)
        return n

    def missing() -> list[str]:
        return [d for d in dois if d not in kept]

    print(f"{len(dois)} original papers; {len(kept)} kept from an earlier run", flush=True)
    held = load.load_original_authors()
    offer("held earlier", {d: (r["abstract"], r.get("title")) for d, r in held.items() if (r or {}).get("abstract")})
    offer("openalex", from_openalex(missing(), max_usd))
    offer("europe pmc", from_europepmc(missing()), title_checked=False)
    offer("crossref", from_crossref(missing()))
    if semantic_scholar:
        offer("semantic scholar", from_semantic_scholar(missing()))
    if pages:
        want = set(missing())
        jobs = []
        for f in findings.values():
            if f.get("doi_o") in want:
                for a in f["attempts"]:
                    url = ((attempts.get(a) or {}).get("retested_review") or {}).get("original_source_url")
                    if url:
                        jobs.append((f["doi_o"], url))
                        break
        offer("saved page", from_pages(jobs, paper_titles))

    by_source = Counter(r["source"] for r in kept.values())
    doc = {"schema_version": 1, "generated_on": date.today().isoformat(), "original_papers": len(dois),
           "counts": {"kept": len(kept), "missing": len(missing()), "rejected": len(rejected), "by_source": dict(by_source)},
           "abstracts": kept, "rejected": {d: r for d, r in rejected.items() if d not in kept}}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    tmp.replace(OUT)
    print(f"kept {len(kept)} of {len(dois)} | missing {len(missing())} | rejected with a reason {len(doc['rejected'])}")
    print("by source:", dict(by_source))
    print("rejections:", dict(Counter(r.split(": ", 1)[1] for r in doc["rejected"].values())))
    print(f"wrote {OUT}")
    return 0
