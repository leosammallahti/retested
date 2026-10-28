"""CLI:  python -m pipeline fetch [--refresh] | build [--accept-baseline]"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from . import (
    authors, choose, claims, discover, export, fetch, fulltext, game, link, load, originals, osf,
    osf_documents, outcomes, pair_summaries, queue, reconciliation_registry, references, registry, reread, score,
    stats, triage, validate, verify,
)
from . import curated_links, flora_validation, openalex_works, read_pairs, forrt_ledger, rr_list, explanation_import, original_abstracts, posts, rep_abstracts, wiki
from .ids import EffectLedger
from .load import ROOT

LEDGER = ROOT / "data" / "curated" / "registry" / "effect_ids.csv"


def build_reconciliation_artifacts(step) -> list[str]:
    """Refresh the pinned comparison input and fail closed on bad registry data.

    This is deliberately after ``export.write``: the reconciliation registry
    consumes the just-built ``data/build/attempts.json``.  Pair summaries use
    only the fetched, manifest-pinned FORRT files and curated promoted rows;
    optional live ``/tmp`` audit files are never consulted here.
    """

    summaries = pair_summaries.regenerate_default_document()
    step(
        f"pair summaries: {len(summaries['query_records'])} Retested records, "
        f"{len(summaries['corpus_records'])} FORRT records"
    )
    document, problems = reconciliation_registry.generate_and_write()
    if problems:
        return problems
    assert document is not None  # ``generate_and_write`` only returns None with problems.
    counts = document["counts"]
    step(
        f"reconciliation registry: {counts['retested_normalized_pairs']} pairs, "
        f"structural=PASS assurance=INCOMPLETE"
    )
    return []


def build(accept_baseline: bool) -> int:
    t0 = time.time()
    step = lambda msg: print(f"[{time.time() - t0:5.1f}s] {msg}", flush=True)  # noqa: E731
    raw_problems = fetch.validate_inputs()
    if raw_problems:
        print("\nRAW INPUT VALIDATION FAILED:", *raw_problems[:40], sep="\n  - ")
        return 1
    promoted_rows = load.load_promoted()
    src = {
        "flora": load.load_flora(), "fred": load.load_fred(), "legacy": load.load_legacy(),
        "famous": load.load_famous(), "openalex": load.load_openalex(), "merges": load.load_merges(), "links": curated_links.load(), "flora_validation": flora_validation.rows(), "openalex_works": openalex_works.load(), "read_pairs": read_pairs.load(),
        "promoted": promoted_rows,
        "explanations": load.load_finding_explanations(promoted_rows),
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
    items, reveals = game.build(g, load.load_claims(), candidates, load.load_refused_claims() | load.load_card_holds(), load.load_posts())
    finding_contexts = game.attach_finding_contexts(g, items, reveals)
    if before != len(candidates):
        step(f"deduped {before - len(candidates)} repeat deposits of work already in the queue")
    queue.consequences(candidates, g)
    pending = queue.pending(candidates, g)
    st = stats.build(g, items, candidates)
    # every row of every FORRT file must have an outcome (on the site, waiting, not yet read, left out with a reason)
    forrt = forrt_ledger.build(g, candidates, rr_list.rows(src["legacy"]["rr"]), src["famous"], load.load_extractor())
    st["forrt_ledger"] = forrt["summary"]
    step(f"FORRT ledger: {len(forrt['lines'])} source rows, {forrt['summary']['missing']} without an outcome")
    if forrt["summary"]["missing"]:
        print("\nFORRT LEDGER FAILED: source rows with no outcome",
              *[f"{l['file']} row {l['row']}" for l in forrt["lines"] if l["outcome"] == "MISSING"][:40], sep="\n  - ")
        return 1
    step(f"game {len(items)} items; {finding_contexts} study contexts attached to finding pages; "
         f"queue {len(candidates)} candidates; "
         f"{sum(len(v) for v in pending['by_finding'].values())} pending on {len(pending['by_finding'])} finding pages")
    problems = validate.run(g, src["flora"], items, reveals, st, accept_baseline, candidates, pending)
    if problems:
        print("\nVALIDATION FAILED:", *problems[:40], sep="\n  - ")
        return 1
    ledger.save()
    sizes = export.write(g, items, reveals, candidates, pending, st, load.load_citation())
    # readings a person must still read: they differ from FORRT's coding, or could not say whether the paper tests it
    notes = ROOT / "data" / "build" / "read_notes.json"
    notes.with_suffix(".json.tmp").write_text(json.dumps(g.get("read_notes") or [], ensure_ascii=False, indent=1), encoding="utf-8")
    notes.with_suffix(".json.tmp").replace(notes)
    out = ROOT / "data" / "build" / "forrt_ledger.json"
    out.with_suffix(".json.tmp").write_text(json.dumps(forrt, ensure_ascii=False), encoding="utf-8")
    out.with_suffix(".json.tmp").replace(out)
    wiki_effects, wiki_findings = wiki.write_release()
    step(f"wiki stories: {wiki_effects} effect pages and {wiki_findings} finding pages have a reviewed post")
    reconciliation_problems = build_reconciliation_artifacts(step)
    if reconciliation_problems:
        print("\nRECONCILIATION REGISTRY FAILED (structural validation; assurance remains incomplete):",
              *reconciliation_problems[:40], sep="\n  - ")
        return 1
    (ROOT / "data" / "build" / "build-log.txt").write_text("\n".join(g["log"]), encoding="utf-8")
    step("wrote " + ", ".join(f"{k} {v / 1e6:.1f}MB" for k, v in sizes.items()))
    print(json.dumps(st["counts"], indent=1))
    return 0


def run_discover(mode: str) -> int:
    promoted_rows = load.load_promoted()
    src = {"flora": load.load_flora(), "fred": load.load_fred(), "legacy": load.load_legacy(),
           "famous": load.load_famous(), "openalex": load.load_openalex(), "merges": load.load_merges(), "links": curated_links.load(), "flora_validation": flora_validation.rows(), "openalex_works": openalex_works.load(), "read_pairs": read_pairs.load(),
           "promoted": promoted_rows, "explanations": load.load_finding_explanations(promoted_rows)}
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
    ei = sub.add_parser("explanations-import", help="validate and merge source-reviewed explanation packets")
    ei.add_argument("packets", nargs="+", type=Path, help="versioned finding_explanations JSON packet(s)")
    ei.add_argument("--target", type=Path, default=load.ROOT / "data" / "curated" / "finding_explanations.json",
                    help="committed explanation layer to update")
    check_mode = ei.add_mutually_exclusive_group()
    check_mode.add_argument("--check", action="store_true", help="validate/merge-check without writing")
    check_mode.add_argument("--dry-run", action="store_true", help="show the safe merge result without writing")
    dp = sub.add_parser("discover", help="find candidates outside Retested's counted record")
    dp.add_argument("--mode", choices=["cites", "keyword", "coverage"], default="cites", help="cites = citation graph of known originals; keyword = title search; coverage = what a keyword search can see")
    ap_ = sub.add_parser("authors", help="fetch author identities for the originals our finds point at")
    ap_.add_argument("--max-usd", type=float, default=0.10, help="OpenAlex spending cap")
    ap_.add_argument("--deck", action="store_true", help="fetch abstracts for the originals the game deals cards about")
    ap_.add_argument("--finds", action="store_true", help="fetch abstracts for the originals our own finds point at")
    ap_.add_argument("--famous", action="store_true", help="find the famous effects' papers by title and fetch their abstracts")
    pi_ = sub.add_parser("posts-import", help="validate and merge written feed posts (what was done, then what was found)")
    pi_.add_argument("packets", nargs="+", type=Path, help="JSON array(s) of {id, post, source_level}")
    pi_.add_argument("--writer", default="claude-sonnet-5-5", help="who wrote them, recorded with each post")
    pi_.add_argument("--check", action="store_true", help="validate only; write nothing")
    oa_ = sub.add_parser("original-abstracts", help="keep every original paper's abstract with its source and date")
    oa_.add_argument("--max-usd", type=float, default=0.10, help="OpenAlex spending cap")
    oa_.add_argument("--semantic-scholar", action="store_true", help="also ask Semantic Scholar (free but slow and throttled)")
    oa_.add_argument("--no-pages", action="store_true", help="do not re-read the original pages reviewers already used")
    rp = sub.add_parser("references", help="find the original in the replication's own reference list")
    rp.add_argument("--max-usd", type=float, default=1.20, help="OpenAlex spending cap")
    rp.add_argument("--by-author", action="store_true",
                    help="match the author and year the abstract names against the paper's own reference list")
    rp.add_argument("--relink", action="store_true",
                    help="also reconsider finds whose author-and-year match landed in the weak band")
    sub.add_parser("rep-abstracts", add_help=False, help="keep each later paper's own abstract from the caches already on disk "
                                                          "(free; `python -m pipeline rep-abstracts`)")
    sub.add_parser("wiki", add_help=False, help="assemble the story each effect and finding page tells "
                                                "(`python -m pipeline wiki --help`)")
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
    sub.add_parser("quality-audit", help="list every item in the built site that still needs a decision "
                                         "(writes data/build/quality_audit.json; see pipeline/quality_audit.py)")
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
    if sys.argv[1:2] == ["rep-abstracts"]:
        sys.exit(rep_abstracts.main(sys.argv[2:]))
    if sys.argv[1:2] == ["wiki"]:
        sys.exit(wiki.main(sys.argv[2:]))
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
    if a.cmd == "quality-audit":
        from . import quality_audit
        return quality_audit.main([])
    if a.cmd == "authors":
        sys.exit(authors.run_finds(a.max_usd) if a.finds
                 else authors.run_famous(a.max_usd) if a.famous
                 else authors.run_deck(a.max_usd) if a.deck else authors.run(a.max_usd))
    if a.cmd == "posts-import":
        sys.exit(posts.run(a.packets, a.writer, a.check))
    if a.cmd == "original-abstracts":
        sys.exit(original_abstracts.run(a.max_usd, a.semantic_scholar, not a.no_pages))
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
    if a.cmd == "explanations-import":
        sys.exit(explanation_import.run(a.packets, a.target, check=a.check, dry_run=a.dry_run))
    if a.cmd == "build":
        sys.exit(build(a.accept_baseline))
    if a.cmd == "fetch":
        sys.exit(fetch.run(a.refresh))


if __name__ == "__main__":
    main()
