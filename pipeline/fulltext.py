"""Find the result where the abstract does not report it.

2,448 of our psychology finds — nearly 60% — cannot become a card because nothing we hold says how the
replication turned out. That is the largest single loss in the funnel by a wide margin, and it is not a matching
problem: the abstract describes what the study DID. Reading it harder will not help, and was measured not to: of
the 573 such finds that have an abstract at all, 14 contain a result-shaped sentence and every one of those
reports the ORIGINAL study's result rather than the replication's.

The result exists; it is just somewhere else. This module goes and gets it.

WHERE IT IS, MEASURED RATHER THAN ASSUMED:

  OSF wikis          Most of these finds are OSF deposits, and 11 of 12 plain projects sampled have a wiki.
                     The wiki is where a student team writes up what happened — "effect sizes tended to be
                     large and were in the same directions and slightly larger than the original" — in plain
                     text, free, no document parsing. 694 finds are OSF objects we have already identified.
  Europe PMC         37% of the finds with a DOI are in Europe PMC and about 10% have full text there, served
                     as structured XML, so the Results section can be taken on its own instead of a whole
                     paper. It also carries an abstract for roughly 30%, and 1,261 of these finds have no
                     abstract anywhere else.

  Open-access PDFs   1,053 silent finds have a DOI and no full text in Europe PMC, and OpenAlex already tells
                     us, in records we cached during discovery, which of them are open access and where the
                     PDF is. Fetching and parsing those is free; only reading them costs. The yield is lower
                     than Europe PMC's because a PDF is a picture of a paper rather than a structured one:
                     publishers refuse a third of the requests outright, some of what comes back is a
                     supplement rather than the article, and the mid-century psychology journals that make up
                     much of this pile were scanned without a usable text layer.

What this does NOT reach: articles behind a paywall, and OSF projects whose result is inside an attached .docx.

    python -m pipeline fulltext --osf        # wikis and descriptions, free
    python -m pipeline fulltext --pmc        # Europe PMC abstracts and Results sections, free
    python -m pipeline fulltext --pdf        # open-access PDFs, parsed locally, free
    python -m pipeline fulltext --report

Nothing here calls a language model. It collects text; `pipeline outcomes` is what reads it.
"""
from __future__ import annotations

import argparse
import io
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from collections import Counter

from .load import CACHE, DISCOVERY, osf_token

OUT = DISCOVERY / "fulltext.json"
UA = {"User-Agent": "Retested/0.1 (noncommercial replication research)"}
OSF_API = "https://api.osf.io/v2"
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"
MAX_CHARS = 6000          # enough for a Results section; a whole paper is not needed and is not free to read
MAX_PDF_BYTES = 40_000_000
PDF_PAGES = 30            # a Results section is never on page 31; a thesis appendix often is


def _get(url: str, raw: bool = False, tries: int = 4):
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45) as r:
                b = r.read()
            return b.decode("utf-8", "replace") if raw else json.loads(b)
        except urllib.error.HTTPError as e:
            if e.code in (404, 403, 410):
                return "" if raw else {}
            if attempt == tries - 1:
                return "" if raw else {}
            time.sleep(2 * 2 ** attempt)
        except Exception:
            if attempt == tries - 1:
                return "" if raw else {}
            time.sleep(2 * 2 ** attempt)
    return "" if raw else {}


def _cached(kind: str, key: str, build) -> dict:
    f = CACHE / "fulltext" / kind / f"{re.sub(r'[^A-Za-z0-9._-]+', '_', key)[:120]}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    f.parent.mkdir(parents=True, exist_ok=True)
    rec = build()
    f.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    return rec


# ---------------------------------------------------------------- OSF

def osf_text(token: str) -> dict:
    """A project's description and every wiki page it has, as one block of plain text.

    The wiki is the whole point. An OSF project's description is usually a line or two, but the wiki is where a
    replication team writes what they found, and it comes back as markdown from an endpoint that needs no key.
    Registrations and preprints have the same endpoints, so they go through here too.
    """
    def build() -> dict:
        # An OSF id is a node, a registration or a preprint, and each lives at its own endpoint — asking
        # /nodes/ for a registration is a 404, which silently lost 16 of the first 25 tried.
        at, kind = {}, None
        for k in ("nodes", "registrations", "preprints"):
            d = _get(f"{OSF_API}/{k}/{token}/")
            if (d.get("data") or {}).get("attributes"):
                at, kind = d["data"]["attributes"], k
                break
        parts, kinds = [], []
        if at.get("title"):
            parts.append(f"TITLE: {at['title']}")
        if at.get("description"):
            parts.append(f"DESCRIPTION: {at['description']}")
            kinds.append("description")
        if kind in ("nodes", "registrations"):
            wikis = _get(f"{OSF_API}/{kind}/{token}/wikis/")
            for w in (wikis.get("data") or [])[:6]:
                name = (w.get("attributes") or {}).get("name") or "wiki"
                txt = _get(f"{OSF_API}/wikis/{w['id']}/content/", raw=True)
                if txt and txt.strip():
                    parts.append(f"WIKI [{name}]: {txt.strip()}")
                    kinds.append("wiki")
        # A registration's schema answers are free text the author wrote about the study. Most schemas are
        # filled in before the data exist and say nothing about the result, but a completed Registered Report
        # says what happened, and the field costs nothing to take.
        for key in ("registration_responses", "registered_meta"):
            v = at.get(key)
            if isinstance(v, dict) and v:
                flat = " ".join(str(x.get("value") if isinstance(x, dict) else x)[:800] for x in v.values())
                flat = re.sub(r"\s+", " ", flat).strip()
                if len(flat) > 80:
                    parts.append(f"REGISTRATION ANSWERS: {flat}")
                    kinds.append("registration")
                break
        text = "\n\n".join(parts)[:MAX_CHARS]
        return {"source": "osf", "kind": kind, "got": sorted(set(kinds)), "chars": len(text), "text": text}
    return _cached("osf", token, build)


# ---------------------------------------------------------------- Europe PMC

_SEC = re.compile(r"<sec\b[^>]*>(.*?)</sec>", re.S)
_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.S)
_WANTED = re.compile(r"result|finding|conclusion", re.I)


def _strip(x: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", x)).strip()


def pmc_lookup(dois: list[str]) -> dict[str, dict]:
    """DOI -> what Europe PMC holds, 20 DOIs per query."""
    out: dict[str, dict] = {}
    for i in range(0, len(dois), 20):
        chunk = dois[i:i + 20]
        q = " OR ".join(f'DOI:"{d}"' for d in chunk)
        url = f"{EPMC}/search?" + urllib.parse.urlencode(
            {"query": q, "format": "json", "pageSize": 100, "resultType": "core"})
        d = _cached("epmc-search", f"{i}-{len(chunk)}-" + str(abs(hash(q)) % 10 ** 10), lambda: _get(url))
        for r in ((d.get("resultList") or {}).get("result") or []):
            doi = (r.get("doi") or "").lower()
            if doi:
                out[doi] = {"pmcid": r.get("pmcid"), "in_epmc": r.get("inEPMC") == "Y",
                            "abstract": r.get("abstractText")}
        time.sleep(0.15)
    return out


def pmc_text(pmcid: str) -> dict:
    """The Results and Conclusions sections of an open-access full text, and nothing else.

    A whole paper is 100kB+ of XML and the answer lives in two sections; taking those keeps what a model has to
    read small enough to be cheap, and keeps the methods and introduction — which describe the ORIGINAL study's
    finding and are exactly what a reader confuses for the replication's — out of the way.
    """
    def build() -> dict:
        xml = _get(f"{EPMC}/{pmcid}/fullTextXML", raw=True)
        if not xml:
            return {"source": "epmc", "got": [], "chars": 0, "text": ""}
        parts = []
        for sec in _SEC.findall(xml):
            t = _TITLE.search(sec)
            if t and _WANTED.search(_strip(t.group(1))):
                parts.append(f"{_strip(t.group(1)).upper()}: {_strip(sec)}")
        text = "\n\n".join(parts)[:MAX_CHARS]
        return {"source": "epmc", "got": ["fulltext"] if text else [], "chars": len(text), "text": text}
    return _cached("epmc", pmcid, build)


# ---------------------------------------------------------------- open-access PDFs

# A Results section is what this is after. The headings are matched on their own line, because "results" appears
# in running prose constantly and a heading is the only reliable signal that the numbers start here.
_PDF_HEAD = re.compile(
    r"^[ \t]*(?:\d+(?:\.\d+)*\.?[ \t]*)?"
    r"(results?(?:[ \t]+and[ \t]+discussion)?|findings|general[ \t]+discussion|discussion|conclusions?)"
    r"[ \t]*:?[ \t]*$", re.I | re.M)
_PDF_END = re.compile(r"^[ \t]*(references|bibliography|acknowledge?ments?|author[ \t]note|"
                      r"supplementary|appendix)\b", re.I | re.M)

# A short mid-century note has no headings at all. "Effects of irrelevant colors on reading of color names: A
# controlled replication" (Psychonomic Science, 1971) runs title, prose, table, references over two pages and
# never writes the word "Results" — it yielded nothing until this fallback existed. Taking the whole of a short
# note is safe in a way that taking the whole of a modern paper is not: there is no ten-paragraph introduction
# restating the ORIGINAL study's finding for a reader to mistake for this one's. It is recorded as `whole-note`
# rather than `results` so its yield can be scored on its own instead of hiding inside the section figure.
# Measured in PAGES rather than characters: that paper extracts 17,600 characters from three pages, so a
# character budget generous enough to admit it would also admit half the theses in this pile.
SHORT_NOTE_PAGES = 4
MIN_SECTION = 500         # a heading with nothing under it is not a Results section

# Mid-century journals printed several one-page papers per sheet, and a publisher's PDF for one DOI can hold the
# next article too. `pipeline fulltext --pdf` then returns a real, fluent, quotable Results section belonging to
# a DIFFERENT study, which the quote check cannot catch — the quote is genuinely in the text it was given. A
# reader found one in 25: "Noncontingent reward magnitude effects on reaction time: A replication" came back
# with the results of a study on alternating-case letters and word identification.
#
# The test is deliberately weak. Requiring a decent overlap between the paper's own title and the extracted text
# would be wrong: "The intermittent punishment effect: A replication with improved controls" shares 20% of its
# title with a section that says "IP Ss showed a marked increase in latency", and the maternal-rations paper
# 22% with one about "pups reared by Purina-fed dams" — both correct, both would have been thrown away. What
# separates the bad case is that NONE of the title's content words appear anywhere in the text.
_TITLE_STOP = frozenset("the of and to in a an for on with by from is are as at we our this that study "
                        "effects effect replication replicating report".split())


def _about_this_paper(title: str | None, text: str) -> bool:
    want = {w for w in re.findall(r"[a-z]{4,}", (title or "").lower()) if w not in _TITLE_STOP}
    return not want or bool(want & set(re.findall(r"[a-z]{4,}", text.lower())))


def pdf_sections(text: str, pages: int | None = None) -> tuple[str, list[str]]:
    """The Results section if the paper has one, else its Discussion or Conclusion, else a short note whole.

    Taking the whole of a long paper would work and is the wrong thing to do: the introduction of a replication
    restates the ORIGINAL study's finding, at length and in the past tense, and that is precisely the sentence a
    reader mistakes for the replication's own result. Europe PMC gets this for free from structured XML; here
    the headings have to be found in running text.

    There is deliberately no check for whether the text layer is any good. The obvious one — counting common
    English words — was written, and then measured on the 1971 Psychonomic Science scan that motivated it: the
    scan's front matter is debris ('"mi I. Thi ... ,tud: i ~uppurtcd in part hy J pO\\ldol.:toral'), it scores
    the same as a clean modern PDF, and its Results section extracts perfectly readable prose reporting
    F = 2.72, df = 5/110. The guard would have thrown away a usable result to protect against a header nobody
    reads. What actually protects the answer is downstream and already exists: `reread` must quote a verbatim
    sentence from this text and the quote is checked against it, so unreadable text yields no answer rather
    than a wrong one.
    """
    heads = [(m.start(), m.end(), m.group(1).lower()) for m in _PDF_HEAD.finditer(text)]
    def pick(pred):
        return next((h for h in heads if pred(h[2])), None)
    h = (pick(lambda t: t.startswith("result") or t == "findings")
         or pick(lambda t: "discussion" in t) or pick(lambda t: t.startswith("conclusion")))
    if h:
        end = _PDF_END.search(text, h[1])
        body = re.sub(r"\s+", " ", text[h[0]:end.start() if end else len(text)]).strip()[:MAX_CHARS]
        # The same floor the whole-note branch has always had. Without it a heading with nothing under it is a
        # Results section: one journal's PDF extracted to the eighteen characters "Results Discussion" — its
        # own table of contents — and that was carried forward as text a model was asked to read.
        if len(body) >= MIN_SECTION:
            return body, [h[2].split()[0]]
        return "", []
    if pages is not None and pages <= SHORT_NOTE_PAGES:
        end = _PDF_END.search(text)
        body = text[:end.start()] if end else text
        body = re.sub(r"\s+", " ", body).strip()[:MAX_CHARS]
        if len(body) >= MIN_SECTION:
            return body, ["whole-note"]
    return "", []


def pdf_text(doi: str, url: str, title: str | None = None) -> dict:
    """One open-access PDF, fetched, parsed locally and cut down to its Results section.

    Every failure is recorded rather than dropped, because the reason a PDF yields nothing is the whole
    question here: a publisher refusing the request, a landing page served in place of the file, a scan with no
    text layer and a paper with no Results heading are four different problems with four different answers.
    """
    def build() -> dict:
        blank = {"source": "pdf", "got": [], "chars": 0, "text": "", "url": url}
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read(MAX_PDF_BYTES)
        except Exception as e:
            return dict(blank, why=f"fetch:{type(e).__name__}")
        if not raw.startswith(b"%PDF"):
            return dict(blank, why="not-a-pdf")          # usually a landing page or a paywall interstitial
        try:
            import pypdf
            pages = list(pypdf.PdfReader(io.BytesIO(raw)).pages)
            text = "\n".join((pg.extract_text() or "") for pg in pages[:PDF_PAGES])
        except Exception as e:
            return dict(blank, why=f"parse:{type(e).__name__}")
        if len(text.strip()) < 500:
            return dict(blank, why="no-text-layer")      # a scan of the page images, nothing to read
        body, got = pdf_sections(text, len(pages))
        if not body:
            return dict(blank, why="no-results-section")
        if not _about_this_paper(title, body):
            return dict(blank, why="another-article-on-the-page")
        return {"source": "pdf", "got": got, "chars": len(body), "text": body, "url": url}
    return _cached("pdf", doi, build)


def oa_pdf_urls() -> dict[str, str]:
    """Normalised DOI -> a PDF we are allowed to fetch, taken from OpenAlex records already on disk.

    Discovery cached the whole work record for every candidate it searched, and `primary_location` carries
    `is_oa` and `pdf_url`. So the question "which of these can we read" was already answered months ago and
    costs no API call to ask again.
    """
    from .load import norm_doi
    out: dict[str, str] = {}
    for f in sorted((CACHE / "openalex").glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        for r in (d.get("results") or []) if isinstance(d, dict) else []:
            loc = r.get("primary_location") or {}
            if r.get("doi") and loc.get("pdf_url"):
                out.setdefault(norm_doi(r["doi"]), loc["pdf_url"])
    return out


# ---------------------------------------------------------------- drivers

def _silent() -> list[dict]:
    """Finds with no yes/no outcome — the rows this module exists for."""
    from . import claims as C, load, registry, score
    from .ids import EffectLedger
    src = {k: getattr(load, f"load_{k}")() for k in ("flora", "fred", "legacy", "famous", "openalex", "merges")}
    g = registry.build(src, EffectLedger(load.ROOT / "data" / "curated" / "registry" / "effect_ids.csv"))
    score.score(g)
    return [c for c in C._queue_candidates(g)
            if c.get("origin") == "retested_discovery" and c.get("group") == "replication"
            and c.get("field") == "psychology" and c.get("outcome") not in ("successful", "failed")]


def _merge(found: dict[str, dict]) -> None:
    have = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    for cid, rec in found.items():
        if rec.get("chars"):
            have[cid] = rec
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(have, ensure_ascii=False), encoding="utf-8")
    print(f"  wrote {OUT} · {len(have)} finds now have text ({len(found)} looked at this run)")


def run_osf(limit: int | None) -> int:
    rows = _silent()
    todo = [(c["id"], t) for c in rows if (t := osf_token(c.get("landing_page")))]
    if limit:
        todo = todo[:limit]
    print(f"  {len(todo)} silent finds are OSF deposits")
    found, t0 = {}, time.time()
    for i, (cid, tok) in enumerate(todo, 1):
        found[cid] = osf_text(tok)
        if i % 100 == 0:
            got = sum(1 for r in found.values() if r["chars"])
            print(f"    {i}/{len(todo)} · {got} with text · {time.time() - t0:.0f}s")
    _merge(found)
    return 0


def run_pmc(limit: int | None) -> int:
    rows = _silent()
    todo = [c for c in rows if c.get("doi_r")]
    if limit:
        todo = todo[:limit]
    dois = sorted({(c["doi_r"] or "").lower() for c in todo})
    print(f"  {len(todo)} silent finds have a DOI; asking Europe PMC about {len(dois)}")
    held = pmc_lookup(dois)
    print(f"  {len(held)} are in Europe PMC, {sum(1 for v in held.values() if v['pmcid'])} with a PMC id")
    found = {}
    for c in todo:
        h = held.get((c["doi_r"] or "").lower())
        if not h:
            continue
        rec = pmc_text(h["pmcid"]) if h.get("pmcid") else {"source": "epmc", "got": [], "chars": 0, "text": ""}
        # No full text but an abstract Europe PMC holds and we do not is still worth having: 1,261 of these
        # finds have no abstract anywhere, and an abstract that states the outcome makes the find usable.
        if not rec["chars"] and h.get("abstract") and not c.get("abstract"):
            rec = {"source": "epmc", "got": ["abstract"], "chars": len(h["abstract"]),
                   "text": h["abstract"][:MAX_CHARS]}
        found[c["id"]] = rec
    _merge(found)
    return 0


def run_pdf(limit: int | None) -> int:
    from .load import norm_doi
    rows = _silent()
    have = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    urls = oa_pdf_urls()
    dois = sorted({norm_doi(c["doi_r"]) for c in rows if c.get("doi_r")})
    in_pmc = {d for d, v in pmc_lookup(dois).items() if v.get("pmcid")}
    todo = [c for c in rows if c.get("doi_r") and c["id"] not in have
            and norm_doi(c["doi_r"]) not in in_pmc and norm_doi(c["doi_r"]) in urls]
    print(f"  {len(rows)} silent finds · {len(todo)} have an open-access PDF and no text yet")
    if limit:
        todo = todo[:limit]
    found, why, t0 = {}, Counter(), time.time()
    for i, c in enumerate(todo, 1):
        d = norm_doi(c["doi_r"])
        rec = pdf_text(d, urls[d], c.get("title_r"))
        found[c["id"]] = rec
        why[rec.get("why") or "ok"] += 1
        if i % 25 == 0:
            print(f"    {i}/{len(todo)} · {why['ok']} with a Results section · {time.time() - t0:.0f}s")
        time.sleep(0.2)
    print(f"  outcome of {len(todo)} fetches: {dict(why.most_common())}")
    _merge(found)
    return 0


def report() -> int:
    if not OUT.exists():
        print("nothing fetched yet")
        return 0
    have = json.loads(OUT.read_text(encoding="utf-8"))
    from collections import Counter
    src = Counter(r["source"] for r in have.values())
    got = Counter(k for r in have.values() for k in r["got"])
    print(f"  {len(have)} finds have text that the abstract did not give us")
    print("  by source:", dict(src))
    print("  by what was found:", dict(got))
    lens = sorted(r["chars"] for r in have.values())
    if lens:
        print(f"  length: median {lens[len(lens) // 2]} chars, range {lens[0]}–{lens[-1]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="pipeline fulltext", description=__doc__.split("\n")[0])
    p.add_argument("--osf", action="store_true", help="OSF project descriptions and wiki pages")
    p.add_argument("--pmc", action="store_true", help="Europe PMC Results sections and abstracts")
    p.add_argument("--pdf", action="store_true", help="open-access PDFs, fetched and parsed locally")
    p.add_argument("--report", action="store_true")
    p.add_argument("--limit", type=int)
    a = p.parse_args(argv)
    if a.osf:
        return run_osf(a.limit)
    if a.pmc:
        return run_pmc(a.limit)
    if a.pdf:
        return run_pdf(a.limit)
    if a.report:
        return report()
    p.print_help()
    return 1
