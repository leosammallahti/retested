"""Collect source-located original-study clues from public OSF attachments.

This command makes no link decisions. A DOI in a bibliography is usually background;
the output is an evidence index for a reader, not an original-link table.

    python -m pipeline osf-documents --pilot   # fixed 20-case stratified check
    python -m pipeline osf-documents           # every currently unlinked OSF find

Public OSF metadata and up to five PDF/DOCX files per project are fetched for free.
Successful responses and document text are cached by URL or OSF file id/version under
data/cache/osf_documents. Transient failures are left uncached for the next run.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from .load import CACHE, DISCOVERY, ROOT

API = "https://api.osf.io/v2"
OUT = DISCOVERY / "osf_document_evidence.json"
STORE = CACHE / "osf_documents"
UA = {"User-Agent": "Retested/0.1 (noncommercial replication research)"}
MAX_BYTES = 20_000_000
MAX_FILES = 5
MAX_PAGES = 200
MAX_DEPTH = 5
MAX_LIST_PAGES = 20
MAX_LISTED = 500
DOI = re.compile(r"(?i)\b10\.\d{4,9}/[-._;()/:a-z0-9]+")
CUE = re.compile(r"(?i)\b(?:replicat\w*|reproduc\w*|original study|original paper|"
                 r"previous study|prior study|based on|follow.up study)\b")
YEAR = re.compile(r"\b(?:18|19|20)\d{2}\b")
POSITIVE = ("manuscript", "report", "paper", "preprint", "writeup", "write-up",
            "replication", "reproduction", "prereg", "pre-reg", "registered",
            "article", "thesis", "dissertation", "protocol")
NEGATIVE = ("raw data", "dataset", "analysis", "analyses", "code", "script",
            "stimuli", "material", "qualtrics", "questionnaire", "consent",
            "instruction", "plot", "figure", "jasp", "survey")
logging.getLogger("pypdf").setLevel(logging.ERROR)


class FetchError(Exception):
    """An OSF request failed; failures are not cached as empty results."""


def _digest(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _request(url: str, limit: int, refresh: bool = False) -> bytes:
    if urllib.parse.urlsplit(url).scheme != "https":
        raise FetchError("non_https_url")
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                raw = r.read(limit + 1)
            if len(raw) > limit:
                raise FetchError(f"over_{limit}_bytes")
            time.sleep(0.12)       # public API; be gentle even when requests are cached later
            return raw
        except FetchError:
            raise
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 404, 410):
                raise FetchError(f"http_{e.code}") from e
            if attempt == 3:
                raise FetchError(f"http_{e.code}") from e
        except Exception as e:
            if attempt == 3:
                raise FetchError(type(e).__name__) from e
        time.sleep(1 + 2 * attempt)
    raise FetchError("request_failed")


def _json(url: str, refresh: bool = False) -> dict:
    path = STORE / "api" / (_digest(url) + ".json")
    if path.exists() and not refresh:
        return json.loads(path.read_text(encoding="utf-8"))
    raw = _request(url, 10_000_000, refresh)
    try:
        data = json.loads(raw)
        if not isinstance(data, dict) or data.get("errors"):
            raise ValueError("OSF returned an error document")
    except (ValueError, UnicodeDecodeError) as e:
        raise FetchError("invalid_json") from e
    _write_json(path, data)
    return data


def _related(row: dict, name: str) -> str | None:
    r = (((row.get("relationships") or {}).get(name) or {}).get("links") or {}).get("related")
    return r.get("href") if isinstance(r, dict) else None


def _kind(token: str, known: dict, refresh: bool) -> str | None:
    kind = (known.get(token) or {}).get("kind")
    if kind in ("nodes", "registrations", "preprints", "files"):
        return kind
    try:
        d = _json(f"{API}/guids/{token}/", refresh)
        kind = (d.get("data") or {}).get("type")
        return kind if kind in ("nodes", "registrations", "preprints", "files") else None
    except FetchError:
        return None


def _list_files(token: str, kind: str | None, refresh: bool) -> tuple[list[dict], list[str]]:
    files: dict[str, dict] = {}
    errors: list[str] = []
    if kind == "preprints":
        try:
            p = _json(f"{API}/preprints/{token}/", refresh)
            url = _related(p.get("data") or {}, "primary_file")
            if not url:
                return [], ["no_primary_file"]
            f = _json(url, refresh).get("data") or {}
            return ([f] if f.get("id") else []), ([] if f.get("id") else ["empty_primary_file"])
        except FetchError as e:
            return [], [f"preprint:{e}"]
    if kind == "files":
        try:
            f = _json(f"{API}/files/{token}/", refresh).get("data") or {}
            return ([f] if f.get("id") else []), ([] if f.get("id") else ["empty_file"])
        except FetchError as e:
            return [], [f"file:{e}"]
    if kind not in ("nodes", "registrations"):
        return [], ["unknown_osf_kind"]
    try:
        providers = _json(f"{API}/{kind}/{token}/files/", refresh).get("data") or []
    except FetchError as e:
        return [], [f"providers:{e}"]
    seen_urls: set[str] = set()
    pages = 0

    def walk(url: str, depth: int) -> None:
        nonlocal pages
        if depth > MAX_DEPTH:
            errors.append("folder_depth_cap")
            return
        while url:
            if url in seen_urls:
                errors.append("repeated_page_url")
                return
            if pages >= MAX_LIST_PAGES or len(files) >= MAX_LISTED:
                errors.append("listing_cap")
                return
            seen_urls.add(url)
            pages += 1
            try:
                d = _json(url, refresh)
            except FetchError as e:
                errors.append(f"listing:{e}")
                return
            for row in d.get("data") or []:
                a = row.get("attributes") or {}
                if a.get("kind") == "folder":
                    child = _related(row, "files")
                    if child:
                        walk(child, depth + 1)
                elif a.get("kind") == "file" and row.get("id"):
                    files.setdefault(row["id"], row)
            url = (d.get("links") or {}).get("next")

    for p in providers:
        root = _related(p, "files")
        if root:
            walk(root, 0)
    return list(files.values()), errors


def _rank(row: dict, title: str | None) -> int | None:
    a = row.get("attributes") or {}
    name = (a.get("name") or "").lower()
    size = a.get("size")
    if not name.endswith((".pdf", ".docx")) or (size is not None and (size <= 0 or size > MAX_BYTES)):
        return None
    score = 2
    score += 5 * sum(word in name for word in POSITIVE)
    score -= 7 * sum(word in name for word in NEGATIVE)
    if "supplement" in name:
        score += 1
    title_words = set(re.findall(r"[a-z]{5,}", (title or "").lower()))
    name_words = set(re.findall(r"[a-z]{5,}", name))
    if len((title_words - {"replication", "replicating", "study"}) & name_words) >= 2:
        score += 3
    return score if score >= 2 else None


def _file_cache_key(row: dict) -> str:
    a = row.get("attributes") or {}
    return re.sub(r"[^A-Za-z0-9_-]", "_", str(row["id"])) + "_v" + \
        re.sub(r"[^A-Za-z0-9_-]", "_", str(a.get("current_version") or "unknown"))


def _download(row: dict, refresh: bool) -> tuple[bytes, str]:
    name = (row.get("attributes") or {}).get("name") or ""
    ext = ".pdf" if name.lower().endswith(".pdf") else ".docx"
    key = _file_cache_key(row)
    path = STORE / "files" / (key + ext)
    if path.exists() and not refresh:
        return path.read_bytes(), key
    url = (row.get("links") or {}).get("download")
    if not url:
        raise FetchError("no_download_url")
    raw = _request(url, MAX_BYTES, refresh)
    if ext == ".pdf" and not raw.startswith(b"%PDF"):
        raise FetchError("not_pdf")
    if ext == ".docx" and not raw.startswith(b"PK"):
        raise FetchError("not_docx")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(raw)
    tmp.replace(path)
    return raw, key


def _extract(raw: bytes, name: str) -> list[dict]:
    if name.lower().endswith(".pdf"):
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(raw))
        out = []
        for i, page in enumerate(reader.pages[:MAX_PAGES], 1):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            if text.strip():
                out.append({"location": f"page {i}", "text": text})
        return out
    out = []
    w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for member in ("word/document.xml", "word/footnotes.xml", "word/endnotes.xml"):
            if member not in z.namelist():
                continue
            if z.getinfo(member).file_size > 40_000_000:
                raise ValueError("large_docx_xml")
            root = ET.fromstring(z.read(member))
            for i, paragraph in enumerate(root.iter(w + "p"), 1):
                text = "".join(t.text or "" for t in paragraph.iter(w + "t")).strip()
                if text:
                    out.append({"location": f"{member} paragraph {i}", "text": text})
    return out


def _text_parts(row: dict, refresh: bool) -> tuple[list[dict], str]:
    key = _file_cache_key(row)
    path = STORE / "text" / (key + ".json")
    if path.exists() and not refresh:
        return json.loads(path.read_text(encoding="utf-8")), key
    raw, key = _download(row, refresh)
    parts = _extract(raw, (row.get("attributes") or {}).get("name") or "")
    _write_json(path, parts)
    return parts, key


def _evidence(parts: list[dict]) -> tuple[list[dict], list[dict]]:
    dois: dict[str, dict] = {}
    cues: list[tuple[int, dict]] = []
    for part in parts:
        text = re.sub(r"\s+", " ", part["text"]).strip()
        location = part["location"]
        for m in DOI.finditer(text):
            doi = m.group().rstrip(".,;:")
            # A trailing sentence parenthesis is not part of the DOI.
            while doi.endswith(")") and doi.count(")") > doi.count("("):
                doi = doi[:-1]
            norm = doi.lower()
            if norm not in dois:
                dois[norm] = {"doi": doi, "location": location,
                              "context": text[max(0, m.start() - 95):min(len(text), m.end() + 110)]}
        for m in CUE.finditer(text):
            context = text[max(0, m.start() - 140):min(len(text), m.end() + 220)]
            if not YEAR.search(context):
                continue
            rank = (3 if re.search(r"(?i)\b(?:we|this study|our study)\b.{0,100}\breplicat", context) else 0) \
                   + (2 if "original" in context.lower() else 0) \
                   + (1 if DOI.search(context) else 0)
            cues.append((rank, {"location": location, "context": context}))
    cues.sort(key=lambda x: -x[0])
    selected, seen = [], set()
    for _, cue in cues:
        k = (cue["location"], cue["context"][:100])
        if k not in seen:
            selected.append(cue)
            seen.add(k)
        if len(selected) >= 10:
            break
    return list(dois.values()), selected


def _unlinked_osf() -> tuple[list[dict], str]:
    path = ROOT / "data" / "build" / "candidates.json"
    raw = path.read_bytes()
    cands = json.loads(raw)
    rows = [c for c in cands if c.get("origin") == "retested_discovery"
            and c.get("field") == "psychology" and c.get("group") == "replication"
            and not c.get("doi_o") and c.get("osf_id")]
    return rows, hashlib.sha256(raw).hexdigest()


def _pilot(rows: list[dict], known: dict) -> list[dict]:
    f = DISCOVERY / "fulltext.json"
    fulltext = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    def wiki(c):
        return "wiki" in ((fulltext.get(c["id"]) or {}).get("got") or [])
    def kind(c):
        return (known.get(c["osf_id"]) or {}).get("kind")
    groups = [
        (8, lambda c: kind(c) == "nodes" and not c.get("abstract") and not wiki(c)),
        (4, lambda c: kind(c) == "nodes" and bool(c.get("abstract")) and not wiki(c)),
        (2, lambda c: kind(c) == "nodes" and wiki(c)),
        (3, lambda c: kind(c) == "registrations"),
        (3, lambda c: kind(c) == "preprints"),
    ]
    out = []
    seen = set()
    for n, pred in groups:
        pool = sorted((c for c in rows if pred(c) and c["id"] not in seen),
                      key=lambda c: _digest("osf-file-pilot-20260924/" + c["id"]))
        for c in pool[:n]:
            out.append(c)
            seen.add(c["id"])
    remaining = sorted((c for c in rows if c["id"] not in seen),
                       key=lambda c: _digest("osf-file-pilot-20260924/" + c["id"]))
    out.extend(remaining[:max(0, 20 - len(out))])
    return out


def run(pilot: bool = False, limit: int | None = None, refresh: bool = False) -> int:
    rows, build_hash = _unlinked_osf()
    osf_path = DISCOVERY / "osf.json"
    known = json.loads(osf_path.read_text(encoding="utf-8")) if osf_path.exists() else {}
    selected = _pilot(rows, known) if pilot else sorted(rows, key=lambda c: c["osf_id"])
    if limit is not None:
        selected = selected[:limit]
    entries = []
    for i, c in enumerate(selected, 1):
        token = c["osf_id"]
        kind = _kind(token, known, refresh)
        files, errors = _list_files(token, kind, refresh)
        ranked = sorted(((score, row) for row in files if (score := _rank(row, c.get("title_r"))) is not None),
                        key=lambda pair: (-pair[0], (pair[1].get("attributes") or {}).get("name") or ""))
        docs = []
        for score, row in ranked[:MAX_FILES]:
            a = row.get("attributes") or {}
            rec = {"file_id": row["id"], "version": a.get("current_version"),
                   "name": a.get("name"), "size": a.get("size"),
                   "source_url": (row.get("links") or {}).get("download"), "priority": score}
            try:
                parts, cache_key = _text_parts(row, refresh)
                dois, cues = _evidence(parts)
                rec.update(cache_key=cache_key, text_chars=sum(len(p["text"]) for p in parts),
                           text_sections=len(parts), doi_mentions=dois, replication_cues=cues)
            except Exception as e:
                rec["error"] = f"{type(e).__name__}: {e}"
            docs.append(rec)
        entries.append({"id": c["id"], "osf_id": token, "kind": kind, "title_r": c.get("title_r"),
                        "landing_page": c.get("landing_page"), "files_listed": len(files),
                        "eligible_files": len(ranked), "documents": docs, "errors": errors})
        if i % 10 == 0 or i == len(selected):
            print(f"  {i}/{len(selected)} OSF finds · "
                  f"{sum(bool(r['documents']) for r in entries)} with selected documents · "
                  f"{sum(bool(d.get('replication_cues')) for r in entries for d in r['documents'])} documents with cues",
                  flush=True)
    output = {"version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
              "source": "data/build/candidates.json", "source_sha256": build_hash,
              "scope": "unlinked Retested psychology replication candidates with OSF ids",
              "pilot": pilot, "selected": len(selected), "pool": len(rows),
              "summary": {"with_files": sum(r["files_listed"] > 0 for r in entries),
                          "with_eligible_files": sum(r["eligible_files"] > 0 for r in entries),
                          "with_extracted_text": sum(any(d.get("text_chars", 0) > 0 for d in r["documents"])
                                                     for r in entries),
                          "with_document_errors": sum(bool(any(d.get("error") for d in r["documents"]) or r["errors"])
                                                      for r in entries)},
              "rows": entries}
    out = STORE / "pilot-evidence.json" if pilot or limit is not None else OUT
    _write_json(out, output)
    print(f"  wrote {out}")
    print("  evidence only; no original DOI was linked or trusted")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="pipeline osf-documents", description=__doc__.splitlines()[0])
    p.add_argument("--pilot", action="store_true", help="repeat the fixed, stratified 20-case pilot")
    p.add_argument("--limit", type=int, help="process at most this many selected OSF ids")
    p.add_argument("--refresh", action="store_true", help="re-fetch successful cached metadata and documents")
    a = p.parse_args(argv)
    return run(a.pilot, a.limit, a.refresh)
