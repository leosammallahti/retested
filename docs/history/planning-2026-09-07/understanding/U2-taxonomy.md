# U2 — The taxonomy / categorization / clustering experiments (Dec 24–28, 2025)

Scope: everything in the project root that tried to categorize FReD studies — `test_taxonomy_v2.py` … `test_taxonomy_v17.py`, `test_v10a_updated.py`, `create_taxonomy*.py`, the emergent/hierarchical/optimal clustering scripts, the abstract-based domain tests (`test_taxonomy_agreement.py`, `test_multidimensional_taxonomy.py`, `test_taxonomy_v2_datadriven.py`, `test_taxonomy_v3_refined.py`, `test_methodology_only.py`), `analyze_openalex_topics.py` + `openalex_analysis/`, `cogatlas/`, and all the markdown briefs/reports. Every number below was read from the result JSON/CSV files, not from the prose reports, unless stated otherwise.

All paths are relative to `C:\Users\OMISTAJA\PsychologyReplication\`.

---

## 1. What the taxonomy was for

The stated goal (`prompt_for_taxonomy_rethink.md`) was **semantic enrichment: group studies that manipulate similar things (X) and measure similar outcomes (Y)** so that "similar studies" can be found across the ~4.4k FReD rows. Three parallel goals drifted in and out:

1. A psychology-subdomain taxonomy (COGNITIVE / SOCIAL / …) for browsing (`CATEGORIZATION_IMPROVEMENT_PLAN.md`, Gap 1).
2. An X/Y "what was manipulated → what was measured" code pair per study (the V1–V17 line).
3. Methodology/population/replication-feature facets (Gaps 2–4 of the plan) — planned, never built (`classify_studies_llm.py`, `apply_taxonomy_full.py` do not exist).

The briefs repeatedly say the target is "~5,400 studies"; the actual data was `fred_database_english.csv` (4,376 rows, 100 columns, legacy FReD v1) → `fred_enriched.csv` (same 4,376 rows + LLM effect names). Only **2,445 rows** ever got X/Y extractions, and all the V1–V17 agreement tests ran on **100-row samples** drawn from a fixed 500-row subsample (`analysis_sample.json`).

**The success metric for the whole exercise was cross-model agreement between two LLMs (DeepSeek V3-0324 and Kimi K2 via OpenRouter, temperature 0.1) on the same 100 studies.** No human ever coded a gold-standard set. No kappa was computed. This matters for everything that follows.

---

## 2. Timeline and what each phase actually did

### Phase 0 — effect-name enrichment and free-form extraction probes (Dec 24–25)

- `enrich_effect_names.py` / `process_effects.py`: for FReD rows missing `effect`, three models (DeepSeek, Kimi, Mistral-small) each proposed a 2–5-word effect name; majority vote, DeepSeek as tiebreak. Output `fred_enriched.csv`, progress cache `enrichment_progress.json`. Not a taxonomy, but it produced the `effect` values that later prompts saw.
- `test_semantic_extraction.py` (50 items, 3 models), `test_prompt_strategies.py`, `test_alternative_approaches.py`, `test_classification_approach.py`, `test_single_question.py`, `test_emergent_approach.py` (10 items each): free-form "construct/operation", "causal triplet", "WHAT_CHANGED / WHAT_WAS_MEASURED" prompts. Result JSONs (`test_semantic_results.json`, `emergent_results.json`, `classification_results.json`, `alternative_approaches_results.json`, `prompt_strategy_comparison.json`, `single_question_results.json`) contain raw model text only — **no metrics were computed**. Pure exploration.

### Phase 1 — emergent clustering (Dec 25–26)

Pipeline (`full_emergent_pipeline.py`):
1. For every `fred_enriched.csv` row with a `description` longer than 20 chars, DeepSeek was asked "X (the cause/manipulation): / Y (the outcome/measurement): — 2-5 words each" on the first 400 chars. → `full_extraction_progress.json`: **2,445 rows processed; 2,443 X phrases, 2,398 Y phrases**, keyed by legacy FReD `id`.
2. Phrases embedded with OpenAI `text-embedding-3-small`, KMeans k=20 → `full_emergent_clusters.json`.
3. `find_optimal_clusters.py` / `recluster_optimal.py`: HDBSCAN found 37 X / 40 Y clusters; silhouette sweep picked **k=48 for X (silhouette 0.288) and k=54 for Y (0.296)** (`optimal_k_analysis.json`). Those silhouettes are low — essentially no cluster structure.
4. `recluster_with_optimal_k.py` → `optimal_clusters_results.json` (48/54 clusters). `analyze_cluster_quality.py` → `cluster_quality_analysis.json`: 15 heterogeneous X clusters and 15 Y clusters flagged (diversity up to 0.92, e.g. a Y cluster mixing "Word processing speed", "Decision accuracy/speed", "Naming speed accuracy"); 0 redundant pairs found.
5. `improve_clusters.py` (merge/split) → `improved_clusters.json` (80 X / 79 Y). `label_clusters.py` (DeepSeek names each cluster) → `labeled_clusters.json`: 79 X labels, 77 Y labels. Biggest clusters: X "Previous Value Influence" 248, "Value Priming" 113, "Numerical Anchoring Effects" 91, "Anchoring Manipulations" 64; Y "Numerical Estimate Effects" **495** of 2,398. The data is dominated by anchoring rows (see §4.6), so the "emergent" structure is mostly *anchoring vs everything else*.
6. `hierarchical_clustering.py` → `hierarchical_clusters.json` (10 level-1 KMeans clusters, silhouette-chosen sub-clusters).
7. `create_taxonomy.py` → `taxonomy.json`: DeepSeek grouped the top-50 clusters into 12 X domains (Previous Experience 508, Cognitive Load & Control 287, Perceptual & Sensory 279, Numerical & Anchoring 254, …) and 10 Y domains (Numerical & Estimation Tasks 594, Cognitive Performance 238, …). `total_x` = 2,853 > 2,443 phrases, i.e. members were double-assigned. `create_taxonomy_v2.py` → `taxonomy_v2.json`: 8 predefined X domains (ANCHORING 649, COGNITIVE LOAD 261, PRIMING 248, SOCIAL CONTEXT 236, EMOTIONAL STATE 202, FRAMING 201, SENSORY INPUT 199, INDIVIDUAL DIFFERENCES 150) and 8 Y domains (NUMERICAL ESTIMATES 662, SOCIAL JUDGMENT 459, EMOTIONAL RESPONSE 258, …). Spot-check of members shows obvious misfiles ("Grey matter volume" under COGNITIVE LOAD; "Weight-related feedback" under SENSORY INPUT). **Neither taxonomy.json nor taxonomy_v2.json was ever validated.**

### Phase 2 — the X/Y code taxonomy, V1 → V17 (Dec 26–27, roughly 36 hours)

Test harness (identical across versions): load `analysis_sample.json` (500 rows; 332 have an `effect` name; sources OpAQ 101, ML1 73, FORRT 71, Individual submissions 73, ML3 40, CORE 36, Boyce et al. 2023 32, OSC 2015 25), `random.seed(S)`, sample 100, send `Effect / Description / X / Y` to both models with the taxonomy prompt, compare `X_code`/`Y_code` exact match. Seed 42 for V1–V8, V10, V12, V16, V10A-updated; seeds 42/99/123 for V9, V11, V13, V14, V15A–F; seeds 200/300/400 for V15G; 42/123/456 for V17.

Verified results (from `taxonomy_v*_results.json`, `taxonomy_agreement_results.json`, `v10a_updated_results.json`, `taxonomy_v17_output.txt`):

| Version | Idea | X | Y | Both | Source / note |
|---|---|---|---|---|---|
| V1 | 15 X codes in 4 domains × 11 Y codes in 3 families, by construct (`Potentialcategories1`) | 82 | 84 | 69 | `taxonomy_agreement_results.json`; domain-level X 88, Y 91 |
| V2 | V1 + 8 priority rules for the confused boundaries | 76 | 84 | 63 | `taxonomy_v2_results.json` |
| V3 | Streamlined 13 X / 10 Y, "classify by surface, not mechanism" | 79 | 80 | 66 | `taxonomy_v3_results.json` |
| V4 | "Method over theory" (deleted X5_META, renamed) | 82 | 83 | 72 | `taxonomy_v4_results.json` |
| V5 | Decision tree, 8 X / 6 Y (X_TRAIT/FRAME/THREAT/SOC/RES/STATE/TASK/SENS; Y_BIO/ACT/PERF/FACT/VAL/JUDGE) | 80.2 | 90.1 | 73.6 | n=91 valid |
| V6 | Multi-label, overlap scoring | — | — | ~74 (claimed) | **no results file exists** (`taxonomy_v6_results.json` missing); the figure only appears in `CATEGORIZATION_IMPROVEMENT_PLAN.md` |
| V7 | "Observable features": X = input channel (STIM/TASK/SOC/ENV/TRAIT), Y = response format (BIO/PERF/ACT/EST/RATE) | 79.8 | 90.9 | 72.7 | n=99; **Y axis "solved" here and barely changed afterwards** |
| V8 | Verb/noun: X_PROC vs X_CONTENT | 84 | 88 | 74 | |
| V9A–D | "Pure locus" (SUBJECT/AGENT/CONTEXT/PROCEDURE/STIMULUS) in 4 prompt formats | A 85 / B 89 / C 85 / D 87 | 92 / 88 / 88 / 86 | 78 / 79 / 79 / 74 | `taxonomy_v9_results.json` is the seed-123 run. `v9_breakthrough_report.md` announced 88/92/**81** on seed 42; `v9_final_report.md` then averaged 3 seeds: A 85/90/**76**, B 87/85/76, C 84/86/76, D 89/84/75 (seed range for A: 69–82) |
| **V10A** | **"Input channel"**: X_SELECTION > INTERACTION > ENVIRONMENT > INSTRUCTION > DISPLAY; Y_BIO > PERF > ACTION > NUMBER > SCALE | **90** | **92** | **83** | seed 42 only; declared the best |
| V10B | Two-dimensional X (channel + semantic domain) | ch 71.7 | 91.9 | 60.6 (all three) | |
| V10C | V10A + effect-name lookup table (Anchoring→DISPLAY/NUMBER …) | 88 | 94 | 83 | |
| V10D | V10A + CLEAR/LEAN/BORDERLINE confidence | 81 | 89 | 74 | |
| V10A re-run | Same X, Y renamed PHYSIO/PERFORMANCE/BEHAVIOR/ESTIMATE/RATING, same seed 42 | 88.9 | 88.9 | **80.8** | `v10a_updated_results.json`; the 83 did not reproduce |
| V11 | "Who authored the content": X_TASK/INPUT/ATTRIBUTE/PHYSICAL/AGENT; Y_GENERATED/SELECTED/SCORED/BEHAVIORAL/PHYSIOLOGICAL | 86.6 | 78.9 | 69.6 | 3-seed avg; Y_GENERATED vs Y_SELECTED alone = 25 disagreements |
| V12A | 3×3 (PERSON/TASK/WORLD × BODY/DEED/REPORT) | 89 | 91 | 81 | |
| V12B | Two-stage coarse→fine | 91 (coarse) | 91 | 82 (coarse both) | fine X 71 per brief |
| V12C | 10 yes/no questions → derived codes | 88.9 | 87.8 | 78.9 | per-question agreement 96.1 |
| V13 | 3 X (PARTICIPANT/STIMULUS/PROCEDURE) × 4 Y, "camera test" | 89.7 | 86.7 | 77.7 | 3-seed avg; PROCEDURE vs STIMULUS = 16 |
| V14 | Domain-based X (MENTAL/PHYSICAL/PERSON/LANGUAGE/QUANTITY) | 81.3 | 92.3 | 75.7 | X_MENTAL vs X_PHYSICAL = 20 |
| V15A | 8×8 keyword categories | 85.3 | 81.6 | 70.2 | |
| **V15B** | Grammatical form: X_NOUN_PERSON / NOUN_THING / VERB / NOUN_SETTING × Y_OBJECTIVE / NUMERIC / SUBJECTIVE / VERB | 91.3 | 90.0 | **82.0** | 3-seed avg (79 / 86 / 81); second best |
| V15C | Diagnostic yes/no (WHO/THINK/WHERE/NUMBER/SHOW × BODY/CORRECT/DID/NUMBER/RATED) | 87.6 | 85.6 | 74.9 | |
| V15D | Pure lexical pattern matching with DEFAULT | 79.3 | 84.6 | 68.9 | DEFAULT hit ~36% |
| V15E | High-confidence + OTHER | 94.7 | 84.7 | 81.7 | **X_OTHER 65%, Y_OTHER 88%**; "specific" agreement 99/97 |
| V15F | V15E with expanded Y | 94.0 | 87.7 | 82.7 | X_OTHER 62%, Y_OTHER 22% |
| V15G | Full-coverage 6×7, new seeds 200/300/400 | 91.4 | 87.4 | 79.9 | OTHER 2.5%/6.5%; per-seed both 76.9 / 75.8 / 87.0 |
| V16 | 4×4 (TRAIT/CONTEXT/TASK/STIMULUS × BIO/PERF/BEHAVIOR/REPORT) | 78 | 90 | 69 | `v16_failure_report.md` |
| V17 | V10A-like with explicit disambiguation constraints | 89 / 89 | 94 / 88 | **84 / 80** | seeds 42 / 123; seed 456 aborted at 25/100, no JSON written |

`disagreement_studies.txt` and `extract_disagreements.py` dump the 23 V10A disagreements on seed 42 (11 X-only, 8 Y-only, 4 both) with both models' reasoning — the most useful qualitative artifact of this phase.

### Phase 3 — abstract-based domain classification and OpenAlex (Dec 28)

After V17 stalled, the work switched input (full abstracts from `fred_enriched_with_abstracts.csv`: 3,734 of 4,376 rows have an abstract; 713 DOIs have an AI "TL;DR") and target (topic domain rather than X/Y). Same 100-study sample (seed 42 over rows with abstracts), same two models:

| Test | Scheme | Agreement |
|---|---|---|
| `test_taxonomy_agreement.py` V1_SIMPLE | 5 domains (COGNITIVE/SOCIAL/DEVELOPMENTAL/CLINICAL/INDIVIDUAL) + 7 methodology + 5 measurement | domain **97%**, methodology 92%, measurement 79%, all three 74% |
| same, V2_MULTILABEL | 1–2 domains + 1–3 subdomains | primary domain 88.8%, any-overlap 100%, subdomain Jaccard 0.53 |
| same, V3_PHENOMENON | domain + free-text phenomenon + iv_type + dv_type | domain 97%, iv_type (MANIPULATION/MEASURED/CONTEXT) **94%**, dv_type 91%, phenomenon fuzzy-similar 84% |
| `test_multidimensional_taxonomy.py` | 4 independent facets | broad_domain **95%**, specific_area (12) 83%, manipulation_type (6) 77%, outcome_type (7) 90% |
| same, hierarchical | 3 → 15 | level-1 91.9%, level-2 77.8% |
| `test_taxonomy_v2_datadriven.py` | COARSE_4 / SIMPLE_6 | 92% / 84% |
| `test_taxonomy_v3_refined.py` | 3_MINIMAL / 4_MERGED / 5_CLEAR | **95%** / 94% / 91.9% |
| `test_methodology_only.py` | manipulation_type / outcome_type / effect_type (MAIN/INTERACTION/MEDIATION/MODERATION) | 79.8% / 86.9% / **93.9%** (80% MAIN) |

Pattern: **agreement is a near-linear function of category count.** 3–5 broad domains → 92–97%; 12–15 subdomains → 78–83%; manipulation type → 77–80% regardless of framing. This is the same ceiling seen in Phase 2, just measured on better input.

`analyze_openalex_topics.py` (with `openalex_utils.py`, `fetch_openalex_original_dois.py`) fetched OpenAlex works for **1,623 original DOIs (1,590 with topics)** → `openalex_original_enrichment.json`, and merged into `fred_enriched_openalex.csv`: **4,232 / 4,376 rows (96.7%) have a primary subfield; 1,652 of 1,688 unique original DOIs**. `map_broad_category(field, subfield)` collapses OpenAlex subfields into 11 "broad categories" by fixed rules (lines 59–110 of the script). The `openalex_analysis/` folder holds the resulting tables (see §5.3).

---

## 3. What was the best-performing scheme?

Nominal winner: **V10A "Input Channel"** — X 90 / Y 92 / both **83%**, seed 42, n=100. Honest reading:

- Re-running V10A with only the Y labels renamed on the *same seed* gave 88.9 / 88.9 / **80.8**. V17 (a V10A derivative) gave 84 and 80 on two seeds. V15B (grammatical) averaged 82 over three seeds. V9A dropped from a single-seed 81 to a 3-seed average of 76. **The realistic band for the best single-label 5×5 X/Y scheme is 78–84% joint agreement, X ≈ 88–91%, Y ≈ 88–92%.** The differences between V10A, V12A, V12B, V15B, V15F, V15G and V17 (79.9–83) are inside the sampling noise of n=100 (95% CI ≈ ±8 points).
- The one component that was genuinely stable is the **Y axis as "output format"** (physiological / objectively scored / consequential behavior / generated number / scale rating): 88–94% in V7, V9, V10, V12, V14, V16, V17 and 87–90% as `outcome_type` on abstracts. Its residual confusions are always the same three: ESTIMATE vs RATING (WTP, probability sliders), BEHAVIOR vs RATING (hypothetical vs real choice), PERF vs RATING (self-rated performance/confidence).
- For **topic** organization the best numbers are trivially the coarsest: 3 domains 95%, 4 domains 92–94%, 5 domains 92–97% depending on definitions. `effect_type` (main/interaction/mediation/moderation) 94% and `iv_type` (manipulated/measured/context) 94% are also robust.

---

## 4. Why it never converged — specifically

1. **The metric was agreement, not validity, and it was gameable.** Two LLMs agreeing says nothing about whether a code is right, and agreement rises whenever categories get vaguer or an escape hatch exists: V15E hit 99% "specific" agreement by dumping 65% of X into OTHER; V12C hit 96% on yes/no questions and 79% on the derived codes. There was never a human-coded gold set, never a kappa, and the target (>85%) was arbitrary. `v9_final_report.md` even asks "Is high agreement even the right goal?" — and then two more days were spent on it.
2. **n=100 per seed, seed 42 reused for tuning.** Observed seed-to-seed swings of 10–17 points (V9A 69–82, V15G 76–87, V15B 79–86). Almost every "breakthrough" (V9: 81, V10A: 83) was a single seed-42 run that shrank when replicated (76, 81). Versions were designed *after looking at seed-42 disagreements*, so later versions overfit the same 100 studies; when V15G finally used fresh seeds it landed at 80.
3. **The input underdetermines the answer.** The unit being classified was a 2–5-word DeepSeek paraphrase of a one-line FReD `description` (often a paper title — "Functional smiles: Tools for love, sympathy, and war"; "Power manipulation"). Whether power was *induced* or *measured*, whether a smile was a *photo* or a *confederate*, whether "decision-making behavior" was *real* or *hypothetical* is simply not in the text. Every report from V4 onward says this ("the ambiguity is in the source data"), and the persistent confusion pairs never changed: TASK/INSTRUCTION vs TRAIT, INSTRUCTION vs DISPLAY ("think about X" vs "read about X"), ESTIMATE vs RATING, BEHAVIOR vs RATING. The X/Y extraction step itself was single-model, zero-shot, never validated.
4. **Structural mis-framing, correctly diagnosed and then ignored.** `prompt_for_taxonomy_rethink.md` states the real problem: X categories mix *content*, *delivery method* and *mechanism*, and multi-IV designs cannot get one label. The obvious fixes — multi-label, separate facets, an explicit "unresolvable from text" state — were then written into the briefs as **hard constraints not to do** ("must produce exactly one X label", "no OTHER", "no multi-label"). V10B (two facets for X) was scored on all-three-match and declared a failure at 60.6% even though its Y was 91.9% and its channel facet was the same idea as V10A. V6 (multi-label) has no saved results.
5. **Goal drift and late discovery of existing metadata.** The goal shifted from "find similar studies" → "maximize LLM agreement on X/Y" → (Dec 28) "classify domain from abstracts" — at which point it turned out that OpenAlex already supplies subfield/topic for 97% of rows and that broad-domain agreement from abstracts is 92–97%. The topic-organization problem was essentially solved by external metadata in one day; the two-day X/Y campaign was solving a different, much harder, and less necessary problem.
6. **Data skew made "emergent" structure fake.** Legacy FReD is dominated by multi-site anchoring/JDM replications: `tags` = "anchoring, anchor, numerical estimates…" on 477 rows; CORE 223, ML1 352, OpAQ 479 rows; `openalex_analysis/broad_group_row_vs_doi.csv` shows Decision/Economics has 747 rows from 56 DOIs (13.3 rows/DOI) and Applied/Safety 265 rows from 20 DOIs. Clusters like "Previous Value Influence" (248 identical phrases) and Y "Numerical Estimate Effects" (495) are artifacts of row multiplicity, not of the field's structure. Silhouettes of 0.29 confirm there is no clean cluster structure in the embedded phrases.
7. **Process.** 17 versions in ~36 hours, driven by LLM agents writing briefs to each other (`v4_feedback_for_taxonomy_agent.md`, `taxonomy_improvement_brief_v2.md`, …) with no human coder in the loop; V17 was abandoned mid-run; the five-phase implementation plan was never started; nothing was ever applied to the full dataset except the unvalidated cluster labels. `taxonomy.json` double-counts members; `emergent_clusters.json` is not even valid JSON.
8. **Security hygiene.** About twenty of these scripts contain a live-looking OpenRouter API key and `emergent_clustering.py` / `full_emergent_pipeline.py` contain an OpenAI project key in plaintext. These must be rotated and must not be copied into the new repo.

---

## 5. What is salvageable

### 5.1 The hand-curated famous-effects list (high value)
- `docx_parsed_entries.json` — **362 entries** parsed from `Psychology Replications (1).docx`: `name`, `description`, `discipline`, `status`, `original_paper` (351 carry a year), `critiques`, `original_es`, `replication_es`. Status after trivial normalization: replicated ≈113, mixed ≈118, not replicated ≈100, reversed 9, NA/None ≈21. Disciplines: Social Psychology 99, Cognitive Psychology 90, JDM 50, Political Psychology 34, Marketing 28, Developmental 14, Parapsychology 12, Speech Language Therapy 9, Experimental Philosophy 8, Educational 6, Psychiatry 4, Positive Psychology 2, Psychophysiology 2, Applied Linguistics 2, Health 2.
- `canonical_effect_names.json` — **361 `{name, discipline}`** objects; 352 of 353 normalized names are identical to the docx list. It is *not* a canonicalization of FReD effect names — it is the docx list with a cleaned discipline field. Use it as the seed of the wiki's effect registry, but it needs dedup and alias work (e.g. "Imagined Contact - Bias" / "Imagined Contact - Intentions"; parenthetical synonyms inside names).
- `all_known_effects.txt` — 724 lines, **598 unique normalized names** = union of the legacy FReD `effect` column (390 of its 392 unique values) and the docx names (353). Overlap between the two sources is only **149** names, i.e. the docx list and FReD cover largely different territory. Contains junk lines (a horse-cognition sentence, "of Japanese Kanji', Yamazaki et al") and ~30 fine-grained "Age of acquisition influence on …" variants that should collapse to one effect with sub-findings.
- Note: the **current** FReD (`data/raw/forrt/fred-data/output_FReD.xlsx`, 2,164 rows, 56 columns) has **no effect-name column at all** — only `effect_id` (a row counter), `description` (a claim sentence), `discipline`, `tags`. Legacy v1 had `effect` (2,620 non-null, 440 unique). Any effect registry therefore has to be built by us (from legacy `effect`, docx names, FLoRA/FReD descriptions, and manual curation).

### 5.2 Validated low-cardinality facets (medium value)
Reusable *because* they were the only things that held up across many samples and framings:
- Outcome format, 5 values (physiological / objectively scored / real-consequence behavior / open number / scale-rating): 88–94% two-model agreement; known ambiguous pairs listed in §3.
- IV kind, 3 values (manipulated / measured / context): 94%. Effect type (main / interaction / mediation / moderation): 94%.
- Broad domain, 3–5 values: 92–97% from abstracts.
Prompts for these are in `test_taxonomy_v10.py` (V10A block), `test_taxonomy_agreement.py` (V3_PHENOMENON), `test_methodology_only.py`. Use them only with two-model consensus + human review of disagreements, and never as a forced single label.

### 5.3 OpenAlex enrichment and its mappings (medium-high value)
- `openalex_original_enrichment.json` (1,623 DOIs; 1,590 with topics) and `openalex_analysis/work_groupings.csv` (1,599 works with primary topic, top-3 topics with scores, subfield/field/domain, broad category, plus cited_by, fwci, OA status, abstract). Keyed by original DOI — joins cleanly to the new FReD/FLoRA `doi_o`.
- `analyze_openalex_topics.py::map_broad_category()` — a 10-rule collapse of OpenAlex subfields into Cognitive/Neuroscience, Social/Intergroup, Development/Education, Clinical/Health, Decision/Economics, Methods/Statistics, IO/Business/Marketing, Applied/Safety, Arts/Humanities, Other STEM, Other. Work-level counts: Cognitive/Neuroscience 474, Social/Intergroup 362, Clinical/Health 177, Decision/Economics 128, Development/Education 126, IO/Business/Marketing 87, Applied/Safety 76, Other STEM 62, Other 60, Arts/Humanities 24, Methods/Statistics 14. Row-level: Social/Intergroup 1,126, Decision/Economics 923, Cognitive/Neuroscience 862, Applied/Safety 477, …
- 661 distinct OpenAlex topics over the corpus; the top ones are genuinely useful navigation labels: "Social and Intergroup Psychology" 227 works, "Psychology of Moral and Emotional Judgment" 182, "Decision-Making and Behavioral Economics" 148, "Cultural Differences and Values" 121, "Neural and Behavioral Psychology Studies" 116, "Behavioral Health and Interventions" 112, "Evolutionary Psychology and Human Behavior" 74, "Memory Processes and Influences" 57, "Reading and Literacy Development" 55, "Face Recognition and Perception" 42, "Death Anxiety and Social Exclusion" 39.
- `discipline_vs_primary_subfield.csv` shows how FReD `discipline` and OpenAlex relate: JDM → General Decision Sciences 482/483; Experimental Philosophy → Cognitive Neuroscience 28/43; "Psychology" (1,649 rows) spreads over Applied Psychology 292, Cognitive Neuroscience 253, Sociology & Political Science 232, Social Psychology 227; the 1,542 discipline-NaN rows are mostly Cognitive Neuroscience / Sociology & Political Science / Social Psychology. So OpenAlex fills exactly the gap where FReD discipline is missing or generic.
- Caveats to carry forward: OpenAlex subfield names are odd for psychology ("Experimental Behavioral Economics Studies" sits under *Safety Research*; "Media Influence and Health" under *Literature and Literary Theory*; "Cognitive and developmental aspects of mathematical skills" under *Statistics and Probability*), so the broad mapping needs a curated override table. Legacy OpenAlex *concepts* are noise ("Quantum mechanics" 193 works, "Paleontology" 131 in `concept_counts.csv`) — ignore concepts, use topics/subfields and possibly keywords.

### 5.4 Cognitive Atlas keyword list (low-medium value)
`cogatlas/cognitive_atlas_keywords.csv` — 2,339 exact terms (1,010 concepts, 1,108 tasks, 221 disorders) with Cognitive Atlas IDs and definitions, CC BY-SA 3.0, plus `demo_tagger.py` (strict longest-match, word-boundary tagger). **Never applied to FReD** (no script references it). Its own README predicts 20–40% match rates on social-psychology abstracts. Worth keeping as an optional precision-first tagger for cognitive/neuro items and as a source of task names ("Stroop task", "dictator game") for a "paradigm" facet.

### 5.5 Discard / archive
- `taxonomy.json`, `taxonomy_v2.json`, `labeled_clusters.json`, `improved_clusters.json`, `optimal_clusters_results.json`, `hierarchical_clusters.json`, `full_emergent_clusters.json`, `emergent_clusters.json` (invalid JSON), `cluster_quality_analysis.json`, `optimal_k_analysis.json` — unvalidated, anchoring-skewed, keyed to legacy row ids.
- All `test_taxonomy_v*.py`, `test_v10a_updated.py`, `create_taxonomy*.py`, clustering scripts, `extract_disagreements.py` — one-off harnesses with hard-coded keys.
- `taxonomy_v*_results.json`, briefs and reports — keep only as history (this document summarizes them).
- `full_extraction_progress.json` (2,445 X/Y phrases) — borderline: usable as *draft* "what was varied / what was measured" snippets for study pages if shown as unreviewed suggestions, otherwise archive.

---

## 6. How the new wiki should organize topics (without repeating this)

Principles derived from the failure: **facets, not a tree; observed metadata before inferred labels; low cardinality where inference is needed; every LLM-inferred label carries provenance + a review state; human gold set and kappa before scaling; no single-label forcing.**

Proposed facet set (each is a separate column/relation, all filterable and combinable in the explore UI; "topic pages" are saved facet queries plus a curated blurb):

1. **Discipline (FReD-native).** Normalize the new FReD `discipline` (40 raw values → ~30 after trim/lowercase: Social Psychology 643, Cognitive Psychology 442, Psychology 151, Marketing 129, Economics 119, Management 103, Experimental Philosophy 75, Education 74, Differential Psychology 69, JDM 48, Linguistics 47, Neuroscience 43, Developmental 35, …) through a small mapping table to a controlled list; keep the raw value. FLoRA rows without a discipline inherit from OpenAlex.
2. **Field / area (OpenAlex, per original paper).** Store primary subfield + top-3 topics with scores for every `doi_o` (and `doi_r`). Provide a curated ~9-area collapse (reuse `map_broad_category` rules with overrides for the Safety-Research/Literature oddities). This is the browse-by-area entry point and covers ~97% of items with zero inference.
3. **Effect / phenomenon (curated registry).** One record per effect with canonical name, aliases, one-sentence claim, and links to every FReD `fred_id`, FLoRA pair, project, and famous-effect docx entry. Seed: 362 docx effects (with status, critiques, ES) + 392 legacy FReD effect names + manual passes. This is the wiki's spine; the ~360 famous effects get hand-written tags and are the pool for the guessing game.
4. **Method facets (LLM-assisted, only the robust ones):** outcome format (5), IV kind (3), effect type (4), maybe "sample type" (student/online/field/child/clinical) which was never tested but is largely extractable from FReD `n`/`participants` text. Apply with two-model consensus; disagreements are stored as `unresolved`, shown as such, and queued for human review — never coerced. Validate on a 200-item human-coded set and publish kappa in the docs.
5. **Keyword tags.** Split FReD `tags` (727 unique strings, comma/semicolon lists such as "anchoring, anchor, numerical estimates, anchoring and adjustment, heuristics and biases") into a normalized tag vocabulary; add OpenAlex keywords; optionally Cognitive Atlas concept/task matches on abstracts, flagged by source.
6. **Project / source** (ML1–5, RP:P, SSRP, CORE, OpAQ, Many Babies, …) and **paradigm** (dictator game, Stroop, IAT — from Cognitive Atlas task list + manual) as further facets.
7. **Similarity, not clusters.** For "related studies", use nearest neighbours over embeddings of abstract + description (per effect, deduplicated across multi-site rows) rather than any fixed clustering; the silhouette results show there is no stable partition to find.

Things to explicitly not do again: single-label mutually-exclusive X/Y trees; iterating prompts against one 100-item sample; using inter-model agreement as the quality bar; letting one source (anchoring multi-site rows) dominate any data-driven structure without deduplicating to the effect level; committing API keys.
