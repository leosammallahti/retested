# U1 — FReD-expansion HARVESTER sub-project: understanding report

Status: COMPLETE. All numbers below were verified by reading files / running pandas on 2026-09-07.
Project root: C:\Users\OMISTAJA\PsychologyReplication (all paths below relative to it unless absolute).
Author: subagent U1.

---

## 0. Inventory (verified via ls / wc)

Scripts (line counts): harvest_crossref_replications.py 999 (main), simple_replication_search.py 153, expanded_search_queries.py 59 (never imported by anything — a dead "demonstration" list), run_all_searches.py 98, harvest_multiple_years.py 113 (never run: no per-year outputs other than 2021), harvest_2021_comprehensive.py 55, compare_search_strategies.py, check_search_progress.py, check_results.py, fetch_all_abstracts.py 332, fetch_study_metadata.py 267, verify_quality.py 211, filter_high_confidence.py 119, check_duplicates.py 191, create_final_2021_dataset.py 122, merge_crossref_outputs.py 119, expand_replications_crossref.py 376 (early v0, offset paging, no year filter), collect_citations.py 317, collect_citation_dois.py 204, openalex_utils.py 80.

Docs: README.md 778, PROJECT_STATUS.md 396, TECHNICAL_REFERENCE.md 490, SEARCH_EXPANSION_SUMMARY.md 72, ENRICHMENT_COVERAGE_README.md 460, START_HERE.md, QUICK_START.md, research_agent_prompt.md (a *data-source discovery* prompt, not the harvester spec).

output/ (all dated 2026-01-04): crossref_replications_2021.csv (96 rows), crossref_replications_2021_filtered.csv (75), crossref_replications_2021_comprehensive.csv (52), crossref_replications_2021_expanded.csv (0 rows, header only), crossref_new_papers_2021.csv (96, identical to raw), simple_replications_2021.csv (1,024), simple_replications_2021_psych_only.csv (53), test_improved_2021.csv (14), test_keywords_2021.csv (44), final_2021_psychology_replications.csv (125), crossref_state_2021*.json (3 state files + a stray .tmp), tmp_issn*.csv (scratch).
logs/: crossref_2021.log, crossref_2021_issn.log, crossref_2021_expanded.log (UTF-16 encoded — PowerShell redirection), crossref_2021_comprehensive.log (UTF-8, ends in a Python traceback), test_2021.log (empty).
Side files in root used by the harvester: crossref_issn_whitelist_from_fred.csv (285 ISSNs ranked by frequency in legacy FReD BibTeX), forrt_fred_data.csv, fred_enriched.csv (legacy FReD 4,376 rows), fred_main_database.csv, psychology_replications.csv.

The whole harvesting sub-project was executed in a single session on 2026-01-04 between 02:17Z and ~03:07Z (per log timestamps). Everything after that is documentation written in anticipation of scaling that never happened.

---

## 1. Architecture of the main script (harvest_crossref_replications.py)

Pipeline per year:
1. Build an ISSN whitelist from legacy FReD BibTeX fields (`bibtex_ref_r`/`bibtex_ref_o` in forrt_fred_data.csv), rank by frequency, keep those with count >= 2, drop PLOS ONE (1932-6203) and Scientific Reports (2045-2322) as "too broad", truncate to `--max-issns` (80/120/150 were used).
   Top of the whitelist: 1467-9280 Psych Science (186), 1095-9203 Science (141), 2054-5703 Royal Society Open Science (137), 0022-3514 JPSP (104), 1091-6490 PNAS (54), 2397-3374 Nature Human Behaviour (48), 0022-1031 JESP (39), 2515-2467 AMPPS (39), 1878-5166 (38), 0278-7393 JEP:LMC (31) ...
2. Build "jobs" = (query_title phrase) x (ISSN) for `scope: issn` specs, plus a few `scope: global` specs.
3. For each job: Crossref `/works` with `query.title=<phrase>`, `filter=type:journal-article,from-pub-date:YYYY-01-01,until-pub-date:YYYY-12-31[,issn:X]`, `rows=100`, `cursor=*` deep paging, `select=` a minimal field list, `mailto=` set; User-Agent "PsychologyReplicationHarvester/1.0 (mailto:leosammallahti@gmail.com)".
4. For each item: normalize DOI, skip if already in FReD or output; (optionally) fetch OpenAlex `/works/doi:<doi>?select=id,doi,title,publication_year,primary_location,concepts,abstract_inverted_index` and compute a "psychology score" = max concept score over 10 named psychology concepts; reject if < `--min-psych-score` (0.25/0.30). Fill abstract from Crossref JATS (tags stripped) or reconstructed OpenAlex inverted index; truncate abstract to 500 chars (!).
5. Apply `looks_like_replication_study(title, abstract)` heuristic; extract `original_study` by regex; infer `replication_success` by keyword lists; append row to CSV; checkpoint job cursor to state JSON via atomic tmp+os.replace.

Output schema: title, doi, journal, year, url, authors (first 3), abstract (<=500 chars), original_study, replication_success, source_query, source_scope, source_issn, openalex_psych_score.

---

## 2. Which searches were ACTUALLY run (from state files + logs), vs. what the docs claim

| Run | Config (from log) | Jobs | Scanned | Kept | Result |
|---|---|---|---|---|---|
| crossref_2021.log (02:17Z) | 5 global queries only (rrr, many_labs, reproducibility_project, direct_replication, conceptual_replication), openalex on, 200 rows/job cap | 5 | 1,000 | 64 | first 64 rows of crossref_replications_2021.csv |
| crossref_2021_issn.log (02:31Z) | 80 ISSNs x 6 title phrases (rrr_pops, preregistered_replication, replication_of, replication_and_extension, many_labs, ...) openalex off for ISSN scope | 481 | 1,179 | 32 | appended -> 96 rows total; state file crossref_state_2021.json: 486 jobs, all done, scanned 2,179, kept 96 |
| crossref_2021_expanded.log (02:56Z) | 120 ISSNs, 2,524 jobs | 1 done | 3 | 0 | **Died after the first job** (state file has 1 job). CSV is header-only. Docs call this "running in background". |
| crossref_2021_comprehensive.log (02:56Z–03:07Z) | 150 ISSNs, --openalex-mode all, min score 0.25, 3,157 jobs | 403/3,157 done (12.8%) | 613 | 45 (52 in CSV) | **Crashed** with `PermissionError: [WinError 5] Access is denied: ...json.tmp -> ....json` in atomic_json_dump (os.replace on Windows while another process held the file). Cause: harvest_2021_comprehensive.py started it, then run_all_searches.py *re-launched* a second process on the same state file ("resume if state exists"), so two writers raced on the same JSON. |
| simple_replication_search.py | 8 free-text `query=` searches, offset paging, 500 max/query | — | ~4,000 | 1,024 | simple_replications_2021.csv; then filtered (by an ad-hoc step that is not in any script: `psych_only` appears only in file names) to 53 |

Per-query yields in crossref_state_2021.json (scanned -> kept): preregistered_replication 185 -> 29; conceptual_replication 438 -> 24; rrr(global) 200 -> 19; direct_replication 525 -> 18; reproducibility_project(global) 200 -> 4; replication_and_extension 191 -> 2; many_labs 269 -> 0; replication_of 168 -> 0 (!); rrr_pops 3 -> 0.
Note "replication_of" — the single most productive phrase in the free-text search (589 of 1,024 simple hits) — yielded 0 keeps in the ISSN run, which shows the ISSN-scoped run was extremely narrow (Crossref `query.title` is a relevance search, not phrase match, and the 80 whitelisted journals published few such titles in 2021).

The ~70-entry DEFAULT_QUERY_SPECS now in harvest_crossref_replications.py ("PHASE 1 ADDITIONS": grammatical forms, fMRI/EEG/longitudinal/cross-cultural/workplace replication, validation study, robustness check, ...) was added AFTER the runs and has never been executed. The comprehensive run used ~28 specs (3,157 = 1 + 21x150 + 6 global).

`final_2021_psychology_replications.csv` = union of filtered (75) + simple psych_only (53 -> 44 new) + comprehensive (52 -> 6 new) = 125 rows, deduped on lowercase DOI.

---

## 3. Precision / recall evidence

### 3.1 What the docs claim
"94% precision", "99.2% new to FReD (124/125)", "1,500–2,000 papers expected across 2012–2025". None of these was measured against a labelled set. The 94% figure has no computation behind it anywhere in the code (verify_quality.py only counts rows passing the same heuristic that produced them — circular). "124 new" was measured against the *legacy* FReD snapshot (fred_enriched.csv, doi_replication column).

### 3.2 My precision judgement of final_2021_psychology_replications.csv (125 rows)
Random 30-row sample (random_state=42) judged from title+abstract: 20 genuine empirical replication attempts in psychology/behavioural science, 1 borderline (SSRN "systematic replication of clinical cases"), 9 not (a citation-pattern meta-study, a Bayes-factor methods paper, a corrigendum, a "Supplemental Material" stub DOI, an Academia Letters piece on rural prosperity in India, an editorial, two essays on replication in CSR/public administration, "Saving Science Through Replication Studies", a clinical-trial protocol). => ~67-70% precision on the sample.

Full-list judgement (all 125 titles read): 39 rows are not replication attempts:
- Bio/medical/non-psych false positives (5): Nature retraction note on epistasis (#65), Cancer Research "replication stress" abstract (#75), Trends in Cancer (#98), COVID replication inhibitors (#88), AIDS/HCV replication (#109), plus Pan African Medical Journal GIS (#117), JMIR social-media manuscript collaboration (#97).
- Non-article DOIs (7): "Supplemental Material for ..." (#49, #53, #73, #80, #90, #119), Corrigendum (#42), Correction (#22).
- Essays / commentaries / meta-science about replication (~25): #10, #14, #18, #40, #41, #51, #78, #79, #83, #84, #86, #89, #92, #94, #96, #101, #102, #105, #108, #112, #113, #116, #118, #76.
=> ~86/125 (69%) genuine. By source: Crossref Filtered 63/75 (84%), Simple Search Psychology 18/44 (41%), Comprehensive 5/6.
The good part of the list is genuinely good (e.g. registered direct replication of Zmigrod 2019; multi-lab non-replication of the ACE; Southgate/Senju/Csibra 2007 two-lab replication; Fernbach et al. 2013 three failures; Gebauer et al. 2018 direct replications; Flavell 1966 multilab; Stern/West/Schmitt 2014; Medvec 1995 Olympic medalists; Boivin 1995 quasi-replication; Luria 1976 illiterates).

### 3.3 Overlap with CURRENT FLoRA (data/raw/forrt/fred-data/output_flora.csv, 2,815 rows)
DOI normalisation: lowercase, strip https://(dx.)doi.org/ and "doi:", strip trailing period.
- 24/125 final DOIs are already in FLoRA `doi_r` (19.2%); 1/125 in `doi_o`. Of the 24: 21 came from FLoRA source "replications" (FORRT's curated sheet), 3 from FLoRA source "openalex". Outcomes of those 24 in FLoRA: mixed 10, successful 8, failed 6 — so ~all 24 overlaps are real replications (a useful confirmed-positive subset). 21 of the 24 were from the "Crossref Filtered" source, 3 from Simple Search.
- Against the legacy FReD (fred_database_english.csv, 4,376 rows) only 1 overlaps — consistent with the docs' "124 new". FORRT has since added most of the good 2021 finds itself.

### 3.4 RECALL against FLoRA ground truth (the number the old project never computed)
FLoRA contains 140 unique replication papers (type=replication) with year_r=2021 (sources: replications 87, COS 29, openalex 23, openalex_snapshot 1). The harvester found 24 of them => **recall = 17.1%** for the one year it did.
Why the misses: (a) journal not on the ISSN whitelist (PLOS ONE deliberately blacklisted — 6 misses; OSF Registries 4; J Applied Econometrics 4; AIS Transactions on Replication Research 3; J Economic Psychology 3; Meta-Psychology 2; Collabra 2 ...), (b) phrase not in title ("Revisiting ...", "Rethinking ...", "Testing ...", "Absence of a bilingual advantage ..."), (c) the global searches were capped at 200 results each, (d) the two broader runs died.
Title-signal ceiling: across ALL 1,865 unique FLoRA replication papers, only 64.9% have "replicat" anywhere in the title; only 36.1% match the harvester's STRONG_REPLICATION_TITLE_PHRASES and 33.9% pass looks_like_replication_study(title, "") with no abstract. For 2021 specifically: 99/140 (70.7%) contain "replicat", 63 match strong phrases, 61 pass the classifier title-only. => A title-phrase strategy can never exceed ~65-70% recall, and the implemented one caps at ~35% even with perfect journal coverage.

### 3.5 Classifier bug with measurable damage
NON_PSYCH_REPLICATION_TERMS uses bare substring matching on title+abstract: "rna" matches "inte**rna**lizing"/"jou**rna**l", "gene" matches "**gene**ral", "cell" matches "ex**cell**ence", "viral" matches "**viral**" only but "gene"/"genetic" hits "gene**ral**ization". Running the term list over FLoRA's 1,865 replication titles rejects 151 (8.1%) genuine replications (e.g. "Trajectory of externalizing child behaviors in a KEEP replication", "...reciprocal internal/external frame of reference model", "digital technology use ... internalizing symptoms ... replication and extension"). Any port must use word-boundary regexes and collocations ("dna replication", "viral replication", "replication fork").

### 3.6 Other heuristic fields
- `replication_success`: 80 "unclear", 1 "mixed", 44 NaN (rows from simple search have no such column). Effectively useless — keyword lists on a 500-char truncated abstract.
- `original_study`: populated for 44/125 but values are regex tails like "their study 1", "existing research is often referred to as one of the cornerstones of modern scie", "previous investigations". Only the "X et al. (YYYY)" forms are useful.
- Abstract present for 71/125 (Crossref JATS coverage is ~36-57% in this domain; the OpenAlex inverted index fills most of the gap when fetched).

---

## 4. API etiquette / rate-limit / paging lessons (verified in code + logs + ENRICHMENT_COVERAGE_README.md)

Crossref
- Use `cursor=*` deep paging (not `offset`; offset is capped and unstable) and persist `next-cursor` per job; stop when items empty or next-cursor repeats.
- Always send `mailto=` AND a User-Agent with mailto (polite pool). `select=` to cut payload. `rows=100` max. 0.5 s delay between pages worked with zero 429s in ~1,300 pages. Exponential backoff on 429/5xx (base 0.8 s, 6 tries).
- Crossref has NO subject filter on /works — hence the ISSN whitelist + OpenAlex-concept gating.
- `query.title` is relevance-ranked fuzzy search, not phrase match: results include anything whose title tokens overlap, and the tail is noise. Per-job scan caps are needed, but capping the *global* jobs at 200 threw away recall.
- `filter=from-pub-date/until-pub-date` slices by *any* published date; `year` sanity-check still needed (verify_quality found 100% correct for 2021).
- Crossref abstracts are JATS XML; strip tags. Abstract coverage ~36% (n=50 legacy test) / 57% in 2021 harvest.
- Supplementary-material DOIs (APA `*.supp`), corrigenda, retraction notes and "Response to"/"Commentary on" pieces come back as `type:journal-article` — must be filtered by title prefix and/or Crossref `subtype`/`update-to` fields.

OpenAlex
- `/works/doi:<doi>` with `select=` (id, doi, concepts, topics, abstract_inverted_index, primary_location, open_access ...). URL-encode the DOI (openalex_utils.openalex_work_url_for_doi does `quote(doi, safe='')`). ~10 req/s with mailto; 0.12 s delay used. 100k/day.
- Concept scores: the "psychology" concept threshold 0.30 produced mean 0.58 (min 0.31) over kept rows. Note: OpenAlex `concepts` are deprecated in favour of `topics` (domain/field/subfield); fetch_study_metadata.py and analyze_openalex_topics.py already switched to topics; the harvester still uses concepts.
- Abstract must be rebuilt from `abstract_inverted_index` (sort by position). OpenAlex filled 16.4% of abstracts missing from PubMed/Crossref in the legacy enrichment (1,632 DOIs: 87% any-text coverage: PubMed 55%, OpenAlex 16%, Crossref 13%, S2 TL;DR 2%).
- Citation graph: `filter=cites:<W-id>&per_page=200&cursor=*` for citing works; `filter=openalex_id:W1|W2|...` (batch 50) to resolve referenced_works to DOIs. collect_citation_dois.py ran 10 threads; research_agent_prompt.md records the result: 68K references, 354K citing papers for ~1,600 originals (citation_data.json 29MB, citation_dois.json).
- OpenAlex found 98.3% of legacy FReD original DOIs (1,596/1,623).

Other services (ENRICHMENT_COVERAGE_README.md): PubMed e-utils 3 req/s no key (50% abstract hit for FReD originals; structured abstracts need Label handling); Semantic Scholar 100 req/5 min unkeyed (TL;DR 52%, SPECTER embeddings ~55%); OpenCitations moved to https://w3id.org/oc/index/coci/api/v1/citations/{doi} (old opencitations.net endpoint returns HTML); Altmetric now requires an API key (403 since 2025-11-10); Unpaywall rejects placeholder emails (422) — use the real owner email; CORE full text ~20%; OSF API v2 nodes/registrations — FReD-linked OSF registrations use the "Replication Recipe (Brandt et al. 2013)" schema with item30-item37 = effect size, CI, comparison, success judgement, interpretation, limitations (a rich structured source nobody has mined).

Process/Windows lessons
- PowerShell `>` redirection produced UTF-16 logs; use `python -X utf8` / PYTHONIOENCODING=utf-8 and open files with encoding='utf-8'.
- Atomic `os.replace` fails with WinError 5 when another process (or an AV/indexer, or a second launcher) holds the target; never allow two processes to share a state file; lock or use per-process state files.
- Deprecated datetime.utcnow() warning on Python 3.13 (already fixed in code).
- State files grew to 800KB because they hold a per-job dict for thousands of (phrase x ISSN) jobs — the job explosion (queries x ISSNs = 3,157 HTTP jobs per year) is the real reason the runs never finished, not API limits: 21 phrases x 150 ISSNs each returning 0-3 items is a terrible query plan; Crossref lets you OR ISSNs in one filter? No — but you can drop the ISSN loop entirely and post-filter on ISSN/OpenAlex instead (1 query per phrase per year, deep-paged).

---

## 5. Heuristics / lists worth porting (with fixes)

Keep (after cleanup):
1. `normalize_doi` in openalex_utils.py (handles doi:, dx.doi.org, [Opens in new window], trailing punctuation, percent-decoding, regex extraction) — the best of the four DOI normalisers scattered across scripts. Port this one only.
2. STRONG_REPLICATION_TITLE_PHRASES (harvest_crossref_replications.py ~L188): "replication of", "replication and extension", "direct replication", "conceptual replication", "replication attempt", "replication note", "registered replication report", "preregistered replication", "pre-registered replication", "many labs", "multi-lab replication", "failed to replicate", "attempted to replicate", "non-replication", "nonreplication". Add from evidence in FLoRA-missed titles: "replication study", "replicating", "replications of", "a replication", "quasireplication", "constructive replication", "revisiting", "reanalysis"/"reproduction" (FLoRA type=reproduction), "does X replicate", "registered report".
3. META_REPLICATION_TITLE_KEYWORDS + filter_high_confidence.is_meta_policy_paper list ("replication crisis", "how (not) to measure", "assessing/measuring/quantify replication", "replication success metric(s)", "simulation study", "saving science", "reconsidering", "survey on attitudes", "registered report protocol", "is replication relevant for ...") — plus, from my review: "the role of replication", "replication is important", "understanding replication", "why did it take", "framework for classifying", "lessons from replication", "citation patterns", "prevalence of", and the non-article prefixes "supplemental material for", "corrigendum", "correction to", "retraction note", "response to", "commentary on", "reply to", "erratum".
4. NON_PSYCH terms — only as word-boundary regexes and collocations: r"\b(dna|rna|mtdna|viral|virus|plasmid|chromosom\w*|telomer\w*|polymerase|replicon|replication fork|replication stress|origin of replication|genome|cell cycle|database replication|data replication|distributed replication|replica placement|blockchain)\b". Never bare "gene", "cell", "rna".
5. First-person attempt phrases for abstracts ("we conducted", "we attempted to replicate", "we report a (direct|close|conceptual) replication", "this study replicat", "in a preregistered ...") and the success/failure/mixed cue lists — as *features* for an LLM/ML classifier, not as the decision rule.
6. `extract_original_study_hint` regexes — only the variant that captures "Author(s) et al.? (YYYY)" patterns; wire it to Crossref `reference` list / OpenAlex `referenced_works` to resolve the cited original DOI (the actual FLoRA key `doi_o`).
7. The ISSN-frequency idea (journals that already publish replications) — but computed from CURRENT FLoRA `journal_r` -> ISSN via Crossref /journals, and used as a *ranking/prior feature*, not as a hard search scope; and never blacklist PLOS ONE / Royal Society Open Science / Scientific Reports (they are top replication venues in FLoRA).
8. OpenAlex psychology gate — reimplemented on `topics` (field = Psychology, or subfield list) with the score as a feature; keep threshold ~0.3 for concepts if used.
9. Checkpoint pattern (per-job cursor + atomic write + resume by reading output DOIs) — good, but one state file per process.
10. Multi-source abstract cascade (PubMed > Crossref > OpenAlex > S2 > TL;DR) and its measured coverage numbers — reuse for the wiki's paper pages.
11. The OSF "Replication Recipe" registration schema mapping (item30-item37) as a structured extraction target.

Discard: expand_replications_crossref.py (offset paging, no year filter, `.title()`-cased "original study" strings, "algorithm/network/ai" substring exclusions), simple_replication_search.py's free-text `query=` approach (86% noise), the (phrase x ISSN) job explosion, `replication_success` keyword inference, the 500-char abstract truncation, the 3-author truncation, expanded_search_queries.py (dead code), all docs' throughput/precision claims.

---

## 6. What was fundamentally wrong

1. **No ground truth, no evaluation loop.** The project had FReD/FLoRA on disk — a labelled set of ~1,900 replication papers with DOIs — and never used it to measure recall of any query or the classifier. One 20-line script (Section 3.4) shows the strategy tops out at ~35% recall by construction and achieved 17% for 2021. All "precision 94%" / "1,500-2,000 papers" numbers are fiction.
2. **Wrong unit of work: paper-level "is this a replication?"** instead of the pair (replication paper -> original paper -> effect). FLoRA's key is (doi_o, doi_r, outcome). The harvester never attempted to identify the original study beyond a regex tail, so even its good hits are not FLoRA-ingestible without manual work.
3. **Title-phrase search as the discovery primitive.** 35% of true replications have no "replicat*" in the title. Better primitives exist and were even listed in the README "Future Directions" but never tried: (a) citation-graph: works that cite a FLoRA original AND use replication language in the abstract/full text; (b) OpenAlex full-text/abstract search (`search=` / `filter=abstract.search:` / `fulltext.search`) rather than Crossref title search; (c) venue-native feeds: Registered Reports (Crossref `type`/`subtype`, OSF Registries, PCI RR), Meta-Psychology, Collabra, AMPPS, JDM, "AIS Transactions on Replication Research", Journal of Numerical Cognition replication section, Psych Science Accelerator, CREP, ManyBabies/ManyLabs/RRR OSF projects, Data Replicada, I4R/Journal of Applied Econometrics replication section, Economics replication (Critical Finance Review, Economics e-journal); (d) OSF registrations with the Brandt "Replication Recipe" schema; (e) FORRT's own openalex source in FLoRA (23 of the 140 2021 papers came from it) — reuse/extend the FORRT pipeline (pipelines_flora_prepare_flora.qmd) instead of competing with it.
4. **Query plan explosion**: 21 phrases x 150 ISSNs x 14 years = ~44,000 Crossref jobs, most returning 0-3 items, for a domain where a single deep-paged Crossref/OpenAlex query per phrase-year returns everything in minutes.
5. **Substring classifier bugs** (Section 3.5) silently discard ~8% of true positives; supplemental/corrigenda DOIs pass as papers.
6. **Operational sloppiness**: two processes on one state file -> crash; the "expanded" run died after job 1 and nobody noticed; docs written for a state that was never reached; logs in UTF-16; results (125 rows, 69% precision, 17% recall for one year) presented as "Phase 1 complete, foundation solid".
7. **Ignored the deliverable format**: no fields for doi_o, outcome evidence quote, effect sizes, or the FLoRA `outcome_quote_source` conventions; nothing could be contributed back to FORRT.

---

## 7. Concrete facts for the new discovery pipeline design

- Ground truth for evaluation: FLoRA 2,526 replication rows -> 1,865 unique doi_r; 140 for year 2021; per-source title-signal rates: replications 66%, COS 64%, openalex 56%.
- The 24 harvester DOIs already in FLoRA + the ~62 other genuine 2021 finds not in FLoRA (Section 3.2 list minus the 39 non-genuine minus the 24 overlaps) are a ready-made *human-review queue seed*: e.g. 10.1111/lcrp.12201 (Zmigrod 2019 registered direct replication), 10.1177/0956797621989733 (multisite ego-depletion), 10.1016/j.cortex.2020.12.024 (dyslexia neural entrainment conceptual replication), 10.1027/1864-9335/a000448 (Stern/West/Schmitt 2014), 10.1016/j.jenvp.2021.101709 (simulated nature / attention network), 10.3389/fnhum.2021.680885 (failed replication of Mager et al. 2009), 10.1037/dev0001186 (stereotype threat, Italian girls), 10.1016/j.cognition.2020.104521 (approximate arithmetic training failure to replicate). Counter-example that must NOT enter the queue: 10.1177/09567976211005767 (citation-pattern meta-study). File: output/final_2021_psychology_replications.csv (keep as raw archive; do not trust its `replication_success`/`original_study` columns).
- Reusable code, by absolute path: C:\Users\OMISTAJA\PsychologyReplication\openalex_utils.py (normalize_doi, openalex_work_url_for_doi, save_json_atomic); harvest_crossref_replications.py functions `reconstruct_openalex_abstract`, `strip_jats`, `crossref_request_with_backoff`, `openalex_fetch_with_backoff`, `extract_issns_from_bibtex`, and the phrase lists at lines ~47-120 (DEFAULT_QUERY_SPECS) and ~150-215 (concept names, NON_PSYCH terms, STRONG phrases, META keywords); fetch_all_abstracts.py (`fetch_pubmed` with structured-abstract label handling, `fetch_semantic_scholar` tldr); collect_citation_dois.py (`get_citation_dois`: cites: filter paging + batched openalex_id resolution); crossref_issn_whitelist_from_fred.csv (285 ISSNs ranked; note it is derived from the *legacy* FReD BibTeX and mixes original and replication journals).
- ENRICHMENT_COVERAGE_README.md is the one document whose numbers are real (they came from actual n=50/100 and full-dataset runs in Dec 2025); README/PROJECT_STATUS/START_HERE/QUICK_START/SEARCH_EXPANSION_SUMMARY/TECHNICAL_REFERENCE are aspirational and internally inconsistent (TECHNICAL_REFERENCE documents functions like `search_crossref_cursor` and `fetch_openalex_for_doi` that do not exist in the code).
