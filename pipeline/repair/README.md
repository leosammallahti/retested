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

## The paid reading

The reading used DeepSeek v4.1 flash and GLM 5.3 flash through cheaperinference, approved by Leo ("Yeah"; "GLM is
fine, $1.4 is fine"; cap $1.60). About 2,300 later papers were read from their titles and abstracts.

- An answer stands when both models agree and every quote is found word for word.
- A paper with no abstract that the title alone does not settle is recorded as not readable.
- Splits were decided by Sonnet 5.5 helpers following `reading/ADJUDICATION_BRIEF.md`, and samples were checked by
  Claude.
- The answer logs are in the evidence folder as `reading_answers_*.jsonl.gz`.
