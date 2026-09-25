#!/usr/bin/env python3
"""Bounded, cache-backed primary-source prefetch for exact replication review.

Run from the repository root::

    python3 -m pipeline.source_prefetch --input later.jsonl --out evidence.jsonl \
        --cache /tmp/retested-evidence-cache --workers 3 --jina

Input is a JSON array or JSONL of candidate objects. Each object needs
``doi``, ``doi_r``, or ``replication_doi``; optional OpenAlex
``abstract_inverted_index`` avoids another abstract lookup. The optional
``known_original_doi`` or ``known_original_dois`` enables
``--emit-exact two_abstracts.jsonl``, a source-lead packet for
``python3 -m pipeline.exact_review --input two_abstracts.jsonl --all``.
Missing abstracts are skipped; callers may provide primary-source text in
``original_abstract_cached`` or ``replication_abstract_cached``.
Output never implies that a citation match is a verified replication.
The CLI uses no credentials and never edits curated or build files.
"""
import argparse
import concurrent.futures as cf
import hashlib
import html
import json
import re
import threading
import time
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

UA = "RetestedEvidencePrefetch/0.1 (noncommercial DOI evidence review)"
DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.I)
BAD = ("Just a moment", "Checking your browser", "Access Denied", "404 Page not found", "CAPTCHA")
lock = threading.Lock()
last = {}
def norm(s):
    s = str(s or "").strip().lower()
    return re.sub(r"^https?://(?:dx\.)?doi\.org/", "", s).rstrip(".,;")
def inverted(obj):
    d = obj.get("abstract_inverted_index") or {}
    if not d: return ""
    positions = [i for v in d.values() for i in v]
    if not positions: return ""
    a = [""] * (max(positions) + 1)
    for word, places in d.items():
        for i in places: a[i] = word
    return " ".join(a)
def clean_markup(s):
    from html.parser import HTMLParser
    class TextParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.skip = 0
            self.parts = []
            self.focus = 0
            self.focus_parts = []
        def handle_starttag(self, tag, attrs):
            if tag in ("script", "style", "nav", "footer", "header"):
                self.skip += 1
            if tag in ("article", "main"):
                self.focus += 1
        def handle_endtag(self, tag):
            if tag in ("script", "style", "nav", "footer", "header"):
                self.skip = max(0, self.skip-1)
            if tag in ("article", "main"):
                self.focus = max(0, self.focus-1)
        def handle_data(self, data):
            if not self.skip and data.strip():
                self.parts.append(data.strip())
                if self.focus: self.focus_parts.append(data.strip())
    if "<" not in s: return re.sub(r"\s+", " ", html.unescape(s))
    parser = TextParser()
    parser.feed(s)
    parts = parser.focus_parts if len(" ".join(parser.focus_parts)) > 800 else parser.parts
    return re.sub(r"\s+", " ", html.unescape(" ".join(parts)))
class HTTPResult:
    def __init__(self, status_code, headers, content):
        self.status_code = status_code
        self.headers = headers
        self.content = content

    @property
    def text(self):
        return self.content.decode("utf-8", errors="replace")


def request(url, host, delay, timeout, params=None):
    # Reserve a per-host slot under the lock, then sleep outside the lock.
    if params:
        url += ("&" if "?" in url else "?") + urlencode(params)
    for attempt in range(3):
        with lock:
            now = time.monotonic()
            ready = max(now, last.get(host, 0.0) + delay)
            last[host] = ready
        wait = ready - now
        if wait:
            time.sleep(wait)
        try:
            req = Request(
                url,
                headers={"User-Agent": UA, "Accept": "application/json,text/html,application/xml,text/plain"},
            )
            try:
                with urlopen(req, timeout=timeout) as response:
                    r = HTTPResult(response.status, response.headers, response.read())
            except HTTPError as exc:
                r = HTTPResult(exc.code, exc.headers, exc.read())
            if r.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(min(6, float(r.headers.get("Retry-After") or 1.5 * (attempt + 1))))
                continue
            return r
        except (URLError, TimeoutError, OSError):
            if attempt == 2:
                raise
            time.sleep(1.0 + attempt)
    raise RuntimeError("unreachable")
def cache_fetch(path, url, host, delay, timeout, params=None):
    if path.exists():
        return path.read_text(errors="replace"), "cache", 200
    r = request(url, host, delay, timeout, params)
    if r.status_code != 200:
        return "", "http", r.status_code
    text = r.text
    path.write_text(text)
    return text, "network", r.status_code
def source_url(doi, meta):
    links = [x.get("URL", "") for x in meta.get("link", [])]
    for u in links:
        if any(x in u for x in ("frontiersin.org", "cambridge.org", "link.springer.com")) and "pdf" not in u:
            return u
    if doi.startswith("10.1016/"):
        for u in links:
            m = re.search(r"PII:([A-Z0-9]+)", u, re.I)
            if m: return "https://www.sciencedirect.com/science/article/pii/" + m.group(1)
    if doi.startswith("10.1186/"): return "https://link.springer.com/article/" + doi
    if doi.startswith("10.1080/"): return "https://www.tandfonline.com/doi/full/" + doi
    if doi.startswith("10.1089/"): return "https://www.liebertpub.com/doi/full/" + doi
    if doi.startswith(("10.1002/", "10.1111/")): return "https://onlinelibrary.wiley.com/doi/full/" + doi
    if doi.startswith("10.3389/"): return "https://www.frontiersin.org/articles/" + doi + "/full"
    if doi.startswith("10.1037/"): return "https://psycnet.apa.org/doi/" + doi
    if doi.startswith("10.1521/"): return "https://guilfordjournals.com/doi/" + doi
    return meta.get("URL", "https://doi.org/" + doi)
def evidence_context(text):
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
    keys = ("replicat", "original study", "previous study", "prior study")
    return [s.strip()[:800] for s in sentences if any(k in s.lower() for k in keys)][:24]
def ref_score(ref, contexts):
    title = str(ref.get("article-title") or "").lower()
    author = str(ref.get("author") or "").split(",")[0].lower()
    year = str(ref.get("year") or "")
    score = 0
    if title and any(title[:30] in c.lower() for c in contexts): score += 3
    if author and year and any(author in c.lower() and year in c for c in contexts): score += 4
    if author and any(author in c.lower() for c in contexts): score += 1
    return score
def process(row, args):
    start = time.monotonic()
    doi = norm(row.get("doi_r") or row.get("replication_doi") or row.get("doi"))
    if not DOI_RE.fullmatch(doi): return {"doi": doi, "error": "invalid_doi"}
    key = hashlib.sha256(doi.encode()).hexdigest()[:16]
    folder = Path(args.cache) / key
    folder.mkdir(parents=True, exist_ok=True)
    errors = []
    cross = {}
    try:
        raw, origin, status = cache_fetch(folder/"crossref.json",
            "https://api.crossref.org/works/" + quote(doi, safe=""),
            "crossref", .45, args.timeout)
        if raw: cross = json.loads(raw).get("message", {})
        if status != 200: errors.append("crossref_http_" + str(status))
    except Exception as e: errors.append("crossref_" + type(e).__name__)
    epmc = {}
    try:
        raw, origin, status = cache_fetch(folder/"epmc.json",
            "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
            "epmc", .15, args.timeout,
            {"query": "DOI:" + doi, "resultType": "core", "format": "json", "pageSize": 1})
        if raw:
            x = json.loads(raw).get("resultList", {}).get("result", [])
            epmc = x[0] if x else {}
        if status != 200: errors.append("epmc_http_" + str(status))
    except Exception as e: errors.append("epmc_" + type(e).__name__)
    oa_abs = str(row.get("replication_abstract_cached") or "").strip() or inverted(row)
    cross_abs = clean_markup(cross.get("abstract") or "")
    pmc_abs = clean_markup(epmc.get("abstractText") or "")
    abstract = oa_abs or cross_abs or pmc_abs
    abstract_source = ("supplied primary abstract" if row.get("replication_abstract_cached") else "OpenAlex") if oa_abs else "Crossref" if cross_abs else "EuropePMC" if pmc_abs else ""
    full = ""
    full_source = ""
    pmc_ref_dois = []
    pmcid = epmc.get("pmcid")
    if pmcid:
        try:
            raw, origin, status = cache_fetch(folder/"pmc.xml",
                "https://www.ebi.ac.uk/europepmc/webservices/rest/" + pmcid + "/fullTextXML",
                "epmc", .15, args.timeout)
            if raw and "<article" in raw[:1000]:
                from xml.etree import ElementTree as ET
                xml = ET.fromstring(raw)
                for ref in xml.findall(".//ref"):
                    pmc_ref_dois.extend(norm(d) for d in DOI_RE.findall(" ".join(ref.itertext())))
                body = xml.find(".//body")
                if body is not None:
                    full = re.sub(r"\s+", " ", " ".join(body.itertext()))[:args.max_chars]
                    full_source = "EuropePMC fullTextXML"
            if status != 200: errors.append("pmc_http_" + str(status))
        except Exception as e: errors.append("pmc_" + type(e).__name__)
    publisher = source_url(doi, cross)
    if not full and publisher:
        try:
            from urllib.parse import urlparse
            host = urlparse(publisher).hostname or "publisher"
            pb = folder/"publisher.bytes"
            if pb.exists():
                raw_bytes, status = pb.read_bytes(), 200
            else:
                response = request(publisher, host, .3, args.timeout)
                status = response.status_code
                raw_bytes = response.content if status == 200 else b""
                if raw_bytes: pb.write_bytes(raw_bytes)
            if status == 200 and raw_bytes:
                if raw_bytes.startswith(b"%PDF"):
                    try:
                        from pypdf import PdfReader
                        from io import BytesIO
                        pdf = PdfReader(BytesIO(raw_bytes))
                        txt = " ".join((page.extract_text() or "") for page in pdf.pages)
                        txt = re.sub(r"\s+", " ", txt)[:args.max_chars]
                    except Exception as exc:
                        txt = ""
                        errors.append("pdf_" + type(exc).__name__)
                else:
                    txt = clean_markup(raw_bytes.decode("utf-8", errors="replace"))[:args.max_chars]
                if len(txt) >= 800 and not any(b.lower() in txt[:1000].lower() for b in BAD):
                    if "APA PsycNet" in txt[:300] and len(txt) < 5000:
                        errors.append("publisher_shell_only")
                    else:
                        full, full_source = txt, publisher
                else: errors.append("publisher_unusable")
            else: errors.append("publisher_http_" + str(status))
        except Exception as e: errors.append("publisher_" + type(e).__name__)
    if not full and publisher and args.jina:
        try:
            raw, origin, status = cache_fetch(folder/"jina.txt",
                "https://r.jina.ai/" + publisher,
                "r.jina.ai", .6, args.timeout)
            if status == 200 and len(raw) >= 800 and not any(b.lower() in raw[:1200].lower() for b in BAD) and not ("APA PsycNet" in raw[:300] and len(raw) < 5000):
                full, full_source = raw[:args.max_chars], "Jina mirror of " + publisher
            else: errors.append("jina_unusable_" + str(status))
        except Exception as e: errors.append("jina_" + type(e).__name__)
    if full:
        (folder/"primary_text.txt").write_text(full)
    elif (folder/"primary_text.txt").exists():
        (folder/"primary_text.txt").unlink()
    refs = []
    for ref in cross.get("reference", []):
        d = norm(ref.get("DOI"))
        if d and d != doi: refs.append({"doi": d, "title": ref.get("article-title") or "",
          "author": ref.get("author") or "", "year": str(ref.get("year") or ""),
          "unstructured": str(ref.get("unstructured") or "")[:300]})
    # Publisher/PMC full text can contain reference DOIs absent from Crossref.
    ref_seen = {x["doi"] for x in refs}
    for d in pmc_ref_dois + DOI_RE.findall(full[-100000:] if full else ""):
        d = norm(d)
        if d != doi and d not in ref_seen:
            refs.append({"doi": d, "title": "", "author": "", "year": "", "unstructured": ""})
            ref_seen.add(d)
    contexts = evidence_context((abstract + " " + full[:args.max_chars]) if full else abstract)
    ranked = sorted((dict(ref, score=ref_score(ref, contexts)) for ref in refs),
        key=lambda x: (-x["score"], x["doi"]))
    known = norm(row.get("doi_o") or row.get("original_doi") or row.get("known_original_doi"))
    result = {"doi": doi, "pool_index": row.get("raw_index", row.get("pool_index")),
      "title": row.get("title") or cross.get("title", [""])[0],
      "primary_field": ((row.get("primary_topic") or {}).get("field") or {}).get("display_name"),
      "abstract": abstract, "abstract_source": abstract_source,
      "full_text_path": str(folder/"primary_text.txt") if full else "",
      "full_text_source": full_source, "full_text_chars": len(full),
      "publisher_url": publisher, "reference_count": len(refs),
      "references": refs, "replication_contexts": contexts,
      "original_doi_given": known, "original_doi_in_references": bool(known and known in ref_seen),
      "original_doi_in_text": bool(known and known in {norm(x) for x in DOI_RE.findall(full)}),
      "ranked_original_candidates": ranked[:10], "errors": errors,
      "elapsed_s": round(time.monotonic() - start, 2)}
    (folder/"evidence.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, help="JSON array or JSONL candidate file")
    ap.add_argument("--out", required=True, help="output evidence JSONL")
    ap.add_argument("--cache", default="/tmp/retested-evidence-prefetch-cache", help="persistent cache directory, default /tmp/retested-evidence-prefetch-cache")
    ap.add_argument("--workers", type=int, default=3, help="parallel DOI workers, 1..4; default 3")
    ap.add_argument("--timeout", type=float, default=12, help="per-request timeout in seconds")
    ap.add_argument("--max-chars", type=int, default=160000, help="maximum retained primary-source characters per DOI")
    ap.add_argument("--jina", action="store_true", help="try a public text mirror if publisher and PMC full text fail")
    ap.add_argument("--emit-exact", help="Optional valid pipeline.exact_review two-abstract JSONL")
    args = ap.parse_args()
    if not (1 <= args.workers <= 4): ap.error("workers must be 1..4")
    raw = Path(args.input).read_text()
    try:
        rows = json.loads(raw)
        if isinstance(rows, dict): rows = rows.get("candidates") or [rows]
    except json.JSONDecodeError:
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    t = time.monotonic()
    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda x: process(x, args), rows))
    Path(args.out).write_text("".join(json.dumps(x, ensure_ascii=False)+"\n" for x in results))
    if args.emit_exact:
        packet = []
        for original, result in zip(rows, results):
            candidates = original.get("known_original_dois") or [original.get("known_original_doi") or original.get("doi_o") or original.get("original_doi")]
            for odoi in candidates:
                odoi = norm(odoi)
                if not DOI_RE.fullmatch(odoi) or len(result.get("abstract", "")) < 100:
                    continue
                ocache = Path(args.cache) / hashlib.sha256(odoi.encode()).hexdigest()[:16]
                ocache.mkdir(parents=True, exist_ok=True)
                try:
                    raw, _, status = cache_fetch(ocache/"crossref.json", "https://api.crossref.org/works/" + quote(odoi, safe=""), "crossref", .45, args.timeout)
                    meta = json.loads(raw)["message"] if raw and status == 200 else {}
                except Exception:
                    meta = {}
                try:
                    raw, _, status = cache_fetch(ocache/"epmc.json", "https://www.ebi.ac.uk/europepmc/webservices/rest/search", "epmc", .15, args.timeout,
                        {"query":"DOI:"+odoi,"resultType":"core","format":"json","pageSize":1})
                    choices = json.loads(raw).get("resultList",{}).get("result",[]) if raw and status == 200 else []
                    emeta = choices[0] if choices else {}
                except Exception:
                    emeta = {}
                oabs = original.get("original_abstract_cached") or clean_markup(meta.get("abstract") or "") or clean_markup(emeta.get("abstractText") or "")
                title = original.get("original_title") or (meta.get("title") or [emeta.get("title") or ""])[0]
                date = meta.get("published",meta.get("issued",{})).get("date-parts",[[None]])[0][0]
                try: year = int(original.get("original_year") or date or emeta.get("pubYear"))
                except (ValueError,TypeError): continue
                try:
                    rep_year = int(original.get("publication_year") or original.get("replication_year") or original.get("year_r"))
                except (ValueError, TypeError):
                    continue
                if len(oabs) < 100 or year >= rep_year: continue
                packet.append({
                    "original_doi":odoi,"original_title":title,"original_year":year,
                    "original_abstract_cached":oabs,
                    "replication_candidate_id":result["doi"],"replication_doi":result["doi"],
                    "replication_title":result["title"],"replication_year":rep_year,
                    "replication_abstract_cached":result["abstract"],
                    "original_source_url":original.get("original_source_url") or source_url(odoi,meta),
                    "replication_source_url":result["publisher_url"],
                    "review_checks":"Primary abstracts prefetched; exact original DOI is " +
                       ("in later structured references" if odoi in {r["doi"] for r in result["references"]} else "supplied as a source-review lead; verify citation in full paper")
                })
        Path(args.emit_exact).write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in packet))
        print("exact_review_packet",args.emit_exact,"rows",len(packet))

    print(json.dumps({"count":len(results),"wall_s":round(time.monotonic()-t,2),
      "abstract_usable":sum(len(x.get("abstract",""))>=100 for x in results),
      "full_text_usable":sum(x.get("full_text_chars",0)>=800 for x in results),
      "with_references":sum(x.get("reference_count",0)>0 for x in results),
      "errors":sum(bool(x.get("errors")) for x in results),
      "out":args.out},indent=2))
if __name__ == "__main__": main()

