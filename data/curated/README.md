# data/curated: every judgement a person (or a checked reading) made

The build (`python -m pipeline build`) reads these files on top of FORRT's downloaded files in `data/raw/`. Each row
says what it decides, why, and on what evidence. A row that no longer matches the data stops the build rather than
being skipped. Nothing here is edited to make a number come out; change a row only with its reason and evidence.

## Decisions the build applies

| File | Decides | Read by |
|---|---|---|
| `merges.yaml` | Names that are one effect (the same claim on the same original paper), and the name shown | `pipeline/registry.py` |
| `effects_kept_apart.csv` | Effects that share replications but are different claims (read, kept apart) | `pipeline/quality_audit.py` |
| `effect_originals.csv` | An effect's original paper when FORRT names it only in prose | `pipeline/curated_links.py` |
| `effect_original_exclusions.csv` | An effect name attached to a paper about something else | `pipeline/curated_links.py` |
| `effect_description_exclusions.csv` | A source description that belongs to another claim, or is not a claim | `pipeline/curated_links.py` |
| `attempt_effects.csv` | Which named effect a replication tested, when its original carries several | `pipeline/curated_links.py` |
| `attempt_duplicates.csv` | One study listed twice under one original: merged and counted once | `pipeline/curated_links.py` |
| `attempt_exclusions.csv` | An "attempt" that is not a replication of its original (wrong original, the original itself, published before it, a review): set aside with the reason | `pipeline/curated_links.py` |
| `attempt_relinks.csv` | A replication filed under the wrong original, moved to the original it replicates | `pipeline/curated_links.py` |
| `link_checks.csv` | Whether a machine-found pair replicates the original it is linked to, checked against both abstracts: yes joins the record, no leaves the queue, can't tell waits | `pipeline/curated_links.py` |
| `paper_details.csv` | Title, authors and year of a later paper no catalogue supplies, looked up by hand | `pipeline/curated_links.py` |
| `attempt_results.csv` | A result corrected against the replication's own abstract; the earlier coding is shown beside it | `pipeline/curated_links.py` |
| `attempts_checked.csv` | An attempt that looked wrong (dated before its original, titled like a review or like its original, a reading that differs) checked and kept, or found to need the full text | `pipeline/curated_links.py`, `pipeline/quality_audit.py` |
| `read_pairs.json` | Later papers read from their title and abstract: what the paper is, whether it tests the finding, what it found, with quotes | `pipeline/read_pairs.py` |
| `promoted_pairs.json` | The 1,941 pairs Retested's readers checked against the papers (the "Retested reviewed" attempts) | `pipeline/promoted.py` |
| `psychology_alternative_finds.json`, `replication_primary_fields_20260925.json` | Source-checked fields for those pairs (dates, preregistration, primary-source values) | `pipeline/load.py`, `pipeline/promoted.py`, `pipeline/batch_publish.py` |
| `original_links.csv`, `multi_original_links.csv` | The original a machine find replicates, read from the source | `pipeline/load.py`, `pipeline/queue.py` |
| `original_audit.csv`, `outcome_audit.csv` | Hand-read checks of whether a machine find was matched to the right original and its result read right | `pipeline/audit.py`, `pipeline/originals.py`, `pipeline/outcomes.py` |
| `low_tier_review.csv` | Hand decisions on low-ranked machine finds | `pipeline/load.py` |
| `effect_lines.json` | One plain sentence per effect, keyed by the stable effect id | `pipeline/wiki.py` |
| `effect_typology.json` | How each effect's original study worked, keyed by the stable effect id | `pipeline/wiki.py` |
| `wiki_lines.json`, `wiki_explanations.json`, `wiki_scenes.json` | Written text for attempts and findings, each from its own sources | `pipeline/wiki.py` |
| `finding_explanations.json`, `finding_explanation_review_holds_20260926.json` | Explanations of original findings, and those held back | `pipeline/explanations.py` |
| `posts.json`, `card_holds.json` | Feed posts, and cards held out of the game | `pipeline/posts.py`, `pipeline/wiki.py`, `pipeline/load.py` |
| `forrt_overlap_audit_20260926.json`, `forrt_overlap_reconciled_20260926.json`, `forrt_semantic_match_review_20260926.json` | The September comparison of Retested's reviewed pairs with FORRT's records | `pipeline/reconciliation_registry.py`, `pipeline/pair_match_*.py` |
| `registry/effect_ids.csv` | The stable id of every effect name (never reused) | `pipeline/__main__.py` (the effect-id ledger) and the writers that key on ids |
| `registry/reconciliation_policy_v1.json` | The rules of that comparison | `pipeline/reconciliation_registry.py` |
| `baseline/SUMMARY.json` | The counts the last accepted build had; a drop of more than 1% stops the build until accepted with a reason | `pipeline/validate.py` |

## The record behind earlier decisions (read by no code)

Kept because the decisions above cite them. Several are named by path inside other files here, so they stay where they
are.

| File | What it is |
|---|---|
| `forrt_identity_review_20260926.json`, `forrt_identity_second_review_20260926.json` | Which records are the same publication, for the September comparison |
| `forrt_negative_evidence_repair_20260926.json`, `forrt_negative_location_repair_20260926.json`, `forrt_negative_rationale_correction_20260926.json` | Repairs and one retraction of reasons given in that comparison |
| `forrt_textless_alias_audit_20260926.json` | FORRT records the comparison could not embed, checked by hand |
| `registry/reconciliation_checkpoint_20260926.json` | A reproducible checkpoint of that comparison |
| `finding_explanation_quality_audit_20260926.json`, `site_release_qa_20260926.json` | Release checks of the finding pages, September |
| `held_out_of_scope_primary_20260925.json`, `screening_pilot_flora_20260925.json`, `screening_pilot_replicating_20260925.json`, `psychology_alternative_review.csv` | Scope decisions and pilot readings behind the reviewed pairs |
| `source_review_archive_20260926.json` | The archive of the parallel source-review packets |
| `forrt_snapshots/2026-09-07/` | Compressed copies of FORRT files as fetched on 7 Sep, used by `python -m pipeline fetch` if a download disappears |
| `review_evidence/2026-10-28/` | The helpers' decisions, briefs and the paid reading's answer logs behind the 28 Oct changes (see `pipeline/repair/README.md`) |
| `review_evidence/2026-10-29/` | The blind check of 200 machine-found pairs that keeps machine-found pairs out of the count until verified |
