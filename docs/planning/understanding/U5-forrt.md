# U5 — FORRT data reference (FReD + FLoRA + codebooks + pipelines + R package + OSF)

Written 2026-09-07 from the files in `C:\Users\OMISTAJA\PsychologyReplication\data\raw\forrt\` (MANIFEST.json lists every file with its source URL and sha256). Every number below was computed with pandas from the files on disk; nothing is taken from memory.

Directory layout (81 files, ~40 MB):
- `fred-data/` — mirror of GitHub `forrtproject/FReD-data` (output/, pipelines/, cos_score_integration/, API guide, archive/).
- `fred-r-package/` — R sources of GitHub `forrtproject/FReD` (v0.2.0).
- `osf/` — OSF project 9r62x downloads: change_log.md, NEWS.md, datastructure.png, fred_explorer_app.R (Shiny, v0.4.6 Feb 2024), flora_osf_2026-03-21.csv, success_criteria.Rmd, Replication_Project_Data_Validation.pdf, `sub-datasets/` (18 files), `version-history/` (5 xlsx), `registries-subproject/` (6 files).
- `osf/FReD_osf_2tbvd.xlsx` and `osf/wiki_home.md` are 332-byte HTML "502 Server Error" stubs, NOT data. Discard.

---

## 0. Executive findings (read this first)

1. **Two datasets, two grains.** `output_FReD.xlsx` is effect-level (2,164 rows = one row per original claim/effect x replication effect, 56 columns, with effect sizes, Ns, p-values). `output_flora.csv` is paper-level (2,815 rows = one row per (original paper, replication/reproduction paper) pair, 35 columns, no effect sizes, only a narrative `outcome`). FLoRA is the bigger, fresher, faster-growing table (FORRT's README update log: 1,126 rows on 2026-03-16 -> 2,815 on 2026-09-06; ~4 releases/week); FReD is the statistically rich one.
2. **The current FReD.xlsx is exactly the COS/SCORE-validated subset**, not the full crowdsourced database. `fred-data/archive/2025-11-30_COSdata_validated.xlsx` has the same 2,164 rows in the same order with identical `doi_o`/`es_value_o` (100% match) and adds columns the public output lacks: `r_o`, `r_r` (already converted to Pearson r: 839 / 1,002 non-null, 733 both), `statistical_success` (901 coded), `file_o`/`file_r` (PDF filenames), `fred_id_old`, `cos_phase1`. **Use the archive file as the primary effect-level source**; it is a strict superset of output_FReD.xlsx.
3. **The legacy crowdsourced FReD (OSF "FReD_2.4.1_2025-06-25.xlsx" = `sub-datasets/FReD_legacy_v1.xlsx`, both 4,661 x 100, 'Data' sheet, first 2 rows are English/German column descriptions -> 4,659 data rows) is NOT superseded.** Only 1,548 of the 2,164 current rows have their (doi_o, doi_r) pair in legacy; 3,234 legacy rows are absent from the current FReD (743 with validated==1; 362 with both es_original and es_replication in r). Legacy carries closeness_* (10 columns, ~175 rows), power (834), CI bounds (~880), osf_link (1,781), preregistration (808), effect name (2,623), result (1,427), orig_journal (2,089), contributors (2,873), source (4,296; ML1 352, OpAQ 479, Anna van 't Veer 351, OSC 2015 167, ML3 145, ...). Joining legacy -> current by normalized (doi_o, doi_r) works for 1,548 rows; joining by `fred_id` == legacy `id` stem gives 1,544 rows. Note legacy DOIs include uppercase and `doi.org/` prefixes; normalize (lowercase, strip prefix).
4. **FReD <-> FLoRA join**: 1,967 FReD rows have a DOI pair; 1,783 of them (678 of 745 distinct pairs) match a FLoRA (doi_o, doi_r) pair exactly; +4 via url_r fallback; +65 via FLoRA `alt_identifier_r` = 2,036 / 2,164 rows (94%). 2,080 FReD rows (746 of 786 distinct doi_o) have their original DOI in FLoRA. Outcome agreement on matched rows is 93.3% (disagreements: 68 FReD-failed rows are FLoRA-mixed, 48 FReD-successful are FLoRA-mixed — because FLoRA aggregates a multi-effect replication paper into one "mixed").
5. **`entry_id` in output_FReD.xlsx is broken: it is 1 for every row** (pipeline uses `first(row_number())` inside a group, which is always 1). Recompute entries yourself: grouping by (ref_o, study_o, ref_r, study_r) gives 1,003 groups; the COS archive file has a correct `entry_id` (1,004 distinct) and a per-entry `effect_id` (1..76). In output_FReD.xlsx `effect_id` is just the row number (1..2164).
6. **Forest-plot eligibility (FReD)**: 1,163 rows have numeric `es_value_o` AND `es_value_r`; 1,154 also have n_o and n_r. Applying the R package's conversion rules (d, r, r², OR, eta², f, f², and APA test statistics t/F(1,df)/z/chi²(1)) yields Pearson r for 1,286 originals and 1,272 replications, **1,061 both, 1,056 with both Ns** (by outcome: 448 failed, 442 successful, 159 mixed, 7 "stat. successful but flawed"). The archive file's precomputed r_o/r_r covers 733 pairs; my emulation covers more because it parses test statistics (505 of 758 "test statistic" originals parse). Non-convertible by design: beta (std) 151, b (unstd) 123, etasq (partial) 173, dz, cramer's V, cohen's h, semipartial r.
7. **FLoRA outcomes**: replication rows 2,526 -> successful 1,042 (41.3%), failed 901 (35.7%), mixed 564 (22.3%), statistically successful but flawed 7, descriptive only 6, uninformative 4, NA 2. Reproductions 289 -> 284 have NA outcome (reproduction outcomes were apparently not yet exported), 5 coded with the reproduction vocabulary ("computationally reproducible, robust", etc.). Non-English: 9 originals (de 3, fr 2, it/es/nl/pt 1 each), 4 replications (fr 2, de 1, nl 1); 337 replication rows lack language_r.
8. **License/citation**: CC-BY 4.0 for data (CITATION.cff: title "FORRT Library of Replication Attempts (FLoRA)", version 1.0.0, date-released 2026-01-13, doi 10.17605/OSF.IO/9R62X, ~200 authors; `output_citation.txt` is the ready-made APA string: "Wallrich, L.*, & Röseler, L.*, Hartmann, H., ... Azevedo, F. (2026). FORRT Library of Replication Attempts (FLoRA) [Data set]. OSF. https://doi.org/10.17605/OSF.IO/9R62X"). R package code: MIT. The Explorer FAQ says "please cite us if you use these resources".
9. **FORRT already ships**: Shiny FReD Explorer (Replicability Tracker w/ bar plot, RPP-style scatter, z-curve, forest plot, dataset download, correlates by decade/journal, moderator meta-regression, reference checker), FReD Annotator (web, forrt.org), a Zotero "Replication Checker" plugin backed by a DOI/hash API at `https://rep-api.forrt.org/v1` (endpoints `prefix-lookup?prefixes=abc` and `original-lookup?dois=10.x/y`, CORS-enabled, JSON with replications[]/originals[]/reproductions[] per DOI). None of these is effect-centric, none has a guessing game, none groups replications into families/effects, none has topic pages.

---

## 1. `fred-data/output_FReD.xlsx` — effect-level FReD (current public build)

Sheet "Sheet 1", 2,164 rows x 56 columns. Built by `pipelines_fred_prepare_fred.qmd` from a Google Sheet (published CSV, first row = descriptions, skipped) filtered to `status == "validated - chosen"` and `exclusion` empty, then DOI-normalized, IDs generated, augmented (CrossRef/DataCite refs + BibTeX, author overlap, OpenAlex language), joined to the "success coding" Google Sheet for `reported_success`, recoded to canonical outcome vocabulary, and column-selected. Source data = Google Sheets (URLs in the qmd), so the xlsx is the only stable artefact.

### 1.1 Column dictionary (dtype | non-null % | distinct | codebook definition | observed notes)

| column | dtype | non-null | nunique | definition (codebook) | observed |
|---|---|---|---|---|---|
| entry_id | int | 100% | **1** | consecutive number per replication reference; rows sharing it = same entry | BUG: always 1. Recompute. |
| effect_id | int | 100% | 2164 | consecutive number for rows within one entry | actually global row number 1..2164 |
| fred_id | str | 99.8% | 1116 | corresponding entry in FReD 1.0 (crowdsourced) | prefix families: additional_studies 351, Boyce_etal 280, av_ 165, add_ai 164, soscisubmission 125, CORE_ 114, OpenMKT 102, osc 99, curatescience 97, jcre_ 71, XPHI 69, Soto 60, Camereretal 39, ManyLabs/Manylabs 76, Arb 32, RRR_BrohmerHofer 30, Holzmeisteretal 26, FORRT_ 24, datareplicada 17, + ~150 random 4-char legacy ids (e.g. `zlBL_md`, `AqDO_single`). 831 fred_ids have 1 row, 285 have 2-12 rows. |
| ref_o | str | 100% | 786 | APA reference of original | CrossRef-generated (`&amp;` entities present) |
| doi_o | str | 100% | 786 | DOI of original, no prefix | lowercase; 2 non-DOI values (e.g. `scholars.indianastate.eduetds--2136`) |
| study_o | str | 80% | 42 | study number in paper | messy: "1", "1a", "Experiment 1", "Study 3", "1,3", "1b-1c", "1 (laboratory experiment)" |
| ref_r | str | 99.7% | 430 | APA reference of replication | |
| doi_r | str | 90.9% | 320 | DOI of replication | 197 rows lack doi_r; 190 of those have url_r. Some doi_r are pseudo-ids ("korbmacher_2022", "bischoff_ma_bms", "kontkanen_jaakko_thesis_2024") |
| url_r | str | 33.8% | 383 | link to results when no DOI or DOI is aggregate report | theses repositories, OSF, drive links |
| study_r | str | 69.2% | 122 | study number in replication | |
| author_overlap | float | 95% | 7 | codebook says TRUE/FALSE but data is a COUNT of shared authors | 0:1719, 1:148, 2:93, 3:67, 4:14, 5:7, 6:8 |
| author_overlap_pct | float | 95% | 27 | % of replication authors who are original authors (0 = independent) | |
| discipline | str | 99.8% | 40 (34 after lower/strip) | broad field | Social Psychology 643, Cognitive Psychology 439, Marketing 129, Psychology 109, Economics 104, Management 100, Experimental Philosophy 75, Differential Psychology 69, Education 62, JDM 48, Linguistics 47, Neuroscience 43, psychology 42 (case dup), Developmental 35, Communication Science 25, political science 21, Political Psychology 18, Medicine 17, Evolutionary Psychology 17, marketing/org behavior 17, sociology 16, economics 15, education 12, Clinical 8, Organizational 8, Consumer Research 6, health 5, NaN 4, Gender Stereotypes 4 (not a discipline), Consumer Psychology 4, Cognitive psychology 3, management 3, Human Genetics 3, Sports Science 2, Political Science 2, Psychopathology 2, Law 2, Social/cognitive psychology 2, Animal Psychology 1, Health Psychology 1, criminology 1. Needs a normalization map. |
| tags | str | 92.4% | 727 | comma-separated keywords | 2,253 distinct tags after lower/strip; top: open data 144, decision making 131, replication 130, judgment 124, open materials 118, humans 105, attention 83 ... (mix of PsycINFO-style and OpenAlex keywords; some are per-project boilerplate, e.g. 76 rows share 'rigid flexibility, manufacturing practice...' from a JOM project) |
| description | str | 90.6% | 1597 | description of the effect (x leads to y) | the closest thing to an "effect statement"; e.g. "The emotion associated with loss is more than the emotion associated with gain of the same magnitude" |
| claim_text_o | str | 98.5% | 1743 | verbatim key statistical result + interpretation | quotes with page refs — great for the guessing game card |
| claim_page_o | str | 99.1% | 361 | page(s) of claim | |
| n_o | float | 99.4% | 405 | original N for the critical test | |
| es_value_o | str/mixed | 95.7% | 1217 | numeric unless test statistic | numeric-parsable 1,318 rows; strings like "X2(1, N = 45) = 43.02", "F(1, 37) = 6.40", "F < 1", "binomial z = 2.94" |
| es_type_o | str | 96% | 43 | effect size type | test statistic 758, d 320, etasq (partial) 173, r 162, beta (std) 151, b (unstd) 123, etasq 120, OR 74, r-squared 42, ser_method 32, Cohen's f^2 19, Cohen's d 14 (dup of d), partial correlation 14, omega squared 9, Mean difference 8, hedges' g 7, ... |
| es_repr_o | str | 92.6% | 440 | where/how es was obtained ("p. 11, Table 1", formulas) | |
| pval_value_o | float | 92.5% | 302 | reported p | |
| pval_type_o | str | 92.5% | 8 | e/l/g/le/ge | 'l (<)' 1059, 'e (=)' 808, 'g (>)' 106, 'ge (>=)' 10, 'le (<=)' 8, '<' 8, '"="' 2, 'ge (>)' 1 -> normalize |
| pval_tails_o | str | 18.8% | 4 | 1/2/unknown | '2 (two)' 243, '2' 79, '1 (one)' 79, '1' 5 |
| nested_o | str | 92.5% | 2 | test accounts for dependence? | no 1348, yes 654 |
| prereg_o | str | 2.7% | 31 | prereg link of original | 58 rows |
| n_r | float | 99.4% | 612 | replication N | |
| es_value_r | mixed | 97.8% | 1251 | | numeric-parsable 1,636 |
| es_type_r | str | 98.2% | 46 | | d 510, test statistic 485, r 210, etasq (partial) 198, beta (std) 149, b (unstd) 136, etasq 103, ser_method 66, OR 51, r-squared 42, hedges' g 32, Cohen's f^2 20, cohen's h 19, semipartial correlation 14, ... meta-analysis 4, Bayes factor 2 |
| es_repr_r | str | 92% | 474 | | |
| pval_value_r | float | 92.7% | 681 | | |
| pval_type_r | str | 92.8% | 7 | | 'e (=)' 1218, 'l (<)' 619, 'g (>)' 143, 'ge (>=)' 19, '"<"' 7, '"="' 2, 'le (<=)' 1 |
| pval_tails_r | str | 26.4% | 3 | | |
| nested_r | str | 92.5% | 2 | | no 1357, yes 644 |
| prereg_r | str | 54.3% | 540 | prereg link of replication | 1,175 rows (OSF/AsPredicted links) |
| reported_success | str | 100% | 6 | narrative outcome by replication authors | successful 985 (45.5%), failed 787 (36.4%), mixed 359 (16.6%), statistically successful but flawed 18, descriptive only 10, uninformative 5 |
| reported_success_quote | str | 100% | 547 | outcome statement | one quote per replication paper (547 distinct) |
| reported_success_quote_source | str | 96.9% | 161 | | abstract 1073, a GitHub issue comment 153 (Boyce et al. student replications), "coding rule" 132 (SCORE-derived), OSF data files, page refs |
| title_o / author_o / journal_o / year_o / volume_o / issue_o / pages_o | | 100/100/100/100/98/88.6/96.5% | | CrossRef/DataCite | author_o is a JSON array `[{"given","family","sequence"}]`; journal has `&amp;`; year_o 1935..2024 (mode 2008:181, 2015:160, 2018:155; 17 rows 1946) |
| title_r / author_r / journal_r / year_r / volume_r / issue_r / pages_r | | 99.6/99.4/80.1/92/78/65/50% | | | journal_r NaN 431 (theses, OSF reports); Royal Society Open Science 283, Science 112, Psych Science 79, JOM 76, PNAS 71, AMPPS 70, RPP 69, Collabra 64 ...; year_r 1989..2026 (2024:395, 2023:324, 2025:144, 2026:1) |
| bibtex_o / bibtex_r | str | 100/99.6% | | BibTeX entries | |
| language_o / language_r | str | 99.2/90% | 1 | OpenAlex language | all 'en' in FReD |

### 1.2 Structure facts
- 786 distinct doi_o (originals), 320 distinct doi_r (+383 url_r), 1,116 fred_ids, 859 distinct (doi_o, doi_r) pairs, 1,003 entries by (ref_o, study_o, ref_r, study_r).
- Rows per original DOI: 435 have 1 row, 126 have 2, ..., up to 15. Replications per original (distinct doi_r): 627 originals have exactly 1, 41 have 2, 8 have 3, 3 have 4, 107 have 0 doi_r (url only).
- Outcome by discipline (lower-cased): social psychology 224 succ / 319 fail / 90 mixed; cognitive 241/130/70; management 100/3/0 (the JOM project — beware, almost all successful); psychology 76/59/16; experimental philosophy 56/17/1; differential psychology 49/0/19 (Soto Big Five); marketing 31/60/38; economics 26/24/69 (mixed-heavy); education 25/34/15; linguistics 15/26/0.
- reported_success is consistent within a DOI pair except 23 pairs (multiple effects with different outcomes within a paper are still given the paper's outcome... but 23 pairs show >1 value).

### 1.3 How IDs are generated (`pipelines_fred_prepare_fred.qmd`, Step 6)
```r
fred_id  = str_remove(id, "_[a-z]{1,2}$")   # strip per-effect suffix (_a, _b, _ab) from sheet id
effect_id = row_number()
entry_id = group_by(ref_o, study_o, ref_r, study_r) %>% mutate(first(row_number()))  # -> always 1 (bug)
```
Dedup/validation rules in the pipeline: filter `status == "validated - chosen"`; drop rows with any `exclusion`; DOI normalization = lowercase + strip `https://(dx.)doi.org/` + strip `doi:`; DOI format check (must start with "10."), only warns; the full validation module is "in progress" (a separate `archive/dataset_validation.Rmd` exists). reported_success join key = (doi_o, id_r = coalesce(url_r, doi_r), study_o, study_r) against the success-coding sheet, keeping rows where `validation != "validated - discarded"` and preferring "validated - chosen". SCORE rows (optional, `params$include_score`) get reported_success derived from `statistical_success` with quote source "coding rule". Outcome vocabulary is normalized by `R/outcome_vocabulary.R` (not on disk; canonical labels = successful, failed, mixed, uninformative, statistically successful but flawed, descriptive only + reproduction labels).

### 1.4 `pipelines_fred_fred_codebook.xlsx`
56 variable definitions (one sheet) — reproduced in the table above. Note the author_overlap definition (TRUE/FALSE) contradicts the data (count).

### 1.5 `fred-data/archive/2025-11-30_COSdata_validated.xlsx` (**use this**) and `archive/cos_codebook.xlsx`
2,164 x 44, identical rows/order to output_FReD.xlsx, plus: `fred_id_old` (1,732 distinct, e.g. `add_ai57_a`), `r_o` (839), `r_r` (1,002), `file_o`/`file_r` (PDF names like `10.1037--0003-066x.54.6.408.pdf`), `statistical_success` (1.0: 446, 0.0: 455, NA: 1,263), `cos_phase1` (True 132), correct `entry_id` (1,004) and `effect_id` (within-entry 1..76). Cross-tab statistical_success vs reported_success: stat=1 -> successful 344, mixed 73, failed 17; stat=0 -> failed 306, successful 78, mixed 70. Lacks the augmentation columns (title/author/journal/year/bibtex/language/author_overlap_pct) — take those from output_FReD.xlsx by row position or (doi_o, doi_r, effect order). cos_codebook.xlsx: 43 definitions matching these columns (fred_id_old: "less consistent version of fred_id - only to combine with earlier versions"). `cos_score_integration_cos_test_set_phase1.csv` (132 x 39) is the phase-1 SCORE test set with `claim_id`; `cos_score_integration_cos_score_references.xlsx` (124 rows: url, apa, bibtex) are manual refs for SCORE reports.

---

## 2. Legacy crowdsourced FReD — `osf/version-history/FReD_2.4.1_2025-06-25.xlsx` (= `osf/sub-datasets/FReD_legacy_v1.xlsx`, same 4,661 x 100)

Sheets: Data (4661x100), FORRT R&R (editable) (1406x73), Data (editable), Copy of Data (2188x74), Additional Studies to be added (476x15 and 210x13 — a to-do list of un-coded replications), File Links (2992x5), COS coding (2902x53), DOI_dedup (1689x2), Data validation, ES calculations, ORG - var renames (96x6 — old->new variable name map), Contributors FReD (193x47), Roadmap, Check regularly for Replication, Variables and Subdatasets, Key Variables (14 — the Explorer display set), **Reversals Effects (583x6: discipline, effect original, effect renamed, alternative names, description, status — the FORRT "Replications & Reversals" effect list, e.g. "Elderly priming", "Hostility priming (unscrambled sentences)")**, Meta-Analyses (WIP, empty).

Older versions on disk: ReD_2023-03-28 (1065x64), FReD_1.0.0_2024-02-08 (1904x74), 1.5.0_2024-06-30 (2337x80), 2.0.0_2024-10-18 (3660x80), 2.4.1 (4661x100). change_log.md says current version is 2.4.2 (2025-06-25); the legacy line was then frozen and replaced by the FReD-data pipeline.

'Data' sheet: rows 1-2 are English and German column descriptions (drop them). Key columns (non-null over 4,659 rows): `id` (3,443 distinct, e.g. xszk6), `rowid` (id_rownumber), `status` (1947 '2', 272 '1' + junk mime types in some rows — column misalignment in a few rows), `validated` (0: 1742, 1: 1140, 3: 693, 2: 78, NA 1006; 1 = validated OK), `validated_person`, `source` (34 values: FORRT 1229, OpAQ 479, Individual submissions 401+114, ML1 352, Anna Van 't Veer 351, CORE 223, Boyce_etal2023 176, OSC 2015 167, ML3 145, AI search 113, OSF Registries 97, Soto 74, AI screening 67, openmkt 50, XPHI 40, ML2 33, RRR1 29, RRR10 25, RRR9 23, RRR2 23, SSRP 21, datareplicada 19, RRR3 12, RRR Inclusive Language 12, RRR4 7, JCRe 6, CRSP special issue 4, RescienceX 1 ...), `discipline` (124 raw values), **`effect` (2,623 non-null, 443 distinct effect names — the only place FORRT names effects)**, `tags`, `description` (1,439 distinct), `es_original`/`es_replication` (Pearson r, 1290/1240 non-null), `n_original`/`n_replication` (2806/2757), `ref_original`, `doi_original` (1,698 distinct), `study_original`, `ref_replication`, `doi_replication` (1,348 distinct), `es_orig_value`/`es_orig_estype`/`es_rep_value`/`es_rep_estype` (raw ES; types d 1110, hedges' g 267, r 208, etasq 67, f 29, OR 21, Cohen's h 16 ...), `teststatistic_orig/rep`, `osf_link` (1,781), `outcome` (694: "signal - consistent", "no signal - inconsistent", "(imprecise)" variants — LeBel et al. 2018 framework), `result` (1,427: success / informative failure to replicate / practical failure to replicate / inconclusive / "sucess" typo), `published_rep` (0/1/2/3/Yes), `same_design`, `same_test`, `nesting`, `original_authors` (0/1), `preregistration` (808), `closeness_instructions/measures/stimuli/procedure/location/renumeration/participants/exclusions/language/nationality` (~165-180 rows each; values 1-5 on the Brandt et al. 2014 replication-recipe scale; datasubmission_template.xlsx closeness_scoring: exact=2, close=1, different=-1 summed), `differences` (free text), `vi_orig/rep`, `ci.lower/upper_original/replication` (~880/828), `significant_original/replication`, `power` (834), `orig_journal` (2,089), plus `Unnamed: 91..99` overflow columns.

**Join to current**: normalize both sides' DOIs (lowercase, strip doi.org prefix). 1,548 current rows match a legacy (doi_original, doi_replication) pair; 1,425 legacy rows match a current pair. Recoverable for matched rows: closeness_* ~160 rows, power 565, CI bounds ~565, osf_link 751, preregistration 205, same_design 243, effect name 794, result 884, orig_journal 957, contributors 871. **Beyond recovery, legacy contributes 3,234 rows not in current FReD** (FORRT 961, OpAQ 477, Anna van 't Veer 286, CORE 204, Individual submissions 280, AI search 113, ML1 107, OSF Registries 88, OSC 2015 70, Boyce 68, AI screening 50, RRR1/2/9/10 100, ...) — 743 validated==1 and 362 with r-scale ES for both. Caveat: FORRT R&R rows (source FORRT, from `231026_forrt_with_journals.xlsx`, 1,296 x 33: id, Discipline, Effect, Original_*, Critique_*, Effect_size_original/replication, abstracts, citation counts) were "non-validated" when added (change_log v2.0.0) and CurateScience entries were flagged erroneous (v1.9.0).

`datastructure.png`: illustrates that `id` is shared by rows from the same sample/registration; one replication report can cover several originals (id 3), one original can have several effects (ids 4, 5), and one replication can reference two original papers for the same effect (id 6). Row = (original study, replication study, effect).

---

## 3. `fred-data/output_flora.csv` — FLoRA (paper-level)

2,815 rows x 35 columns (2,526 replication + 289 reproduction). Built by `pipelines_flora_prepare_flora.qmd`.

### 3.1 Column dictionary

| column | non-null | nunique | notes |
|---|---|---|---|
| doi_o | 99.5% | 2589 | lowercase DOI of original (14 rows have no doi_o -> book chapters etc.) |
| alt_identifier_o | 0.5% | 10 | preprint/alternate DOI of original |
| doi_o_hash | 99.5% | 1920 | first 3 hex chars of md5(doi_o) — privacy-preserving API key |
| title_o | 100% | 2601 | CrossRef/DataCite, HTML-cleaned |
| author_o | 99.6% | 2575 | JSON array of {given, family, sequence} |
| journal_o | 98.7% | 829 | Psych Science 224, JPSP 151, PNAS 73, Science 66, JEP:LMC 42, AER 42, JEP:G 39, Cognition 39, JCR 38, JESP 34, Nature 29, JABA 27, Nature Genetics 26, QJE 19 ... (broad: psych + econ + genetics + sports med + IS) |
| year_o | 100% | 74 | 1880..2026, median 2011 |
| volume_o / issue_o / pages_o | 95.7/89.9/94.4% | | |
| apa_ref_o / bibtex_ref_o | 100% | | |
| url_o | 18.9% | 520 | |
| language_o | 99.3% | 7 | en 2785, de 3, fr 2, it/es/nl/pt 1 |
| doi_r | 92.8% | 2148 | 200 replication rows have url_r only (OSF projects, theses, ResearchGate) |
| alt_identifier_r | 4.4% | 121 | preprint / OSF registration / meta-paper DOI; also used by FORRT to keep SCORE report ids |
| doi_r_hash | 92.8% | 1689 | |
| title_r / author_r / journal_r / year_r / volume_r / issue_r / pages_r / apa_ref_r / bibtex_ref_r | 100/99.9/90.9/100/81.7/71.9/66.4/100/100% | | journal_r: OSF Registries 12 rows slipped through; Royal Society Open Science 166, Science 110, Nature Human Behaviour 49, AMPPS 48, RPP 39, J Applied Econometrics 36 ... year_r 1969..2026 (2023: 283, 2020: 265, 2025: 239, 2018: 240, 2026: 147) |
| url_r | 23.9% | 631 | |
| language_r | 88% | 4 | en 2474, fr 2, de 1, nl 1, NA 337 |
| oa_url_o / oa_url_r | 33.3% / 56.2% | | Unpaywall open-access PDF/landing links (pipeline sources unpaywall_cache.R) |
| outcome | 89.8% | 10 | successful 1042, failed 901, mixed 564, NA 286 (284 are reproductions), stat. successful but flawed 7, descriptive only 6, uninformative 4, computationally reproducible/robust variants 5 |
| outcome_quote | 89.9% | 2236 | median 152 chars, max 2,369; COS shorthand quotes are rewritten to sentences ("Coded as ...") and multi-coding quotes joined with " \|\| " |
| outcome_quote_source | 89.1% | 159 | abstract 1744, OSF report 153, data files, page refs |
| type | 100% | 2 | replication 2526, reproduction 289 |
| source | 100% | 7 | replications 1522 (FORRT sheet), COS 716, reproductions 284, openalex 200, SCORE 88, openalex_snapshot 4, i4r 1 |

`osf/flora_osf_2026-03-21.csv` (1,507 x 37) is an older snapshot with two extra columns not in the GitHub output: `self_identified_replication` and `replication_intent_confidence` (LLM classification from `R/llm_classification.R`), and `doi_o_alt/doi_r_alt` naming; its 'source' has only replications 773 / COS 726 / reproductions 8. Not needed except as evidence that FORRT runs an LLM "is this really a replication?" screen.

### 3.2 Outcome shares
- By type: replications 41.3% successful / 35.7% failed / 22.3% mixed.
- By source: replications-sheet 41.5/33.0/25.2; COS 39.9/42.9/15.6; SCORE 45.5/39.8/13.6; openalex 42.3/27.6/29.1.
- By replication-year bucket (5-yr): 2010-14 (n=312) 42.3/29.5/27.6; 2015-19 (758) 43.1/37.3/18.9; 2020-24 (959) 38.2/35.2/25.7; 2025-26 (378) 43.9/37.8/17.5; pre-2010 (n<=36 per bucket) noisy ~40-60% successful. Full per-year table computed (e.g. 2015: 74 succ/80 fail/21 mixed; 2018: 106/77/44; 2023: 102/102/70; 2025: 103/86/44; 2026: 63/57/22).
- Structure: 2,209 originals have exactly one replication row, 100 have 2, 22 have 3, 7 have 4-7. Mega-papers: doi_r 10.1098/rsos.231240 covers 140 originals (Boyce et al. student replications, 2024 RSOS), 10.1126/science.aac4716 (RP:P 2015) 92, 10.1007/s13164-018-0400-9 (X-Phi) 39, 10.1038/s41562-024-02062-9 26, 10.1007/s40279-025-02201-w (sports med) 25, 10.1177/2515245918810225 (ML2) 24, 10.1038/s41562-018-0399-z (SSRP) 21, 10.1126/science.aaf0918 (ML? econ 2016) 18, 10.1073/pnas.2103313118 17, 10.3389/fcomm.2022.1048896 10.
- Duplicates: 10 (doi_o, doi_r) pairs appear twice (allowed when url_r differs = different reports on same dataset).

### 3.3 FLoRA pipeline rules (`pipelines_flora_prepare_flora.qmd`)
Sources (all Google Sheets published as CSV, plus one GitHub CSV):
1. REPLICATION_GSHEET (gid=863031634) — the FORRT "replications" sheet; keep `validation_status in {validated - chosen, validated - changed, validated - unchanged}`; tag type=replication, source=replications.
2. REPRODUCTION_GSHEET (gid=984458430 of the same doc) — reproductions; same validation filter; type=reproduction. (FAQ: reproductions come from the Replication Network list and Institute for Replication reports.)
3. FReD_FOUNDATION_SUCCESS_CODING (doc 1J9Lp_RF6…, gid=984458430) — the COS success-coding sheet; validated only; `rewrite_cos_quote()` expands shorthand; grouped by (doi_o, coalesce(url_r, doi_r)): outcome = unique value or "mixed" if coders disagree, quotes concatenated with " || "; source=COS.
4. SCORE_URL (doc 2PACX-1vSlPVI…, gid=1421575264) — SCORE entries; source=SCORE.
5. VALIDATED_EXPORT_URL = `https://raw.githubusercontent.com/forrtproject/flora-validation/main/data/validated_export.csv` — output of a separate "flora-validation" repo (human validation app; this is where `openalex` / `openalex_snapshot` / `i4r` sourced rows come from). **This repo is a lead for the "find more replications" pipeline: FORRT already runs an OpenAlex keyword search ("replication") with R extraction + human validation.**
Then: `normalise_outcome()`; exclusions sheet (gid=1098183075) by doi_r/url_r; manual exclusions (withdrawn 10.31234/osf.io/jfmsz; Soto 2019 10.1177/0956797619831612 "replicates correlations, not claims"; korbmacher_2022; a clearerthinking URL); `clean_doi()` (lowercase, strip prefixes, cut at first whitespace, strip "digital object identifier"/"get rights and content" scraping garbage); url_r dropped when it merely repeats doi_r; dedup on (doi_o, coalesce(norm_url(url_r), doi_r)) then `merge_doi_pair_dups()`; DOI format warnings; confirmed preprint dedup (cache/confirmed_preprint_duplicates.csv, actions keep_both/keep_1/keep_2); CrossRef+DataCite refs (`get_references`), manual URL overrides (cache/manual_references.xlsx), OpenAlex fallback for OpenAlex URLs, synthesized APA/BibTeX from fields; `clean_flora_text_fields()` (strip JATS/HTML, entities, PDF linebreaks); `resolve_preprint_dedup()` (title similarity + first author + year; preprint loses); 3-char md5 hashes; OpenAlex language; (later steps, not shown in the excerpt: Unpaywall OA URLs, filter step writing flora_filtered.csv, export log).

### 3.4 `output_flora_filtered.csv`, `output_flora_filter_log.csv`, `output_flora_export_log.csv`, `output_dup_outcome_conflicts.csv`, `output_preprint_dedup_candidates.csv`
- flora_filtered.csv: 2,457 x 35 (same columns) = flora.csv minus 358 rows logged in flora_filter_log.csv: `invalid_identifier` 205 ("doi_r is not a valid DOI and does not contain handle.net/" — i.e. rows with url_r only / NA doi_r), `boyce_exclusion` 140 ("Multi-study paper: Eleven years of student replication projects" — the RSOS 10.1098/rsos.231240 mega-paper is removed), `osf_registration` 12 ("OSF GUID resolved to a registration, not a preprint/paper"), `retracted` 1 (Nature correction/retraction via RetractionWatch). Filtered outcome counts: successful 907, failed 748, mixed 502. **This "filtered" file is what the Zotero API loads** (it wants resolvable DOIs). For a wiki, use the unfiltered flora.csv but carry the filter reason as a flag.
- flora_export_log.csv (101 rows): rows dropped at export for missing title_o (35) / title_r (63) / both (3), by source: reproductions 61, replications 27, openalex 10, COS 3 — so the true FORRT-curated set is ~2,916 pairs; 101 lack CrossRef metadata (mostly finance/econ reproductions with malformed DOIs like `10.1111/j.1540-6261.2004.00679`).
- dup_outcome_conflicts.csv: 1 conflict (10.1002/(sici)1099-0771... vs ML2 10.1177/2515245918810225: failed|successful -> resolved "mixed").
- preprint_dedup_candidates.csv (15 rows): pairs detected as preprint/publication or DOI-variant duplicates (e.g. `10.1037/0022-3514.68.5.793` vs `10.1037//0022-3514.68.5.793`; PsyArXiv eu9cj vs yt9n8), actions auto_keep_1 / keep_both.

### 3.5 `output_flora_faq.md` — coding rules (verbatim gist)
- Outcome = what replication authors say in the abstract, else discussion/conclusion; for meta-papers use individual reports if available else the meta-paper's main criterion. Outcome concerns the central finding the replication was designed to test (robustness checks/exploratory analyses ignored).
- Failed manipulation check => failed; manipulation OK but main test fails => failed; title focused on one effect that failed => failed regardless of other successes.
- Close works but conceptual doesn't => mixed. Conflicting multi-study results => mixed.
- Overlapping data with additional observations (e.g. extra decade) => replication, not reproduction. Reanalyses/multiverse that test the same claim => included as reproductions; reproduction outcomes encode computational reproducibility + robustness.
- Paper with both reproduction and replication => two rows. Row = one pair of references; multi-study replications aggregated.
- Preprints: version of record preferred; alternates in alt_identifier_*; studies published individually and in a meta-paper: published version in doi_r, meta-paper in alt_identifier_r.
- Peer-review status: CrossRef journal found => "journal article"; NA or "SSRN Electronic Journal" => "working paper" (this variable is not in the export, but libre2.csv has `publicationstatus_r`).
- Inclusion: must self-identify as a replication before reporting results, name target study, replicate a study/experiment (not merely an association); close-to-conceptual all allowed; quality NOT assessed. Excluded: OSF registrations (can't link to publication), Google-docs reports, PsychFileDrawer-style blogs; Zenodo/OSF reports OK; ideally both sides have DOI/handle.
- Synthetic-data replications and meta-analyses replicating meta-analyses (with new data) are included.

### 3.6 `fred-data/archive/libre2.csv` (403 x 31)
An earlier (2024?) "Replication List" export — the precursor of FLoRA built by `archive/list_data_creator.qmd`: doi_o/doi_r + hashes, CrossRef fields, apa/bibtex, ref_o/ref_r, url_r, outcome (6 values), outcome_quote, out_quote_source, **keywords** (OpenAlex, 100%), **metapaper_r** (0/1), **publicationstatus_r** ("Peer-reviewed (published in a journal)" / "Working paper" / ...). 380 distinct doi_o, 137 doi_r. Overlap with FLoRA: 400/403 doi_o present in FLoRA doi_o; 387/403 doi_r present in FLoRA doi_r. So it is fully absorbed; its only unique value is `keywords`, `metapaper_r`, `publicationstatus_r` for those 403 pairs. Archive.

Other archive files: `AI_coded.xlsx` (78 x 13: fred_id, refs, abstract_r, success_rating, success_quote — LLM-coded outcomes), `additional_subjective_coding_with_ai.csv` (24 x 13, same idea), `subj_coding_Roksana.csv` (674 x 14: human outcome coding with abstract_r, outcome, outcome_quote, out_quote_source), `doio_keywords.csv` (539 x 4: OpenAlex keywords per doi_o), `doi_o_getkeywords.R`, `hackathon_prep_flora.qmd` (55 KB older pipeline), `dataset_validation.Rmd` (38 KB; the validation checks referenced by prepare_fred), `cos_report.qmd` (47 KB; COS Phase-1 report), `archive_AUTHOR_OVERLAP.md` (method note for author overlap).

---

## 4. Replication success criteria — `fred-r-package/replication_outcomes.R` + `osf/success_criteria.Rmd`

All criteria operate on Pearson r (es_o, es_r) and Ns (n_o, n_r). Helper formulas (helpers.R / effect_size_transformations.R):
- `p_from_r(r, N)`: t = r*sqrt((N-2)/(1-r^2)); p = 2*pt(-|t|, df=N-2) (two-tailed); NA if N<=2.
- `compute_ci_r(r, n, 0.95)`: Fisher z = atanh(r); se = 1/sqrt(n-3); CI in z ± 1.96*se, back-transformed with tanh; NA if n<=3.
- `calculate_prediction_interval(r, n_o, n_r)`: Z=atanh(r); SE_PI = sqrt(1/(n_o-3) + 1/(n_r-3)); Z ± z_{α/2}*SE_PI; back-transform (Patil, Peng & Leek 2016 supplement).
- `compare_effectsizes(r1,n1,r2,n2)`: metafor::escalc(measure="COR") for each, then fixed-effect `rma(method="FE")` -> est, ci_lb, QEp (Q-test p).
- `find_r_for_power(.33, n_o)` (in helpers, not shown) = r giving 33% power at n_o; `compute_power_r` = pwr.r.test-style two-tailed power.

`assess_replication_outcome(es_o, n_o, es_r, n_r, criterion)` returns (outcome ∈ {success, failure, OS not significant, NA}, outcome_detailed, outcome_report):
1. **significance_r**: if p_from_r(es_o,n_o) >= .05 -> "OS not significant"; elif p_from_r(es_r,n_r) >= .05 -> failure ("replication effect is not significant"); elif sign(es_o)==sign(es_r) -> success; else failure, reported "failure (reversal)".
2. **significance_agg**: FE meta-analysis of both; ci_lb > 0 & est > 0 -> success; ci_lb > 0 & est < 0 -> "failure (reversal)"; ci_lb <= 0 -> failure. (Note: assumes original direction positive; use `align_effect_direction()` first: es_o := |es_o|, es_r := es_r*sign(es_o).)
3. **consistency_ci**: success iff es_o strictly inside 95% CI of es_r (compute_ci_r(es_r, n_r)).
4. **consistency_pi**: success iff es_r strictly inside the 95% prediction interval from (es_o, n_o, n_r).
5. **homogeneity**: Q-test p (QEp) >= .05 -> success ("effects are not heterogeneous"), < .05 -> failure.
6. **homogeneity_significance**: if p_from_r(es_o,n_o) >= .05 -> "OS not significant"; else success iff QEp > .05 AND ci_lb > 0 ("homogeneous and jointly significantly above 0"); all other combos failure, with outcome_report "failure (homogeneous but not significant)" etc.
7. **small_telescopes** (Simonsohn 2015): success iff es_r >= r that gives the original study 33% power at n_o.
The vignette also notes each criterion's known biases (sig_r ignores original evidence; consistency_ci rewards low-powered replications; PI is very wide for small studies; homogeneity has low power; small telescopes judges evidence quality not truth).

`code_replication_outcomes()` (LeBel et al. 2018 framing) adds: `signal` (p_r < .05), `consistency` ("OS not significant" | "consistent" if es_o within replication CI | "inconsistent, larger/smaller/opposite" | "inconsistent"), `result` ("successful replication" if p_r<.05 & same sign; "failed replication"; "OS not significant"), `result2 = signal - consistency`. `add_replication_power()` = power of replication for es_o at n_r (0 if n_r<4). `augment_for_zcurve()` = Fisher z / se for z-curve of originals. `test_equivalence_r(r, n, sesoi)` = TOST equivalence test.

## 5. Effect-size conversions — `effect_size_transformations.R::convert_effect_sizes(es_values, es_types)`
Target metric Pearson r. Accepted (case-insensitive; curly apostrophes normalized):
- r / phi / φ -> as is (sign kept).
- r2 / r^2 / r² / r-square -> sqrt(R²) (positive).
- d / cohen's d / hedges' g / smd -> r = d/sqrt(d²+4) (sign kept).
- OR / odds ratio -> d = ln(OR)*sqrt(3)/π, then d->r (sign from OR<1).
- etasq / eta^2 / η² -> d = 2*sqrt(η²/(1-η²)), then d->r (positive).
- f / cohen's f -> d = 2f; f2 / f^2 / f² -> R² = f²/(1+f²), r = sqrt(R²).
- "test statistic" strings: `t(df) = v` -> r = t/sqrt(t²+df); `F(1, df2) = v` -> t = sqrt(F) (df1 must be 1); `z = v, N = n` -> r = z/sqrt(z²+N); `x2(1, N = n) = v` / `χ2(...)` -> r = sqrt(χ²/N). Anything else (F with df1>1, "F < 1", "binomial z = 2.94", χ² with df>1) -> NA.
- Explicitly non-convertible -> NA: beta (std), b (unstd), b, beta, partial etasq / etasq (partial), χ2 (bare), cramer's v, dz, hazards ratio, percentage, squared semipartial correlation, cohen's h, semipartial correlation.
`add_common_effect_sizes()` writes es_o/es_r (coalescing with pre-existing r values); `add_uncertainty()` adds vi_o/vi_r (metafor COR), ci.lower/upper_o/r, p_value_o/r.
Note: the FReD-data repo's own `es_type_o` vocabulary is messier than the map (e.g. "Cohen's f^2", "etasq (partial)", "partial correlation", "ser_method", "Wilcoxon r", "Cohen's dz", "kendall's w", "omega squared") — the R package emits warnings for unknown types. Our normalizer must map: partial correlation / partial r -> r (treat as r), omega squared ~ etasq, ser_method (spearman?) unclear -> NA, hedges' g -> d.

## 6. The official tools (what to differentiate from)

### 6.1 FReD Explorer (`osf/fred_explorer_app.R`, Shiny v0.4.6 dated 14 Feb 2024; reads legacy `https://osf.io/z5u9b/download`, so it still shows the legacy 4.6k-row data)
Tabs: (1) landing/info; (2) **Replicability Tracker** — sidebar: minimum power slider (.05-.999), "Browse Large-Scale Projects" select (All / Individual submissions / FORRT R&R / CORE / CRSP special issue / Data Replicada / ML1 / ML2 / ML3 / OpAQ / OpenMKT / OSF Registries / OSC 2015 / RRR1 / RRR3 / RRR4 / RRR8 / RRR9 / Soto / SSRP), "validated only" and "coded only" checkboxes; main: red/green outcome bar plot, filterable DT table (description, es_original, es_replication, n_original, n_replication, osf_link, contributors, result, refs, tags, discipline), RPP-style scatter (es_original vs es_replication, plotly, 800px), second bar plot (outcome by criterion), **z-curve** of original studies (zcurve::zcurve EM, "Observed Replication Rate"); (3) **Study Overview** — a 17,000-px-tall forest plot of es_replication by ref_original; (4) **Dataset** — download button + full DT + variable definitions; (5) **Correlates of Replicability** — success rate by decade of original, and by original journal (2,000 px bar chart); (6) **Moderators [alpha]** — metafor meta-regression of replication ES on es_original / orig_journal / orig_year / power with table + text; (7) **References-Checker [alpha]** — paste a reference list, DOIs are extracted and matched, bar plot + table (the seed of the Annotator); (8) References; (9) FAQ; (10) About + changelog. Success criteria selectable in newer package versions (NEWS 0.1.0: "choice between many methods to assess replication success").
Package (`fred-r-package/`, v0.2.0): `load_fred_data()`, `read_fred()`, `clean_variables()`, `load_retractionwatch()`, `use_FReD_offline()`, `run_explorer()`, `run_annotator()` (now just opens forrt.org web annotator), `create_citation()`, `get_dataset_changelog()` (reads https://osf.io/fj3xc/download). NEWS 0.2.0: renamed to `_o`/`_r` suffixes; "Effect size conversions now retain the sign".

### 6.2 Zotero Replication Checker API (`fred-data/API_Integration_Guide_README.md`, `..._build_two_tables_doi_records.py`)
- Base `https://rep-api.forrt.org/v1` (AWS Lambda + DynamoDB, eu-central-1; test base `https://80zw14hxjc.execute-api.eu-central-1.amazonaws.com/v1`).
- `GET/POST /prefix-lookup?prefixes=198` — 3-char md5 prefix (of doi_o or doi_r) -> list of DOI records (privacy-preserving: the client hashes its DOIs locally and only sends prefixes).
- `GET/POST /original-lookup?dois=10.1037/a0027598` — full-DOI lookup, works for original, replication or reproduction DOIs. Param is `dois` (plural).
- Record shape: {doi, doi_hash, title, authors[], journal, year, volume, issue, pages, apa_ref, bibtex_ref, url, record:{stats:{n_replications, n_unique_replication_dois, n_originals, n_unique_original_dois, n_reproductions, n_reproduction_only}, replications:[{doi, doi_hash, rep_type, title, authors, journal, year, ..., outcome, abstract, outcome_quote}], originals:[...], reproductions:[...]}}. CORS enabled, cacheable. Built from flora_filtered.csv via `build_two_tables_doi_records.py` (PREFIX_TABLE prefix->dois; DOI_TABLE doi->record JSON).
- **Reusable idea**: our build can emit the same two-table JSON so the wiki is API-compatible / a drop-in for the plugin; and the wiki can link "check in Zotero".

### 6.3 FReD Annotator — web app at forrt.org (annotate reading lists with replication findings). Reference-list -> DOI -> FReD lookup.

## 7. OSF sub-datasets and the OSF Registries scraper subproject
`osf/sub-datasets/readme_subdatasets.txt`: each large project's meta-dataset was restructured by `process_<name>.R` into the ReD template, appended, hand-completed and validated. Files: `220621_red_template_osc2015.xlsx` (168 RP:P rows, 17 template columns incl. closeness, result), `220621_red_template_feldman.xlsx` (110 CORE/Feldman rows), `220627_red_curatescience.xlsx` (831 x 23 — CurateScience import, later flagged erroneous), `220622_red_is.xlsx` (4 rows individual submissions), `datasubmission_template.xlsx` (the contributor template; sheet closeness_scoring = Brandt et al. recipe: 7 questions instructions/measures/stimuli/procedure/location/remuneration/participants scored exact 2 / close 1 / different -1), `core_for_fred.xlsx` (221 x 70 CORE rows, `process_core.R` maps r_evaluation "signal…" -> success), `xphil_for_fred.xlsx` (40, `process_experimentalphilosophy.R`), `camereretal2018.xlsx` (21 SSRP rows, `process_camereretal2018.R`), `231026_forrt_with_journals.xlsx` (1,296 FORRT Replications & Reversals rows: id, Discipline, Effect, Original_Paper_title/ref/doi/N/abstract/citations, Critique_text/ref/doi/N/abstract/citations, Effect_size_original/replication, Description — **a second effect-named source, with abstracts and citation counts**), `red_forrt_synthesis.R`, `red_processing.R`, `220621_OSFregistries.xlsx`, and **`quiz.html` (60 KB) = a saved copy of the 80,000 Hours GuidedTrack quiz "Psychology results in top journals - can you guess which ones were true, and which didn't replicate?"** — prior art for the owner's guessing-game feature (FORRT kept it as a sub-dataset source, i.e. its items were entered into ReD). It is a static third-party page (guidedtrack.com scripts), not FORRT code; use it only as design inspiration and as a check that its items exist in FReD.
The two 'Additional Studies to be added' sheets in FReD_2.4.1 (476 x 15 free-form browse/add list, and 210 x 13 Google-Form submissions with columns id, Timestamp, Type of Reference, Field, Description, Reference-Original (APA+DOI), Reference-Replication, Contributor, Type of Study, "Replication outcome as reported by the replication authors", Outcome quote, "Copied to Data?") are FORRT's own uncoded backlog.

`osf/registries-subproject/` ("Documenting the Replicability of Psychological ... " — an OSF Registries study, preregistration.pdf): `rr_scraper_links.R` scrapes the OSF API v2 (`https://api.osf.io/v2/registrations/{id}/?format=json` + `/contributors/`) for the **"Replication Recipe" post-completion and pre-registration forms** (registered_meta items 29-37 -> pc01..pc09: where materials registered, replication effect size, its CI, "significantly different / not significantly different from original", judged outcome (success / informative failure / practical failure / inconclusive), reasons, data link, limitations; pr01..pr28 for the pre-registration form: target effect, original ES, planned N, setting, country, sample, mode, differences...). Results: `OSF_scraped-2022-05-31.csv` 132 registrations (131 ids; 104 titles; 30% also have a linked pre-registration); `220805_OSFregistries.xlsx` 'data' 137 rows hand-coded (result: success 49, informative failure 44, inconclusive 8, practical failure 2, NA 34; notes: duplicate 40, "access requested without response" 16, "no information available" 8) with es_original/es_replication in r (36/60 non-null), Ns, closeness score; `RR_processeddata.csv` 95 rows after exclusions (result success 29 / inf. failure 23 / inconclusive 8 / practical failure 2 / NA 33; es pairs available for ~23). `analyses_final.R` = analysis for that paper (pairs, z-curve, C-3PR). Takeaway: the OSF Replication Recipe registry form is a structured, machine-readable source of replication outcomes (fields pc02-pc06), but only ~130 registrations existed by 2022 and 40 were duplicates — **this is a discovery channel we can re-run against the OSF API (registration_supplement == "Replication Recipe (Post-Completion)")**. FLoRA's FAQ excludes registrations from FLoRA itself, so anything found this way is complementary.

## 8. Joins & counts (all verified)
- FReD rows 2,164; distinct doi_o 786; distinct doi_r 320 (+ 383 url_r); fred_id 1,116; discipline 40 raw / 34 normalized; (doi_o, doi_r) pairs 859; entries (ref_o, study_o, ref_r, study_r) 1,003.
- FReD rows with numeric es_o & es_r: 1,163; with also n_o & n_r: 1,154. Converted-to-r both sides (R-package rules): 1,061; with Ns 1,056. Archive precomputed r_o & r_r both: 733.
- FReD -> FLoRA: 1,783 rows / 678 pairs by exact DOI pair; 2,036 rows with url_r + alt_identifier_r fallbacks; 128 rows unmatched (Soto 60 rows because Soto 2019 is manually excluded from FLoRA; 21 additional_studies; pseudo-DOIs; a few PsyArXiv preprints). 2,080 FReD rows have doi_o in FLoRA; 40 original DOIs in FReD are absent from FLoRA.
- FLoRA rows whose pair is in FReD: 683 (so 1,843 replication pairs in FLoRA have NO effect-size coding — the main gap for any forest plot).
- FLoRA: 2,589 distinct doi_o, 2,148 distinct doi_r, 289 reproductions vs 2,526 replications; non-English originals 9, replications 4.
- Legacy 2.4.1 -> current FReD: 1,548 rows joinable by DOI pair; 3,234 legacy rows not in current.
- libre2 -> FLoRA: 400/403 doi_o, 387/403 doi_r overlap.

## 9. Data-quality issues to handle in our build
1. entry_id constant; effect_id = row number. Rebuild entry/effect ids from the COS archive file (correct) or from (doi_o, study_o, id_r, study_r).
2. Discipline casing/synonyms (40 -> ~30). "Gender Stereotypes" is a topic, not a discipline.
3. es_type vocabularies differ across FReD (43/46 labels), legacy (34/31), R package map. Build one mapping table; keep raw label.
4. pval_type labels mix "l (<)" and "<" and '"="'; pval_tails "2" vs "2 (two)".
5. author_overlap is a count despite the codebook; author_overlap_pct is the usable independence measure.
6. HTML entities (`&amp;`) in journal_o, ref_r, description in FReD (FLoRA is cleaned; FReD is not).
7. Pseudo-DOIs in FReD doi_r (thesis ids); FLoRA filter log marks 205 such rows.
8. FLoRA outcome NA for 284/289 reproductions; reproduction vocabulary has 4 tiny categories.
9. Mega-papers (RSOS student replications 140 originals; RP:P 92) dominate counts — weight/flag them.
10. Management/JOM block (100 of 103 successful) and Soto Big Five (60 rows) are project artefacts that skew any naive "success rate".
11. year_o has 17 rows at 1946 and one at 1935 (Asch/classic?) — fine, but check.
12. Legacy sheet has column-shift junk in `status`/`temp` for some rows (mime types), and German/English description rows at top.

## 10. What to reuse (paths)
- `data\raw\forrt\fred-data\archive\2025-11-30_COSdata_validated.xlsx` — primary effect-level table (r_o, r_r, statistical_success, correct ids).
- `data\raw\forrt\fred-data\output_FReD.xlsx` — augmentation columns (title/author JSON/journal/year/bibtex/language/author_overlap_pct) to merge by row order or DOI pair.
- `data\raw\forrt\fred-data\output_flora.csv` (+ `output_flora_filter_log.csv` as a flag table, `output_flora_export_log.csv` for 101 dropped pairs) — paper-level registry, canonical outcomes.
- `data\raw\forrt\osf\version-history\FReD_2.4.1_2025-06-25.xlsx` 'Data' + 'Reversals Effects' sheets — effect names (443 + 583), closeness, power, CI, osf_link, prereg, source project, 3,234 extra rows; 'Additional Studies to be added' (686 rows) = FORRT's own backlog of known-but-uncoded replications (seed for our discovery queue).
- `data\raw\forrt\osf\sub-datasets\231026_forrt_with_journals.xlsx` — FORRT R&R with abstracts + citation counts.
- `data\raw\forrt\fred-r-package\replication_outcomes.R`, `helpers.R`, `effect_size_transformations.R` — port formulas 1:1 to TypeScript/Python (see sections 4-5).
- `data\raw\forrt\fred-data\API_Integration_Guide_build_two_tables_doi_records.py` + README — JSON record schema for API compatibility.
- `data\raw\forrt\fred-data\output_flora_faq.md` — coding rules to adopt verbatim in our contributor docs.
- `data\raw\forrt\osf\registries-subproject\rr_scraper_links.R` — OSF Registrations API recipe for discovery.
- `data\raw\forrt\osf\sub-datasets\quiz.html` — inspect (possible existing quiz idea).
- `data\raw\forrt\fred-data\output_citation.txt`, `CITATION.cff` — required attribution (CC-BY 4.0).

## 11. Discard / archive
- `osf\FReD_osf_2tbvd.xlsx`, `osf\wiki_home.md` (HTML 502 stubs).
- `fred-data\archive\libre2.csv` (absorbed into FLoRA), `AI_coded.xlsx`, `additional_subjective_coding_with_ai.csv`, `subj_coding_Roksana.csv` (intermediate coding sheets; keep only as provenance).
- `osf\version-history\ReD_2023-03-28.xlsx`, `FReD_1.0.0`, `1.5.0`, `2.0.0` (superseded by 2.4.1; keep for version diffing only).
- `osf\flora_osf_2026-03-21.csv` (older FLoRA snapshot; only useful for the two LLM columns).
- `osf\fred_explorer_app.R` (old Shiny; read for features only).
- `osf\sub-datasets\220627_red_curatescience.xlsx` (flagged erroneous by FORRT).

## 12. Ideas suggested by the data (for the design agents)
- Effect-centric spine: (a) legacy `effect` + 'Reversals Effects' sheet + FORRT R&R `Effect` give ~1,000 named effects; (b) FReD `description`/`claim_text_o` give claim statements; cluster FLoRA originals under effects via shared doi_o then title/keyword similarity.
- Guessing game cards: FReD rows with claim_text_o + n_o + es_value_o + discipline + year_o, answer = reported_success (only successful/failed; skip mixed) — 985+787 candidates; harder mode reveals replication N/power. Use FLoRA `outcome_quote` as the reveal text and oa_url_r as the "read the replication" link. Exclude mega-project boilerplate to avoid trivial patterns (e.g. JOM management block all successful).
- Compute all 7 criteria per FReD row (1,056 rows) and show a "criteria disagreement" widget — FORRT only shows one at a time.
- Replication families: FLoRA doi_r groups (RSOS 140, RP:P 92, ML2 24, SSRP 21, X-Phi 39, Nature Human Behaviour 26, sports med 25) map to "projects"; legacy `source` gives project labels for ~4,300 legacy rows.
- Independence: author_overlap_pct (0% = fully independent) as a filter/badge.
- Discovery pipeline: replicate FORRT's OpenAlex "replication" keyword search + LLM self-identification screen (flora-validation repo), plus OSF Registrations "Replication Recipe (Post-Completion)" API scrape (registries subproject), plus FORRT's "Additional Studies to be added" backlog (686 rows), plus Zotero-API diff to see what FORRT already has (prefix-lookup lets us check thousands of DOIs cheaply).
- Time series: FLoRA year_r x outcome gives a clean "replication activity by year" chart (2010: 46 -> 2023: 283 rows).
- Contribute back: FORRT's inbound channels are the Google Sheets + `flora-validation` repo + GitHub issues on FReD-data (issue #19 is used as a quote source!). Our review queue should export rows in the replications-sheet column set (doi_o, ref_o, url_o, doi_r, ref_r, url_r, abstract_r, outcome, outcome_quote, out_quote_source, alt_identifier_o/r).
