# The 28 October 2026 repair: the scripts that made the decisions

On 28 Oct 2026 Leo found that FORRT's Replications & Reversals list had been used only for names, and asked for
everything to be accounted for, fixed and documented. These are the scripts that found the problems and produced the
reviewed decisions now in `data/curated/`, as they were run. They are kept so every decision can be traced.

The build does not import them. What the build reads is the decisions, documented in `docs/SOURCES_AND_LEDGER.md`.

They were run from `/root/wiki-scratch/` and still name those paths. Logs and intermediate files stay there; the
evidence that matters is copied to `data/curated/review_evidence/2026-10-28/` by `copy_in.sh`.

## In the order they were used

| Step | Scripts | Produced |
|---|---|---|
| 1. Find the gap | `merges/gap*.py`, `merges/rr_pairs.py`, `merges/feeds_cover.py` | the counts of empty effects and unused FORRT pairs |
| 2. Whole-site audit | `audit/audit.py` (later `python -m pipeline quality-audit`), `audit/probe.py` | the list of every error class |
| 3. Duplicate names | `merges/merge_layout.py` (reading files), `merges/merge_decisions.py` | `data/curated/merges.yaml` |
| 4. Keyed by id | `merges/rekey_by_id.py`, `merges/reconcile_ids.py` | `effect_lines.json`, `effect_typology.json` keyed by effect id |
| 5. FORRT ledger checks | `merges/run_ledger.py`, `merges/check_registry.py` | in-memory checks before each build |
| 6. Paper identity | `audit/fetch_all_papers.py`, `audit/identity_check.py`, `audit/write_openalex_meta.py` | `data/raw/local/openalex_paper_metadata.json` (OpenAlex, free) |
| 7. Helper reading files | `helpers/make_layouts.py` | the files Sonnet 5.5 helpers read; their decisions are in the evidence folder |
| 8. Re-links | `relinks/lookup.py`, `relinks/layout.py`, `relinks/lookup2.py` (Crossref, free) | `data/curated/attempt_relinks.csv` |
| 9. Paper reading (paid, approved) | `reading/build_items.py`, `reading/questions.py`, `reading/run_reading.py`, `reading/keep_running.sh`, `reading/consensus.py`, `reading/ADJUDICATION_BRIEF.md` | `data/curated/read_pairs.json` |
| 10. Proof | `audit/compare.py` | before-and-after comparison against the build of 28 Oct 06:02 UTC |
| 11. Cases a reader settles | `cases/make_cases.py`, `cases/apply.py` (and the second round, `make_cases2.py`, `apply2.py`), `cases/BRIEF.md` | `attempt_exclusions.csv`, `attempt_relinks.csv`, `attempt_results.csv`, `attempts_checked.csv` |
| 12. Missing paper details | `details/fetch_details.py` (OpenAlex), `details/fetch_osf_registry.py` (OSF and doi.org) | `openalex_paper_metadata.json`, `later_paper_records.json` in `data/raw/local/` |
| 13. Plain lines for the effects that lacked one | `lines/BRIEF.md` (the rules of the earlier line writer, given to a Sonnet 5.5 helper) | `effect_lines.json` |
| 14. The review queue read (paid, approved) | `queue/fetch_abstracts.py`, `queue/build_items.py`, `queue/run_reading.py`, `queue/keep_running.sh`, `queue/consensus.py`, `queue/make_batch.py`, `queue/ADJUDICATION_BRIEF.md`, `queue/settle_all.sh` | `read_pairs.json` (the queue's readings layered on the morning's) |
| 15. Open full text read (paid, approved) | `fulltext/availability.py`, `fulltext/fetch_fulltext.py`, `fulltext/fetch_round2.py`, `fulltext/build_items.py`, `fulltext/run_reading.py` | `read_pairs.json` (a third layer) |
| 16. Checks on the readings | `queue/author_check.py` with `queue/mismatch_cases.py` and `MISMATCH_BRIEF.md` (a replication linked to the wrong paper by the same author); `cases/NULL_BRIEF.md` (an original that is itself a null finding) | decisions in `queue_splits_decided.txt`; corrections in `attempt_results.csv` |
| 17. The numbers in the documents | `queue/numbers.py` | read from the build |

## The paid reading

The reading used DeepSeek v4.1 flash and GLM 5.3 flash through cheaperinference, approved by Leo ("Yeah"; "GLM is
fine, $1.4 is fine"; cap $1.60). About 2,300 later papers were read from their titles and abstracts.

- An answer stands when both models agree and every quote is found word for word.
- A paper with no abstract that the title alone does not settle is recorded as not readable.
- Splits were decided by Sonnet 5.5 helpers following `reading/ADJUDICATION_BRIEF.md`, and samples were checked by
  Claude.
- The answer logs are in the evidence folder as `reading_answers_*.jsonl.gz`.

## The queue reading and the full-text reading (evening of 28 Oct)

Approved by Leo: "Yes, run it (cap $4)" for the queue, and "Yeah" to reading open full text (proposed at about $1.30).
The same two models and the same questions as the morning. The readings are layered: the morning's readings, then the
queue's (which also re-read 282 morning papers that had gained an abstract), then the full-text readings; a later
layer replaces an earlier reading only when it settles the paper. `queue/settle_all.sh` rebuilds `read_pairs.json`
from all three.

Two checks were added after reading samples. A 40-pair sample of agreed replications found two linked to another
paper by the same author, so every queue replication whose title or abstract names a study with other authors or
another year was read again (`queue/author_check.py` selects; a reader decides). And the question counts "no reliable
effect" as not found, which is backwards when the original finding is itself a null; those readings were found and
corrected (`cases/NULL_BRIEF.md`).

The full-text reading's inputs (the downloaded papers' results and discussion sections) are not in the repository:
not every open copy's licence allows republishing them. They stay on the host in
`/root/wiki-scratch/fulltext_20261028/` (`items.jsonl`, `text/`); the answer logs, with their short quotes, are in
the evidence folder.
