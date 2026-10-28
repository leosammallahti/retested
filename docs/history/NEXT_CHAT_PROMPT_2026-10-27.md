Work on **Retested** (`coop-vm` via `ssh -n coop-vm`, worktree `/root/retested-wiki` on branch `wiki-pages`; never build in `/root/retested`). Read `README.md` and the top of `docs/HANDOFF.md` first.

### Current State (2026-10-27)
- **Site & Data**: 2,704 named effects, 4,626 original findings, and 5,356 replication attempts (~11,969 static pages).
  - Plain-English one-sentence claims for 2,582 effects: `data/curated/effect_lines.json`.
  - Plain-English verified accounts for 5,300 of 5,356 replication attempts (99.0%): `data/curated/wiki_accounts.json`.
  - Reviewed original study scenes and explanations: `data/curated/wiki_explanations.json`.
- **Categorization System (Designed & Blind-Tested 2026-10-26/27)**:
  - Proposal and full empirical results: `/root/wiki-scratch/outputs/categories_20261026/PROPOSAL_TYPOLOGY.md` (mirrored on Google Drive at `G:\My Drive\Retested categorization proposal (2026-10-26).md`).
  - Test harness, prompts (`dimensions_typology.py`, version `v5`), outcome-blind packets (`inputs/effect_texts.jsonl`), 100 blind human codings (`human_blind_100.py`), and evaluation scripts (`run_test.py`, `analyse_test.py`, `evaluate_blind_200_v5.py`): `/root/wiki-scratch/typology_test_20261026/`.
  - **What replaced topic shelves**: Earlier 12-topic lists agreed on only ~75% of effects and told readers almost nothing about why findings hold up or fail. We replaced them with a **4 × 4 Study Typology** plus **three factual filters**:
    1. **Axis 1 — What the study did (`study_kind`)**:
       - `TRAIT_OR_GROUP`: Comparing existing traits, groups, diagnoses, genes, or records (**69.9%** replication success on the 200-effect blind sample).
       - `TRAINING_OR_THERAPY`: Teaching a skill, delivering clinical therapy, or reinforcing behaviour with rewards (**64.3%** success).
       - `TASK_OR_FRAMING`: Varying the stimuli, wording, options, or rules inside a task or decision (**44.6%** success).
       - `NUDGE_OR_SPILLOVER`: Exposing people to an incidental prime, induced mood/power state, posture, drink, hormone dose, or prior draining task to see if it spills over into a separate judgment or action (**16.2%** success).
    2. **Axis 2 — What was measured (`outcome_kind`)**:
       - `ACTION_OR_CHOICE` (**56.8%**), `SELF_REPORT_OR_RATING` (**51.9%**), `PERFORMANCE` (**50.0%**), `BRAIN_BODY_OR_RECORD` (**50.0%**).
    3. **Three Factual Filters**:
       - `who_studied`: `ADULTS`, `CHILDREN_AND_TEENS`, `BABIES_UNDER_3`, `MENTAL_HEALTH_PATIENTS`, `AUTISTIC_OR_DISABLED`, `ANIMALS`.
       - `setting`: `SCHOOL`, `CLINIC_OR_HOSPITAL`, `WORKPLACE`, `COURTS_OR_PRISONS`, `NONE_OR_LAB`.
       - `body_brain_genes`: `YES`, `NO`.
  - **Blind Validation Results (`smoke_30` + `blind_200`, `v5`)**:
    - Tested across two independent model families (`deepseek/deepseek-v4.1-flash` and `z-ai/glm-5.3-flash`) on outcome-blind packets, requiring a verbatim quote of ≤20 words verified in Python and `"predictor"` before `"answer"` on `study_kind`.
    - `smoke_30 (v5)`: **149 / 150 (99.3%)** overall cross-model agreement (**30/30 = 100%** on `study_kind`, `outcome_kind`, `who_studied`, and `body_brain_genes`; **29/30 = 96.7%** on `setting`).
    - `blind_200 (v5)`: **964 / 1,000 (96.4%)** overall cross-model agreement (**950 / 1,000 = 95.0%** with both quotes verified):
      - `body_brain_genes`: **198 / 200 (99.0%)**
      - `who_studied`: **195 / 200 (97.5%)**
      - `outcome_kind`: **195 / 200 (97.5%)**
      - `setting`: **192 / 200 (96.0%)**
      - `study_kind`: **184 / 200 (92.0%)**
    - Against 100 blind human codings (`[001]`–`[100]`), the two-model consensus matched **94.6%** raw and **98.4%** (`477/485`) after auditing human quick-read slips.

### Standing Rules
- **Before any paid API call**, state the model, the number of calls, and the estimated cost, and wait for Leo's explicit approval.
- **No regex or word-matching heuristics** to assign categories (`no-regex-labels.md`).
- **No letter-number codes** in user-facing text or documents; use plain English and Finnish local time (`UTC+2`).
- Put anything Leo needs to read in Google Drive (`G:\My Drive\`).
- Commit only when Leo asks.
