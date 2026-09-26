"""CLI:  python -m pipeline fetch [--refresh] | build [--accept-baseline]"""
from __future__ import annotations

import argparse
import json
import sys
import time

from . import (
    authors, choose, claims, discover, export, fetch, fulltext, game, link, load, originals, osf,
    osf_documents, outcomes, queue, reconciliation_registry, references, registry, reread, score,
    stats, triage, validate, verify,
)
from .ids import EffectLedger
from .load import ROOT

LEDGER = ROOT / "data" / "curated" / "registry" / "effect_ids.csv"


def build(accept_baseline: bool) -> int:
    t0 = time.time()
    step = lambda msg: print(f"[{time.time() - t0:5.1f}s] {msg}", flush=True)  # noqa: E731
    src = {
        "flora": load.load_flora(), "fred": load.load_fred(), "legacy": load.load_legacy(),
        "famous": load.load_famous(), "openalex": load.load_openalex(), "merges": load.load_merges(),
        "promoted": load.load_promoted(),
    }
    step(f"loaded: flora {len(src['flora'])}, fred {len(src['fred'])}, legacy {len(src['legacy']['data'])}+{len(src['legacy']['rr'])}, "
         f"famous {len(src['famous'])}, openalex {len(src['openalex'])}, promoted {len(src['promoted'])}")
    ledger = EffectLedger(LEDGER)
    g = registry.build(src, ledger)
    step(f"registry: {len(g['effects'])} effects, {len(g['findings'])} findings, {len(g['attempts'])} attempts, {len(g['papers'])} papers")
    score.score(g)
    candidates = queue.build(load.load_extractor(), g) + queue.build_retested(load.load_triaged(), load.merged_links(), g, load.load_known_replication_dois(), load.load_known_osf_ids(),
                                      load.load_surname_frequency(), load.load_osf(),
                                      load.load_original_authors())
    before = len(candidates)
    candidates = queue.dedupe(candidates)
    items, reveals = game.build(g, load.load_claims(), candidates, load.load_refused_claims())
    if before != len(candidates):
        step(f"deduped {before - len(candidates)} repeat deposits of work already in the queue")
    queue.consequences(candidates, g)
    pending = queue.pending(candidates, g)
    st = stats.build(g, items, candidates)
    step(f"game {len(items)} items; queue {len(candidates)} candidates; "
         f"{sum(len(v) for v in pending['by_finding'].values())} pending on {len(pending['by_finding'])} finding pages")
    problems = validate.run(g, src["flora"], items, reveals, st, accept_baseline, candidates, pending)
    if problems:
        print("\nVALIDATION FAILED:", *problems[:40], sep="\n  - ")
        return 1
    ledger.save()
    sizes = export.write(g, items, reveals, candidates, pending, st, load.load_citation())
    (ROOT / "data" / "build" / "build-log.txt").write_text("\n".join(g["log"]), encoding="utf-8")
    step("wrote " + ", ".join(f"{k} {v / 1e6:.1f}MB" for k, v in sizes.items()))
    print(json.dumps(st["counts"], indent=1))
    return 0


def run_discover(mode: str) -> int:
    src = {"flora": load.load_flora(), "fred": load.load_fred(), "legacy": load.load_legacy(),
           "famous": load.load_famous(), "openalex": load.load_openalex(), "merges": load.load_merges(),
           "promoted": load.load_promoted()}
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
    dp.add_argument("--mode", choices=["cites", "keyword", "coverage"], default="cites", help="cites = citation graph of known originals; keyword = title search; coverage = what a keyword search can see")
    ap_ = sub.add_parser("authors", help="fetch author identities for the originals our finds point at")
    ap_.add_argument("--max-usd", type=float, default=0.10, help="OpenAlex spending cap")
    ap_.add_argument("--deck", action="store_true", help="fetch abstracts for the originals the game deals cards about")
    ap_.add_argument("--finds", action="store_true", help="fetch abstracts for the originals our own finds point at")
    ap_.add_argument("--famous", action="store_true", help="find the famous effects' papers by title and fetch their abstracts")
    rp = sub.add_parser("references", help="find the original in the replication's own reference list")
    rp.add_argument("--max-usd", type=float, default=1.20, help="OpenAlex spending cap")
    rp.add_argument("--by-author", action="store_true",
                    help="match the author and year the abstract names against the paper's own reference list")
    rp.add_argument("--relink", action="store_true",
                    help="also reconsider finds whose author-and-year match landed in the weak band")
    sub.add_parser("osf", help="ask OSF whether our OSF-hosted finds are registrations (free, cached)")
    sub.add_parser("osf-documents", add_help=False, help="collect original-study evidence from public OSF attachments (free)")
    lp = sub.add_parser("link", help="resolve the original study named by triage but given no DOI")
    lp.add_argument("--openalex", action="store_true", help="after the free library pass, look the rest up in OpenAlex")
    lp.add_argument("--max-usd", type=float, default=1.0, help="OpenAlex spending cap")
    lp.add_argument("--check", action="store_true", help="accuracy against originals the citation graph already resolved")
    sub.add_parser("originals", add_help=False, help="hand-read audit of whether each find was matched to the "
                                                    "right earlier paper (`python -m pipeline originals --help`)")
    sub.add_parser("reread", add_help=False, help="read the outcome out of the fetched text "
                                                  "(`python -m pipeline reread --help`)")
    sub.add_parser("fulltext", add_help=False, help="fetch the result where the abstract does not report it "
                                                    "(`python -m pipeline fulltext --help`)")
    sub.add_parser("choose", add_help=False, help="ask which cited paper is the one being replicated "
                                                  "(`python -m pipeline choose --help`)")
    sub.add_parser("verify", add_help=False, help="ask the model whether each find was matched to the right "
                                                  "earlier paper (`python -m pipeline verify --help`)")
    sub.add_parser(
        "reconciliation-registry", add_help=False,
        help="build the evidence-first Retested/FORRT reconciliation registry",
    )
    sub.add_parser("outcomes", add_help=False, help="hand-read audit of whether the verdicts were read correctly "
                                                    "(its own flags: `python -m pipeline outcomes --help`)")
    cp = sub.add_parser("claims", help="write the plain-language claim each game card shows")
    cp.add_argument("--pilot", action="store_true", help="24 cards spread across disciplines, for reading before scaling")
    cp.add_argument("--all", action="store_true", help="every card in the deck")
    cp.add_argument("--plain", action="store_true", help="re-ask, in ordinary words, the cards that read like the paper")
    cp.add_argument("--report", action="store_true", help="what is written, flagged or leaking, from the cache")
    cp.add_argument("--limit", type=int, help="stop after this many cards")
    cp.add_argument("--tier", choices=["study", "famous", "found"], help="only this tier of card")
    cp.add_argument("--max-usd", type=float, default=0.50, help="spending cap at worst-case prices")
    cp.add_argument("--workers", type=int, default=8)
    tp = sub.add_parser("triage", help="DeepSeek check of discovered candidates")
    tp.add_argument("--tier", choices=["high", "medium", "low"], default="high")
    tp.add_argument("--pilot", action="store_true", help="only that tier's labelled sample; report agreement")
    tp.add_argument("--max-usd", type=float, default=1.5, help="spending cap at worst-case prices")
    tp.add_argument("--workers", type=int, default=8, help="parallel requests; ~8 gives 8 papers/s, higher risks 429s")
    tp.add_argument("--limit", type=int, help="screen at most this many selected candidates")
    tp.add_argument("--source", choices=["keyword", "cites", "both"], default="both",
                    help="select from the keyword sweep, citation search, or both (default)")
    tp.add_argument("--fields", help="comma-separated OpenAlex fields to screen, e.g. 'Psychology,Decision Sciences'; "
                                     "default is every field the title sweep covers")
    if sys.argv[1:2] == ["outcomes"]:      # these own their flag sets; keep them out of the shared parser
        sys.exit(outcomes.run(sys.argv[2:]))
    if sys.argv[1:2] == ["reread"]:
        sys.exit(reread.main(sys.argv[2:]))
    if sys.argv[1:2] == ["osf-documents"]:
        sys.exit(osf_documents.main(sys.argv[2:]))
    if sys.argv[1:2] == ["fulltext"]:
        sys.exit(fulltext.main(sys.argv[2:]))
    if sys.argv[1:2] == ["choose"]:
        sys.exit(choose.main(sys.argv[2:]))
    if sys.argv[1:2] == ["verify"]:
        sys.exit(verify.main(sys.argv[2:]))
    if sys.argv[1:2] == ["originals"]:
        sys.exit(originals.run(sys.argv[2:]))
    if sys.argv[1:2] == ["reconciliation-registry"]:
        sys.exit(reconciliation_registry.main(sys.argv[2:]))
    a = ap.parse_args()
    if a.cmd == "authors":
        sys.exit(authors.run_finds(a.max_usd) if a.finds
                 else authors.run_famous(a.max_usd) if a.famous
                 else authors.run_deck(a.max_usd) if a.deck else authors.run(a.max_usd))
    if a.cmd == "references":
        sys.exit(references.run_author(a.max_usd) if a.by_author else references.run(a.max_usd, a.relink))
    if a.cmd == "osf":
        sys.exit(osf.run())
    if a.cmd == "link":
        sys.exit(link.run(a.openalex, a.max_usd, a.check))
    if a.cmd == "claims":
        if a.plain:
            sys.exit(claims.run_plain(a.max_usd, a.workers, a.limit))
        if a.report:
            sys.exit(claims.report())
        sys.exit(claims.run("all" if a.all else "pilot", a.max_usd, a.workers, a.limit, a.tier))
    if a.cmd == "triage":
        sys.exit(triage.run(a.tier, a.pilot, a.max_usd, a.workers,
                            {f.strip() for f in a.fields.split(",")} if a.fields else None, a.source, a.limit))
    if a.cmd == "discover":
        sys.exit(run_discover(a.mode))
    if a.cmd == "build":
        sys.exit(build(a.accept_baseline))
    if a.cmd == "fetch":
        sys.exit(fetch.run(a.refresh))


if __name__ == "__main__":
    main()
