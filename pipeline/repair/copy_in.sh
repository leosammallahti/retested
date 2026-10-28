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
