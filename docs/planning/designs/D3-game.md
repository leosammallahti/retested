# D3 — "Did it replicate?" : the guessing game as a first-class product AND a data-generating instrument

Author: designer agent D3 (game designer / product lead angle). Date 2026-09-07.
Inputs: BRIEF.md, _DIGEST.md, U5-forrt.md (columns), U6-landscape.md (quizzes, forecasting literature), U3-data-assets.md (famous effects), U7-discovery.md; every number below was recomputed from the files on disk with the scripts in
`C:\Users\OMISTAJA\AppData\Local\Temp\claude\C--Users-OMISTAJA-PsychologyReplication\220afa57-c1c1-43dd-9752-8f938442a4d8\scratchpad\{game_items.py, legacy_pool.py, flora_pool.py}` (outputs `fair_fred_rows.csv`, `fair_fred_originals.csv` in the same folder). Nothing here is invented; where a number is a design target rather than a measurement it is marked TARGET.

---

## 0. One-paragraph thesis

Every existing "did it replicate?" quiz (80,000 Hours, ClearerThinking, Domke) is a frozen 21-item SSRP-2018 set with yes/no answers. Ours is generated from the database at every build, played at the level of the *original study* (not the effect row, not the paper), elicits a **probability** instead of a yes/no, scores with the **Brier rule**, teaches the documented cues (p<=.005 vs .005<p<.05, interaction vs main effect, N, era, subfield base rate) through progressive reveals, and — the part nobody has — records every forecast as **open data**: (a) on settled items it measures how good humans are at this (a running replication of Hoogeveen 2020 / Gordon 2021 with thousands of items instead of 27/103), and (b) on not-yet-replicated effects it produces a **crowd replicability forecast** that is settled automatically when FORRT's FLoRA later adds a replication (generalising Transparent Replications + Metaculus). The reveal screen is the wiki's "three lenses" (author verdict / numerical record / design differences), so every game round is also a wiki page visit.

Playable **today, with zero LLM work: 693 original studies (349 replicated / 344 failed = 50.4%)** from current FReD with claim text, year, N and a clean outcome; **~1,188 more originals** exist in FLoRA with a clear outcome but no coded claim text (needs the claim-writing pipeline in section 8); **223 famous effects** from the hand-curated list (113 replicated / 101 not / 9 reversed) form the "famous-effects" mode once their DOIs are resolved.

---

## 1. Prior art on disk: the 80,000 Hours quiz copy FORRT saved

File: `C:\Users\OMISTAJA\PsychologyReplication\data\raw\forrt\osf\sub-datasets\quiz.html` (60,346 bytes; listed in FORRT's OSF Sub-Datasets folder next to the CORE / X-Phi / Camerer import sheets, with `readme_subdatasets.txt` explaining sub-datasets are "meta-datasets provided by the respective project").

What it actually is (verified by parsing the HTML):
- A saved WordPress page `https://80000hours.org/psychology-replication-quiz/`, title "Quiz: Psychology results in top journals - can you guess which ones were true, and which didn't replicate?", og:image from 2018/08, meta description "Does a heavier clipboard really get job applicants taken more seriously? Try your luck with this quiz."
- The quiz itself is a **GuidedTrack program** (`<div class="guidedtrack program_container gt-replication-quiz" id="8032" data-environment="production">` with `#program_navigation`, `.points .total`, `.main`) loaded from guidedtrack.com at runtime. **The saved file contains no item text, no answers, no scoring logic** — only the 80k navigation, the empty program container, and social-share buttons. It is prior-art evidence, not an item set. The 21 SSRP items are documented in U6 (Camerer et al. 2018, Nature Human Behaviour; the same 21 items used by ClearerThinking).
- Format lessons (from U6 + the LessWrong/Gelman comment threads): 10/15/21-item lengths, binary yes/no + "don't know" (underused), feedback compares you with expert psychologists (commenters scored 71–93%), users explicitly asked for probabilistic answers and calibration feedback. Domke's 13-item "replication game" uses a 0–4 scale and warns of selection bias ("all hot effects failed").
- Hoogeveen, Sarafoglou & Wagenmakers (2020) is the best-designed template: 27 SSRP+ML2 items, deliberately stratified to 14 successful / 13 failed (52%), descriptions "rephrased to be comprehensible by laypeople", **no author names, no titles, no direct quotes** (to prevent look-ups), a description-only vs description-plus-Bayes-factor condition (59% vs 67% accuracy), one bogus attention-check item. We copy exactly these authoring rules and both conditions become our "plain" and "stats" modes.

Sources to seed the *forecast comparison* layer (all open): Gordon et al. 2021 pooled market/survey data (103 findings), Hoogeveen OSF wg9s3 (lay forecasts on 27 items), SCORE OSF dtzx4 (repliCATS/market forecasts on 3,000 claims; join by DOI to FLoRA/FReD). Where a game item matches one of these, the reveal shows "markets said 63%, laypeople said 55%, you said 40%".

---

## 2. Product principles

1. **Unit of play = one original study (doi_o + study_o) with one focal claim.** Not the FReD effect row (76 rows of the same JOM paper would be 76 identical guesses), not the replication paper (RP:P covers 92 originals). Multiple replications of the same original are shown together on the reveal.
2. **Probability, not yes/no.** Slider 1–99%, default at the displayed base rate. Scored with a strictly proper rule (Brier), so honesty is the best strategy; no streak multipliers on the proper score (compounding breaks properness — Replication Markets' complaint was flat points, but the fix is *immediate feedback + calibration*, not multipliers).
3. **Fair by construction.** Every session is stratified to ~50% replicated (Hoogeveen/Gordon/SCORE base rates are all ~49–52%); only items with an unambiguous outcome and a non-leaking claim; leaky project blocks excluded; card text passes automated leakage tests and a review state.
4. **Every round teaches.** Reveal = outcome + numbers + the authors' own words + design differences + "what the cues said" + link to the wiki finding page.
5. **Every round is data.** Forecasts are stored anonymously (opt-in cloud) and published as an open dataset; open forecasts on unreplicated effects become a crowd prior shown on wiki pages and settled automatically.
6. **Works with no backend.** Static JSON + localStorage gives the full single-player game; Supabase adds daily leaderboards, crowd stats, classroom rooms and open forecasts. Degrade gracefully.
7. **Never embarrass a finding.** Tone is the field guide's: "this finding was tested again and the result was X", with the replication team's quote, closeness and shrinkage — not a scoreboard of "debunked" scientists.

---

## 3. How many fair items exist NOW (computed 2026-09-07)

### 3.1 Tier A — current FReD (stats-ready, no LLM needed)

Pipeline applied to `data/raw/forrt/fred-data/output_FReD.xlsx` (2,164 effect rows) + row-identical `fred-data/archive/2025-11-30_COSdata_validated.xlsx` (adds r_o, r_r, statistical_success, correct entry_id):

| Filter step | Effect rows | Note |
|---|---|---|
| all rows | 2,164 | |
| `reported_success` in {successful, failed} ("clear") | 1,772 | drops mixed 359, "stat. successful but flawed" 18, descriptive-only 10, uninformative 5 |
| + usable text (description >= 30 chars OR claim_text_o >= 40 chars) | 1,770 | description filled 1,960 rows (median 90 chars), claim_text_o 2,131 (median 233 chars); 45 rows have description only, 262 claim only |
| + year_o and n_o present | 1,757 | year_o is 100% filled; n_o 99.4% |
| − leaky blocks (management/JOM 103 rows; Soto 2019 Big Five 60 rows; 13 replication papers with >=15 clear rows and >=90% one-way outcome) | **1,408** | 717 successful / 691 failed (50.9%) |
| grouped to original study (doi_o + study_o) | 711 originals | |
| … with a consistent outcome across its fair effects | **693** | **349 successful / 344 failed** ; 18 originals have effects pointing both ways (usable as "mixed" expert items, not as binary items) |
| grouped to doi_o only (one item per paper) | 620 consistent (322/298), 29 inconsistent | if a paper contributes several studies, prefer the doi_o+study_o grain but never show two studies of one paper in one session |

Robustness: with only JOM + Soto excluded (no per-paper skew rule) the consistent-original pool is 701 (352/349) — i.e. the 13 skewed replication-paper blocks matter at the *effect* level (they inflate rows) but barely at the *original* level (−8 originals). This is the main argument for the original-study grain: it dissolves the block-leakage problem instead of patching it. (Naively capping "5 originals per replication paper" would be wrong: RP:P/ML papers each cover dozens of distinct originals; that cap collapses the pool to 335.)

The 13 skewed replication papers (n>=15 clear rows, >=90% one direction), for the exclusion table: 10.1016/j.jom.2005.11.004 (da Silveira 2005, JOM, 76 rows, 100% successful), 10.1177/0956797619831612 (Soto 2019, 41 rows 100%), 10.12688/openreseurope.17749.1 (Eben 2024, 32, 100%), 10.31219/osf.io/q56rk (Brohmer et al., 30, 100%), 10.1002/erv.3103 (Sfärlea 2024, 26, 100%), 10.1177/2515245920958687 (Ebersole ML5, 20, 10%), 10.1525/collabra.35271 (Klein et al., 18, 0%), 10.1080/00222895.2014.898608 (Boyle 2014, 17, 100%), 10.3758/s13423-024-02602-4 (Ebert 2024, 17, 0%), 10.1111/padm.12860 (Chen 2024 public admin, 16, 100%), 10.1007/s11251-024-09670-y (Loibl & Leuders 2024, 16, 0%), 10.17605/osf.io/wmqtb (Au & Feldman 2024, 16, 100%), 10.1525/collabra.310 (Shanks 2020, 15, 0%). At the original grain these are 1 original each (many effects of one study) except ML5/Klein; rule: **one item per original per session, and at most one item per replication *project* per daily set**.

Fair Tier-A originals by discipline (consistent outcome; FReD `discipline` lower-cased):

| discipline | failed | successful | n |
|---|---|---|---|
| social psychology | 140 | 88 | 228 |
| cognitive psychology | 58 | 80 | 138 |
| psychology (unspecified) | 32 | 48 | 80 |
| experimental philosophy | 8 | 30 | 38 |
| economics | 17 | 19 | 36 |
| marketing | 19 | 8 | 27 |
| judgment and decision making | 15 | 10 | 25 |
| marketing/org behavior | 8 | 9 | 17 |
| education | 7 | 7 | 14 |
| linguistics | 6 | 5 | 11 |
| developmental psychology | 3 | 8 | 11 |
| political psychology | 4 | 5 | 9 |
| neuroscience | 3 | 5 | 8 |
| political science | 4 | 4 | 8 |
| sociology | 3 | 4 | 7 |
| medicine | 1 | 6 | 7 |
| health | 2 | 3 | 5 |
| others (comm. sci, org psych, evolutionary, clinical, differential, sports, genetics, nan) | 8 | 6 | 14 |

By decade of the original: 1930s 1, 1970s 6, 1980s 13, 1990s 31, 2000s 223 (118 failed/105 succ), 2010s 379 (190/189), 2020s 40 (17/23). "By decade" mode is therefore realistic only for 1990s / 2000s / 2010s / 2020s; pre-1990 items come from the famous-effects tier.

Top original journals in the pool: Psychological Science 115, JPSP 69, PNAS 36, Science 31, JEP:LMC 28, J Consumer Research 24, Cognition 23, JESP 22, JEP:General 19, American Economic Review 18, OBHDP 12, J Marketing Research 12 — enough for "journal" as a revealable cue with real per-journal base rates.

Fields available for the **stats mode** among the 1,408 fair effect rows: original p-value 1,339; numeric es_value_o 880; Pearson r_o 643; r_r 730; both r 554 (forest-plot-ready reveal); n_r 1,405; `reported_success_quote` 1,408 (100% — every fair item has the replication authors' own verdict sentence); `author_overlap_pct` 1,303 (1,096 rows fully independent teams = "independence" badge); prereg_r link 843. Multi-replication originals in the pool: 26 (>=2 replication papers) — good "aggregate verdict" items.

### 3.2 Empirical cue base rates *in our own pool* (fair effect rows) — what onboarding should teach with our numbers, next to the literature's

| cue | levels | success rate (successful/(successful+failed)) |
|---|---|---|
| original p-value | p <= .005 | **61%** (341/561) |
| | .005 < p < .05 | **39%** (173/445) |
| | p >= .05 reported (n.s. originals / one-sided oddities) | 47% (158/333) |
| | not coded | 65% (45/69) |
| original N | <=50 | 51% ; 51–100 40% ; 101–200 54% ; 201–500 58% ; >500 59% |
| era of original | <2000 44% ; 2000–09 48% ; 2010–14 45% ; 2015+ **59%** |
| discipline | social 42% ; cognitive 61% ; marketing 34% ; exp. philosophy 77% ; economics 52% ; JDM 40% ; evolutionary 0/17 |
| "interaction/moderat" in description or claim (crude text proxy) | 48% vs 52% — the text proxy is too weak; the interaction flag must be coded by the claim-writing LLM step (section 8) before it is shown as a cue |

The literature values (Gordon 2021: p<=.005 74% vs 28%; Altmejd 2019: interactions 20% vs main effects 53%; Hoogeveen: laypeople 59% / 67% with Bayes factors; markets 73%, repliCATS 76%) are shown side-by-side with these; the difference (our p<=.005 bucket is 61%, not 74%) is itself a teaching point about selection into replication projects.

### 3.3 Tier B — FLoRA-only originals (clear outcome, no coded claim)

From `output_flora.csv`, replication rows only (2,526): 1,943 with outcome successful/failed; 1,814 distinct originals with a clear outcome, **1,799 consistent** (994 successful / 805 failed = 55%); of these **1,188 originals are not in current FReD at all**. They have title_o, journal_o, year_o, apa_ref_o, outcome, `outcome_quote` (present on 1,940 of the 1,943 clear rows), oa_url_o on 422 of the 1,188, and a locally cached abstract for only 63 (abstract_enrichment.json covers legacy FReD DOIs). Top journals of this extra pool: JPSP 43, Psych Sci 42, PNAS 23, J Applied Behavior Analysis 21, AER 16, Science 15, Cognition 14, Nature 14, JESP 13, QJE 12. Decades: 2000s 311, 2010s 606, 2020s 115, 1990s 76, 1980s 43, 1970s 27, earlier 10.
To make these playable each needs (i) an abstract (OpenAlex `abstract_inverted_index`, ~74% coverage in U7's tests; Crossref/PubMed cascade from the old `fetch_all_abstracts.py` for the rest), (ii) an LLM-written plain-language claim (section 8), (iii) N of the original — **not available** in FLoRA; the claim writer must extract N from the abstract or the card shows "N not coded" and the item is excluded from stats mode. Expect ~800–900 playable Tier-B items after abstract coverage and review losses (TARGET, not measured).

### 3.4 Tier C — the 362 famous effects (docx_parsed_entries.json)

Normalised status: replicated 113, not replicated 101, reversed 9, mixed 117, unknown 22 → **223 binary-usable famous items** (reversed counts as "failed" with a special reveal). Discipline of the binary set: Social 54, Cognitive 57, JDM 26, Political 18, Marketing 18, Parapsychology 10, Developmental 7, others. Descriptions are already plain-language ("that hearing about old age makes people walk slower"), median 150 chars; **11 descriptions leak** (contain "replicat"/"failed"/"did not") and must be rewritten. They carry Google-Scholar citation counts (341 entries) → a "fame" difficulty tier and the "citations kept rising after the failed replication" reveal (needs OpenAlex counts_by_year, already cached for 1,596 legacy DOIs). Zero DOIs: resolve via Crossref bibliographic query on the 329 quoted titles (U3: 68% fuzzy match locally; Crossref should resolve nearly all) so famous items link to their FReD/FLoRA attempts and reuse the same reveal. Until resolved they are playable with the docx `critiques`/`replication_es` text as the reveal.

### 3.5 Tier D — legacy FReD 2.4.1 adds almost no *new* items but enriches reveals

Legacy rows with clear `result` (success 678 / informative failure 726), description >= 30, n_original and a year: 1,049; only **177 rows / 25 originals (19 with a consistent outcome)** have a doi_o absent from current FReD — mostly ML1 multi-site rows (107) and RRR9 (23). So legacy is not a source of items; it is a source of reveal content for matched items: effect names (794 matched rows → item titles like "Sunk cost effect"), closeness_* (Brandt recipe, ~160), power (565), CIs (~565), osf_link (751), preregistration (205), project labels (ML1/ML2/ML3/OSC2015/RRR/CORE/…). The legacy 'Reversals Effects' sheet (583 rows) has **no status column filled** (0/583) — it cannot be used as an answer key; the docx list can.

### 3.6 Totals

| tier | playable now | after pipeline | outcome balance |
|---|---|---|---|
| A FReD originals | 693 | 693 (+18 mixed expert items, +40 multi-replication aggregates) | 50.4% |
| B FLoRA-only originals | 0 | ~850 TARGET of 1,188 | 55% raw → stratified per session |
| C famous effects | 223 (text-only reveal) | 223 linked | 51% (113 vs 110) |
| **union** (C overlaps A/B after DOI resolution; U3 found 100 docx titles already in FLoRA title_o) | **~700–900** | **~1,900–2,100 originals** | |

Daily-10 at ~2,000 items = 200 days before the pool cycles; endless mode never repeats within a device (localStorage seen-list) until the pool is exhausted.

---

## 4. Game modes

| mode | selection rule | scoring | needs backend? |
|---|---|---|---|
| **Daily 10** | deterministic seed = UTC date; 5 replicated + 5 failed; max 1 per discipline until all disciplines used; max 1 per replication project; difficulty mix 3 easy / 4 medium / 3 hard (difficulty = crowd mean Brier once available, else a prior from p-bucket + N + fame); identical for everyone | Brier per item, session Brier, skill score vs base rate; share card | leaderboard only |
| **Endless** | random from unseen items, stratified 50/50 in rolling windows of 10; adaptive: after 30 items, sample harder items more when the player's skill score > 0.15 | running calibration curve; "session ends when you want" | no |
| **By discipline** | pool filtered on FReD discipline / OpenAlex subfield facet (social, cognitive, JDM, marketing, economics, exp. philosophy, developmental, …; only facets with >= 20 items each side are offered — today: social, cognitive, psychology, exp. philosophy, economics, marketing, JDM; famous-tier adds political) | same; the reveal shows the discipline base rate | no |
| **By decade** | 1990s / 2000s / 2010s / 2020s (+ "classics" = famous tier pre-1990) | same; teaches era effect (2015+ 59% in our pool) | no |
| **Famous effects only** | Tier C; sorted into "textbook classics" (GS citations > 1,000) and "viral findings" | binary Brier; reveal includes critiques and citation trajectory | no |
| **Stats mode** ("Hoogeveen condition B") | any pool; the card starts plain and the player can *buy* cues one at a time (p-value bucket → N → effect size with a plain gloss → journal/era → design type → prereg/independence of the replication team); each purchased cue costs 5 points from the max 100, so revealing all cues (30) still leaves a positive maximum; the forecast is re-elicited after each cue (we store the whole path) | Brier on the final probability, minus cue costs; **the stored path is the research payload** (measures the marginal value of each cue on thousands of items) | no (richer with) |
| **Classroom** | teacher creates a room (6-char code), picks a set (daily, a discipline, or a curated "Intro Psych 12" list), students join with nickname/no login; teacher screen shows live per-item probability histograms and the class calibration curve; CSV export | class Brier, per-item split | yes (Supabase realtime) |
| **Open forecasts** (section 9) | effects with no replication yet | unsettled; resolves later | yes |
| **Expert three-way** (opt-in) | includes the 359 mixed FReD rows / 564 FLoRA mixed pairs; elicit a 3-way distribution (replicated / mixed / failed) | multiclass Brier | no |

Onboarding (first visit, skippable, 3 screens + 3 tutorial items):
1. "About half replicate." A real stacked bar from FLoRA: 41% successful / 36% failed / 22% mixed (n = 2,526 replication pairs, FORRT FLoRA, dated). "In this game we only ask about clear cases and we show you 50/50."
2. "Give a probability, not a verdict." Slider demo; Brier explained as "distance between your number and what happened; 50% always scores 75/100; being 90% sure and right scores 99; being 90% sure and wrong scores 19."
3. "Cues that actually predict replication." Three tiles with both literature and our-pool numbers: p <= .005 (74% vs 28% in Gordon 2021; 61% vs 39% here), interaction vs main effect (20% vs 53%, Altmejd 2019), sample size and era; a fourth tile "what does NOT predict: how famous it is."
Then 3 tutorial items with the cues pre-revealed and an explanation of why the cue pointed the way it did.

---

## 5. The card

### 5.1 Before the guess (plain mode)

```
┌──────────────────────────────────────────────────────────────┐
│ #7 of 10 · Social psychology · Journal of Personality & Social │  ← facet chips; journal optional (cue)
│                                                              │
│ Recalling something unethical you did makes the room         │  ← claim_plain (<= 30 words, present tense,
│ seem darker.                                                 │     no authors, no year in the sentence)
│                                                              │
│ How it was tested: 40 students wrote about an ethical or     │  ← claim_method (1–2 sentences, N stated in words)
│ unethical deed, then rated the brightness of the room.       │
│ Original study: 2012 · N = 40                                │  ← always shown (year, N); cheap and honest
│                                                              │
│ Did an independent replication find the effect?             │
│  0% ───────────●──────────────────── 100%      you: 35%      │  ← slider, default = session base rate (50%)
│  [ Reveal a cue ▾ ]                          [ Lock in → ]   │
└──────────────────────────────────────────────────────────────┘
```
Cue reveal sheet (stats mode; each row appears when tapped, with its base rate): "Original p-value: p < .001 (bucket p <= .005 → 61% of such originals replicated in this dataset)"; "Effect size: d = 0.9 — a large effect for N = 40" (r converted via the R-package rules; verbal label from Cohen with a caveat); "Design: main effect / interaction / correlation"; "Journal: Psychological Science (pool base rate 47%)"; "Era: pre-2015"; "Replication team: independent (0% author overlap), preregistered, N = 1,200" (the *replication* N is a strong cue by itself and is shown last).

### 5.2 After the guess — the three lenses, compact

1. **Verdict line**: "Failed to replicate" / "Replicated" / (famous tier) "Reversed", with your probability, your points, and the crowd's mean probability (n) when available; a one-line "cue check": "p was .03 and the design was an interaction — both cues pointed to 'unlikely'".
2. **Lens 1 – In the authors' words**: `reported_success_quote` (FReD) or FLoRA `outcome_quote`, with `outcome_quote_source` and the replication citation; "Read the replication (open access)" via oa_url_r.
3. **Lens 2 – The numbers**: original vs replication effect size as a two-dot forest strip (r_o vs r_r with CIs when both exist — 554 fair rows; otherwise the raw es/N pair), shrinkage %, the verdict under two or three of the seven FReD criteria when they disagree ("significant in the same direction: yes; inside the original's prediction interval: no; small telescopes: no").
4. **Lens 3 – How close was the replication**: closeness_* (Brandt items; legacy rows), same_design/same_test, preregistration link, author overlap %, power; "N: 40 → 1,200".
5. **Context**: discipline base rate, decade base rate, "this original has 3 replications: 1 successful, 2 failed" (multi-replication items), citation sparkline (counts_by_year from the OpenAlex cache) with the replication year marked; Wikipedia/textbook presence if the overlay exists.
6. **Links**: wiki finding page (canonical), original paper, replication paper(s), FORRT record (rep-api / Replication Atlas DOI page), "report a problem with this card" (opens a pre-filled review issue: leaky / wrong claim / wrong outcome).
7. Next button; keyboard: 1–9 sets 10–90%, Enter locks, Space next.

### 5.3 Item JSON (public, built at `npm run data`)

```json
{
 "item_id": "fred:10.1037/a0026626:study1",         // stable: source + doi_o + study slug; famous:<slug> for tier C
 "version": 3,                                     // bump when text/outcome changes; forecasts store the version
 "tier": "A", "review_state": "reviewed",          // machine | spot-checked | reviewed | retired
 "claim_plain": "...", "claim_method": "...",
 "orig": {"year": 2012, "n": 40, "journal": "Psychological Science", "discipline": "social psychology",
          "subfield_openalex": "Social Psychology", "p_bucket": "0.005-0.05", "p_reported": "0.03",
          "es_repr": "d = 0.90", "r": 0.41, "design": "main_effect", "iv_kind": "manipulation"},
 "cues": ["p_bucket","n","es","journal","era","design","rep_team"],   // which cue rows exist for this item
 "reveal_ref": "items/fred:10.1037…/reveal.json",  // separate file, fetched after lock-in (keeps answers out of the list payload)
 "facets": {"discipline": "social", "decade": 2010, "project": null, "famous": false},
 "difficulty_prior": 0.55,                         // model prior, section 9.3; replaced by crowd Brier when n >= 30
 "provenance": {"fred_effect_ids": [1203,1204], "flora_pairs": [["10.1037/a0026626","10.1177/0956797614562832"]],
                "legacy_ids": ["1234_a"], "docx_name": null, "claim_source": "llm:claude-sonnet-5@2026-09|human:leo"}
}
```
`reveal.json`: outcome (successful|failed|reversed), verdict quotes, numbers for the forest strip, closeness, criteria table, links, base rates, external forecasts (Gordon market price / Hoogeveen lay mean / SCORE where matched).

---

## 6. Scoring, streaks, calibration, sharing, leaderboards

- **Elicitation**: p in [0.01, 0.99] (slider; clamped so log score is finite). Default position = the base rate shown for the session (50% by construction).
- **Per-item score**: Brier B = (p − y)², y ∈ {0,1}. Displayed points = round(100 × (1 − 4B)): p=.5 → 0; p=.9 right → +96; p=.9 wrong → −224; p=.99 wrong → −292; p=.7 right → +64, wrong → −96. Negative points are intentional and explained ("overconfidence is expensive"); the running total is the sum. Simpler alternative shown as the headline: **accuracy-equivalent** = mean Brier translated to the literature scale (0.25 = coin flip; 0.20 ≈ Hoogeveen laypeople; ~0.17 ≈ markets) so players can compare with "laypeople 59%, markets 73%, repliCATS 76%".
- **Stats mode cue costs**: each revealed cue −5 points from that item's score (never from the Brier record, which is stored raw with the cue path).
- **Session summary**: items, hits (p on the right side of 50%), mean Brier, skill score 1 − B̄/0.25, over/under-confidence index (mean |p − 0.5| vs hit rate), best and worst call with its cue check.
- **Calibration curve** (unlocked after 30 lifetime items; stored locally): 5 bins (0–20, 20–40, 40–60, 60–80, 80–100) plotting forecast vs observed frequency with Wilson intervals; text summary "when you say 80% you are right 61% of the time"; overlay the crowd curve and the literature (experts over-optimistic by 12–14 points).
- **Streaks**: *day streak* (played the daily set N days in a row) and *calibration streak* (N consecutive daily sets with skill score > 0) — cosmetic, never multiplied into the score. Badges: "Reads the p-value" (stats-mode Brier improves after cue reveal on 20 items), "Base-rate respecter", "Domke-proof" (correctly low on 5 famous 'hot' findings).
- **Share card**: Wordle-style text + image. Text: `Did it replicate? · Daily #142 · 7/10 · Brier .16 · 🟩🟩🟨🟥🟩🟩🟨🟩🟩🟩 · <url>#d=2026-09-07` where 🟩 = right side and p ≥ 70% confidence-appropriate, 🟨 = right side but hedged (50–70%), 🟥 = wrong side, ⬛ = skipped; emoji order reveals nothing about which items (everyone has the same items on the same day, and the outcome of item k is not derivable from a square colour without knowing the guess). Image: client-rendered SVG→PNG (Web Share API on mobile, copy-to-clipboard on desktop); OG preview for the `#d=` URL is a static per-day image built at deploy time (no server needed).
- **Leaderboards**: daily only (same items for all) with a minimum of 10 items, ranked by mean Brier; ties by earlier completion; anonymous by default ("Anonymous otter #4821" generated names), optional nickname; all-time board = mean of the last 30 dailies with >= 10 dailies played (prevents one lucky day). Classroom boards are room-scoped. No global endless leaderboard (unequal items → not comparable).

---

## 7. Fairness rules and leakage tests

Inclusion (binary modes):
1. Outcome ∈ {successful, failed} in FReD `reported_success`, or FLoRA `outcome`, or docx status ∈ {replicated, not replicated, reversed}; if both FReD and FLoRA code the pair they must agree (93.3% do; 116 rows disagree — those are set to "mixed" and removed from binary play).
2. All fair effects of the original agree (693 of 711 originals), and if several replication papers exist they agree (else the item goes to the aggregate/mixed tier with the majority shown as "mostly failed/replicated" and 3-way scoring).
3. Card text exists and passes leakage tests (below); year and N of the original known (N may be "not coded" for Tier B → plain mode only).
4. Not in the exclusion table: `discipline == management` (JOM block: 100/103 successful), Soto 2019 (41 successful/19 mixed rows), any replication paper with >= 15 clear effect rows and >= 90% one-way (list in 3.1) — at the original grain these collapse to 1 item each anyway; plus a manual exclusions file (`data/curated/game/exclusions.csv` with reason + reviewer + date).
5. One item per original per session; at most one item per replication project (RP:P, ML1–5, SSRP, RRRs, CORE, X-Phi, Boyce RSOS student replications) per daily set, so "project style" cannot be learned as a tell.
6. Per-session stratification: exactly 50/50 in daily and by-facet sets; rolling 50/50 in endless.
7. Never show the replication's N, year, or team before the guess in plain mode (they are strong tells: preregistered multi-site N = 4,000 ⇒ likely a failed famous effect); in stats mode they are the *last* cue and cost the most.

Leakage tests (run at build; any failure → `review_state = flagged`, item not shipped):
- **Regex**: claim_plain / claim_method must not match `replicat|reproduc|did not|failed|fail(ure|s)|null result|no (significant )?effect|not significant|robust|meta-analy|retract|controvers|debunk|famous|classic`. Today: 74 of 1,408 fair FReD descriptions and 130 claim_text_o strings, and 11 of 362 docx descriptions, trip this (mostly harmless "replicated condition: grasp" style, but they must be rewritten anyway).
- **Entity**: no author surname from `author_o`/`author_r`, no title words in unusual sequence (n-gram overlap of >= 5 consecutive tokens with title_o → flag), no year inside the claim sentence, no verbatim overlap of >= 8 tokens with `reported_success_quote`/`outcome_quote`.
- **Hedging asymmetry**: successful items must not be written more confidently than failed ones. Test: an LLM judge scores each claim for hedging (0–3) blind to outcome; mean hedging by outcome must not differ by > 0.2; also word-count and readability parity by outcome.
- **Model-guess test** ("can the card be gamed?"): a held-out classifier (and a separate LLM given only the card text) predicts the outcome. Pool-level: if accuracy from *text alone* exceeds ~70% (human ceiling from Hoogeveen 59–67%; literature markets 73% *with* stats), the claim style is leaking something systematic — inspect top features. Item-level: any item the LLM calls with >= 90% confidence, correctly, *and* whose stated reason cites the wording rather than the science → flag for rewrite. Record the model's probability as `text_only_prior` (also useful to set difficulty).
- **Crowd retirement**: after 100 crowd forecasts, an item where mean |p − 0.5| > 0.35 and hit rate > 0.9 is auto-flagged (too easy → probably leaking or famous-tier tell) and reviewed.
- **Famous-tier tell**: famous items are only played in the famous mode or mixed in at ≤ 2 per daily set, since "I recognise this" is a legitimate but different skill; the reveal says "you may have heard of this one".

---

## 8. Writing plain-language claims for ~2,000 items (pipeline)

Input per original: FReD `description` (846 of the 1,199 fair descriptions >= 30 chars are already plain claims without statistics/condition labels; 353 are stat fragments like "JE-predicted-experience condition for 10 negative…"), `claim_text_o` (verbatim result sentence with numbers, median 233 chars), title_o, abstract (OpenAlex/Crossref/PubMed cascade; cached for 1,420 legacy DOIs), n_o, es_repr_o, es_type_o, p, discipline, tags, legacy `effect` name where matched, docx description/name for Tier C, and — for Tier B — title_o + abstract + FLoRA `outcome_quote` (used ONLY to help the model identify *which* claim was tested, never quoted).

LLM step (claude-sonnet-5 in Batches, structured output; ~2,100 items × ~2.5k tokens ≈ < $10 total at the prices cached in the claude-api skill; store model id + prompt hash + timestamp per item so it is reproducible):
```
system: You write quiz cards for a game where players guess whether a psychology finding was successfully replicated. Write for a curious non-scientist. NEVER mention replication, authors, years, journals, fame, controversy, or how the study turned out. NEVER hedge more or less depending on how plausible the claim sounds. State the finding as the original authors claimed it, in the present tense, <= 30 words. Then describe how it was tested in 1–2 sentences including the number of participants in words and the key manipulation/measure. Output JSON only.
user: {description, claim_text_o, title_o, abstract, n_o, es_repr_o, discipline, effect_name}
schema: {claim_plain, claim_method, design: main_effect|interaction|correlation|other, iv_kind: manipulation|measured|natural, dv_kind: behaviour|self_report|physiological|judgment|performance, n_extracted, plausibility_neutral_check: bool, uncertain_fields: [..], notes}
```
Post-processing: leakage tests (section 7) → `review_state = machine`; 10% random sample + 100% of flagged + 100% of famous tier → human review in a tiny reviewer UI (the card itself with approve / edit / reject / "outcome looks wrong" buttons; edits are stored as overlay rows in `data/curated/game/claims.jsonl` with reviewer + date, never by editing generated files). Ship `machine` items only in endless mode with a small "unreviewed card" glyph; daily sets use `spot-checked`/`reviewed` only. Reviewer decisions are also training data for the discovery pipeline's classifier (U1 idea) and are exported in FORRT's `description` column format so improved descriptions can be contributed back.

Item titles (post-reveal only): legacy `effect` name (794 matched rows), docx name (Tier C), else the LLM's 3–5 word effect label, provenance-tagged.

---

## 9. Crowd forecasts as a product: "Will it replicate?"

### 9.1 What gets an open question
- **Registered/announced replications in progress**: OSF registrations using the Brandt "Replication Recipe" template without a post-completion registration (U7: 5,466 title hits; FORRT's rr_scraper recipe), PsyArXiv replication preprints (623) not yet in FLoRA, PCI-RR/Registered Reports in-principle acceptances found via OpenAlex/Crossref, PSA/ManyBabies project pages. These have an expected settlement horizon → the most Metaculus-like.
- **FORRT's own backlog**: 'Additional Studies to be added' (686 rows) and 'Check regularly for Replication' sheets in FReD 2.4.1 — findings FORRT knows are being/were replicated but not yet coded.
- **Most-cited never-replicated originals**: from the citation cache (openalex_original_enrichment_full.json / citation_by_outcome_analysis.json) and from OpenAlex field-32 works with high citations and no FLoRA pair; plus user nominations (a "request a forecast" button on any wiki finding page, throttled).
- Each open question shows: the plain claim (same pipeline), the model prior (9.3), crowd distribution (n, median, IQR), your forecast (editable until settlement, history kept), and "how it settles".

### 9.2 Settlement
- Weekly FLoRA refresh (FORRT ships ~4 releases/week): new (doi_o, doi_r) pairs with outcome successful/failed settle the question at 1/0; `mixed` settles at 0.5 with half weight in scoring (announced up front); reproductions and "descriptive only/uninformative" do not settle. Multiple new replications: settle on the first clear one, re-score if a later one flips the consensus within 12 months (question shows "settled — under review").
- Our own discovery pipeline's *reviewed* pairs settle too, but only after human review (review_state = reviewed) and are labelled "settled by <wiki> review, pending FORRT".
- Players get a settlement notification on their next visit; settled open questions are scored with the same Brier and feed a separate "forecaster" calibration curve.

### 9.3 Calibrating the crowd against the replicated set
Because the same population plays the settled items, the crowd's skill is measurable: crowd mean-probability Brier on settled items, by cue exposure (plain vs stats mode) and by player experience. Publish it on an "How good is the crowd?" page next to the literature (laypeople 59/67%, surveys 66%, markets 73%, repliCATS 76%). Use it to **shrink open forecasts**: displayed forecast = w·crowd_median + (1−w)·model_prior, with w = the crowd's out-of-sample skill on settled items (recomputed monthly; start at w = 0.5). The model prior is a transparent logistic regression fitted on the fair pool with only the documented cues (p bucket, log N, era, discipline/subfield, design type, journal base rate; features from the item JSON), reported with cross-validated AUC and never presented as more than "a rule of thumb"; if its CV accuracy is below ~65% it is shown but not used for shrinkage. Every wiki finding page without a replication shows: "Crowd forecast 34% (n = 212) · rule-of-thumb prior 41% · no replication recorded yet · [forecast]".

### 9.4 The open dataset
Export nightly (CC0 for forecasts, CC-BY for item text): `forecasts.csv` (forecast_id, player_hash, item_id, item_version, mode, cue_path, p_initial, p_final, seconds, outcome_at_time, settled_at) and `items.csv`. This is the instrument: with 1,000 players × 10 items/day it yields in a month more human replication forecasts than the whole literature combined (Gordon: 103 findings; Hoogeveen: 27; SCORE: 3,000 claims but by 865 selected experts).

---

## 10. Storage: static-first, Supabase for anything shared

### 10.1 Decision
- **Static + localStorage** is sufficient for: daily/endless/discipline/decade/famous/stats modes, personal calibration curve, streaks, share cards, seen-items list, settings. Items ship as `game/index.json` (list without answers, ~300 KB for 2,000 items) and per-item `reveal.json` (fetched on lock-in). Progress: `localStorage['drg.v1']` = {player_key (random UUID), seen[], forecasts[] (capped at 5,000; older rolled into calibration bins), streak, settings}; export/import as a JSON file for device moves.
- **Supabase** (a project already exists in the owner's org: 5 projects, all `INACTIVE`/paused, eu-north-1; e.g. `myjiqsmlagigitrhztgp` "leosammallahti's Project" — restore one or create `replication-wiki`; free tier is fine: forecasts are tiny rows) adds: crowd stats per item, daily leaderboard, classroom rooms (realtime), open forecasts + settlement, and the open dataset export. The client never needs the service key; anon key + RLS + one Edge Function.
- Without Supabase reachable (offline, paused project, ad-blocker), the game runs fully; only "crowd" panels show "crowd stats unavailable".

### 10.2 Schema (Postgres / Supabase)
```sql
create table players (
  id uuid primary key,                      -- generated client-side, stored in localStorage; no email, no auth
  nickname text check (char_length(nickname) <= 24),
  created_at timestamptz default now(),
  last_seen timestamptz, country char(2)     -- country from CF header, optional, for coarse stats only
);
create table items (                         -- mirror of the built items (answers included, RLS-hidden)
  item_id text primary key, version int not null, tier char(1), outcome text, facets jsonb, difficulty_prior real,
  review_state text, active boolean default true
);
create table daily_sets (day date primary key, item_ids text[] not null, seed text);
create table forecasts (
  id bigint generated always as identity primary key,
  player_id uuid references players(id),
  item_id text references items(item_id), item_version int,
  mode text check (mode in ('daily','endless','discipline','decade','famous','stats','classroom','open','expert3')),
  day date, room_id text,
  p_initial real, p_final real check (p_final between 0.01 and 0.99), dist3 real[],   -- expert3 mode
  cue_path text[], seconds int, client_ts timestamptz, created_at timestamptz default now(),
  outcome_at_time text, brier real,          -- filled server-side for settled items
  unique (player_id, item_id, mode, day)     -- one scored forecast per item per player per mode/day
);
create table open_questions (item_id text primary key, opened_at timestamptz, source text, horizon date, status text, settled_outcome text, settled_at timestamptz, settled_by text);
create table rooms (room_id text primary key, teacher_key uuid, item_ids text[], created_at timestamptz, expires_at timestamptz);
create materialized view item_crowd as
  select item_id, count(*) n, avg(p_final) mean_p, percentile_cont(.5) within group (order by p_final) median_p,
         avg(brier) mean_brier, avg((p_final>=.5)::int = (outcome_at_time='successful')::int) hit_rate
  from forecasts where brier is not null group by item_id;      -- refreshed every 10 min
create view daily_board as ...;              -- day, player nickname/anon label, n_items (>=10), mean_brier
```
RLS: `players` insert/update own row by id (the id is a bearer secret; acceptable for anonymous play). `forecasts` insert only via the Edge Function `submit_forecast` (validates p range, item active, rate limit, computes brier from `items.outcome`, returns the reveal payload) — the browser never reads `items.outcome` from the DB. `item_crowd`, `daily_board`, `open_questions` are readable by anon. Rooms: teacher_key is the write secret; students insert forecasts with room_id.

### 10.3 Abuse stance
- No accounts, so no ban lists; instead: leaderboard eligibility requires >= 10 items, median answer time >= 2 s, and a player_id older than 10 minutes; one scored forecast per (player, item, mode, day); replays of an item are stored with `mode = 'replay'` and never scored for boards or crowd stats.
- Edge Function rate limit: 60 forecasts / 10 min / player_id and / IP (via Supabase's built-in or a KV counter); Cloudflare Turnstile only for nickname changes and room creation (never for guessing).
- Crowd stats use the median and a trimmed mean; items with < 30 forecasts show "early crowd"; per-player weight capped in aggregation.
- Nickname: profanity list + no URLs + no impersonation of FORRT/OSF; report button; boards can hide a nickname by reviewer action (a `hidden` flag).
- Cheating by reading the wiki page first is possible and fine — it is a learning tool; only daily boards are affected, and the per-item time and the text-only-prior tests catch mass lookups statistically.

### 10.4 Privacy stance
- Anonymous by default: a random UUID in localStorage; optional nickname; no email, no OAuth, no fingerprinting, no third-party analytics; IP is not stored by us (Supabase/Cloudflare transient logs are disclosed). Country is optional and coarse.
- Local-first: forecasts live in the browser; "sync to the crowd" is an explicit toggle on first play (default ON with a clear sentence, since the crowd is the point; opt-out keeps everything local).
- Data published as open datasets after k-anonymisation (player_hash = salted hash rotated yearly, no timestamps finer than the hour, no country for n < 50 groups); a "delete my data" button posts the UUID to a `delete_me` function (and we honour it).
- Classroom: students are anonymous; teachers see room-level nicknames only; rooms expire after 30 days; no minors' data beyond nickname + forecasts.

---

## 11. UI flow and mobile behaviour

Routes (Astro, one Preact/Svelte island for the game):
- `/play` — hub: Daily (with today's number and your status), Endless, Modes grid (discipline / decade / famous / stats / expert), Classroom (join / create), Your calibration, About the scoring.
- `/play/daily/2026-09-07` — shareable, deterministic; `/play/endless`, `/play/discipline/social`, `/play/decade/2000s`, `/play/famous`, `/play/stats`, `/play/room/ABC123`, `/forecast` (open questions), `/forecast/<item_id>`.
- Every wiki finding page gets a "Play this one" affordance *only after* the reveal-equivalent content is scrolled past (or a small "Test yourself first" banner at the top that hides the verdict for that page until answered — the wiki-side cousin of the game; opt-in per visit).

Round loop (both plain and stats): card → optional cues → slider → lock → reveal (three lenses) → next; total time per item TARGET 20–40 s in plain mode. Progress bar of 10 dots for daily; endless shows a running calibration sparkline.

Mobile (most players will arrive from a shared card):
- Single column; the claim in display serif at >= 20 px; card fits above the fold on 360×640 with the slider fixed at the bottom (safe-area aware); the cue sheet is a bottom sheet; slider thumb 44 px, tick labels 0/25/50/75/100, tap-to-set plus drag, haptic tick at 50; big "Lock in" button; a swipe-up on the reveal opens the full lenses (collapsed by default: verdict + one quote + numbers strip).
- Keyboard on desktop: digits set probability, Enter locks, →/Space next, C opens cues.
- PWA: installable, `game/index.json` + today's reveals precached, offline endless works; background sync of forecasts when online.
- Share: Web Share API with text + PNG; fall back to copy.
- Accessibility: the slider is a real `<input type=range>` with aria-valuetext ("35 percent likely to replicate"), outcome colours also encoded by icon and word; reduced-motion respected; colour-blind-safe outcome palette (successful/mixed/failed distinct from vermilion/ultramarine brand accents).
- Visual: paper #f7f6f2 background, ink text, vermilion #d83e27 for "failed", ultramarine #1b2663 for "replicated" (plus icons), mixed in an ochre; the card is the same "placard" component the wiki uses so a round looks like a page of the field guide.

---

## 12. Build plan (what the data/site agents need from this design)

1. `data/derived/game/pool.parquet` builder (Python, in the one-command data build): implements section 3's filters + 7's rules; emits `items.json`, `reveals/`, `exclusions.csv` audit, and a **pool report** (counts by tier/discipline/decade/outcome, leakage-test results, cue base rates) that is published as a wiki page ("How the game is built") and re-run every FLoRA refresh.
2. Claim-writing batch job (section 8) with cache keyed by (item_id, input hash, model id); reviewer UI (can be the Astro dev server + a JSON overlay file; no backend needed for reviewing).
3. Game island: modes, slider, scoring, localStorage store, share card, calibration chart (build-time SVG for static, client SVG for the live curve).
4. Supabase migration (10.2) + Edge Functions `submit_forecast`, `settle` (cron after each FLoRA refresh), `export_open_data` (nightly), `delete_me`.
5. Open-questions feeder from the discovery pipeline (D-discovery agent): pending registrations/preprints → `open_questions`; settlement hook on FLoRA diff.
6. Evaluation from day one: dashboards for pool size, per-item crowd Brier, text-only-prior accuracy, cue marginal value (stats-mode paths), crowd skill vs literature.

Open decisions for the orchestrator: (a) whether "mixed" is ever binary-scored (this design: no); (b) whether Tier B items (LLM-written claims from abstracts) go into daily sets before a human has reviewed them (this design: no — daily = reviewed only); (c) Supabase project choice (restore an INACTIVE one vs new); (d) whether to import Gordon/Hoogeveen/SCORE external forecasts for the "compare with markets" reveal in v1 (recommended: yes for the ~130 items they cover).
