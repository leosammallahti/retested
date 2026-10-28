# BRIEF: Psychology Replication Wiki — rebuild from scratch

Date: 2026-09-07. Owner: Leo Sammallahti (snasolid@gmail.com / leosammallahti@gmail.com).

## The ask (verbatim intent from the owner)

- "Build a wiki of psychological findings and replications." The existing folder is "a total mess"; ignore how it was built, think about how to do it in the best way possible.
- Download EVERYTHING FORRT publishes (FReD + FLoRA + codebooks + pipelines), organize it well.
- Keep a feature: "show a psychological study and the user guesses whether it replicated or not" (a guessing game). It does not exist in code yet; it is a required feature of the new build.
- "Find all the replications and organize them well. Then think about how we can extend this — how can we find more replications."
- Quality bar: "It shouldn't just be good. It should be fucking brilliant. Be clever, brilliant, fantastic. Brainstorm. Be creative. Not bare minimum."

## What exists on disk (C:\Users\OMISTAJA\PsychologyReplication)

### Root: three abandoned Python sub-projects (Dec 2025 – Jan 2026), ~200 files
1. **FReD-expansion harvester** (`harvest_crossref_replications.py`, `simple_replication_search.py`, `fetch_all_abstracts.py`, `verify_quality.py`, etc., docs: README.md, START_HERE.md, PROJECT_STATUS.md, TECHNICAL_REFERENCE.md, SEARCH_EXPANSION_SUMMARY.md, ENRICHMENT_COVERAGE_README.md). Searches Crossref/OpenAlex for replication papers per year. Got 125 papers for 2021 in `output/final_2021_psychology_replications.csv`, never scaled.
2. **Taxonomy/categorization experiments** (`test_taxonomy_v2.py` … `test_taxonomy_v17.py`, `create_taxonomy*.py`, `*_brief.md`, `v9_final_report.md`, `v16_failure_report.md`, `CATEGORIZATION_IMPROVEMENT_PLAN.md`, `taxonomy_*.json`, `cogatlas/`, `openalex_analysis/`, `emergent_clustering.py`, `hierarchical_clustering.py`, …). 17 iterations of LLM-prompted taxonomies of effects; never converged.
3. **Enrichment/citation analysis** (`citation_data.json` 29MB, `citation_dois.json`, `analyze_citations.py`, `citation_by_outcome_analysis.json`, `abstract_enrichment.json`, `openalex_original_enrichment_full.json` 40MB, `study_metadata.json`, `enrich_effect_names.py`, `canonical_effect_names.json`, `all_known_effects.txt`, `fred_per_effect.csv`, `fred_per_experiment.csv`, `fred_per_original_study.csv`, `replication_predictors_analysis.json`).
4. Data snapshots: `fred_database_english.csv/.json/.xlsx` (FReD legacy v1, ~2,990 rows, rich columns incl. es_original/es_replication/n_original/n_replication/outcome/result/discipline/tags/description/closeness_*/preregistration/power/orig_journal), `fred_replication_database.xlsx` (= OSF "FReD - legacy v1.xlsx", 5.5MB), `forrt_replications_reversals.csv/json`, `psychology_replications.csv/json`, `osc_2015_rpp_data.csv` (RP:P 2015), `ml4_full_data.csv` (Many Labs 4), `manybabies_mb1_data.csv`, `Psychology Replications (1).docx` (1.6MB hand-curated document) parsed into `docx_parsed_entries.json` = **362 hand-curated famous effects** with fields name/description/discipline/status(replicated|mixed|not replicated|reversed)/original_paper/critiques/original_es/replication_es — high value.
5. Research notes: `data_sources_analysis.md` (47 external data sources incl. LOOPR, OpenMKT, Data Replicada, XPhi, OSC2015, ML1-5, SSRP, RRRs), `replication_projects_reference.md` (Many Labs effect lists), `missing_studies_analysis.md`, `replication_projects_sources.md`.

### wiki/ : Astro 7 + Preact static site "Replication Families" (Aug 2026)
- `wiki/scripts/fetch-data.ts` downloads flora.csv, fred_effect.xlsx (BROKEN: OSF returned a 1x1 placeholder), codebook pdf, disciplines.json. `wiki/scripts/normalize-data.ts` builds a trivial `derived_db.json` (registry of 2,521 FLoRA rows; fred_effects EMPTY).
- Pages: index, explore (Fuse.js search), attempt/[id], paper/[id], family/[id] (one hand-curated JSON family: literary fiction → theory of mind), collections/[id] (placeholders "Data Pending"). `dist/` has 6,000 mostly-placeholder HTML pages.
- Design: warm off-white, serif headlines, "field guide" tone. Zod schemas in `src/lib/schema.ts` (Effect, Experiment, ReplicationFamily, Paper). No node_modules installed. No git repo.

### data/raw/forrt/ : fresh downloads made today (2026-09-07)
- `fred-data/output_FReD.xlsx` (current FReD, effect-level; 1.08MB), `output_flora.csv` (current FLoRA, 9.2MB, 2,815 rows: 2,526 replications + 289 reproductions), `output_flora_filtered.csv`, `output_flora_faq.md`, export/filter logs, `pipelines_fred_fred_codebook.xlsx`, `pipelines_fred_prepare_fred.qmd`, `pipelines_flora_prepare_flora.qmd`, README.md, CITATION.cff, API Integration Guide (DynamoDB/Zotero plugin), COS SCORE integration files.
- `fred-r-package/` : the FReD R package sources — `replication_outcomes.R` implements 7 success criteria (significance_r, significance_agg, consistency_ci, consistency_pi, homogeneity, homogeneity_significance, small_telescopes); `effect_size_transformations.R` converts d/r/eta etc.
- OSF project 9r62x also has: change_log.md, Sub-Datasets folder, Validation PDF, legacy v1 xlsx, explorer app.R, datastructure.png (downloaded to `data/raw/forrt/osf/` where possible).
- FORRT already provides online: FReD Explorer (Shiny), FReD Annotator (Shiny), Zotero "Replication Checker" plugin + DOI-hash API, an R package. License CC-BY / MIT.

## Key data facts
- FLoRA outcome distribution (2,521-row snapshot): successful 1,036, failed 890, mixed 557, other ~38. Sources: "replications" sheet 1,518, COS 716, openalex 184, SCORE 88. Years of replications run to 2026.
- FLoRA columns: doi_o, title_o, author_o (JSON), journal_o, year_o, apa_ref_o, doi_r, title_r, author_r, journal_r, year_r, apa_ref_r, oa_url_o/r, outcome, outcome_quote, outcome_quote_source, type (replication|reproduction), source, language, plus hash prefixes.
- FReD (effect-level) has per-effect rows: effect name, description, es_original, es_replication, n_original, n_replication, p-values, outcome, discipline, tags, closeness_* (instructions/measures/stimuli/procedure/location/renumeration/participants/exclusions/language/nationality), preregistration, power, ci bounds, osf_link, published_rep, same_design, same_test.

## Environment
- Windows 11, Node v22.15, npm 10.9, Python 3.13. No git repo yet in this folder. Supabase MCP is connected (usable for a hosted DB if the design wants one). Hugging Face MCP connected.
- Owner email for API mailto headers: leosammallahti@gmail.com.

## Non-negotiables for the new design
1. Reproducible one-command data build from FORRT sources (+ our own curated overlays). Never hand-edit generated files.
2. Effect/finding-centric wiki (not paper-centric), with paper/attempt/project/author/topic entry points.
3. The "did it replicate?" guessing game.
4. A credible, documented pipeline for discovering NEW replications beyond FORRT, with a human-review queue and a path to contribute back to FORRT.
5. A folder/repo structure that cannot rot into the current mess: clear layers (raw → normalized → curated → site), archival of the old junk, docs that stay true.
