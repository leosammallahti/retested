"""Ask OSF what our OSF-hosted finds actually are: a registration, a preprint, or a plain project.

Most replications FORRT is missing are OSF deposits, and OSF answers the one rigour question that matters most
about them — was this preregistered — better than any amount of reading. A registration is a registration; there
is nothing to infer. Searching abstracts for the word "preregistered" finds it in 6% of our finds, because most
of them have a two-line abstract or none at all.

    python -m pipeline osf            # cached, free, ~0.3s per new id

Results go to data/discovery/osf.json and are keyed by the five-character OSF token, so re-runs cost nothing.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

from .load import CACHE, DISCOVERY

API = "https://api.osf.io/v2/guids/{}/"
UA = {"User-Agent": "Retested/0.1 (mailto:leosammallahti@gmail.com)"}


def lookup(token: str) -> dict:
    """One OSF object, cached on disk. A 404 or a gone project is a fact worth caching too."""
    f = CACHE / "osf" / f"{token}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    f.parent.mkdir(parents=True, exist_ok=True)
    rec: dict = {"osf_id": token}
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(API.format(token), headers=UA), timeout=30) as r:
                d = json.loads(r.read())["data"]
            a = d.get("attributes") or {}
            rec.update(kind=d.get("type"), registration=bool(a.get("registration")), preprint=bool(a.get("preprint")),
                       date_registered=a.get("date_registered"), date_created=a.get("date_created"),
                       title=a.get("title"), public=a.get("public"),
                       schema=((d.get("relationships") or {}).get("registration_schema") or {}).get("data", {}).get("id"))
            break
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                rec.update(kind=None, missing=e.code)
                break
            if attempt == 3:
                return {**rec, "error": f"HTTP {e.code}"}          # not cached: a transient failure is not an answer
            time.sleep(2 * 2 ** attempt)
        except Exception as e:                                      # noqa: BLE001 - transient network error
            if attempt == 3:
                return {**rec, "error": type(e).__name__}
            time.sleep(2 * 2 ** attempt)
    f.write_text(json.dumps(rec), encoding="utf-8")
    time.sleep(0.25)
    return rec


def run() -> int:
    from . import load, queue, registry
    from .ids import EffectLedger
    from .load import ROOT

    src = {k: getattr(load, f"load_{k}")() for k in ("flora", "fred", "legacy", "famous", "openalex", "merges")}
    g = registry.build(src, EffectLedger(ROOT / "data" / "curated" / "registry" / "effect_ids.csv"))
    cands = queue.build_retested(load.load_triaged(),
                                 {**load.load_reference_links(), **load.load_links()}, g,
                                 load.load_known_replication_dois(), load.load_known_osf_ids())
    tokens = sorted({c["osf_id"] for c in cands if c.get("osf_id")})
    print(f"  {len(tokens)} OSF ids among our finds")
    out, errs = {}, 0
    for i, t in enumerate(tokens, 1):
        r = lookup(t)
        if r.get("error"):
            errs += 1
        else:
            out[t] = r
        if i % 200 == 0:
            print(f"    {i}/{len(tokens)}", flush=True)
    DISCOVERY.mkdir(parents=True, exist_ok=True)
    (DISCOVERY / "osf.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    from collections import Counter
    kinds = Counter(r.get("kind") for r in out.values())
    print(f"  kinds: {dict(kinds)}   errors: {errs}")
    print(f"  preregistered (an OSF registration): {sum(1 for r in out.values() if r.get('registration'))}")
    return 0
