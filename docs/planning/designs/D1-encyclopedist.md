# D1 — The Encyclopedist: information architecture and editorial model

Status: COMPLETE (v1, 2026-09-07). Author: design agent D1 (angle: entity model, identifiers, page types, curation overlay, status vocabulary).
Inputs: `_planning/BRIEF.md`, `_planning/understanding/_DIGEST.md`, U3/U5/U6 full reports, and direct pandas runs on the FORRT files (scripts in the session scratchpad: `d1_counts.py`). Every number below was computed from the files on disk on 2026-09-07 unless it cites a reader report.

Files read for the numbers:
- `data/raw/forrt/fred-data/output_FReD.xlsx` (2,164 x 56) and `data/raw/forrt/fred-data/archive/2025-11-30_COSdata_validated.xlsx` (2,164 x 44; adds r_o, r_r, statistical_success, fred_id_old, correct entry_id/effect_id)
- `data/raw/forrt/osf/version-history/FReD_2.4.1_2025-06-25.xlsx` sheets `Data` (4,659 data rows x 100), `FORRT R&R (editable)` (1,406 x 75), `Reversals Effects` (583 x 6)
- `data/raw/forrt/fred-data/output_flora.csv` (2,815 x 35)
- `docx_parsed_entries.json` (362 famous effects)

---

## 0. The one-paragraph design

The wiki is an **effect registry** with everything else hanging off it. One immutable ID per effect; a human slug for the URL; an alias table absorbing the four name sources (legacy FReD `effect`, FORRT Reversals/R&R sheet, the docx famous-effects list, and machine-suggested names, each with provenance and review state). Under each effect sit **Claims** (one original study x one tested claim), under each claim sit **Attempts** (one replication paper/study testing it), and every attempt carries three independent verdict lenses: *what the authors said* (FLoRA `outcome` + quote), *what the numbers say* (FReD effect sizes run through the R package's seven criteria), and *how close the design was* (legacy closeness_*, prereg, power, author overlap). A page-level **status** is computed by fixed, published rules from the author-reported lens (the only lens with wide coverage), shown with a confidence tier and a link to the rule; the numerical lens is shown beside it and may disagree, visibly. Humans never edit generated data: they write one YAML+Markdown file per effect in `curated/` (narrative, aliases, corrections, textbook notes, status overrides with justification), merged at build time via git pull requests with schema validation. Papers, projects, authors, topics, paradigms and collections are secondary entry points, all generated, all cross-linked to effects.

---

## 1. Entity model

### 1.1 Entities, grains, sources, expected counts

| Entity | Grain (what one row means) | Primary sources | Expected count at first build (computed) |
|---|---|---|---|
| **Effect** (a.k.a. Finding) | A named phenomenon/claim family that people talk about ("Macbeth effect", "ego depletion"). Owns aliases, narrative, status. | legacy FReD `effect` (442 raw / 414 case-normalized names), Reversals sheet (583), R&R sheet `effect` (584, identical set + 1), docx (361 names), plus *unnamed* effects created from originals that carry no name | ~750 named clusters (961 exact-lower union -> 802 after normalizing parentheticals/"effect"/punct -> 749 after fuzzy ratio >= 92; 59 fuzzy merges need review) + ~3,100 unnamed "finding stubs" (one per original paper without a name; see 2.4). Target after phase 1 curation: ~800 named effects, ~3,000 stubs. |
| **Claim** | One original study x one tested result. FReD's unit (`doi_o`, `study_o`, `claim_text_o`). | current FReD (865 distinct (doi_o, study_o); 1,743 distinct claim_text_o), legacy FReD (`study_original`, `claim_text_orig`), FLoRA has no claim grain (paper only) | ~2,000 FReD-backed claims; FLoRA-only originals get one implicit "paper-level claim" each (1,728 FLoRA-only originals) |
| **Original Study** / **Paper** (role = original) | A DOI (or URL/handle for DOI-less works) | union of doi_o across FLoRA, current FReD, legacy Data, R&R | **3,820** distinct original DOIs (FLoRA 2,589; current FReD 786; legacy 1,698; R&R 479 unique) |
| **Replication Attempt** | One (original paper, replication paper-or-URL) pair — FLoRA's unit; with nested **effect rows** (FReD grain) for statistics | FLoRA (2,526 replication pairs + 289 reproduction pairs), current FReD (859 pairs / 2,164 effect rows), legacy (1,094 additional pairs), R&R (472 with doi_replication) | **4,550** distinct (original, replication-id) pairs across all sources; 3,672 with a usable outcome grain after dedupe (FLoRA > FReD > legacy priority) |
| **Paper** (any role) | DOI-identified work | all of the above | **7,491** distinct DOIs (3,820 originals + 3,730 replication papers, 59 in both roles) + ~600 URL-only works (FLoRA 200 url_r-only rows, FReD 383 url_r) |
| **Project** | A coordinated multi-study replication effort (Many Labs 1-5, RRRs, RP:P/OSC2015, SSRP, CORE, X-Phi, OpAQ, Boyce student replications, PSA, SCORE/COS, ManyBabies, Data Replicada, OpenMKT, ...) | legacy `source` (32 labels), FLoRA mega `doi_r` (10 papers with >= 10 originals, 15 with >= 5), FORRT's list of 25 large-scale projects (U7), current `fred_id` prefixes (ManyLabs, RRR_, Camerer, Holzmeister, Soto, XPHI, CORE_, OpenMKT, osc, jcre_, Boyce_etal) | ~35 projects at launch, hand-registered in `curated/projects/*.yaml` with matching rules (source label, doi_r, fred_id prefix) |
| **Author / Lab** | A person (ORCID when available) | FLoRA `author_o`/`author_r` JSON (given/family/sequence; 7,594 distinct family names among FLoRA originals alone), FReD `author_o`/`author_r`, OpenAlex authorships (+ORCID, institution) | ~15,000 author strings; pages only for authors with >= 2 papers in the corpus or any effect page (est. ~3,000) |
| **Topic / Discipline** | Facets, not a tree: (a) FORRT discipline (current 34 normalized labels; legacy 123 raw; Reversals 22; docx 15), (b) OpenAlex subfield/topic (144 topics in field 32; 97% coverage), (c) curated tags | FReD discipline + OpenAlex + `curated/topics/*.yaml` override table | ~30 disciplines, ~150 OpenAlex topics, ~100 curated tags |
| **Paradigm** | The experimental task/manipulation family (anchoring task, scrambled-sentence priming, Stroop, dictator game, trolley problem...). Distinct from Effect: one paradigm serves many effects, one effect may be tested with several paradigms. | Cognitive Atlas task list (1,108 tasks) as controlled vocabulary + curated assignment; machine-suggested from FReD `description`/`tags` with provenance | ~120 paradigms at launch (curated), rest as suggestions |
| **Collection** | Editorial list ("Effects every intro textbook teaches", "Most-cited unreplicated", "Reversed effects", "Registered Replication Reports", "Effects with > 5 attempts") | `curated/collections/*.yaml` with either an explicit ID list or a query over the normalized data | ~15 at launch |
| **Journal** | Venue | FLoRA/FReD journal fields + ISSN via Crossref | ~800 |
| **Candidate** (review-queue item) | A discovered (doi_o?, doi_r, evidence, proposed outcome) not yet in FORRT or in our overlay | discovery pipeline (D-other agents) | rolling |

### 1.2 Relationships (all many-to-many unless stated)

```
Effect 1---* Claim *---1 Paper(original)
Claim  1---* Attempt(effect-row) *---1 Attempt(pair) *---1 Paper(replication or reproduction)
Attempt(pair) *---0..1 Project
Paper *---* Author ; Paper *---1 Journal
Effect *---* Topic ; Effect *---* Paradigm ; Effect *---* Collection ; Effect *---* Effect (related / reversed-by / subsumes / sibling-of-same-original)
Effect 1---0..1 CuratedOverlay (one YAML/MD file)
Candidate *---0..1 Effect (proposed) ; Candidate ---> Attempt (on acceptance)
```

Key modelling decisions:
- **An Attempt exists at two grains**, mirroring FORRT: the *pair* (FLoRA grain; carries `outcome`, `outcome_quote`, `type` replication|reproduction, `source`) and the *effect row* (FReD grain; carries `n_o, es_o, es_type_o, p_o, n_r, es_r, ..., reported_success`). Effect rows nest under the pair via `(doi_o, id_r)`; pair-level author verdict is inherited by rows that lack `reported_success`. This is exactly the join U5 verified (1,783 rows / 678 pairs; 93.3% agreement).
- **Reproductions are Attempts with `type = reproduction`** and their own outcome vocabulary (FLoRA: `computationally reproducible, robust` 1 / `computationally reproducible, robustness challenges` 2 / `computational issues, not checked` 1 / `computational issues, robustness challenges` 1; 284 of 289 NA). They never feed the replication **status**; they feed a separate **Reproducibility badge** on the paper and effect page.
- **Claims are the bridge between FReD and effects.** FReD rows already carry `study_o` and `claim_text_o` (2,131 filled). A claim is `(doi_o, study_o, claim_key)` where `claim_key` = normalized `claim_text_o` (or `description` when claim text is missing). Effects group claims; the Macbeth effect groups four claims (Zhong & Liljenquist 2006 Studies 1-4), each with its own replication rows.
- **Effects may span several original papers** (legacy: 372 named effects have 1 original DOI, 28 have 2-3, 3 have >= 4: ego depletion 7, heat priming 6, anchoring 4). And one original paper may carry several effects (legacy: 280 originals map to one name, 63 to several). So Effect<->Paper is many-to-many through Claim.

### 1.3 Identifiers

| Entity | Immutable ID | URL slug (mutable, redirected on change) | Source IDs kept as provenance |
|---|---|---|---|
| Effect | `fx_` + 8 chars Crockford-base32 of sha1(canonical name at creation + first original DOI) e.g. `fx_3vq8h2kd`; assigned once by `registry/effects.csv`, never recomputed | `macbeth-effect` (kebab-case of canonical name, ASCII, <= 60 chars; collisions get `-2`, `-zhong-2006`) | legacy `effect` string(s), Reversals row index, docx `name`, R&R `id` (FORRT_n) |
| Claim | `cl_` + 8 chars of sha1(doi_o + "|" + study_o + "|" + claim_key) | anchor on the effect page `#claim-<id>` (no standalone URL) | FReD `entry_id` (from the archive file, *not* output_FReD's constant 1), `fred_id`, `fred_id_old`, legacy `rowid` |
| Paper | normalized DOI (lowercase; strip `https://`, `dx.`, `doi.org/`, `doi:`); DOI-less works: `url:` + normalized URL, or `hdl:` handle | `/papers/<md5(doi)>/` canonical (identical to FLoRA `doi_o_hash`/`doi_r_hash`, so FORRT's Zotero prefix-lookup semantics carry over) with a readable alias `/papers/zhong-2006-washing-away-your-sins/` | OpenAlex W-id, Semantic Scholar id, PubMed id when fetched |
| Attempt (pair) | `at_` + 12 hex of sha1(doi_o + "|" + id_r) where `id_r = doi_r ?? url_r ?? alt_identifier_r ?? osf_link` (FORRT's own coalesce rule) | `/attempts/<at_id>/` | FLoRA row hash pair; FReD `fred_id`; legacy `id`; source project label |
| Attempt (effect row) | `at_<pair>.<k>` where k = FReD archive `effect_id` within entry, else running index | anchor on the attempt page | `fred_id`, `fred_id_old`, legacy `rowid` |
| Project | slug, hand-assigned (`many-labs-2`, `rpp-2015`, `rrr-ego-depletion`) | `/projects/<slug>/` | legacy `source` label(s), FLoRA `doi_r`, `fred_id` prefix regex |
| Author | ORCID when known, else `au_` + sha1(family|given-initial) — with a merge table in `curated/authors.yaml` | `/authors/<slug>/` | OpenAlex author id |
| Topic | `disc:<slug>` for FORRT disciplines, `oa:T<id>` for OpenAlex topics/subfields, `tag:<slug>` curated | `/topics/<slug>/` | - |
| Paradigm | `pd_<slug>`; Cognitive Atlas id when mapped | `/paradigms/<slug>/` | cogatlas id |

Rules: IDs live in `registry/*.csv` files that are **committed** (they are the only generated files that are versioned, because stability matters more than regenerability). The build refuses to run if a registry ID would be re-assigned. Merging two effects = one keeps its ID, the other's ID goes into `registry/redirects.csv` (`from_id, to_id, reason, pr`). A DOI that FORRT later changes (`DOI_changed` column exists in legacy) gets a paper-level redirect the same way.

---

## 2. The ONE effect registry: sources, merge algorithm, expected counts

### 2.1 Name sources and how they overlap (computed)

| Source | Names (exact, lower/strip) | Notes |
|---|---|---|
| Legacy `Data.effect` (L) | 442 raw -> **414** | only place FORRT's *coded* rows are named; 2,623 rows named; 403 of 414 names have a `doi_original`; 137 have >= 1 row in current FReD; 259 have an original DOI in FLoRA |
| Reversals Effects sheet (V) | **583** | columns `effect renamed`, `alternative names`, `status` are 100% empty; only discipline/effect/description filled |
| FORRT R&R (editable) sheet (R) | **584** | same list as V + 1; 1,406 rows; 550 names have `doi_original`, 472 have `doi_replication`; 154 originals in FLoRA, 119 in current FReD; essentially non-validated (validated NaN 1,390) |
| docx famous effects (D) | **361** (362 entries, 1 duplicate name) | adds status/critiques/GS citations/free-text ES; 0 DOIs; 329 quoted original titles |
| Overlaps | L&V 179, L&D 100, V&D 218, R&V 583, R&D 218 | union exact 961; L-only 234, D-only 142, V-only 0 (vs R), R-only 1 |
| After normalization (strip parentheticals, "effect", punctuation) | 802 | e.g. "Flag Priming"/"flag priming" (already merged), "MacBeth Effect"/"Macbeth effect" (merged), "pre-cognition" vs "precognition" (NOT merged, needs fuzzy). **Counter-example that forces the DOI guard (step 1d):** "moral priming (cleanliness)" normalizes to "moral priming", but legacy "Moral Priming" is 70 rows of Mazar et al. 2008 (10.1509/jmkr.45.6.633) while "moral priming (cleanliness)" and "cleanliness priming" are Schnall et al. 2008 (10.1111/j.1467-9280.2008.02227.x) - verified in the Data sheet. Name normalization alone would merge two different effects. |
| After fuzzy ratio >= 92 (rapidfuzz) | **749 clusters** (59 merges) | half the merges are the ML1 "age of acquisition influence on ... stages of lexical retrieval in ... languages" family, which are *distinct claims of one effect* - so fuzzy merges are correct there but must be reviewed as a batch |

### 2.2 The merge algorithm (deterministic, re-runnable, every step logged to `build/logs/registry_merge.jsonl`)

**Step 0 - Normalize DOIs everywhere** (lowercase, strip prefixes, percent-decode, strip trailing punctuation; port `openalex_utils.normalize_doi`). Normalize names: `norm(name)` = lower, collapse whitespace, strip parentheticals into a separate `qualifier` field, drop stop-words {the, effect, effects, phenomenon}, strip punctuation.

**Step 1 - Seed name clusters from the four name sources.**
1a. Exact-`norm` union -> 802 clusters. Each cluster records every raw spelling as an alias with `source` in {legacy, reversals, rr, docx}.
1b. Fuzzy pass (rapidfuzz `ratio >= 95` **auto-merge**, `92 <= ratio < 95` -> `review_queue/aliases.csv` for a human yes/no) -> ~760 clusters auto, ~15 pending.
1c. Discipline guard: never auto-merge two names whose FORRT disciplines differ (prevents "priming" in Social vs Cognitive collapsing).
1d. **DOI-disjoint guard** (applies to 1a and 1b alike, evaluated after step 2 attaches DOIs): a merge between two raw names is auto-applied only if their original-DOI sets intersect or one side has no DOI at all; if both sides have DOIs and the sets are disjoint, the merge is *rejected* and the names stay separate effects with a `possible_duplicate` link for review. This is what keeps "moral priming (cleanliness)" (Schnall 2008) apart from "Moral Priming" (Mazar 2008, 70 rows) even though they normalize to the same string, and it is why steps 1 and 2 run as one fixpoint loop rather than in sequence.

**Step 2 - Attach original DOIs to clusters.**
- From L: `effect -> doi_original` (403 names get DOIs; 2,623 rows).
- From R: `effect -> doi_original` (550 names).
- From D: resolve the 329 quoted titles to DOIs via Crossref `query.bibliographic` (title + surname + year; accept when Crossref score is top-1 and fuzzy title ratio >= 90 and year within +-1). U3 measured 68% fuzzy hits against local titles alone; Crossref should push this above 90%. Unresolved ones go to `review_queue/docx_dois.csv` (expected ~30).
- Result: each cluster has `original_dois: set`. Expected: ~700 of 749 clusters with >= 1 DOI.

**Step 3 - Merge clusters that share an original DOI *and* refer to the same claim.**
- Same DOI + fuzzy name >= 85 -> merge. Verified example: "cleanliness priming" (4 legacy rows) and "moral priming (cleanliness)" (2 rows) both point at 10.1111/j.1467-9280.2008.02227.x (Schnall et al. 2008) and score >= 85 after normalization, so they become one effect; "Moral Priming" (70 rows, 10.1509/jmkr.45.6.633) stays a separate effect because its DOI set is disjoint (step 1d).
- Same DOI + different names -> keep separate effects but link them as `sibling_of_same_original` (63 legacy originals carry several names; e.g. Zhong & Liljenquist 2006 could later host "Macbeth effect" and "cleansing reduces helping" as two effects).

**Step 4 - Create unnamed finding stubs for every original that has attempts but no name.**
- Current FReD: 1,605 of 2,164 rows have no name via `fred_id`==legacy `id` (365), via (doi_o, doi_r) pair (391) or via a doi_o that carries exactly one legacy name (394): union 559 named, **1,605 unnamed rows = 629 distinct doi_o / 814 fred_ids**. Unnamed prefixes: additional_studies 351, Boyce_etal 270, av_ 164, add_ai 162, osc 94, jcre_ 71, XPHI 69, Soto 60, OpenMKT 49, Camereretal 34.
- FLoRA: 2,589 distinct doi_o, only 228 carry a legacy/R&R name; **1,728 originals exist only in FLoRA**.
- Rule: one stub per (doi_o) with `name_status = unnamed`, display name = `"{first_author} ({year}): {claim_text_o or description or title_o}"` truncated to 90 chars, e.g. "Boyce (2023): Eleven years of student replication..." is the *replication*, so the stub takes the *original's* first author. Stubs are real effect pages (they have attempts and status) but carry a "This finding has no established name yet - suggest one" affordance.
- Machine-suggested names (LLM over `claim_text_o` + `description` + `title_o`; the old `fred_enriched.csv` has ~1,750 such suggestions) are stored as aliases with `source = machine`, `review_state = suggested`, never shown as the H1 until a human promotes them in the overlay.
- Expected: ~3,100 stubs (3,820 original DOIs minus ~700 named).

**Step 5 - Attach attempts.** For every effect, attempts = all pairs whose `doi_o` is in `original_dois` **and** (when the effect is one of several on that original) whose claim rows map to the effect's claims. Claim->effect mapping comes from legacy `effect` on the row, from R&R rows, or from the overlay's `claims:` list; rows on a multi-effect original that map to no effect stay on the original-paper page and on a per-paper stub.

**Step 6 - Compute status, confidence, numbers (section 4), then apply overlays (section 6).**

**Step 7 - Emit** `registry/effects.csv` (id, slug, canonical_name, name_status, created_in_build), `registry/aliases.csv` (effect_id, alias, source, review_state), `registry/redirects.csv`, and the normalized `effects.parquet/json`.

### 2.3 Expected counts after the first automated run (before human curation)

| Quantity | Expected |
|---|---|
| Named effect clusters | ~749 (auto) -> ~720 after review of 59 fuzzy merges and same-DOI merges |
| Named effects with >= 1 attempt with an outcome | ~600 (legacy: 404 of 414 names have attempts; R&R adds names with doi_replication 472; docx-only 142 names need Crossref resolution -> attempts via FLoRA) |
| Named effects with FReD numeric rows (forest-plot-able) | ~250 (137 names in current FReD + legacy names with r-scale ES: 362 legacy rows have r both sides outside current) |
| Unnamed stubs | ~3,100 |
| Effects total | ~3,850 |
| Attempts (pairs) | 4,550 (3,672 with outcome grain: success 1,096 / failure 948 / mixed 590 / inconclusive-or-NA 1,038) |
| Effect rows with stats | 2,164 current + 3,234 legacy-only (362 with r on both sides, 743 validated) |
| docx entries linked to an effect with attempts | 218 immediately (name match to Reversals) + ~100 via title->DOI = ~320 of 362 |

### 2.4 Why stubs and not "only named effects"

FLoRA is the fast-growing table (1,126 -> 2,815 rows in six months) and 67% of its originals have no name anywhere. If the wiki only had named effects it would be a 700-page site that goes stale; with stubs every FORRT pair has a home page from day one, and naming becomes a curation task with a visible queue ("2,900 findings still unnamed - top 50 by citations"). Stubs also make the discovery pipeline's output landable: a new candidate always attaches to an original DOI, hence to a stub or an effect.

---

## 3. Naming, aliases, disambiguation

- **Canonical name** = the most common human spelling among sources with priority docx > Reversals > legacy > R&R > machine, unless the overlay sets `name:`. Title-case only proper nouns ("Macbeth effect", not "Macbeth Effect"); no trailing "effect" duplication rules - keep the natural phrase.
- **Alias record**: `{alias, effect_id, source ∈ {legacy, reversals, rr, docx, machine, curator, wikipedia}, review_state ∈ {imported, suggested, confirmed, rejected}, note}`. All aliases are searchable; rejected ones are excluded from search but kept so re-imports do not resurrect them.
- **Qualifier**: parenthetical fragments become a `qualifier` shown as a subtitle ("Moral priming - cleanliness manipulation"), and when two effects share a normalized name they are disambiguated by qualifier in the slug (`moral-priming-cleanliness`, `moral-priming-contemplation`).
- **Disambiguation page**: any normalized name shared by >= 2 effects gets `/effects/<norm>/` listing them with one-line descriptions and original citations (like Wikipedia's disambiguation). Expected ~40 such pages (e.g. "priming" 8 rows across 2 originals; "anchoring effect" 4 originals).
- **Effect vs paradigm confusion** is the main naming hazard in the legacy list ("Anchoring Effect" has 552 legacy rows because ML1 tested four anchoring *claims* at 36 sites). Rule: a name that appears on >= 2 originals with different claims is an **effect**; the shared task is a **paradigm**; claims keep their own one-line names ("Anchoring - distance to NYC").
- **Reversal naming**: never rename a reversed effect; add the reversal as a statement on the page ("Later evidence points the other way") and a `reversed_by:` attempt list. The Reversals sheet's `effect renamed` column is empty in FORRT's data, so there is no upstream renaming to honour.
- **Search** indexes canonical name, all confirmed/imported aliases, claim texts, original titles, first-author-year strings ("Zhong 2006"), DOIs.

---

## 4. Status vocabulary (data-driven rules)

### 4.1 Per-attempt verdict normalization (the input)

All three source vocabularies collapse to one 4-value `verdict`:

| verdict | FLoRA `outcome` | FReD `reported_success` | legacy `result` |
|---|---|---|---|
| success | successful (1,042) | successful (985) | success (678) + "sucess" typo (1) |
| failure | failed (901) | failed (787) | informative failure to replicate (726) |
| mixed | mixed (564), statistically successful but flawed (7) | mixed (359), statistically successful but flawed (18) | - |
| inconclusive | descriptive only (6), uninformative (4), NA | descriptive only (10), uninformative (5) | inconclusive (18), practical failure to replicate (3), NA |

Pair-level verdict when a pair has several FReD effect rows: all success -> success; all failure -> failure; any informative disagreement -> mixed; none informative -> inconclusive. Priority when the same pair is in several sources: FLoRA > current FReD > legacy > R&R (FLoRA is FORRT's most recent human coding; 93.3% agreement with FReD where both exist). Disagreements are kept as `verdict_conflicts` and shown on the attempt page.

### 4.2 Effect status (the output) - 8 values

Let `n` = informative attempts (success+failure+mixed) among **replications** (type = replication; reproductions excluded), `s`, `f`, `m` their counts, distinct by pair.

| Status | Rule | Colour token |
|---|---|---|
| **Untested** | no attempt of any kind linked | ink-faint |
| **Insufficient evidence** | attempts exist but `n = 0`, or `n = 1` and it is mixed | grey |
| **Replicated** | `s >= 1`, `f = 0`, `s >= m`. Qualifier chip "single attempt" when `n = 1` | green |
| **Largely replicated** | `n >= 4`, `s/n >= 0.75`, `f >= 1` | green-outline |
| **Contested** | `s >= 1` and `f >= 1` with neither share >= 0.75, or `m > max(s, f)` with `n >= 2` | amber |
| **Largely failed** | `n >= 4`, `f/n >= 0.75`, `s + m >= 1` | red-outline |
| **Failed** | `f >= 1`, `s = 0`, `f >= m`. Qualifier chip "single attempt" when `n = 1` | red |
| **Reversed** | **curated flag only** (overlay `status_override: reversed` with a cited attempt). The build computes `reversal_candidate = true` when any effect row has `sign(r_r) != sign(r_o)` and `p_r < .05` (40 rows / 30 originals today), but 4 of the first 12 candidates are rows FORRT coded *successful* - FReD sign conventions are not reliable enough to auto-declare a reversal | vermilion |

Overlays: an original paper flagged retracted (Retraction Watch / OpenAlex `is_retracted`) adds a **Retracted original** banner that sits above the status, without changing it. A paper-level "Reproducibility" badge (from reproductions) is separate.

### 4.3 Dry run of the rules on today's data

Attempt pairs after dedupe: 3,672 -> verdicts success 1,096 / failure 948 / mixed 590 / inconclusive 1,036 (mostly legacy rows with no `result`). Attempts per original: median 1, mean 1.14, max 9; only 285 originals have >= 2 attempts, 19 have >= 5.

| Status | by original paper (3,229 originals with attempts) | by named legacy effect (414) |
|---|---|---|
| Insufficient evidence | 1,358 | 171 |
| Replicated (single attempt) | 982 | 56 |
| Failed (single attempt) | 718 | 77 |
| Failed (>= 2) | 96 | 54 |
| Replicated (>= 2) | 49 | 18 |
| Contested | 25 | 15 |
| Largely failed | 1 | 2 |
| Largely replicated | 0 | 0 |
| Untested | - | 10 |

Two consequences the page design must own: (1) **most effects rest on one attempt**, so the "single attempt" chip and the confidence tier are not decoration - they are the honest headline; (2) the 1,358 "insufficient" originals are mostly legacy rows with effect sizes but no coded result - computing the seven R-package criteria on the 362 legacy-only rows with r on both sides (plus the 1,056 current rows) will move several hundred of them into Replicated/Failed **on the numerical lens**, and the page will say so explicitly ("no author verdict on record; numerical criteria: 4 of 7 fail").

### 4.4 Confidence tier (shown next to the status)

- **A** - >= 3 independent attempts (author_overlap_pct = 0) including >= 1 preregistered or multi-site attempt (Project present or `prereg_r` set)
- **B** - >= 2 attempts, or 1 multi-site attempt with total n_r >= 1,000
- **C** - 1 attempt
- **D** - only non-validated rows (legacy `validated` ∈ {0, 3, NA} and R&R) or only inconclusive attempts

### 4.5 The numerical lens is never folded into the status

For every effect row with Pearson r on both sides (1,061 current + ~362 legacy-only), the build computes the seven criteria from `replication_outcomes.R` (significance_r, significance_agg, consistency_ci, consistency_pi, homogeneity, homogeneity_significance, small_telescopes) and the effect-size ratio `r_r / r_o`. The page shows a 7-cell strip per attempt and an effect-level line "Numerical record: 9 of 10 attempts fail on significance; 6 of 10 fail on small telescopes; median effect-size ratio 0.06". Where the author-reported status and the numerical majority disagree, the page shows a **"Lenses disagree"** chip linking to the explanation. This is the one thing no existing tracker does (U5: the Explorer shows one criterion at a time).

---

## 5. Page types and their sections

Each page is designed in three reading depths: **5 seconds** (what the eye lands on), **30 seconds** (the summary block), **5 minutes** (the full record). All charts are build-time SVG; the only islands are search, the game, and the forest-plot hover.

### 5.1 Effect page `/effects/<slug>/`

**5 seconds** - H1 canonical name + qualifier; one-sentence plain-language claim (overlay `summary:` else FORRT description); **status pill** (e.g. "Largely failed - confidence A") with the rule's mini-legend on hover; three tiny counters: attempts / total replication N / years spanned; discipline + topic chips; a 12-word "why it matters" line for famous effects (overlay).

**30 seconds** - the **Verdict card** with the three lenses side by side:
1. *Authors' reports*: 5 failed - 1 successful - 0 mixed (bar), with the newest outcome quote.
2. *Numerical record*: original r vs. replication r sparkline forest, "median effect-size ratio 0.06", criteria summary.
3. *Design closeness*: how many attempts were direct vs conceptual (closeness score where coded), preregistered, independent teams, multi-site.
Then the **evidence timeline**: one row per attempt in year order (year, first author, N, verdict dot, project chip, closeness chip), original study as row zero.

**5 minutes** -
- *Original study block*: citation, journal, year, abstract (from our abstract cache), claims tested (each with `claim_text_o`, n, es, p), OpenAlex citations by year with the first failed replication marked ("citations kept rising after 2014"), retraction/PubPeer flags, OA link.
- *Attempts table* (all rows, sortable): replication paper, study, n_r, es_r (native + r), p_r, verdict + quote + quote source, project, prereg link, closeness, author overlap, source badge (FLoRA / FReD / legacy / our review queue), and "criteria strip".
- *Forest plot* (effect rows with r both sides; Fisher-z CIs; original in ultramarine, replications in ink, failed ones vermilion outline).
- *Curated sections* (from overlay, each labelled "Editorial - last reviewed <date> by <handle>"): "What the textbooks say", "Why it failed / what changed", "Current understanding", "Controversies", "Further reading".
- *Related effects*: siblings on the same original, same paradigm, same topic, reversed-by, curated `related:`.
- *Open candidates*: discovery-queue items pointing at this effect's originals ("3 papers citing Zhong & Liljenquist mention a replication - not yet reviewed").
- *Data & provenance*: every number's source file + row id, FORRT citation, JSON/CSV download of this effect (`/api/effects/<id>.json`), changelog of the page (status changes are versioned: "2026-09-07: status Contested -> Largely failed (ML2 row added by FORRT release 2026-09-06)").
- *Game hook*: "Test yourself on 5 effects like this one" (links into the game with a topic filter).

### 5.2 Paper page `/papers/<slug>/` (both roles)

5 s: title, authors, journal, year, role badges ("Original of 1 effect", "Replication of 3 findings", "Reproduction"), retraction banner if any. 30 s: for an original - list of effects/claims with status pills; for a replication - the list of originals it tested with verdict per pair and quotes. 5 min: abstract, OpenAlex topics, citations sparkline, OA links, every FReD row where this DOI appears, BibTeX/APA (FLoRA provides both), FORRT Zotero-API-compatible JSON at `/api/doi/<hash>.json`.

### 5.3 Attempt page `/attempts/<at_id>/`

5 s: "Earp et al. (2014) tested Zhong & Liljenquist (2006), Study 2 - Failed". 30 s: the three lenses for this pair only (quote + source; the criteria strip per effect row; closeness/prereg/author-overlap/independence). 5 min: every effect row with original vs replication statistics, conversions shown ("F(1,25) = 6.99 -> r = .467"), source provenance and conflicts between sources (e.g. legacy `curatescience44` says result = success while es_replication = -0.11 and current FReD says failed - both shown, conflict flagged), link to the project, materials/OSF links.

### 5.4 Project page `/projects/<slug>/`

5 s: name, years, sites/labs, N total, outcome split bar. 30 s: list of effects tested with status per effect *within this project* and overall. 5 min: per-site data where raw files exist (RP:P `rpp_data.csv`, ML4, ManyBabies MB1 - forest plots computed at build), methodology note (overlay), the FORRT source labels matched.

### 5.5 Author page `/authors/<slug>/`

Effects originated, replications conducted, "replicated own work" indicator (author_overlap_pct > 0), ORCID, OpenAlex link. No verdict aggregation per author (avoid a scoreboard of people; U6's honesty principle).

### 5.6 Topic page `/topics/<slug>/` and Discipline page

Facet landing: counts by status with denominators and the selection-bias caveat ("people replicate what they doubt"), effects list sortable by attempts/citations/status, base rate for the game, OpenAlex subfield definition, curated override note when the label was renamed.

### 5.7 Paradigm page `/paradigms/<slug>/`

Definition (Cognitive Atlas text where mapped), effects using it, typical manipulations, known moderators (overlay).

### 5.8 Collection page `/collections/<slug>/`

Editorial intro + ordered effect cards; query-backed collections rebuild every build ("Most-cited failed originals" uses `citation_by_outcome_analysis`-style OpenAlex counts).

### 5.9 Journal page, Year page (`/years/2014/`: what was replicated that year, outcomes), Search, Game, Review queue (`/queue/`: candidates with evidence sentence, proposed effect, reviewer state), Methods & rules (`/about/status-rules/` - the exact rules of section 4 with today's counts), Data & API (`/data/` downloads, FORRT citation, licences), Changelog.

---

## 6. Curation overlay model

### 6.1 Principle

Generated data is never edited. Humans write **overlay files** in `curated/`, each keyed by an immutable ID, merged at build. Overlays can add narrative, aliases, relations, status overrides, and *corrections* to specific source cells - always with a reason and a reference. Every overlay field renders with an "Editorial" label and its last-reviewed date, so a reader can always tell FORRT's data from our commentary.

### 6.2 Layout

```
curated/
  effects/<slug>.md          # YAML front matter + Markdown body (one per curated effect; stubs need none)
  aliases.csv                # effect_id, alias, source=curator, review_state, note  (bulk alias decisions)
  merges.yaml                # [{keep: fx_..., absorb: fx_..., reason, evidence}]
  corrections/<source>.yaml  # cell-level patches to FORRT rows, forwarded upstream
  projects/<slug>.yaml
  collections/<slug>.yaml
  topics/overrides.yaml      # OpenAlex subfield -> display name / hide
  paradigms/<slug>.yaml
  authors.yaml               # name merges / ORCID assertions
  famous/docx-import.yaml    # generated once from docx_parsed_entries.json, then hand-edited (status normalized, DOIs resolved)
```

### 6.3 Effect overlay format (`curated/effects/macbeth-effect.md`)

```yaml
---
id: fx_3vq8h2kd                 # required; must exist in registry/effects.csv
name: Macbeth effect            # optional: overrides canonical name
qualifier: null
summary: >-                     # one sentence, plain language, <= 200 chars
  Reminding people of their own immoral acts was reported to make them want to clean themselves.
why_it_matters: Textbook example of embodied cognition; 1,400+ citations.
aliases:
  - {alias: "MacBeth Effect", state: confirmed}
  - {alias: "moral cleansing effect", state: confirmed, note: "used in Siev et al. 2018"}
claims:                         # optional: pin which claims belong here when an original hosts several effects
  - cl_9f2ka7bd                 # Study 2: desirability of cleansing products
  - cl_1m0zq4rt                 # Study 3: antiseptic wipe choice
status_override: null           # one of {reversed, contested, insufficient} or null; requires justification + reviewers >= 2
status_justification: null
reversed_by: []                 # attempt ids, when status_override = reversed
related:
  - {id: fx_7ab2..., relation: same_paradigm, note: "Lee & Schwarz 2010 'Washing away postdecisional dissonance' (failed in SSRP 2018)"}
  - {id: fx_c81e..., relation: see_also, note: "Helzer & Pizarro 2011 'Dirty liberals' (failed)"}
paradigms: [pd_recall-of-moral-transgression, pd_product-desirability-rating]
topics_add: [tag:embodied-cognition, tag:moral-psychology]
topics_remove: []
textbooks:                      # operationalizes Ferguson & Brown / Schimmack audits
  - {title: "OpenStax Psychology 2e", section: "7.x", teaches_as: established, checked: 2026-09-07}
wikipedia: {article: "Embodied cognition", has_replication_section: false, checked: 2026-09-07}
external_ids: {wikidata: null, cogatlas: null}
famous_list: {docx_name: "Macbeth effect", docx_status: mixed, gs_citations: 1407, gs_checked: 2022-01}
review: {state: reviewed, last_reviewed: 2026-09-07, reviewers: [leo], sources_checked: [FReD 2025-11-30, FLoRA 2026-09-06]}
---
## What the textbooks say
...
## Why it failed
...
## Current understanding
...
## Further reading
- Siev, Zuckerman & Siev (2018), Social Psychology 49(5): meta-analysis, g = 0.17 [0.04, 0.31], n = 1,746.
```

Markdown body sections are fixed headings (the build warns on unknown headings so pages stay uniform). Citations in the body use `[@doi:10.1027/1864-9335/a000349]` and are resolved to paper pages at build.

### 6.4 Corrections overlay (`curated/corrections/fred-legacy.yaml`)

```yaml
- source: legacy_2.4.1            # which file/version
  row: curatescience44            # source row id
  field: result
  observed: success
  corrected: informative failure to replicate
  reason: "es_replication = -0.11, n = 286; Earp et al. 2014 Study 3 reports no effect; current FReD row codes it failed."
  evidence: [doi:10.1080/01973533.2013.856792]
  reported_upstream: {date: null, channel: forrt-submit-form, ticket: null}
  reviewers: [leo]
```
Corrections are applied in the normalization layer *after* raw ingest and *before* status computation, and each corrected cell renders with a "corrected by editors (why)" tooltip. A monthly job exports all corrections in FORRT's `datasubmission_template.xlsx` vocabulary for contribution back.

### 6.5 Review flow (git)

1. All overlays live in the repo; `main` is protected. Contributors open a PR (or use a "Suggest an edit" link on every page that pre-fills a GitHub issue/PR template with the effect id).
2. CI on PR: YAML schema validation (Zod/pydantic), referenced IDs exist in the registry, DOIs resolve (cached Crossref HEAD), no unknown headings, no status override without justification, secrets scan, and a **preview build** of the affected pages only.
3. Review rules (CODEOWNERS): narrative-only PRs need 1 reviewer; alias/merge PRs need 1 reviewer + the automated duplicate check; `status_override`, `corrections/*`, and `merges.yaml` need 2 reviewers.
4. Merge -> nightly build -> site + `/api/*.json` + changelog entry generated from the diff ("macbeth-effect: added Further reading; status unchanged").
5. Reviewer decisions on the discovery queue (accept/reject candidate, assign effect) are also overlays (`curated/queue/decisions.csv`) so the queue is reproducible and doubles as labelled training data.
6. FORRT sync: on each FORRT release (they ship ~4/week for FLoRA), the build re-runs; overlays keyed by immutable IDs survive; a report lists effects whose status changed because of upstream data, which is itself a page (`/changelog/`).

### 6.6 How the famous-effects list (docx) merges

1. One-time script converts `docx_parsed_entries.json` to `curated/famous/docx-import.yaml` (362 entries) with: normalized `docx_status` (replicated 113 / mixed 117 / not replicated 101 / reversed 9 / unknown 22 — raw strings include "not replicated.", "mixed (but mostly replicated).", "replicated (ns)..."; the qualifier text is kept verbatim in `docx_status_note`), extracted `original_title`, `first_author`, `year`, `n` per study, GS citations + date, free-text ES.
2. DOI resolution (Crossref bibliographic query on title+author+year; local fuzzy match to FLoRA/FReD/legacy titles as a cross-check) fills `original_doi` with `resolution: {method, score, checked}`; unresolved rows are a review-queue file.
3. Registry step 1 already merges docx names into clusters (218 exact matches with the Reversals sheet; 100 with legacy); step 2 adds the resolved DOIs; the 142 docx-only names become named effects on their own.
4. The docx `status` is **never** the computed status. It is shown on the page as "FORRT/curator list (2021-22) said: mixed" beside the computed status, and a build check lists disagreements between docx status and computed status as a curation queue (expected: many, because the docx counts meta-analyses and unpublished studies that FReD does not).
5. `critiques` and `replication_es` free text seed the Markdown body ("Editorial - imported from the curated list, unverified") until a human rewrites them.

---

## 7. Navigation and cross-links

- **Global nav**: Effects (browse by status / discipline / topic / paradigm / attempts / citations) - Papers - Projects - Collections - Game - Queue (new replications) - Data & API - About (rules, sources, citation).
- **Home**: search box first; then "Entrances": *by status* (8 pills with live counts), *by discipline*, *famous effects* collection, *newest attempts* (FLoRA growth feed), *play the game*; then "How to read a verdict" (the three lenses in 40 words).
- **Every page's right rail**: provenance box (which FORRT files/versions, our overlay date), "Suggest an edit", "Report a replication we missed" (pre-fills the queue form with the effect id), JSON link.
- **Cross-link rules** (generated, not hand-written): effect <-> claims <-> original paper <-> attempts <-> replication papers <-> projects; effect -> siblings (same original), same-paradigm, same-topic; paper -> "cited by N FORRT originals" (from `citation_dois.json`, 376 originals with internal citations) and "builds on a failed foundation" chain; author -> papers -> effects; topic -> base rate -> game.
- **Breadcrumbs**: Effects > Social psychology > Macbeth effect; Papers > 2014 > Earp et al.
- **Stable JSON per entity** at `/api/effects/<id>.json`, `/api/papers/<hash>.json`, `/api/attempts/<id>.json`, plus `/api/doi-lookup?prefixes=` mirroring FORRT's Zotero API record shape (so the plugin could be pointed at us), an RSS feed of new attempts and status changes, and full dumps (`effects.csv`, `attempts.csv`, `aliases.csv`) with the FORRT CC-BY citation embedded.

---

## 8. Worked example: the Macbeth effect (all numbers from the files)

**Registry entry.** Names: "Macbeth effect" (legacy, 11 rows, source Individual submissions/CurateScience import, validated = 3), "MacBeth Effect" (legacy FORRT row `Arb97`), "Macbeth effect" (Reversals sheet, discipline Social Psychology, description "Moral aspersions induce literal physical hygiene"), "Macbeth effect" (docx, status *mixed*, GS citations 1,407 in Jan 2022). All merge in step 1 (exact after lower). Original DOI from legacy/R&R: `10.1126/science.1130726` (Zhong & Liljenquist 2006, *Science* 313:1451-1452, "Washing Away Your Sins: Threatened Morality and Physical Cleansing"). Legacy row `Manylabs2_23` (source ML2, no effect name) attaches through the DOI. Docx title "Washing away your sins: threatened morality and physical cleansing" resolves to the same DOI (exact FLoRA `title_o` match). Slug `macbeth-effect`; id assigned once.

**Claims (from FReD `study_o` + `claim_text_o`).**
- Study 1 (n = 32): recalling an unethical deed -> more cleansing-related word completions, F(1,58) = 4.26, p = .04 (r = .26).
- Study 2 (n = 27): copying an unethical story -> higher desirability of cleansing products, F(1,25) = 6.99, p = .01 (r = .47).
- Study 3 (n = 32): unethical recall -> chose antiseptic wipe 67% vs 33%, chi2(1) = 4.57, p = .03 (r = .38).
- Study 4 (n = 45): cleansing after recalling unethical behaviour -> less volunteering / reduced moral emotion, chi2(1) = 5.02, p = .025 (r = .33).

**Attempts (pairs), in time order.**

| Year | Replication | id_r | Studies tested | n_r | Author verdict (source) | Quote |
|---|---|---|---|---|---|---|
| 2009 | Fayard, Bassi, Bernstein & Roberts, *J. Articles in Support of the Null Hypothesis* | url `jasnh.com/pdf/Vol6-No2.pdf` (no DOI) | S3 (n=210), S4 (n=115) | 325 | failed (FLoRA COS; FReD failed x2; legacy inf. failure x2) | "Despite larger samples and thus greater power to detect effects, both studies failed to replicate..." (abstract) |
| 2011 | Gamez, Diaz & Marrero, *Spanish J. Psychology* | 10.5209/rev_sjop.2011.v14.n1.13 | S1 (n=47), S2 (n=36), S3 (n=45), S4 (n=28) | 156 | failed (FLoRA; FReD failed x4) | "We were unsuccessful in replicating..." (abstract) |
| 2012 | Siev, unpublished, Studies 1-2 | none (legacy only, `curatescience40/41`) | S2 (n=335, 148) | 483 | failure (legacy `result`); r = -.04, -.09 | - |
| 2013 | Reuven, Liberman & Dar, *Clinical Psychological Science* (OCD sample) | 10.1177/2167702613485565 | S4 (n=57) | 57 | **successful** (FLoRA; FReD; legacy success, r = .39) | "Replicating previous findings, physical cleaning reduced the willingness to help and relieved moral emotions." |
| 2014 | Earp, Everett, Madva & Hamlin, *Basic and Applied Social Psychology* | 10.1080/01973533.2013.856792 | S2 x3 (n=153, 156, 269) | 578 | failed (FLoRA; FReD x3) — legacy `curatescience44` says "success" with r = -.11: **source conflict, corrected by overlay** | "Despite multiple good-faith efforts, however, we were unable to detect a 'Macbeth Effect' in any of our experiments." |
| 2018 | Klein et al., **Many Labs 2** (`Manylabs2_19_1`), *AMPPS*, preregistered osf.io/ejcfw | 10.1177/2515245918810225 | S2 (n = **7,001**) | 7,001 | failed (FLoRA COS, quote p. 22; FReD failed; legacy inf. failure) | "This result is not consistent with the hypothesis that copying an account of an unethical action increases the desirability of cleansing products..." |
| 2018 | Siev, Zuckerman & Siev, *Social Psychology* 49(5) (meta-analysis + new data; legacy `Arb97`, osf.io/twsxf, no result coded) | 10.1027/1864-9335/a000349 | - | (docx: k pooled n = 1,746) | inconclusive in data; docx: g = 0.17 [0.04, 0.31] | - |

Counts for the status rule: informative replication pairs n = 6 (Fayard, Gamez, Siev 2012, Reuven, Earp, ML2): f = 5, s = 1, m = 0 -> `f/n = 0.83 >= 0.75`, `n >= 4`, `s >= 1` => **Status: Largely failed**. Confidence: >= 3 independent attempts (author_overlap_pct = 0 on every FReD row) including one preregistered multi-site attempt => **tier A**. Reversal candidate: no (no significant opposite-sign row). Docx status shown beside it: "curated list (2022): mixed". Note the wiki's status is *stricter* than the docx because the one success is in a clinical OCD sample (a conceptual replication) and every direct replication failed - exactly the kind of sentence that belongs in the overlay's "Current understanding".

**Numerical lens (computed from FReD rows with r on both sides, n = 8 of 11 rows; Fisher-z CIs; criteria per `replication_outcomes.R`).**

| Row | Claim | r_o (n_o) | r_r (n_r) | 95% CI r_r | signif. | CI-consistency | PI-consistency | small telescopes (r33) | FE-agg signif. | homogeneity |
|---|---|---|---|---|---|---|---|---|---|---|
| Gamez S1 | S1 | .26 (32) | .14 (47) | [-.15, .41] | F | S | S | F (r33 = .28) | F (agg r = .19) | S |
| Gamez S2 | S2 | .47 (27) | .00 (36) | [-.33, .33] | F | F | S | F (.30) | F | S |
| Gamez S3 | S3 | .38 (32) | .14 (45) | [-.16, .42] | F | S | S | F (.28) | S (agg .24) | S |
| Gamez S4 | S4 | .33 (45) | .20 (28) | [-.19, .53] | F | S | S | F (.23) | S (agg .29) | S |
| Earp S1 | S2 | .47 (27) | .00 (153) | [-.16, .16] | F | F | F | F | F | F |
| Earp S2 | S2 | .47 (27) | -.07 (156) | [-.22, .09] | F | F | F | F | F | F |
| Earp S3 | S2 | .47 (27) | -.11 (269) | [-.23, .01] | F | F | F | F | F | F |
| ML2 | S2 | .47 (27) | .00 (7,001) | [-.02, .02] | F | F | F | F | F | F |

Summary line the page prints: "Numerical record: 0 of 8 replications significant in the original direction; 3 of 8 consistent with the original by CI (all small-n Spanish studies); 0 of 8 pass small telescopes; median effect-size ratio 0.00 (range -0.24 to 0.61)." Lenses agree with the author-reported status (Largely failed), so no "lenses disagree" chip — but the row-level strip shows the well-known pattern: tiny replications are "consistent" only because their CIs are wide.

Rows without a numerical verdict: Fayard S3 (original ES coded as Cohen's h = 0.77, replication h = 0.095 - not convertible under the R package rules; shown as "not convertible"), Fayard S4 and Reuven (partial eta-squared - not convertible), Siev 2012 (legacy r only, no p).

**Design-closeness lens.** Closeness_* columns: none coded for these rows (legacy closeness fields are filled for ~175 rows overall), so the panel shows "Design closeness not coded - help code it (FORRT template)" plus what *is* known: ML2 preregistered (osf.io/ejcfw) and multi-site; Reuven used a clinical sample (Clinical Psychological Science) - conceptual; author overlap 0% on all attempts; legacy power column: 1.0 (Fayard, Earp, Siev), .84/.88 (Gamez S1/S2), .54/.55 (Gamez S4, Reuven).

**Original-study block.** Zhong & Liljenquist 2006, *Science*; docx GS citations 1,407 (Jan 2022); OpenAlex citation trajectory from our enrichment cache (`openalex_original_enrichment_full.json` if the DOI is among the 1,596) with 2014 (Earp) and 2018 (ML2) marked.

**Related effects (generated + overlay).** Same-paradigm/see-also from the data: "Washing away postdecisional dissonance" (Lee & Schwarz 2010, 10.1126/science.1186799; SSRP 2018 failed, legacy name "Cognitive Dissonance", r_o = .39 -> r_r = -.05), "Dirty Liberals!" (Helzer & Pizarro 2011, 10.1177/0956797611402514; replication 10.1037/pspa0000238 failed), "Moral priming (cleanliness)" (Schnall et al. 2008; legacy 9 rows, contested). Overlay adds Siev et al. 2018 as the meta-analytic synthesis.

**5-second view of the page, as text:**
> **Macbeth effect** - Reminding people of their own immoral acts was reported to make them want to clean themselves. **Largely failed · confidence A** · 6 attempts · 8,600 participants · 2009-2018 · Social psychology · embodied cognition, moral psychology. *Curated list said: mixed.*

---

## 9. Risks, open questions, and things other designers should pick up

1. **Sign conventions in FReD are not trustworthy for reversal detection** (4 of 12 candidate rows are coded "successful"); Reversed stays a curated status. A future FORRT column for effect direction would fix this; propose it upstream.
2. **The legacy CurateScience import is flagged erroneous by FORRT** (change_log v1.9.0) and it is where most of the Macbeth rows come from (validated = 3 = "errors not yet corrected"). The page must show validation state per row; the corrections overlay is the mechanism, and the first curation sprint should target the 693 `validated == 3` legacy rows that touch named effects.
3. **Fuzzy name merging** creates plausible-but-wrong merges (the ML1 "age of acquisition" family). Auto-merge only >= 95 with same discipline; everything else is a queue. Budget: ~60 decisions.
4. **Single-attempt dominance** (median 1 attempt per original) means the honest site is mostly "Failed (1 attempt)"/"Replicated (1 attempt)" pages; the game and the collections should be built from the ~285 originals with >= 2 attempts and the multi-site projects, and the status legend must explain single-attempt semantics.
5. **DOI-less works** (Fayard 2009 via URL; 200 FLoRA url_r-only rows; 383 FReD url_r) need the `url:`/`hdl:` identifier scheme and must never be dropped, unlike FORRT's filtered file (which drops 205 `invalid_identifier` rows for the Zotero API).
6. **Claim grain for FLoRA-only originals** is missing (1,728 originals). Until FReD codes them, they are paper-level claims; the discovery pipeline should capture `study` and `claim` text when it extracts outcome sentences so new items arrive at claim grain.
7. **Docx status vs computed status will disagree often** because the docx counts meta-analyses and unpublished studies; that disagreement list is the best first curation queue for the 362 famous effects.
8. **Topics**: no new taxonomy. Facets = FORRT discipline (normalize 40 -> 34 -> ~30 with an override table), OpenAlex subfield/topic (fetch for the 3,820 originals; 1,596 already cached), curated tags. Provenance and review state on every inferred label.
9. **Registry files are committed generated files** - the one deliberate exception to "never hand-edit generated data": they are never hand-edited either; the build appends, a PR reviews the diff.
10. Interfaces for other designers: the discovery agent should emit `(doi_o, id_r, type, outcome, outcome_quote, quote_source, study_o?, claim_text?, evidence_url, model_id)`; the game agent should read `effects.parquet` + `attempts.parquet` and prefer effects with confidence >= B and status in {Replicated, Failed, Largely *}; the pipeline agent should implement layers `raw/ -> normalized/ -> registry/ -> curated/ -> site/` with the registry step idempotent.
