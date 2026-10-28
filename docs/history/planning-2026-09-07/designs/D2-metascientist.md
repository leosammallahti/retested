# D2 — The Meta-Scientist: evidence presentation and computed indicators

Author: designer agent D2 (angle: honest, rigorous evidence presentation). Date: 2026-09-07.
Status: COMPLETE (all numbers below were computed today; scripts and logs listed in §11).

Inputs read: `_planning/BRIEF.md`, `_planning/understanding/_DIGEST.md`, `U5-forrt.md` (data dictionary), `U3-data-assets.md`, `U6-landscape.md`; FORRT code `data/raw/forrt/fred-r-package/{replication_outcomes.R, effect_size_transformations.R, helpers.R}` and `data/raw/forrt/osf/success_criteria.Rmd`.
Data computed on (all local, real files):
- `data/raw/forrt/fred-data/archive/2025-11-30_COSdata_validated.xlsx` (current FReD 2,164 rows + r_o/r_r + statistical_success + correct entry_id) joined row-for-row with `data/raw/forrt/fred-data/output_FReD.xlsx` for year_o/year_r/journals.
- `data/raw/forrt/osf/version-history/FReD_2.4.1_2025-06-25.xlsx` sheet `Data` (legacy, 4,659 data rows).
- `data/raw/forrt/fred-data/output_flora.csv` (FLoRA, 2,815 rows).

---

## 0. TL;DR — what this design commits to

1. **Never one score.** Every attempt gets a 7-criterion matrix (FORRT's R-package criteria, re-implemented in Python and verified: 94.1% agreement with FORRT's own `statistical_success`, 87.2% with authors' `reported_success`). On the 942 attempts where all seven can be computed, the criteria **disagree on 62.3%** of them (unanimous success 207, unanimous failure 148). That is not noise to hide — it is the central content of the "numerical record" lens.
2. **Effect-level verdicts are random-effects meta-analyses of replications only** (Fisher-z, DerSimonian-Laird, project-clustered), reported as pooled r with 95% CI *and* 95% prediction interval, heterogeneity (τ, I²), k, and a leave-one-out stability flag. The verdict label is derived from those intervals by published rules (§4.4), and every label carries the rule, the data tier and the alternative label under the other criteria.
3. **Shrinkage is the headline number, not the binary.** Median replication effect retains **37% of the original** (ratio es_r/es_o, IQR 0.05–0.95, n=1,103); 19.9% flip sign; 22.4% are as big or bigger. Median r_o = .307 vs median r_r = .100.
4. **Site-wide statistics are computed with three denominators** (attempt/effect rows, paper-pair entries, unique originals) because 47.3% of FReD effect rows sit in ten mega-papers; the headline replication rate moves from 45.5% (rows) to 40.5% (entries) to 44.0% (originals) depending on the denominator, so the denominator is always printed.
5. **Data tiers are visible everywhere**: A = r+N on both sides (1,103 attempts), B = one side numeric, C = FReD coded outcome only, D = FLoRA author-reported outcome + quote only (1,843 pairs), R = reproduction (separate vocabulary, never in replication rates).
6. Real predictor findings for the game and the stats pages: original **p ≤ .005 → 56.8% reported success vs 26.1% for .005 < p < .05** (n=512/299, computed from r,N; 57.1% vs 36.3% using reported p-values) — the U6 literature numbers (74% vs 28%) reproduce directionally in FORRT data. N-ratio > 5 → 37.3% success vs 67.0% for N-ratio < 0.5 under authors' verdicts, but flat (47.5% → 43.3%) under `significance_r` — i.e. the N-ratio "effect" is mostly a self-replication / criterion artefact. Author overlap > 0 → **87.3% success (n=292) vs 49.3% (n=1,480)**.

---

## 1. Units of analysis and identity

FReD's own structure (`datastructure.png`, U5 §2): a row = (original study, replication study, effect). We keep that grain and add two layers above it.

| Unit | Definition | Source id | Stable slug (build) | Count today |
|---|---|---|---|---|
| **Attempt** | one effect tested in one replication study against one original study; the row of FReD | archive `effect_id` within `entry_id` (output_FReD.xlsx has entry_id==1 bug — use the archive file or recompute entry_id = group by (doi_o, study_o?, doi_r/url_r)) | `att_<sha1(doi_o|study_o|doi_r_or_url_r|study_r|claim_text_o[:80])[:10]>` | 2,164 (FReD) + 3,234 legacy-only rows (tier C/A) |
| **Entry / Pair** | one (original paper, replication paper) pair = FLoRA row | FLoRA (doi_o, coalesce(url_r, doi_r)) | `pair_<doi_o_hash3><doi_r_hash3>_<n>` | 2,526 replication pairs, 289 reproduction pairs; 1,004 FReD entries |
| **Effect** | a named finding (e.g. "Ego depletion") to which attempts belong | legacy `effect` (443 names), Reversals sheet (583), docx overlay (362), curated overlay; fallback = "original study-effect" key (doi_o, study_o) | `eff_<slug>` for named; `eff_orig_<hash>` for unnamed | legacy names reach 561 current rows (143 names); by doi_o alone 877 rows but 74 originals carry >1 name → needs claim-level review |
| **Original** | a specific original study (paper + study number) | (doi_o, study_o) | `orig_<hash>` | 865 in current FReD |
| **Project** | multi-site collaboration whose sites are separate attempts | legacy `source` (ML1/ML2/ML3/RRR*/OSC 2015/SSRP/CORE/...), FReD doi_r for mega-papers | `proj_<name>` | see §5.3 |

Key finding on identity in current FReD: grouping current rows by doi_o gives 786 originals of which only **52 have ≥2 distinct replication papers, 11 have ≥3 (max 4)**. Multi-attempt effects live mostly in the legacy file (ML sites) and in FLoRA. So the effect layer must be built as a MERGE (current ∪ legacy-only ∪ FLoRA-only), not from current FReD alone.

Also: of 318 FReD entries with >1 effect row, only **9** have heterogeneous outcomes across effects — `reported_success` is effectively coded at paper level and propagated. Treat it as an entry-level variable (and say so on the page), and let the numerical criteria be the effect-level variable.

---

## 2. Effect-size conversions and pitfalls

### 2.1 What FORRT's R package does (`effect_size_transformations.R`, verified by re-implementation)

Target metric: Pearson r (signed where possible). Rules:
- r, phi → as is. R² → √R² (unsigned).
- d, g, SMD → r = d/√(d²+4) (signed).
- OR → d = ln(OR)·√3/π (Sánchez-Meca 2003) → r (signed; OR<1 negative).
- η² (non-partial) → d = 2√(η²/(1−η²)) → r (unsigned). f → d = 2f. f² → R² = f²/(1+f²) → r.
- Test statistic strings: `t(df) = v` → r = t/√(t²+df); `F(1, df2) = v` → t=√F; `z = v, N = n` → r = z/√(z²+N); `X2(1, N = n) = v` → r = √(χ²/N). F with df1>1 and χ² with df>1 → NA.
- Declared non-convertible: partial η², β, b, Cramér's V, dz, hazard ratio, Cohen's h, percentage, sr², unstandardised coefficients.
- Then `align_effect_direction()`: es_o := |es_o|, es_r := es_r·sign(es_o). `add_uncertainty()`: vi = (1−r²)²/(n−1) (metafor COR), CI via Fisher z with se = 1/√(n−3), p from t = r√((N−2)/(1−r²)), df = N−2.

### 2.2 What our re-implementation yields on the current FReD (today)

| | original side | replication side |
|---|---|---|
| converted by us | 1,226 | 1,223 |
| FORRT archive r_o/r_r non-null | 839 | 1,002 |
| both available | 763 | 908 |
| \|ours − FORRT\| > .01 | 9 | 8 |
| **coalesced (ours, fallback FORRT)**, both sides, N>3 | **1,103 attempts** (tier A) | |

Conversion routes (original side): d 341, F(1,df) 275, r 165, t 136, η² 120, F(df1>1) 108 (lost), OR 72, χ²(1) 68, z 26, f² 19; **unparsed test-statistic strings 135** (e.g. `X2(2, N = 64) = 11.28`, `t(84) = .27` — FORRT's regex requires a digit before the decimal point, `F < 1`, `F < 1.4`); non-convertible partial η² 173, β 151, b 123; **'r-squared' 42 rows are lost only because the label is spelled "r-squared" and FORRT's map has "r-square"** (fixable); 'ser_method' 32/65 (undocumented label; treat as unknown until FORRT's codebook explains it).

### 2.3 Pitfalls to encode as explicit flags (each becomes a `caveat[]` entry on the attempt)

1. **Partial η² (173/198 rows)**: convertible to r only in single-factor designs (then η²_p = η²). Policy: do not convert; if `claim_text_o`/test statistic implies a one-way design (F(1,df) present) use the F route instead. Flag `es_nonconvertible:partial_eta2`.
2. **Sign loss**: η², F, χ², R², f give |r| only. The alignment step then assumes the replication is in the same direction whenever its ES is also unsigned — a *silent* success bias. Policy: when both sides are unsigned, take direction from `reported_success` ∈ {failed with quote mentioning "opposite"} or from a curated `direction` field; else flag `direction:unknown` and exclude from `significance_r` reversal detection (still usable for magnitude criteria).
3. **Unequal groups for d → r**: d/√(d²+4) assumes p=q=.5; general form r = d/√(d² + 1/(pq)). FReD lacks group sizes; flag `d_to_r:equal_groups_assumed`.
4. **Nested / dependent data (21% of originals and replications coded `nested_o/r = yes`)**: N is not the number of independent units; CIs and p from r,N are too narrow; homogeneity Q is anti-conservative. Policy: keep criteria but stamp `nested:true` and show CI with a "nominal" label; do not include nested rows in the site-wide criteria disagreement rate (report both with/without).
5. **OR → d** assumes a logistic latent variable; for rare events r is base-rate dependent. Flag `or_to_r:logistic_assumption`.
6. **Within-subject dz** is not d; cannot be converted without the pre/post correlation. Flag and exclude (8 rows).
7. **r = ±1** → clip to ±.9999 (FORRT does this) and flag `es_clipped`.
8. **Reported vs computed significance mismatch**: among 1,035 attempts with a reported original p, **45 have computed p ≥ .05 while the paper reports p < .05, and 125 the reverse**. The 161 tier-A attempts with computed p_o ≥ .05 ("OS not significant") are disproportionately nested (32% vs 21%), small (median n_o = 60, median r_o = .13) and concentrated in the Boyce student-replication paper (31) and RP:P (11). Policy: show both p's; criterion `significance_r` uses the computed one (as FORRT does) but the page says "original reported p < .05; recomputed from r and N: p = .07 (nested design)".
9. **Test-statistic parser**: extend FORRT's regexes: allow `.27`, `−`/`–` minus signs, `t(84.3)`, `X2(1) = 4.1, N = 80`, `F(1,154)=11.03, p<.001` trailing text; for `F(df1>1)` compute η²_p = F·df1/(F·df1+df2) and store it as a *bounded* magnitude (flag), not as r; for `χ²(df>1)` store Cramér's V = √(χ²/(N·min(k−1,…))) as magnitude only.
10. **Hedges' g vs d**: treat as d (FORRT does); the small-sample correction is <2% for n>30.
11. **Meta-analytic replication ES** (`es_type_r = meta-analysis`, 4 rows) — n_r must be the pooled N; flag.

### 2.4 Secondary display metric
Show r as primary (FORRT convention) with d = 2r/√(1−r²) on a secondary axis and in tooltips, and the original reported metric verbatim (`es_value_o`, `es_type_o`, `es_repr_o` page reference) so nobody has to trust the conversion.

---

## 3. Per-Attempt indicators

Computed for every attempt; missing inputs → indicator = null with a reason code, never 0.

### 3.1 Inputs
`r_o, n_o, r_r, n_r` (tier A), `p_rep_o, p_rep_r` (reported p, with `pval_type` ⟨ < , = , > ⟩ and tails), `nested_o/r`, `prereg_r`, `author_overlap`, `reported_success` (+quote, +source), FLoRA `outcome` (+quote), legacy `closeness_*`, `same_design`, `same_test`, `power`, `preregistration`, `osf_link`.

### 3.2 Derived uncertainty
```
z_x = atanh(r_x);  se_x = 1/sqrt(n_x - 3)
CI95_x = tanh(z_x ± 1.96·se_x)
p_x = 2·T.sf(|r_x·sqrt((n_x-2)/(1-r_x²))|, df = n_x-2)
vi_x = (1-r_x²)²/(n_x-1)                       # metafor COR, used for FE pooling
PI95 (Patil/Peng/Leek 2016) = tanh(z_o ± 1.96·sqrt(1/(n_o-3) + 1/(n_r-3)))
power_r = P(replication detects r_o at n_r, two-tailed .05)   # FORRT compute_power_r
r33 = r that gives the original 33% power at n_o             # FORRT find_r_for_power(.33, n_o)
```

### 3.3 The seven FORRT criteria (outcome ∈ {success, failure, failure (reversal), OS n.s., null})
Implemented exactly as `assess_replication_outcome()`; verified on the vignette examples and against the archive `statistical_success` (94.1% agreement, n=615; the 6% are rows where FORRT used a different r than our conversion — those 17 rows are listed by the DQ module).

| # | criterion | rule | today's success share (n=1,103, tier A) |
|---|---|---|---|
| 1 | significance_r | p_o<.05 else "OS n.s."; p_r<.05 & same sign → success; opposite sign → failure (reversal) | 39.9% (46.7% excl. 161 OS n.s.; 58 reversals) |
| 2 | significance_agg | FE pool of both (COR vi); ci_lb>0 & est>0 → success | 71.4% |
| 3 | consistency_ci | r_o strictly inside CI95(r_r) | 35.6% |
| 4 | consistency_pi | r_r strictly inside PI95(r_o, n_o, n_r) | 61.3% |
| 5 | homogeneity | Q-test p ≥ .05 | 58.5% |
| 6 | homogeneity_significance | Q p>.05 & FE ci_lb>0; OS n.s. if p_o≥.05 | 40.7% (47.7% excl.) |
| 7 | small_telescopes | r_r ≥ r33 | 47.1% |

Plus LeBel et al. (2018) coding from `code_replication_outcomes()`: `signal` (p_r<.05) × `consistency` (r_o inside CI_r → consistent; else inconsistent-larger/smaller/opposite) — this is the vocabulary FReD legacy `outcome` already uses ("signal - consistent (imprecise)"), keep it as an 8th, descriptive row.

### 3.4 Criteria disagreement (the fact the page must show)
On the 942 attempts where all seven are defined: satisfied-criteria count distribution 0:148, 1:149, 2:90, 3:104, 4:50, 5:64, 6:130, 7:207 → **62.3% of attempts are "it depends on the criterion"**. Pairwise agreement ranges from .97 (PI ≈ homogeneity — they are almost the same test) to .49 (aggregate significance vs CI consistency). Agreement with authors' `reported_success` (successful/failed only): significance_r .872, small_telescopes .809, homogeneity_significance .694, consistency_ci .660, homogeneity .648, consistency_pi .626, significance_agg .622. Authors, in other words, mostly use criterion 1.

Per-attempt display: a 7-cell strip (✓ / ✗ / ⊘ n.a.) + "5 of 7" + the sentence "Criteria that judge *whether an effect exists* (1, 2, 6) say X; criteria that judge *whether the original was accurate* (3, 4, 5, 7) say Y". Never collapse into a percentage.

### 3.5 Shrinkage (per attempt)
```
ratio = r_r_aligned / r_o_aligned          # "share of original effect retained"; undefined if r_o≈0 (|r_o|<.02 → null)
dz    = atanh(r_r) - atanh(r_o);  se_dz = sqrt(1/(n_o-3) + 1/(n_r-3));  CI95_dz = dz ± 1.96·se_dz
```
Today: ratio quantiles 10% −0.26, 25% 0.05, **50% 0.37**, 75% 0.95, 90% 1.34; 54.7% retain < half; 19.9% reverse sign; 22.4% ≥ 1. By original size: r_o ∈ (0,.1] median ratio .91 (tiny effects can't shrink much — regression artefact), (.1,.2] .28, (.2,.3] .34, (.3,.5] .34, (.5,1] .50. By authors' verdict: failed median ratio .09 (IQR −.05–.30), mixed .36, successful .91 (.60–1.20). Present ratio only with its CI on dz and only when |r_o| ≥ .05; otherwise show dz.

### 3.6 Attempt-level "informativeness" (not success)
- `power_r` for r_o at n_r: 80.1% of tier-A replications have ≥ .8 power for the *original* effect; legacy `power` column median .976. Display as "Could this replication have found the original effect? power = .97".
- `n_ratio = n_r/n_o` (median 1.67; medians n_o 101, n_r 217).
- `prereg_r` present (54% of FReD rows; 64.9% of failed vs 50.9% of successful attempts).
- `author_overlap` (0–1): 87.3% success when >0 vs 49.3% when 0 — show as a badge "replication team overlaps with original authors".
- `closeness` fingerprint where coded (§6.5) and `same_design`/`same_test`.
- Tier badge A/B/C/D/R.

---

## 4. Per-Effect indicators

### 4.1 Which attempts enter the pool
Replications only (originals are shown but not pooled — pooling them assumes no publication bias, which is the thing under test). Tier A attempts. Sites of a multi-site project are pooled **within project first** (RE or FE by project's own choice, default RE) and enter the effect pool as one project-level estimate; the page shows both the "site-level" and "project-level" pooled results (they differ mainly in CI width, and the project-level one is the honest default because sites share protocols). Attempts flagged `nested` or `direction:unknown` enter with a caveat count shown next to k.

### 4.2 Random-effects pooling (formulas, as implemented today in `compute2.py`)
```
z_i = atanh(r_i), v_i = 1/(n_i-3), w_i = 1/v_i
z_FE = Σw_i z_i / Σw_i ;  Q = Σ w_i (z_i - z_FE)² ; df = k-1
C = Σw_i - Σw_i²/Σw_i ;  τ² = max(0, (Q-df)/C)            # DerSimonian-Laird (swap for REML/PM in build; DL is fine for display)
w*_i = 1/(v_i+τ²) ; z_RE = Σw*_i z_i / Σw*_i ; se_RE = sqrt(1/Σw*_i)
CI95 = tanh(z_RE ± 1.96 se_RE)
PI95 (Higgins 2009) = tanh(z_RE ± t_{.975,k-2}·sqrt(τ² + se_RE²))   (k≥3)
I² = max(0,(Q-df)/Q) ; Q p-value = χ²_df.sf(Q)
effect-level shrinkage = tanh(z_RE)/median(r_o over the effect's originals) with bootstrap CI over attempts (B=2000)
leave-one-out stability = does the status label (§4.4) change when any single attempt (or project) is dropped?
```
Results today on legacy effect names (only the legacy file has names + r + N): 51 named effects with tier-A rows; 35 with k≥2, 29 with k≥3, 23 with k≥5, 16 with k≥10 (site-level k). Examples (RE of replications, site-level):

| effect | k (papers) | median r_o | pooled r [CI] | τ | I² | PI |
|---|---|---|---|---|---|---|
| Anchoring | 75 (3) | .313 | .496 [.438,.550] | .31 | 94 | [−.09,.83] |
| Verbal overshadowing (RRR1/2) | 52 (1) | .345 | .176 [.110,.240] | .21 | 88 | [−.25,.55] |
| Imagined contact (ML1) | 36 (1) | .395 | .094 [.070,.119] | 0 | 0 | [.07,.12] |
| Flag priming (ML1) | 36 (1) | .243 | .049 [.025,.074] | 0 | 0 | |
| Money priming | 25 (2) | .359 | .046 [.020,.073] | 0 | 0 | |
| Hostility priming (RRR9) | 23 (1) | .326 | .100 [.058,.142] | 0 | 0 | |
| Availability heuristic (ML3) | 21 (1) | .379 | .072 [.036,.107] | 0 | 0 | |
| Heat priming | 18 (5) | .570 | .007 [−.021,.035] | .02 | 12 | |
| Macbeth effect | 11 (3) | .450 | −.005 [−.067,.057] | .05 | 26 | |
| Ego depletion (individual) | 8 (6) | .397 | .149 [.043,.252] | .11 | 50 | [−.14,.42] |
| Power posing | 6 (6) | .300 | .077 [.020,.134] | 0 | 0 | |
| Elderly priming | 5 (2) | .454 | .115 [−.001,.227] | 0 | 0 | |

Across the 29 named effects with k≥3: pooled CI excludes 0 for 69%, **but pooled estimate is below half the original for 72.4%, and the original median r sits inside the replication prediction interval for only 41.4%**. "Exists but is much smaller than claimed" is the modal outcome and needs its own label (§4.4). I² median for k≥5 is 0 (mean 28.5) because most are Many-Labs sites with shared protocols; anchoring (I² 94) and verbal overshadowing (88) are the genuine heterogeneity cases.

Note the near-duplicate names ("Ego Depletion"/"ego depletion", "Money Priming"/"Money priming") — the effect-name normalisation must be case/whitespace-insensitive with a curated alias table (Reversals sheet has `alternative names`).

### 4.3 Also computed per effect
- `k_attempts`, `k_papers` (distinct doi_r), `k_projects`, `n_total_r`, `n_tierA/B/C/D`.
- Author-reported tally from FReD `reported_success` and FLoRA `outcome` (successful/failed/mixed counts) — always shown next to the numeric verdict as the "author reports" lens.
- Original evidence: each original's r_o [CI], p_o, n_o, `nested_o`, journal, year; z-score of original for the site-wide z-curve.
- Cumulative meta-analysis by replication year (feeds the timeline, §6.3).
- Reproduction record (separate): list of reproduction pairs with their FLoRA outcome vocabulary.

### 4.4 Graded evidence status (label + rule + uncertainty band)
Applied to the project-level RE pool of replications, in the original's direction; SESOI default r = .10 (site-wide constant, changeable per effect in the curated overlay with a reason).

| label | rule | today (k≥2 named effects, n=35) |
|---|---|---|
| **Replicated — robust** | k≥3, CI_lb > 0, PI_lb > 0, pooled ≥ 0.5·median r_o | part of 12 "robust" |
| **Replicated — smaller** | CI_lb > 0, PI_lb > 0 (or k=2), pooled < 0.5·median r_o | (split of the 12; anchoring/ML1 items land here) |
| **Supported but heterogeneous** | CI_lb > 0, PI includes 0 | 9 |
| **Not replicated — negligible** | CI_ub < SESOI (.10) | 4 |
| **Not replicated — inconclusive** | CI includes 0, CI_ub ≥ SESOI | 9 |
| **Reversed** | CI_ub < 0 | 1 |
| **Single attempt** | k = 1 → show attempt criteria only; status = "one replication: <criteria strip>" | (the majority of FReD originals: 734 of 786 have 1 replication paper) |
| **Author-reported only** | tier D (FLoRA outcome + quote) | 1,843 FLoRA pairs |
| **Not yet replicated** | curated effect with 0 attempts | docx-only effects |

Uncertainty band attached to every label: (i) `stability`: label unchanged under leave-one-out (yes/no + which attempt flips it); (ii) `criteria_vote`: share of tier-A attempts where ≥4 of 7 criteria say success, with the full 0–7 histogram; (iii) `tier_mix`: how many attempts are tier A vs C/D; (iv) `alt_label_if_originals_pooled` (the label you would get with FORRT's significance_agg logic) shown greyed, so the reader sees that pooling originals changes the story. The label is rendered as a band, e.g. "Replicated — smaller (pooled r .09 [.07,.12]; original .40; k = 36 sites in 1 project; stable)". No colour-only encoding; the outcome palette (successful/mixed/failed/other) from the design tokens applies to the label chip, with the pattern ✓/~/✗ also in text.

---

## 5. The ugly cases

### 5.1 Mixed / NA / qualitative outcomes
- FReD `reported_success` vocabulary: successful 985, failed 787, mixed 359, "statistically successful but flawed" 18, "descriptive only" 10, "uninformative" 5. FLoRA: successful 1,042, failed 901, mixed 564, + 17 others. Keep the vocabulary verbatim as the *author-report* lens; map to a 4-way display class {success, mixed, failure, other} only for colouring; never fold "mixed" into failure (FLoRA's rule: close works but conceptual fails → mixed; conflicting multi-study → mixed).
- Effect rows within a paper: FReD-vs-FLoRA agreement is 91.9% (n=1,972 joined effect rows); the disagreements are almost all FLoRA "mixed" at paper level where the effect row says failed (85) or successful (66) — exactly the expected grain difference. Display rule: on an attempt page show the effect-level verdict with the sentence "the paper as a whole was coded *mixed* by FORRT (FLoRA)".
- Tier D pairs (no numbers) get no criteria strip, no shrinkage, no pooling; they show the quote, its source (abstract 1,744 / OSF report 153 / …), and a "help code this" call-to-action linking to FORRT's submission template.
- "OS not significant" (161 tier-A attempts): the significance-based criteria are meaningless; show the attempt with the magnitude criteria only and the note in §2.3(8).

### 5.2 Reproductions vs replications
Reproductions (289 FLoRA rows, 98% outcome-NA, own vocabulary "computationally reproducible, robust" etc.) are a separate evidence type: listed on the effect/paper page under "Reproductions & robustness checks", never counted in any replication rate, never pooled. When FORRT's reproduction vocabulary is filled, map to {reproducible, reproducible-with-issues, not reproducible, not checked} with the quote.

### 5.3 Multi-site projects and double counting
Facts: rows per replication DOI in FReD — `10.1098/rsos.231240` (Boyce student replications) 280 rows (13% of FReD), RP:P 94, JOM 2005 block 76 (management, 97.1% "successful" — a coding block, not a finding), X-Phi 69, PNAS 2021 64, Soto 2019 60, ML2 38; **47.3% of all FReD effect rows sit in replication papers with ≥20 rows**. FORRT's own filtered FLoRA drops Boyce (140 pairs) for the Zotero API.
Rules:
1. Every site is an attempt (it is the data), but the *report* is the project paper; statistics pages always show three denominators: attempts (rows), entries (paper pairs; 1,004 in FReD: 45.8% failed / 40.5% successful / 13.6% mixed), unique originals (786: 44.0% successful / 37.2% failed / 18.8% mixed). Rows: 45.5% successful / 36.4% failed.
2. Pool sites within project before pooling across projects (§4.1); site-level k and project-level k both printed ("k = 36 sites in 1 project").
3. Mega-paper flag `mega_report:true` (≥20 rows) shown on the attempt so a reader knows it is one of 280 student replications; the Boyce set and the JOM block are excluded from *predictor* analyses (their internal homogeneity would dominate) and this exclusion is printed on the stats page.
4. Project pages (ML1..5, RRR1-10, OSC 2015, SSRP, CORE, Soto, X-Phi, OpAQ, openmkt, Data Replicada) with the project's own success rate from the legacy `result`: ML1 58.2% (352 site-rows), CORE 72.3% (191), ML3 6.9% (145), OSC 2015 43.8% (80 coded), Soto 87.8% (74), OSF Registries 47.5% (61), openmkt 44.0% (50), X-Phi 77.5% (40), ML2 54.5% (33), RRR1 24.1%, RRR10 24.0%, RRR2 47.8%, RRR9 4.3%, SSRP 66.7% (21), Data Replicada 10.5% (19), RRR3 50%. (These are site-row rates where the project is multi-site; the page must say "per site" vs "per effect".)

### 5.4 Effects with several originals (and originals with several effects)
- The effect page lists each original separately (its own r_o, CI, p, n, year, journal). Shrinkage and PI/CI criteria are computed **per attempt against its own original** (that is what the FReD row encodes). The effect-level pool ignores originals; the effect-level "shrinkage" divides by the median r_o across originals, with the range shown.
- When a replication paper tests one effect against two originals (FReD id 6 pattern), both rows exist; the pooled replication estimate deduplicates by (doi_r, study_r, effect) so the replication sample is counted once.
- One original with several effects: effect rows are separate attempts; the *paper* page shows the entry-level verdict and the effect strips; the *effect* page shows only its rows.

---

## 6. Visualizations (all build-time SVG via Astro components; one interactive island for the explorer scatter)

Palette: paper #f7f6f2, ink, vermilion #d83e27 (originals / "claimed"), ultramarine #1b2663 (replications / "observed"), plus a colour-blind-safe outcome palette for success/mixed/failure/other (distinct from brand accents; U4). Every chart: r axis with d ticks on the top axis, zero line, SESOI band ±.10 shaded, n printed.

### 6.1 Forest plot per effect
Rows: originals (vermilion squares, hollow if OS n.s.) grouped at the top; replications grouped by project (indent sites under a project header with the project-level RE diamond), sorted by year; point = r, whisker = CI95, marker area ∝ n; a light band across all replication rows = PI95 of the pooled estimate; bottom: RE diamond (replications only) + PI bar; right margin: the 7-cell criteria strip per attempt and the tier letter. Caption text auto-generated: "k = 36 sites in 1 project; pooled r = .09 [.07, .12]; τ = 0; original r = .40 (n = 48)". Nested rows get a dashed whisker.

### 6.2 Shrinkage scatter (site-wide and per discipline/project)
RP:P-style: x = r_o, y = r_r (aligned), diagonal y = x, horizontal 0 line, points coloured by the *selected* criterion outcome (dropdown of 7 + authors' verdict), size ∝ n_r, hollow if nested. Marginal histograms of the ratio (log scale for ratio > 0; separate bar for sign flips). Sidebar text: "Median retained: 37% (IQR 5–95%); 20% reverse sign; n = 1,103 tier-A attempts". Toggle to exclude mega-reports.

### 6.3 Evidence timeline per effect
x = year (original year to now), y = r with CI; originals as vermilion; replications as ultramarine; a cumulative-RE line "what the pooled replication evidence said at the end of each year" with its CI ribbon; event markers from the curated overlay (retraction, RRR, expression of concern); author-reported tally per year underneath as small stacked ticks; docx "status" (replicated/mixed/not/reversed) as a labelled curator marker with its date and provenance.

### 6.4 Discipline × year
Small multiples per FReD discipline (34 normalised labels; show the 12 with n ≥ 40): stacked share successful/mixed/failed by replication year with Wilson 95% CI on the success share and the denominator printed; toggle rows/entries/originals; a "mega-report" hatch. Current numbers by discipline (rows, authors' verdict): social 643 → 34.8% s / 49.6% f / 14.0% m; cognitive 442 → 54.5/29.4/15.8; "psychology" 151 → 50.3/39.1; marketing 129 → 24.0/46.5/29.5; economics 119 → 21.8/20.2/58.0 mixed; management 103 → 97.1% (JOM block, flag); X-Phi 75 → 74.7; education 74 → 33.8/45.9; differential 69 → 71.0/0/27.5; JDM 48 → 33.3/50.0; linguistics 47 → 31.9/55.3; neuroscience 43 → 51.2; developmental 35 → 82.9; evolutionary 17 → 0/100. By original decade: 1990s (229) 55.9% s; 2000s (627) 40.2/40.5/19.1; 2010s (1,116) 45.1/36.9/15.4; 2020s (149) 55.7/30.2. FLoRA (paper pairs) by replication year, n≥100: 2014 38.0% s, 2015 42.0, 2016 48.8, 2018 46.5, 2019 37.8, 2020 38.1, 2021 34.8, 2022 36.8, 2023 37.1, 2024 44.3, 2025 44.0, 2026 43.8 — flat within noise; the page must say "no trend".

### 6.5 Closeness fingerprint
Legacy `closeness_*` (10 Brandt-recipe dimensions: instructions, measures, stimuli, procedure, location, remuneration, participants, exclusions, language, nationality; 1 = exact … higher = more different) exists for 180 rows (157 complete; 141 from individual submissions). Glyph: a 10-cell horizontal strip, cell shade by value (1 dark = same, 2 mid, ≥3 light = different), tooltip with FORRT's scale text; missing = hatched "not coded". Effect page aggregates the strips of its attempts. Evidence that it matters (n = 142 with `result`): closest tertile 58.9% success vs 33.3% / 34.1% for the two farther tertiles; corr(closeness_sum, ratio) = −.25. `same_design = 0` (conceptual) shows 81.1% success (n = 37) vs 52.5% direct (n = 257) — a selection effect to be printed as such, not as "conceptual replications work better". The fingerprint is the natural target of the curated overlay and of the OSF Replication-Recipe registrations (pr* fields), so the coder UI should write these 10 integers.

### 6.6 Criteria matrix & disagreement chart (site-wide)
Stacked bars per criterion (FORRT vignette style) plus a histogram of "criteria satisfied 0–7" and a 7×7 agreement heat-map (values in §3.4). This is the page that teaches the visitor why a single replication rate is a fiction.

### 6.7 Status band component
Text-first chip: label · pooled r [CI] · k (papers/projects) · stability · tier mix; hover shows the rule that produced the label and the alternative labels under (a) pooling originals, (b) SESOI .05/.15.

### 6.8 Z-curve of originals (site-wide, optional)
z_i = atanh(r_o)/se_o for tier-A originals (FORRT `augment_for_zcurve`), histogram with the p=.05 line; use the `zcurve` EM fit only if a Python port is validated — otherwise show the raw histogram and the share of z between 1.96 and 2.8 (the "just significant" zone).

---

## 7. Honest-uncertainty rules (site-wide policy, enforced by the page templates)

1. No number without its denominator and its tier. "Replication rate 41%" is always "41% of 2,526 replication paper-pairs (FLoRA, author-reported)".
2. No single replication score for an effect. The status label is a band derived from CI + PI + k; the rule is one click away; alternative labels are shown.
3. Every derived quantity shows its inputs (r_o, n_o, r_r, n_r with page references `es_repr_o/r`) and the conversion route ("d → r, equal groups assumed").
4. Criteria are named, not averaged. "5 of 7" is a count, not a probability.
5. Intervals over p-values; p-values shown both reported and recomputed; discrepancies shown, not resolved silently.
6. Nested designs and unsigned conversions carry a visible caveat chip; excluded rows are listed, not just subtracted.
7. Selection effects are stated on the stats pages in fixed sentences: "FReD/FLoRA is not a random sample of psychology; replications of famous effects are over-represented; multi-site projects dominate the numeric record."
8. Author-reported and numeric verdicts are shown side by side; when they disagree (12.8% of tier-A attempts under significance_r), the disagreement is the visible content, not an error.
9. Predictor analyses report effect sizes with CIs and pseudo-R² (the p-value bucket explains pseudo-R² = .046 of success; N-ratio .016; both .055) so nobody reads them as strong predictors.
10. Guessing game feedback uses base rates from the same denominators (§8.1) and scores with Brier/log score against a probability, never "right/wrong" alone.

---

## 8. Site-wide statistics pages — with today's real numbers

### 8.1 /stats/overview
- FLoRA replication pairs 2,526: successful 41.3%, failed 35.7%, mixed 22.3%; per unique original (2,338): 42.1 / 32.9 / 25.0. Reproductions 289 (outcome NA 284).
- FReD attempts 2,164: successful 45.5%, failed 36.4%, mixed 16.6%; entries 1,004: 40.5 / 45.8 / 13.6; originals 786: 44.0 / 37.2 / 18.8. Tier A attempts 1,103.
- Legacy-only attempts 3,234 (743 validated; 362 tier A) — shown as "awaiting merge" until the build merges them.

### 8.2 /stats/criteria (the disagreement page) — numbers in §3.3–3.4.

### 8.3 /stats/shrinkage — numbers in §3.5; plus by discipline and by project (to compute in build; the per-project version is where ML3's 6.9% vs CORE's 72% become visible).

### 8.4 /stats/predictors ("what predicts replication in FORRT data")
Computed on tier-A attempts with authors' verdict successful/failed (n = 940) unless stated:
- Original p-value (recomputed from r, N): p ≤ .005 → 56.8% (n = 512); .005 < p < .05 → 26.1% (n = 299); computed p ≥ .05 → 66.7% (n = 129; artefact of nested/misreported N — shown with that warning). Under `significance_r`: 57.2% vs 28.5%; under `small_telescopes` 61.7% vs 28.2%; under `consistency_pi` the gradient inverts (48.8% vs 68.0% vs 93.2%) because wide PIs from small originals are easy to land in — the page prints this inversion as the lesson. Using *reported* p: 57.1% (408) vs 36.3% (421); all FReD rows with a reported p (n = 1,642): 61.7% vs 45.4%. Logit on log10 p: slope −.076, pseudo-R² .046.
- N ratio (n_r/n_o): authors' verdict falls monotonically <0.5: 67.0% (106) · 0.5–1: 51.9% (162) · 1–2: 49.6% (252) · 2–5: 46.0% (211) · >5: 37.3% (209); `significance_r` is flat (47.5 → 43.3%); `consistency_ci` collapses 63.0% → 10.8% (mechanical: bigger replications have narrower CIs). Interpretation printed: high N-ratio replications are more often independent, adversarial, multi-site; low N-ratio ones are often self-replications.
- Replication power for r_o: <.5 → 68.9% success (103); .5–.8 → 43.6% (78); .8–.95 → 33.0% (106); >.95 → 48.2% (653). Legacy `power`: 29.0% / 31.3% / 31.1% / 43.4%. (Same selection story; printed.)
- Author overlap > 0: 87.3% (292) vs 49.3% (1,480) — all FReD rows.
- Pre-registered replication: FReD prereg_r present 64.9% of failed vs 50.9% of successful; legacy: 55.3% success with prereg (253) vs 46.8% without (1,152). Direction differs between files → printed as "unclear".
- Closeness (n = 142): 58.9% / 33.3% / 34.1% by tertile; same_design conceptual 81.1% (37) vs direct 52.5% (257).
- Interaction vs main effect: NOT codable from FReD today (no field) — list as a curated-overlay field to add; the U6 numbers (20% vs 53%) stay as literature, clearly labelled external.

### 8.5 /stats/by-discipline and /stats/by-year — numbers in §6.4, three denominators, Wilson CIs, mega-report toggle.

### 8.6 /stats/projects — the legacy `source` table in §5.3, plus per-project shrinkage and I².

### 8.7 /stats/data-quality (public, because honesty is the product)
- ES conversion coverage: 1,226/2,164 originals and 1,223/2,164 replications convertible; 1,103 tier-A attempts.
- Lost by type: partial η² 173/198, β 151/149, b 123/136, 'r-squared' label 42/42 (fixable), unparsed test statistics 135/140, F(df1>1) 108/51, 'ser_method' 32/65 (unknown label).
- Reported vs recomputed significance mismatches: 45 + 125 of 1,035.
- Ours vs FORRT r: 9 + 8 rows differ by > .01 (max .37 on the replication side) → list them.
- Ours vs FORRT `statistical_success`: 94.1% agreement (n = 615) → list the disagreements.
- FReD entry_id bug in output_FReD.xlsx (all 1) → we use the archive ids and recompute.
- Effect-name coverage: 561 current rows get a legacy name (143 names); 74 originals ambiguous.

### 8.8 /stats/methods — the formulas of §3–4 verbatim, with the FORRT R functions they mirror and the vignette's stated biases of each criterion (significance_r ignores original evidence; consistency_ci rewards low power; PI is wide for small originals; homogeneity has low power; small telescopes judges evidence quality not truth).

---

## 9. Build pipeline modules (Python, in `pipeline/compute/`; pure functions, tested against the R vignette examples)

```
raw/            FReD archive xlsx, output_FReD.xlsx, legacy 2.4.1 xlsx, flora.csv   (downloaded, hashed)
normalized/     attempts.parquet, pairs.parquet, originals.parquet, effects.parquet (+ provenance columns)
computed/       attempt_indicators.parquet, effect_indicators.parquet, stats/*.json
site/           per-entity JSON consumed by Astro content loaders
```

### 9.1 `es_convert.py`
```python
def to_r(value, es_type, *, group_sizes=None) -> Conv:   # Conv(r, route, signed: bool, caveats: list[str])
    t = normalise_type(es_type)          # lower, straight quotes, alias table incl. 'r-squared','hedges g',...
    if t in NONCONVERTIBLE: return Conv(None, f'cannot:{t}', False, [f'es_nonconvertible:{t}'])
    if t == 'test-stat':    return parse_test_statistic(value)   # extended regexes; F(df1>1)->eta2p magnitude, chi2(df>1)->V
    v = float(value)
    match t:
      case 'r'|'phi': return Conv(v,'r',True,[])
      case 'r2':      return Conv(sqrt(v),'r2',False,['direction:unknown'])
      case 'd'|'g':   a = 4 if group_sizes is None else 1/(p*q);  return Conv(v/sqrt(v*v+a),'d',True, [] if group_sizes else ['d_to_r:equal_groups_assumed'])
      case 'or':      d = log(v)*sqrt(3)/pi; return Conv(d/sqrt(d*d+4),'or',True,['or_to_r:logistic_assumption'])
      case 'eta2':    d = 2*sqrt(v/(1-v)); return Conv(d/sqrt(d*d+4),'eta2',False,['direction:unknown'])
      case 'f':  ...  case 'f2': ...
def coalesce(ours: Conv, forrt_r: float|None) -> Conv     # prefer ours; fall back to FORRT r_o/r_r with route 'forrt_precomputed'
def align(r_o, r_r, direction_hint) -> (r_o_al, r_r_al, caveats)
```

### 9.2 `uncertainty.py` — `ci_r`, `p_from_r`, `vi_cor`, `prediction_interval`, `power_r`, `r_for_power` (formulas §3.2; ports of helpers.R; golden tests: `compute_ci_r(.3,100)`, vignette calls).

### 9.3 `criteria.py`
```python
CRITERIA = ('significance_r','significance_agg','consistency_ci','consistency_pi','homogeneity','homogeneity_significance','small_telescopes')
def assess(r_o, n_o, r_r, n_r) -> dict[str, Outcome]   # Outcome = Literal['success','failure','failure (reversal)','OS n.s.'] | None
def lebel(r_o, r_r, p_o, p_r, ci_r) -> dict            # signal / consistency / result
def criteria_summary(outcomes) -> {'n_defined','n_success','vote','exists_says','accuracy_says'}
```
Golden tests from success_criteria.Rmd: (.5,50,.1,1000,'significance_r') → success; (.5,50,.1,50,'significance_agg'); (.5,50,.3,50,'consistency_ci') → success and (.5,50,.4,500) → failure; (.5,50,.3,500,'consistency_pi'); (.2,100,0,500,'homogeneity') → failure; (.5,50,.2,100,'small_telescopes') → failure, (.5,30,.2,100) → success. Regression test: agreement with archive `statistical_success` ≥ .94 on the 615 comparable rows.

### 9.4 `attempt_indicators.py`
```python
for a in attempts:
    tier = 'A' if all(r_o,n_o,r_r,n_r) else 'B' if any(...) else 'C' if a.reported_success else 'D'
    if tier=='A': ci/p/vi both sides; pi; power_r; r33; crit = assess(...); shrink = {ratio (None if |r_o|<.05), dz, se_dz, ci_dz}
    flags = conv caveats + ['nested_o'|'nested_r'] + ['os_not_significant'] + ['p_mismatch:computed_ns_reported_sig'|...] + ['mega_report'] + ['es_clipped']
    emit AttemptIndicators(id, tier, r_o_al, r_r_al, ci_o, ci_r, p_o_comp, p_o_rep, p_r_comp, p_r_rep, pi, power_r, r33, crit, crit_summary, lebel, shrink, flags, provenance={'r_o_route':..., 'source_file':..., 'row':...})
```

### 9.5 `meta.py`
```python
def re_pool(rs, ns, method='DL') -> Pool(k, est, lb, ub, tau, I2, Q, Qp, pi_lo, pi_hi)   # Fisher-z; PI only k>=3
def pool_effect(effect):   # replications only, tier A
    sites = [a for a in effect.attempts if a.tier=='A' and a.role=='replication']
    by_project = group(sites, key=project_or_paper)
    project_estimates = [re_pool(g) for g in by_project.values()]        # collapse sites
    pool_site  = re_pool(sites);  pool_proj = re_pool(project_estimates)  # both kept
    loo = [label(re_pool(drop(project_estimates, i))) for i in range(len(project_estimates))]
    cumulative = [re_pool(project_estimates_up_to_year(y)) for y in years]
    shrink_effect = pool_proj.est / median(r_o of effect.originals);  boot CI (B=2000 over attempts)
    return EffectIndicators(k_sites, k_papers, k_projects, pool_site, pool_proj, loo_stable, cumulative, shrink_effect, originals=[...], author_tally={...})
```

### 9.6 `status.py` — the §4.4 table as data (rules in a YAML the site renders in /stats/methods), `label(pool, originals, k, sesoi=.10)` returning (label, rule_id, band{stability, vote, tier_mix, alt_labels}).

### 9.7 `aggregate.py` — every stats page number as a function with an explicit `denominator` argument ∈ {rows, entries, originals}, `exclude_mega: bool`, `tier: set`, returning value + Wilson CI + n; results written to `computed/stats/*.json` with the input file hashes, so a page can say "computed 2026-09-07 from FReD sha…".

### 9.8 `dq.py` — emits the /stats/data-quality lists (unconvertible types, unparsed strings, p mismatches, ours-vs-FORRT diffs, ambiguous effect names, mega-reports).

### 9.9 Tests & reproducibility
- `pytest` golden tests (R vignette values; archive statistical_success agreement threshold; row counts equal to those in this document ±0 for the same input hashes).
- One command `python -m pipeline compute` after `fetch` and `normalize`; deterministic (no LLM in this layer).
- Do NOT port `zcurve` EM unless validated; do not fit REML per effect in the page build unless timing allows (DL is adequate for display and matches the spirit of FORRT's FE comparison).

---

## 10. Open questions / risks
1. **Effect identity is the bottleneck**, not the statistics: only 51 named effects have tier-A rows in legacy, and current FReD has 52 originals with ≥2 replication papers. The effect layer needs (a) the legacy→current merge by (doi_o, doi_r) and fred_id, (b) alias normalisation, (c) claim-level review for the 74 ambiguous originals, (d) the docx/Reversals overlay linked via titles→DOIs.
2. The legacy file has 362 tier-A rows absent from current FReD (validated or not) — include with `validated` shown as a badge.
3. Direction for unsigned conversions (η², F, χ², f, f²) — 33% of tier-A originals (365/1,103: F(1,df) 204, η² 92, χ²(1) 46, f² 19, f 4) arrive unsigned; the alignment assumption should be audited on a sample (does `reported_success = failed` with r_r > 0 ever mean "opposite direction"?).
4. `ser_method` (97 rows) is an undocumented es_type in FReD — ask FORRT.
5. Nested rows (21%) — a design-effect correction needs cluster counts that FReD does not carry; the caveat chip is the honest maximum for now.
6. Interactions vs main effects, and "effect claimed in title" — not in FReD; propose as curated-overlay fields because they are the strongest known predictors (U6).

## 11. Artefacts produced today
- Scripts: `_planning/designs/_d2_compute.py` (criteria, shrinkage, predictors, base rates on current FReD) and `_d2_compute2.py` (legacy, per-effect RE meta, closeness, FLoRA, identity checks); logs `_d2_compute_log.txt`, `_d2_compute2_log.txt`.
- `_planning/designs/_d2_compute_log.txt` — full printed output of compute.py.
- `_planning/designs/_d2_fred_computed.pkl` — 1,103 tier-A attempts with all indicators (pandas pickle).
- `_planning/designs/_d2_effect_meta_legacy.csv` — RE pooling results for the 35 named legacy effects with k≥2.
