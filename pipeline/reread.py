"""Read the outcome out of the text `pipeline fulltext` went and got.

The screen read each find's abstract and, for 2,448 psychology replications, could not say how it turned out —
because the abstract does not say. `pipeline fulltext` collects what does: OSF wiki pages where a replication
team writes up what happened, and Europe PMC Results sections. This reads that text and answers one question.

    python -m pipeline reread --all --max-usd 1
    python -m pipeline reread --report

THE GUARD THAT MAKES IT CHECKABLE. Every answer must carry a VERBATIM quote from the text it was given, and the
quote is checked mechanically against that text before the answer is kept. A model asked "how did it turn out"
about a document that never says will otherwise produce a plausible answer, and this population is exactly the
one where "it does not say" is the commonest true answer — 525 of these are plain OSF project folders and 141
are registrations written before any data existed. An answer whose quote is not in the source is dropped, and
how often that happens is printed, because it is the number that says whether to believe the rest.

This is the same device the original screen used on abstracts, where it was worth having; here it is essential.

WHAT STILL HAS TO BE DONE BY HAND. Nothing below establishes accuracy. The outcome reader was measured at 94%
on abstracts (n=224, docs/LINK_AUDIT_20260919.md) and this is a different population and a different kind of
source, so that number does not carry. `pipeline outcomes --sample` draws from the pool and the labels
accumulate in data/curated/outcome_audit.csv; until some of these rows are in there, what this produces is
queue-grade and not page-grade.
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .load import CACHE, DISCOVERY
from .triage import URL, Meter, _key, balance

MODEL = "deepseek-v4-flash"
PROMPT_VERSION = "r1"
OUT = DISCOVERY / "reread.json"
SOURCE = DISCOVERY / "fulltext.json"
VALID = ("successful", "failed", "mixed", "not_reported")

SYSTEM = """You are told about a replication study and given text its authors wrote about it. Say how the
replication turned out. Reply with one JSON object, nothing else.

  {"outcome": "successful" | "failed" | "mixed" | "not_reported",
   "quote": "<verbatim sentence from the text that says so, or null>",
   "confidence": <0.0-1.0>}

successful     the replication found the original effect again
failed         it did not find the effect, or found it reversed
mixed          several outcomes were tested and they disagree, or the effect appeared only under some conditions
not_reported   the text does not say how it turned out

MOST OF THESE WILL BE "not_reported", AND THAT IS THE RIGHT ANSWER. Much of this text is a study plan written
before any data existed, a project folder description, a materials list, or an ethics statement. A plan that
says what the authors EXPECT to find is not a result. A description of the original study's finding is not a
result. A statement that data were collected is not a result.

THE QUOTE IS NOT OPTIONAL. If you answer anything other than "not_reported" you must copy, word for word, the
sentence from the given text that reports the outcome. Do not paraphrase it, do not assemble it from pieces, do
not quote the original study's finding. If you cannot find such a sentence, the answer is "not_reported" with a
null quote. Your quote is checked against the text and your answer is thrown away if it is not there.

WHOSE RESULT IS IT. These documents discuss two studies: the earlier one being re-tested and this replication.
The question is only about THIS replication. "Smith found that X increases Y" is the earlier study. "We found
that X increases Y", "the effect did not replicate", "our results were consistent with the original" are this
one."""


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", re.sub(r"\s+", " ", (s or "").lower())).strip()


def quote_is_real(quote: str | None, text: str) -> bool:
    """Is the quoted sentence actually in the text it was taken from?

    Compared on letters, digits and single spaces, because a model reflows whitespace and swaps quotation marks
    even when it is copying faithfully, and punishing that would throw away good answers. Anything shorter than
    25 characters is not evidence of anything and is refused.
    """
    if not quote or len(quote.strip()) < 25:
        return False
    return _norm(quote) in _norm(text)


def _user_msg(cid: str, title: str | None, rec: dict) -> str:
    return "\n".join([
        f"THE REPLICATION: {title or '(untitled)'}",
        f"SOURCE OF THE TEXT: {rec.get('source')} ({', '.join(rec.get('got') or []) or 'unknown'})",
        "", "TEXT:", rec["text"],
        "", "How did this replication turn out?"])


def read_one(cid: str, title: str | None, rec: dict, key: str, meter: Meter, cache_dir: Path) -> dict | None:
    gid = re.sub(r"[^A-Za-z0-9._-]+", "_", cid)[:110]
    f = cache_dir / f"{gid}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    if meter.over:
        return None
    body = json.dumps({
        "model": MODEL, "temperature": 0, "max_tokens": 350, "thinking": {"type": "disabled"},
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": _user_msg(cid, title, rec)}],
    }).encode()
    d = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(URL, data=body, headers={"Authorization": f"Bearer {key}",
                                                                  "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.loads(r.read())
            break
        except (urllib.error.URLError, TimeoutError):
            if attempt == 4:
                return None
            time.sleep(2 * 2 ** attempt)
    meter.add(d.get("usage") or {})
    try:
        out = json.loads(d["choices"][0]["message"]["content"])
    except (KeyError, json.JSONDecodeError):
        out = {}
    outcome = out.get("outcome") if out.get("outcome") in VALID else "not_reported"
    quote = out.get("quote")
    real = quote_is_real(quote, rec["text"])
    if outcome != "not_reported" and not real:
        outcome, dropped = "not_reported", True          # unsupported claim about a result is no result
    else:
        dropped = False
    res = {"id": cid, "outcome": outcome, "quote": quote if real else None,
           "confidence": out.get("confidence"), "quote_checked": real, "dropped_for_bad_quote": dropped,
           "source": rec.get("source"), "model": MODEL, "prompt_version": PROMPT_VERSION}
    f.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
    return res


def run(max_usd: float, workers: int, limit: int | None) -> int:
    if not SOURCE.exists():
        print("no text fetched yet — run `python -m pipeline fulltext --osf --pmc` first")
        return 1
    have = json.loads(SOURCE.read_text(encoding="utf-8"))
    from . import load
    titles = {r["cid"]: r.get("title_r") for r in load.load_triaged()}
    todo = [(cid, titles.get(cid), rec) for cid, rec in have.items() if rec.get("chars")]
    if limit:
        todo = todo[:limit]
    key = _key()
    cache_dir = CACHE / "reread" / MODEL / PROMPT_VERSION
    cache_dir.mkdir(parents=True, exist_ok=True)
    meter = Meter(max_usd)
    print(f"  {len(todo)} finds with text · model {MODEL} · prompt {PROMPT_VERSION} · cap ${max_usd:.2f} "
          f"· balance ${balance(key)}")
    got, t0 = [], time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(read_one, cid, t, rec, key, meter, cache_dir) for cid, t, rec in todo]
        for i, fu in enumerate(as_completed(futs), 1):
            r = fu.result()
            if r:
                got.append(r)
            if i % 200 == 0:
                print(f"    {i}/{len(todo)} · est ${meter.usd:.3f} · {time.time() - t0:.0f}s")
    print(f"  done: {len(got)} read, {len(todo) - len(got)} not (cap or errors) · est ${meter.usd:.3f}")
    merged = {r["id"]: r for r in (json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else [])}
    merged.update({r["id"]: r for r in got})
    OUT.write_text(json.dumps(sorted(merged.values(), key=lambda r: r["id"]), ensure_ascii=False, indent=0),
                   encoding="utf-8")
    print(f"  wrote {OUT} · {len(merged)} read in all ({len(got)} from this run)")
    report()
    return 0


def report() -> int:
    if not OUT.exists():
        print("nothing read yet")
        return 0
    recs = json.loads(OUT.read_text(encoding="utf-8"))
    c = Counter(r["outcome"] for r in recs)
    usable = c["successful"] + c["failed"]
    dropped = sum(1 for r in recs if r.get("dropped_for_bad_quote"))
    print(f"\n  {len(recs)} finds read from fetched text")
    for k in VALID:
        print(f"    {k:<14} {c[k]:>5}  {c[k] / max(len(recs), 1):>4.0%}")
    print(f"  {usable} now have a yes/no outcome they did not have before")
    print(f"  {dropped} answers were thrown away because the quote was not in the source"
          f" ({dropped / max(len(recs), 1):.0%})")
    by_src = Counter(r["source"] for r in recs if r["outcome"] in ("successful", "failed"))
    if by_src:
        print("  where the usable ones came from:", dict(by_src))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="pipeline reread", description=__doc__.split("\n")[0])
    p.add_argument("--all", action="store_true", help="read every find that has fetched text")
    p.add_argument("--report", action="store_true")
    p.add_argument("--max-usd", type=float, default=1.0)
    p.add_argument("--workers", type=int, default=16)
    p.add_argument("--limit", type=int)
    a = p.parse_args(argv)
    if a.all:
        return run(a.max_usd, a.workers, a.limit)
    if a.report:
        return report()
    p.print_help()
    return 1
