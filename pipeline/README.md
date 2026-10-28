# pipeline: the code that builds Retested

Run everything as `python -m pipeline <command>` from the checkout, with `/root/retested/.venv/bin/python -X utf8`.
What each source and reviewed file is: `docs/SOURCES_AND_LEDGER.md` and `data/curated/README.md`.

## The build: `python -m pipeline build`

Sources and reviewed decisions in, `data/build/` and `site/public/generated/` out. The build stops on any FORRT row
left without an outcome, on a reviewed row that no longer matches the data, and on a count that drops by more than 1%
(`--accept-baseline` accepts a drop that has a reason).

| Step | Modules |
|---|---|
| Read the downloaded sources | `load.py`, `rr_list.py` (the Replications & Reversals list), `flora_validation.py`, `openalex_works.py` |
| Read the reviewed decisions | `curated_links.py` (the reviewed CSV files), `read_pairs.py` (papers read for Retested), `promoted.py` (Retested's reviewed pairs) |
| Join it into papers, attempts, findings and effects | `registry.py`, with `ids.py` (DOIs, stable effect ids, slugs) and `explanations.py` |
| Score and count | `score.py` and `evidence.py` (the three lenses), `stats.py` |
| The review queue of machine finds | `queue.py` |
| The game deck and feed | `game.py`, `posts.py` |
| Account for every FORRT row | `forrt_ledger.py` |
| Check and write | `validate.py`, `export.py`, `wiki.py` (the story each page tells) |

## Other commands

| Command | Module | Cost |
|---|---|---|
| `fetch [--refresh]` | `fetch.py`: download FORRT's files listed in `data/raw/forrt/MANIFEST.json` | free |
| `quality-audit` | `quality_audit.py`: every item in the built site that still needs a decision | free |
| `discover`, `link`, `references` | `discover.py`, `link.py`, `references.py`: find replications FORRT does not have, and their originals | OpenAlex calls, capped by `--max-usd` when the project's OpenAlex key is set |
| `choose`, `verify` | `choose.py`, `verify.py`: ask a model which earlier paper a find replicates | paid: ask Leo first |
| `triage` | `triage.py`: a model's first read of discovered papers | paid: ask Leo first |
| `fulltext`, `reread` | `fulltext.py` collects result text (OSF wikis, Europe PMC, open PDFs), free; `reread.py` reads it | `reread` is paid: ask Leo first |
| `authors`, `original-abstracts` | `authors.py`, `original_abstracts.py`: OpenAlex records and abstracts of originals | OpenAlex calls, capped by `--max-usd` |
| `osf`, `osf-documents`, `rep-abstracts` | OSF facts and documents; abstracts already on disk | free |
| `originals`, `outcomes` | `originals.py`, `outcomes.py`, `audit.py`: hand-read audits of machine matches and results | free |
| `claims`, `posts-import`, `explanations-import`, `wiki` | write or import page text | `claims` is paid: ask Leo first |

## Tools kept for the September comparison with FORRT

`reconciliation_registry.py` runs inside the build; `pair_summaries.py`, `pair_embeddings.py`, `pair_match_queue.py`,
`pair_match_adjudication.py`, `pair_match_reconcile.py`, `pair_match_benchmark.py`, `forrt_provenance.py`,
`candidate_inventory.py`, `doi_aliases.py`, `exact_review.py`, `primary_source_review.py`, `source_prefetch.py`,
`batch_publish.py`, `audit_promoted.py` and `plain.py` produced or check the reviewed pairs (`docs/FORRT_OVERLAP_AUDIT.md`,
`docs/REPLICATION_REGISTRY.md`).

## `repair/`

The scripts that made the 28 October 2026 decisions, kept so each decision can be traced. The build does not import
them. See `repair/README.md`.
