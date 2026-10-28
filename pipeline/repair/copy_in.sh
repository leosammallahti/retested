#!/bin/bash
# Copies the scripts and evidence of the 28 Oct 2026 repair from /root/wiki-scratch into the project (rerun is safe).
set -e
R=/root/retested-wiki/pipeline/repair; E=/root/retested-wiki/data/curated/review_evidence/2026-10-28; S=/root/wiki-scratch
mkdir -p $R/audit $R/merges $R/relinks $R/reading $R/helpers $E
cp $S/audit_20261028/{audit.py,compare.py,identity_check.py,fetch_all_papers.py,fetch_meta.py,fetch_abstracts.py,write_openalex_meta.py,reading_set.py,probe.py} $R/audit/
cp $S/link_fix_20261028/{gap.py,gap2.py,gap3.py,famous_candidates.py,merge_layout.py,merge_decisions.py,rekey_by_id.py,reconcile_ids.py,check_registry.py,run_ledger.py,rr_pairs.py,feeds_cover.py} $R/merges/
cp $S/relink_20261028/{lookup.py,lookup2.py,layout.py} $R/relinks/
cp $S/reading_20261028/{questions.py,build_items.py,run_reading.py,consensus.py,crossref_refs.py,fetch_missing.py,keep_running.sh,ADJUDICATION_BRIEF.md,STATUS.md} $R/reading/
cp $S/helpers_20261028/make_layouts.py $R/helpers/
cp $S/helpers_20261028/{dup_decisions.txt,attempt_decisions.txt,dq_decisions.txt,same_title_decisions.txt,shared_owner_decisions.txt,line_outputs_17.json,data_questions_raw.txt} $E/
cp $S/relink_20261028/decisions.txt $E/relink_decisions_pass1.txt; cp $S/relink_20261028/decisions2.txt $E/relink_decisions_pass2.txt
cat $S/reading_20261028/adjudicated_batch*.txt > $E/reading_splits_decided.txt
cp $S/reading_20261028/ADJUDICATION_BRIEF.md $E/reading_splits_brief.md
for f in $S/reading_20261028/answers/*.jsonl; do gzip -c "$f" > "$E/reading_answers_$(basename "$f" .jsonl | tr '#' '_').jsonl.gz"; done
gzip -c $S/reading_20261028/items.jsonl > $E/reading_items.jsonl.gz
echo copied

# --- the afternoon and evening of 28 Oct 2026: the review queue read, open full text read, cases decided
mkdir -p $R/queue $R/fulltext $R/cases $R/lines
cp $S/queue_20261028/{fetch_abstracts.py,build_items.py,run_reading.py,questions.py,consensus.py,settle_all.sh,make_batch.py,keep_running.sh,ADJUDICATION_BRIEF.md,author_check.py,mismatch_cases.py,MISMATCH_BRIEF.md,numbers.py} $R/queue/
cp $S/fulltext_20261028/{availability.py,fetch_fulltext.py,fetch_round2.py,build_items.py,run_reading.py} $R/fulltext/
cp $S/cases_20261028/{make_cases.py,apply.py,BRIEF.md,NULL_BRIEF.md} $R/cases/
cp $S/lines_20261028/BRIEF.md $R/lines/BRIEF.md
cp $S/queue_20261028/adjudicated.txt $E/queue_splits_decided.txt
cp $S/queue_20261028/ADJUDICATION_BRIEF.md $E/queue_splits_brief.md
cp $S/queue_20261028/mismatch_decisions.txt $E/queue_mismatch_decisions.txt
cp $S/queue_20261028/MISMATCH_BRIEF.md $E/queue_mismatch_brief.md
cp $S/fulltext_20261028/adjudicated.txt $E/fulltext_splits_decided.txt
cp $S/cases_20261028/null_decisions.txt $E/null_decisions.txt
for f in $S/queue_20261028/answers/*.jsonl; do gzip -9nc "$f" > "$E/queue_answers_$(basename "$f" .jsonl | tr '#' '_').jsonl.gz"; done
for f in $S/fulltext_20261028/answers/*.jsonl; do gzip -9nc "$f" > "$E/fulltext_answers_$(basename "$f" .jsonl | tr '#' '_').jsonl.gz"; done
gzip -9nc $S/queue_20261028/items.jsonl > $E/queue_items.jsonl.gz
# the full-text items hold long excerpts of papers whose licences do not all allow republishing: they stay on the host,
# in /root/wiki-scratch/fulltext_20261028/ (items.jsonl and text/), and are not copied into the public repository
echo copied the queue, full-text and case records
