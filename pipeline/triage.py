"""AI triage of discovered candidates with DeepSeek: is it really a replication, of what, and what did it find?

    python -m pipeline triage --pilot          # the 70 hand-labelled papers only; prints agreement + real cost
    python -m pipeline triage --tier high      # all high-tier candidates from both searches
    python -m pipeline triage --tier high --max-usd 1.5

Results are cached per candidate in data/cache/triage/<model>/<prompt_version>/ so runs resume and
never pay twice. Every record stores the model id and prompt version. Quotes are checked mechanically:
a quote that is not literally in the title/abstract is dropped and flagged.

Needs DEEPSEEK_API_KEY in the environment, in ROOT/.env, or in /root/CoopContent/.env (the owner's shared key).
"""
from __future__ import annotations

import json
import re
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .load import CACHE, DISCOVERY, ROOT

URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-v4-flash"
PROMPT_VERSION = "t1"
# worst case (peak, cache miss) from the owner's CoopContent notes; used for the spending cap only
PRICE_IN, PRICE_OUT = 0.44, 1.32

SYSTEM = """You screen scientific papers for a database of REPLICATION STUDIES in psychology and the behavioural sciences.
Read the title and abstract and answer with a single JSON object, nothing else.

Definitions
- "replication": the paper reports NEW data (or a re-analysis for "reproduction") that tests whether a SPECIFIC earlier
  finding holds again. Direct, close, conceptual, systematic, registered and multi-lab replications all count, as do
  student/class replications (e.g. CREP) and dissertations. A single study that "replicates and extends" counts.
- NOT a replication: essays, reviews, meta-analyses, editorials or commentaries about replication; methods papers;
  forecasts/predictions of replicability; recommendations or peer-review letters (e.g. a PCI RR recommendation text);
  papers where "replication" means DNA/cell/virus/data/software replication; scale-validation papers that only
  re-test a questionnaire's factor structure are "psychometric".
- A preregistration or protocol with no results yet is "registration_only".

Return exactly these keys:
{
 "kind": "replication" | "reproduction" | "psychometric" | "registration_only" | "about_replication" | "not_replication",
 "field": "psychology" | "other_behavioural" | "non_behavioural",
 "original": {"authors": "<first author surname(s) of the replicated study, or null>", "year": <year or null>,
              "description": "<the finding being replicated, <= 20 words, or null>"},
 "original_index": <index from the CITED ORIGINALS list if one of them is the replicated study, else null>,
 "outcome": "successful" | "failed" | "mixed" | "not_reported",
 "outcome_quote": "<one short verbatim sentence fragment from the abstract that states the result, or null>",
 "confidence": <0.0-1.0>,
 "reason": "<= 15 words"
}
Use "other_behavioural" for economics, management, marketing, political science, education or sociology experiments
on human behaviour; "non_behavioural" for genetics, medicine without a behavioural outcome, computing, physics, etc.
outcome: "successful" if the original effect was found again, "failed" if not, "mixed" if partly."""


def _key() -> str:
    import os
    if os.environ.get("DEEPSEEK_API_KEY"):
        return os.environ["DEEPSEEK_API_KEY"].strip()
    for env in (ROOT / ".env", Path("/root/CoopContent/.env")):
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("DEEPSEEK_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("DEEPSEEK_API_KEY not found (env, .env, or /root/CoopContent/.env)")


def balance(key: str) -> float | None:
    try:
        req = urllib.request.Request("https://api.deepseek.com/user/balance", headers={"Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read())
        return sum(float(b["total_balance"]) for b in d.get("balance_infos", []) if b.get("currency") == "USD")
    except Exception:  # noqa: BLE001
        return None


def _user_msg(c: dict) -> str:
    origs = [f"[{i}] {t}" for i, t in enumerate(c.get("original_titles") or []) if t]
    return (f"TITLE: {c.get('title_r')}\nYEAR: {c.get('year_r')}  TYPE: {c.get('type')}  VENUE: {c.get('venue')}\n"
            f"ABSTRACT: {(c.get('abstract') or '(none)')[:2500]}\n"
            f"CITED ORIGINALS (studies from our database that this paper cites):\n" + ("\n".join(origs) if origs else "(none)"))


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


class Meter:
    def __init__(self, cap: float):
        self.cap, self.usd, self.n, self.lock = cap, 0.0, 0, threading.Lock()

    def add(self, usage: dict) -> None:
        with self.lock:
            self.n += 1
            self.usd += (usage.get("prompt_tokens", 0) * PRICE_IN + usage.get("completion_tokens", 0) * PRICE_OUT) / 1e6

    @property
    def over(self) -> bool:
        return self.usd >= self.cap


def classify(c: dict, key: str, meter: Meter, cache_dir: Path) -> dict | None:
    cid = re.sub(r"[^A-Za-z0-9._-]+", "_", c["cid"])[:120]
    f = cache_dir / f"{cid}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    if meter.over:
        return None
    body = json.dumps({
        "model": MODEL, "temperature": 0, "max_tokens": 400, "thinking": {"type": "disabled"},
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": _user_msg(c)}],
    }).encode()
    for attempt in range(5):
        try:
            req = urllib.request.Request(URL, data=body, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.loads(r.read())
            break
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == 4:
                print(f"    give up {cid}: {e}")
                return None
            time.sleep(2 * 2 ** attempt)
    meter.add(d.get("usage") or {})
    try:
        out = json.loads(d["choices"][0]["message"]["content"])
    except (KeyError, json.JSONDecodeError):
        out = {"kind": "error", "raw": d.get("choices", [{}])[0].get("message", {}).get("content")}
    # quote grounding: keep only quotes that literally occur in the text we sent
    q = out.get("outcome_quote")
    src = _norm(f"{c.get('title_r')} {c.get('abstract')}")
    out["quote_grounded"] = bool(q) and _norm(q) in src
    if q and not out["quote_grounded"]:
        out["outcome_quote_ungrounded"] = q
        out["outcome_quote"] = None
    idx = out.get("original_index")
    origs = c.get("originals") or []
    out["original_doi"] = origs[idx] if isinstance(idx, int) and 0 <= idx < len(origs) else None
    rec = {"cid": c["cid"], "model": MODEL, "prompt_version": PROMPT_VERSION, "usage": d.get("usage"), **out}
    f.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    return rec


def candidates(tier: str) -> list[dict]:
    tiers = {"high": {"high"}, "medium": {"high", "medium"}}[tier]
    seen, out = {}, []
    for mode in ("keyword", "cites"):
        p = DISCOVERY / f"discovered-{mode}.json"
        if not p.exists():
            continue
        for c in json.loads(p.read_text(encoding="utf-8"))["candidates"]:
            cid = c.get("doi_r") or c["openalex_id"]
            if c["tier"] not in tiers or not c.get("title_r"):
                continue
            if cid in seen:  # found by both searches: keep the richer record (with cited originals)
                if c.get("originals") and not seen[cid].get("originals"):
                    seen[cid].update(originals=c["originals"], original_titles=c["original_titles"])
                seen[cid].setdefault("found_by", []).append(mode)
                continue
            c = {**c, "cid": cid, "found_by": [mode]}
            seen[cid] = c
            out.append(c)
    return out


def run(tier: str = "high", pilot: bool = False, max_usd: float = 1.5, workers: int = 8) -> int:
    key = _key()
    b0 = balance(key)
    cache_dir = CACHE / "triage" / MODEL / PROMPT_VERSION
    cache_dir.mkdir(parents=True, exist_ok=True)
    cands = pilot_set() if pilot else candidates(tier)
    meter = Meter(max_usd)
    print(f"  {len(cands)} candidates · model {MODEL} · cap ${max_usd:.2f} (worst-case pricing) · balance ${b0}")
    results, t0 = [], time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(classify, c, key, meter, cache_dir): c for c in cands}
        for i, fu in enumerate(as_completed(futs), 1):
            r = fu.result()
            if r:
                results.append({**futs[fu], "triage": r})
            if i % 200 == 0:
                print(f"    {i}/{len(cands)} · est ${meter.usd:.3f} · {time.time() - t0:.0f}s")
    b1 = balance(key)
    skipped = len(cands) - len(results)
    print(f"  done: {len(results)} classified, {skipped} not (cap or errors) · est ${meter.usd:.3f} · "
          f"real spend ${(b0 - b1) if (b0 is not None and b1 is not None) else float('nan'):.3f}")
    if pilot:
        return report_pilot(results)
    out = DISCOVERY / "triaged.json"
    out.write_text(json.dumps(results, ensure_ascii=False), encoding="utf-8")
    from collections import Counter
    print("  kinds:", Counter(r["triage"].get("kind") for r in results).most_common())
    print("  fields of replications:", Counter(r["triage"].get("field") for r in results if r["triage"].get("kind") == "replication").most_common())
    print("  outcomes of psychology replications:", Counter(r["triage"].get("outcome") for r in results
          if r["triage"].get("kind") == "replication" and r["triage"].get("field") == "psychology").most_common())
    return 0


# ---------------------------------------------------------------- pilot: agreement with hand labels

# Hand labels (2026-09-19) for the random samples shown to the owner: seed 7 of keyword high tier, seed 11 of
# citation-only high tier. Y = psychology/behavioural replication, B = borderline, N = not, X = replication outside
# the behavioural sciences.
_KW = "YYYYYYYYYNYBYNBYYNYNYNYYNNBYNYBYBYNNYYYB"
_CI = "XNNNBNNNXXXYBNXNNYYYXYXXXNNXYN"


def pilot_set() -> list[dict]:
    import random
    K = [c for c in json.loads((DISCOVERY / "discovered-keyword.json").read_text(encoding="utf-8"))["candidates"] if c["tier"] == "high"]
    random.seed(7)
    ks = random.sample(K, 40)
    C = json.loads((DISCOVERY / "discovered-cites.json").read_text(encoding="utf-8"))["candidates"]
    kall = {c.get("doi_r") or c["openalex_id"] for c in K} | {c.get("doi_r") or c["openalex_id"] for c in
            json.loads((DISCOVERY / "discovered-keyword.json").read_text(encoding="utf-8"))["candidates"]}
    only = [c for c in C if c["tier"] == "high" and (c.get("doi_r") or c["openalex_id"]) not in kall]
    random.seed(11)
    cs = random.sample(only, 30)
    out = []
    for c, lab in zip(ks, _KW):
        out.append({**c, "cid": c.get("doi_r") or c["openalex_id"], "hand": lab})
    for c, lab in zip(cs, _CI):
        out.append({**c, "cid": c.get("doi_r") or c["openalex_id"], "hand": lab})
    return out


def report_pilot(results: list[dict]) -> int:
    def model_label(t: dict) -> str:
        if t.get("kind") in ("replication", "reproduction"):
            return "Y" if t.get("field") in ("psychology", "other_behavioural") else "X"
        return "N"
    agree = strict = n = 0
    rows = []
    for r in results:
        h, m = r["hand"], model_label(r["triage"])
        n += 1
        ok = (h == m) or (h == "B")
        agree += ok
        strict += (h == m)
        if not ok:
            rows.append(f"    hand {h} / model {m} ({r['triage'].get('kind')}, {r['triage'].get('field')}): {r['title_r'][:90]}")
    print(f"  agreement with hand labels: {agree}/{n} (borderline counts as agreeing) · strict {strict}/{n}")
    print("  disagreements:", *rows, sep="\n")
    return 0
