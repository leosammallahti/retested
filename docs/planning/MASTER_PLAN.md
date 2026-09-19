# MASTER PLAN — "Retested": the effect-level replication explorer built on FORRT data

Status: v1, 2026-09-07. Author: chief architect / editor (synthesis of BRIEF, U1–U8, D1–D6, plus recomputations listed in Appendix A).
Audience: the build agents and the owner. This file is the single source of decisions; where it contradicts a design report, this file wins and says why.

Numbering convention: every figure carries a tag like `[U5]`, `[D2]`, `[A-7]` (Appendix A row) so its provenance is one lookup away. Figures marked EST are estimates that a build step must replace.

---

## 0. Executive summary (one screen)

- **What**: an effect-centric, story-telling, playable explorer of psychology's replication record, generated from FORRT's open data (FReD + FLoRA + legacy 2.4.1 + the curated Replications & Reversals list) with small git-curated overlays, a calibration game, and an evaluated discovery pipeline that contributes findings back to FORRT.
- **Name**: **Retested** (`retested.science`, fallback `retested.org`). Tagline: *"Every psychology finding, tested again."* Collision-free per D6's checks; the owner may override (alternatives: *The Rerun*, *Twice*).
- **Not another atlas**: FORRT's Replication Atlas already has a page per original DOI (4,717 originals, CC0, JSON-LD, daily refresh) `[U8]`. We do not rebuild it. Every DOI we show links to `https://forrt.org/flora-replication-atlas/doi/<doi>/` and to `https://doi.org/<doi>`. Our unit is the **effect** (named finding across originals and attempts) and the **finding** (one original paper with its attempts), never the paper alone.
- **Three lenses, never one score**: authors' verdict (FLoRA outcome + quote) · numerical record (FORRT's seven criteria, shrinkage, pooled estimate with CI/PI) · design closeness (Brandt items, prereg, independence). Criteria disagree on 62.3% of attempts where all seven are defined `[D2]` — that disagreement is content, not noise.
- **The game** ("Did it replicate?") is a Phase-1 product: one original study per item, probability slider, Brier points, daily set of 10, progressive cues, three-lens reveal; 693 fair items exist today with zero LLM work `[D3]`.
- **Discovery**: FORRT's public machine-extracted candidate pool (3,147 rows, 2,485 resolved pairs, only 17 already in FLoRA `[A-20]`) is day-one queue material; we add the citation-graph crawl FORRT's gate structurally misses and the recall harness FORRT lacks; accepted pairs go back in FORRT's `validated_export.csv` column set.
- **Stack**: Python 3.13 pipeline (pandas + pydantic v2 + DuckDB + Parquet, `uv`), Astro 7 + Preact islands, Pagefind + MiniSearch, build-time SVG charts, GitHub Pages, Supabase only in Phase 3 for crowd data. One command: `npm run build`.
- **Anti-rot**: root allowlist test, append-only id ledger, committed count baseline, secrets scan, `pipeline migrate` with a TRASH protocol, docs with generated numbers.
- **Roadmap**: Phase 0 scaffold+migration (2 weeks) → Phase 1 shippable site + game + queue (6–8 weeks) → Phase 2 live discovery + contribute-back + LLM claim cards → Phase 3 crowd (Supabase) → Phase 4 integrations.

---

## 1. Vision

FORRT owns the rows; nobody owns the stories `[D6]`. Retested gives every psychological finding a **biography**: the claim sentence as the original authors wrote it (2,131 verbatim `claim_text_o` sentences in FReD `[U5]`), its fame (OpenAlex citation curve, cached for 1,583 originals `[D6]`), its trials (every attempt, three lenses), its verdict (multi-criterion, with confidence and an explicit rule), and its afterlife (did citations bend? is it still in textbooks? what was built on it?).

Design north star: *a field guide to what psychology actually knows* — warm paper, ink, vermilion for "claimed", ultramarine for "observed" (kept from wiki v1 `[U4]`), and a dead-serious commitment to denominators and provenance so that delight never costs credibility.

Three audiences, three depths on every page: **5 seconds** (status, glyph, one sentence), **30 seconds** (verdict card with the three lenses and the timeline), **5 minutes** (every row, every formula, every source).

Non-negotiables inherited from the BRIEF: reproducible one-command build from FORRT sources + curated overlays; effect-centric with paper/attempt/project/author/topic entry points; the game; a credible documented discovery pipeline with a human queue and a contribute-back path; a repo that cannot rot.

---

## 2. Positioning vs FORRT — spelled out

### 2.1 The FORRT ecosystem we sit on (verified live 2026-09-07 `[U8]`)

| FORRT asset | What it is | Our relationship |
|---|---|---|
| **FLoRA** `output/flora.csv` (2,815 rows: 2,526 replications + 289 reproductions; CC-BY 4.0; ~4 releases/week) | Paper-pair registry with author-reported outcome + verbatim quote | Primary source of attempts at pair grain. Fetched weekly; sha256 pinned; cited per `output_citation.txt` on every page. |
| **FReD** `output/FReD.xlsx` (2,164 rows) + `archive/2025-11-30_COSdata_validated.xlsx` (same rows + `r_o`, `r_r`, `statistical_success`, correct `entry_id`) | Effect-level statistics | Primary source of numeric attempts. The archive file is the base table (output_FReD's `entry_id` is 1 on every row `[U5]`); output_FReD supplies bibliographic augmentation by row order. |
| **Legacy FReD 2.4.1** (OSF; 4,659 data rows × 100 cols) | Crowdsourced FReD with effect names (443), Brandt closeness (~175 rows), power (834), CIs, prereg, `result`, project `source`, plus the 583-row *Reversals Effects* sheet and 686 backlog rows | Merged onto current by (doi_o, doi_r, study, ordinal) for 1,548 rows; 3,234 legacy-only rows kept as their own attempts with a "legacy coding" badge `[U5][D5]`. |
| **Replications & Reversals list** (docx parse, 362 effects with status/critiques/GS citations; FORRT's `231026_forrt_with_journals.xlsx` 1,296 rows) | The famous-effects overlay | Imported once into `data/curated/famous/`; statuses shown as *"curated list (2021–22) said: …"* beside our computed status, never as our status `[D1]`. |
| **Replication Atlas** (`forrt.org/flora-replication-atlas/doi/<doi>/`, CC0, 4,717 originals, JSON-LD, OG images) | Per-original-DOI "has this been replicated?" pages | **We link out, we do not rebuild.** Our paper pages are thin and exist only where they add effect-level context (§4.6). We reuse their CC0 `refresh_data.py` (OpenCitations timeline) and `pageMeta.js` patterns. |
| **rep-api.forrt.org/v1** (`/dois`, `/original-lookup`, `/prefix-lookup`, `/search`) | Read-only DOI-record API behind atlas/Zotero/extension | Consumed **at build time only** (CORS is forrt.org-only for `/search`; no SLA). We emit the same record shape statically at `/api/v1/doi/{hash3}.json` so the Zotero plugin *could* point at us `[D5]`. |
| **fred-apps** `data/explorer-data.json` (MIT; 2,164 rows with all 7 criteria precomputed weekly) | Static FReD Explorer/Annotator | Test oracle for our Python port of the criteria (agreement floored in CI); their `success-criteria.js` labels/notes reused verbatim (MIT). |
| **flora-explorer** (CC-BY-4.0; `originals.json` 2,146 originals with pre/post-replication citations, `author_overlap_data.json` 2,415 pairs, `disciplines.json` journal→discipline) | Dataset-level dashboards | Consumed as enrichment; their CONTRIBUTING invites new tabs — we offer an effect-level tab (Phase 4). |
| **flora-extractor** (no LICENSE file; public `data/*.csv`) | 4-stage LLM discovery/extraction pipeline; `extracted.csv` 3,147 rows, `target_pending.csv` 2,329, + 780 other set-asides `[A-20]` | **Consume the CSVs as candidate feeds** (tagged `origin=forrt_extractor`, `review_state=machine`, never shown as validated). Prompts/specs are *ask-first*; we adopt the ideas (classify categories, outcome rules, cache-key discipline). |
| **flora-validation** (no LICENSE; `validated_export.csv` 263 rows nightly; consensus engine; 34 validators) | Human validation app feeding FLoRA | Gold labels for our outcome-replay metric; leading indicator of what enters FLoRA; design model for our review queue (port the *design*; ask before copying code). |
| **fred R package** (MIT) | `replication_outcomes.R`, `effect_size_transformations.R` | Ported 1:1 to Python with golden tests from the vignette. |
| **flora-zotero** (AGPL), **chromium-extension** (MIT) | Client integrations | Never copy AGPL code; reuse MIT DOI-extraction utilities; both link to the atlas, so our effect pages are reached *from the atlas*, not from the plugin. |
| **replicatethis** (nomination portal, GitHub Issues; v2 has boolean `will_replicate` predictions, not deployed) | Nominations + binary votes | Our crowd forecasts (probabilistic, scored, settled by FLoRA) are the missing loop; approved nominations become open questions (Phase 3). |
| **open-research-games-portal** (51 games) | Catalogue | Has no "did it replicate" game `[U8]`; we submit ours to their sheet. |

### 2.2 What is genuinely ours (differentiators)

1. **Effect identity with lineage**: stable ids, aliases from four name sources, claims bridging FReD rows to effects, siblings on the same original, "built on a failed foundation" chains (1,148 internal citation edges, 263 into failed originals `[D6]`).
2. **Three lenses side by side per attempt and per effect**, including the closeness fingerprint nobody surfaces `[D2 §6.5]`.
3. **Multi-criterion verdicts per effect** (not per dataset): 7-cell strips, disagreement histogram, RE pooling of replications only with CI + PI + τ + leave-one-out stability `[D2]`.
4. **Biographies**: claim sentence vs outcome quote face to face; Rise & Fall citation curves with attempt markers; Graveyard / Survivors / Reversals editorial doors `[D6]`.
5. **The game** as product and instrument (probabilities, Brier, cues, open forecast dataset) — absent from the entire FORRT ecosystem and from every frozen 21-item quiz `[U6][U8]`.
6. **A public, measured discovery queue**: FORRT's own machine-extracted candidates + our citation-graph finds, with a recall harness against FLoRA by year that FORRT does not have `[U8 §4.8]`, and a visible "Community-added → Submitted → In FORRT since" badge lifecycle `[D4]`.
7. **Topic facets** (FORRT discipline × OpenAlex topics × curated tags × Cognitive Atlas paradigms) and honest stats pages with three denominators.
8. **Textbook / Wikipedia overlay** per famous effect (Phase 2) — no structured table exists anywhere `[U6]`.

### 2.3 Etiquette

- Cite `output_citation.txt` (Wallrich & Röseler et al., 2026) in the footer of every page and every export; label provenance per row (FLoRA / FReD / legacy 2.4.1 / R&R list / community).
- Link every DOI to the atlas and doi.org; link every effect page to FORRT's submit form and the Replication Handbook.
- Write to Wallrich/Röseler before Phase 2: (a) permission to reuse flora-extractor prompts and flora-validation consensus code, (b) offer the citation-graph leg their issue #150 wants, (c) offer an effect-level tab for flora-explorer, (d) list the game in the games portal.

---

## 3. Decision log — conflicts between reports, resolved

| # | Conflict | Decision | Why |
|---|---|---|---|
| D-1 | **D1** wants an effect page (stub) for every original with attempts (~3,100 stubs); **D5** says FLoRA-only originals do not create effects; the owner forbids stub pages that mirror the atlas | **Two-tier findings.** Every original DOI with ≥1 attempt gets a *Finding* record (id, JSON, searchable, row in the "Unnamed findings" index). It gets its own HTML page only when *promoted*: named effect, or ≥2 attempts, or any FReD numeric row, or a game item, or curated. Everything else is reachable inline on the index page grouped by original (outcome + quote + atlas link) and via `/api/v1/doi/{hash3}.json`. | Satisfies "every pair reachable" without 3,100 near-empty pages; naming stays a visible queue; page count drops to ~2–3k. |
| D-2 | **D1** effect id = `fx_` + hash of (name + first DOI) in committed registry CSVs; **D5** effect id = ledger-assigned `fx:` + slug | **Ledger (D5) issuing opaque ids (D1)**: `fx_<8 Crockford-base32>` assigned once per key in `data/curated/registry/effect_ids.csv`; mutable readable slug; merges → `merged_into` + redirect page. | Opaque ids survive renames; the ledger forbids reuse; slugs stay human. |
| D-3 | **D1** status = 8-value author-reported vocabulary; **D2** status = graded numeric labels from RE pooling | **Both, never merged.** *Record* (author lens, D1 rules, coverage ~100% of attempts) and *Numerical verdict* (D2 labels, tier-A only). Disagreement shown as a chip. | Author reports cover 3,672 attempt pairs; numeric data cover ~1,100 attempts. One vocabulary would either hide numbers or drop coverage. |
| D-4 | **D1** Reversed is curated-only; **D2** allows numeric "Reversed" (CI_ub < 0) | Record: Reversed curated-only (4 of 12 opposite-sign candidates are FORRT-coded successes `[D1]`). Numerical verdict may say "Reversed (pooled CI below 0)" with the unsigned-conversion caveat. | Sign conventions are unreliable for 33% of tier-A originals `[D2]`. |
| D-5 | **D4** separate `discovery/` package; **D5** `pipeline/discover/` subpackage | One package: `pipeline/discover/` with D4's module list unchanged. One CLI, one lockfile, one test suite. | Two packages is how the old root rotted. |
| D-6 | **U4** prefers Cloudflare Pages; **D5** GitHub Pages (file count) | GitHub Pages (owner's decision). With D-1 the output shrinks to ~6–8k files, so Cloudflare stays possible; a file-budget test keeps it so. | — |
| D-7 | **D3** unit of play = original study (doi_o + study_o); **D5** GameItem keyed by attempt/pair | D3 wins: `GameItem.id = "gi:" + doi_o_key [+ ":" + study_norm]`; answers live in per-item `reveal.json`. | 693 fair originals at 50.4% base rate; dissolves the mega-paper leakage. |
| D-8 | **D1** overlay = one `.md` with YAML front matter per effect; **D5** one `.yaml` per effect | `.md` with YAML front matter (D1 format) under `data/curated/effects/`. | Prose sections need Markdown; the front matter is schema-validated either way. |
| D-9 | **D2** wants REML/PM; DL is what was computed | DL for the build (deterministic, fast); REML in notebooks only. | Display-grade; matches FORRT's FE comparison spirit. |
| D-10 | **D6** ranks 48 ideas; not all fit Phase 1 | Phase 1 takes D6's top-12 minus shared-state items (classroom, follow, votes, crowd forecasts → Phase 3) and minus textbook table (Phase 2). | Brilliant *and* buildable from files on disk. |
| D-11 | Person pages: **D1** ≥2 papers, **D5** ≥3 | ≥3 papers in the bundle *or* author of a named effect's original. | Budget knob; keeps ~1,000–1,500 pages `[D5]`. |
| D-12 | Legacy-only attempts (3,234): show by default or behind a toggle? | Shown by default with a "legacy coding · validated=<n>" badge; `validated ∈ {3, NA}` rows carry an amber warning; the corrections overlay can suppress a row with a reason. | Hiding data is how the current FReD lost closeness/power; badges keep honesty. |
| D-13 | Game: are Tier-B (LLM-written) claims playable before review? | Endless mode only, with an "unreviewed card" glyph; daily sets = reviewed/spot-checked only; famous tier ≤2 per daily set. | D3's fairness rules. |
| D-14 | LLM taxonomy (17 iterations) | Never. Facets only (§9). Any inferred label carries provenance + review state. | U2's post-mortem. |
