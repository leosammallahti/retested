"""CLI:  python -m pipeline fetch [--refresh] | build [--accept-baseline]"""
from __future__ import annotations

import argparse
import json
import sys
import time

from . import discover, export, fetch, game, load, queue, registry, score, stats, validate
from .ids import EffectLedger
from .load import ROOT

LEDGER = ROOT / "data" / "curated" / "registry" / "effect_ids.csv"


def build(accept_baseline: bool) -> int:
    t0 = time.time()
    step = lambda msg: print(f"[{time.time() - t0:5.1f}s] {msg}", flush=True)  # noqa: E731
    src = {
        "flora": load.load_flora(), "fred": load.load_fred(), "legacy": load.load_legacy(),
        "famous": load.load_famous(), "openalex": load.load_openalex(), "merges": load.load_merges(),
    }
    step(f"loaded: flora {len(src['flora'])}, fred {len(src['fred'])}, legacy {len(src['legacy']['data'])}+{len(src['legacy']['rr'])}, "
         f"famous {len(src['famous'])}, openalex {len(src['openalex'])}")
    ledger = EffectLedger(LEDGER)
    g = registry.build(src, ledger)
    step(f"registry: {len(g['effects'])} effects, {len(g['findings'])} findings, {len(g['attempts'])} attempts, {len(g['papers'])} papers")
    score.score(g)
    items, reveals = game.build(g)
    candidates = queue.build(load.load_extractor(), g)
    st = stats.build(g, items, candidates)
    step(f"game {len(items)} items; queue {len(candidates)} candidates")
    problems = validate.run(g, src["flora"], items, reveals, st, accept_baseline)
    if problems:
        print("\nVALIDATION FAILED:", *problems[:40], sep="\n  - ")
        return 1
    ledger.save()
    sizes = export.write(g, items, reveals, candidates, st, load.load_citation())
    (ROOT / "data" / "build" / "build-log.txt").write_text("\n".join(g["log"]), encoding="utf-8")
    step("wrote " + ", ".join(f"{k} {v / 1e6:.1f}MB" for k, v in sizes.items()))
    print(json.dumps(st["counts"], indent=1))
    return 0


def run_discover(mode: str) -> int:
    src = {"flora": load.load_flora(), "fred": load.load_fred(), "legacy": load.load_legacy(),
           "famous": load.load_famous(), "openalex": load.load_openalex(), "merges": load.load_merges()}
    g = registry.build(src, EffectLedger(LEDGER))
    discover.run(g, mode)
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(prog="pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="sources -> data/build + site/public/generated")
    b.add_argument("--accept-baseline", action="store_true", help="accept count changes and rewrite the baseline")
    f = sub.add_parser("fetch", help="download the raw sources listed in data/raw/forrt/MANIFEST.json")
    f.add_argument("--refresh", action="store_true", help="re-download from upstream and record new hashes")
    dp = sub.add_parser("discover", help="find replications FORRT has not recorded")
    dp.add_argument("--mode", choices=["cites", "keyword"], default="cites", help="cites = citation graph of known originals; keyword = title search")
    a = ap.parse_args()
    if a.cmd == "discover":
        sys.exit(run_discover(a.mode))
    if a.cmd == "build":
        sys.exit(build(a.accept_baseline))
    if a.cmd == "fetch":
        sys.exit(fetch.run(a.refresh))


if __name__ == "__main__":
    main()
