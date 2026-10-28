# D6 — The Visionary / Wildcard design

Author: designer agent D6 (visionary angle). Date: 2026-09-07. Status: COMPLETE (verified numbers in Appendix A; everything cited below was computed from local files in this session unless marked "U#" = reader report).

Purpose: brainstorm without limits, then rank. Raw material for the synthesis agent, not prose for a human. Every idea states: pitch / why delightful / data needed (have it?) / effort S-M-L / brilliance 1-5. Ideas marked ★ use data that nobody else (FORRT included) currently surfaces.

---

## 0. The thesis in three sentences

FORRT owns the *rows*; nobody owns the *stories*. The wiki should be the place where a finding has a biography — birth (original paper, its claim sentence, its p-value), fame (citation curve), trial (every attempt, three lenses), verdict (multi-criterion, with confidence) and afterlife (does the citation curve bend? is it still in textbooks? who built on it?). Everything below is a way to make that biography vivid, playable, embeddable, or contributable — from data already on disk.

Design north star: **"A field guide to what psychology actually knows"** — keep paper/ink/vermilion/ultramarine, keep the three lenses, add a dead-serious commitment to denominators and provenance so that delight never costs credibility.

---

## 1. The idea bank (48 ideas)

### A. Storytelling (the biography of an effect)

**A1 ★ Rise & Fall citation curves.** Per-effect line of citations/year with the replication attempts drawn as vertical markers coloured by outcome, so the reader sees whether the field *noticed*. Delight: Bargh 1996 elderly priming keeps getting 100+ cites/yr for eight years after Doyen 2012 (117 in 2012 → 148 in 2020, only falling to 64 by 2023); Kidd & Castano 2013 peaks in 2018 (188) two years *after* Panero 2016 failed. Data: openalex_original_enrichment_full.json has counts_by_year for 1,583/1,623 originals (HAVE, 2012-2025 window only — OpenAlex truncates; re-fetch needed for older curves) + FLoRA year_r/outcome (HAVE). Effort M. Brilliance 5.

**A2 ★ The Graveyard.** A dedicated, beautifully typeset page of effects that failed decisively (FLoRA failed + FReD failed + docx "not replicated"/"reversed"), sorted by Google-Scholar fame at time of death, each with an epitaph = the outcome_quote from the replication paper. Data: docx 362 (102 not-replicated + 10 reversed with GS counts, e.g. Pygmalion 13,625; ego depletion 7,141; elderly priming 5,938; oxytocin-trust 4,800), FLoRA outcome_quote (100% coverage on 2,526 replication rows). HAVE. Effort S-M. Brilliance 5.

**A3 ★ The Survivors.** Mirror page: effects that were attacked and held (docx "replicated" with fame: framing/prospect-theory family ~76k GS cites, classical anchoring 46k, Asian-disease 25k, Dunning-Kruger 8.4k; legacy FReD "Anchoring Effect" has 552 attempt rows). Frame as "the load-bearing walls of psychology". Data HAVE. Effort S. Brilliance 4.

**A4 ★ Comeback Kids.** Effects whose record is failed → later success (or mixed → clarified moderator), auto-detected as outcome sequences per doi_o in FLoRA ordered by year_r; 29 originals have ≥3 attempts, 5 have ≥5 (10.1037/a0021524 and 10.1111/j.1467-9280.2008.02227.x with 7 each; Kidd & Castano 6). Hand-curate the top 20 with a narrative overlay. Data HAVE (sparse: most originals have one attempt). Effort M. Brilliance 4.

**A5 ★ Built on a Failed Foundation.** Internal citation graph among FReD originals: 1,148 reference edges between 1,687 originals; 263 edges from 187 later originals point at an original that itself failed to replicate. Top "cracked foundations": Mani et al. 2013 scarcity (10.1126/science.1222426, cited by 32 other FReD originals), availability heuristic 1973 (21), Higgins 1977 category accessibility (18), Bargh 2001 automated will (14), Zhong & Liljenquist 2006 Macbeth effect (13), Bargh 1996 (12). Render as a dependency graph with failed nodes in vermilion; a "what rests on this?" panel on each effect page. Data: citation_dois.json ref_dois (HAVE) + outcome (HAVE). Caveat: outcome labels here come from legacy result (341 originals) — recompute from the merged layer. Effort M. Brilliance 5.

**A6 The Long Wait.** Time-to-first-replication distribution (FLoRA lag median 7 y, mean 9.6, 9% ≥ 20 y, max 135 y: Ebbinghaus 1880 "Ueber das Gedächtniß" replicated 2015; Triplett 1898 replicated 2025). Story page + per-effect "waited N years" badge. Data HAVE. Effort S. Brilliance 3.

**A7 Decade cohorts.** "Findings born in the 1970s replicate 29%; 1980s 53%; 2010s 43%" (FLoRA by year_o; small-n caveats). Interactive cohort strip. Data HAVE. Effort S. Brilliance 3.

**A8 Effect biographies as long-form (curated overlay).** 20-30 written essays for the famous cases (the docx critiques are a first draft: 354/362 entries carry dated critique citations), with the evidence timeline interleaved with the citation curve. Data HAVE (docx prose). Effort L (writing). Brilliance 4.

**A9 The Reversals gallery.** Effects where the replication found the *opposite* sign (docx "reversed" ×10, e.g. depressive realism; plus FReD rows where sign(r_o) ≠ sign(r_r)). Data HAVE (r_o/r_r in archive file, 733 rows). Effort S. Brilliance 3.

**A10 "The same effect, 60 labs" small multiples.** For Many Labs / RRR / ManyBabies effects, a wall of per-site forest strips (ML4 17 sites on disk; RP:P 168-row master table; MB1 67 labs / 19,603 infants). Data HAVE for 3 projects; others re-downloadable from OSF. Effort M. Brilliance 4.

### B. Leaderboards & rankings (always with denominators)

**B1 ★ Most-cited unreplicated.** Failed originals sorted by cited_by_count (availability heuristic 1973: 9,660 OpenAlex cites; Dweck 2007: 3,581; chameleon effect: 3,523; Bargh 1996: 2,348 — citation_by_outcome_analysis.json lists 37 "high-profile failures"). Data HAVE. Effort S. Brilliance 4.

**B2 ★ Biggest shrinkage.** |r_r|/|r_o| per FReD row: 733 rows with both r; median ratio 0.58; 46% shrink by more than half; median |r_o| 0.30 vs |r_r| 0.14. Leaderboard of effects that shrank most, with the SCORE ">50% median shrinkage" context. Data HAVE. Effort S. Brilliance 4.

**B3 Most-replicated effects.** Legacy effect names: Anchoring 552 rows, unconscious-thought advantage 243, girls-math stereotype 70, commitment priming 64, SVO 52, verbal overshadowing 52. Data HAVE (legacy). Effort S. Brilliance 3.

**B4 ★ Journals with denominators.** FLoRA journal_o × outcome: Psychological Science 224 attempts / 28% successful; JPSP 151 / 29%; PNAS 73 / 41%; Science 66 / 36%; JEP:General 39 / 23%; Journal of Consumer Research 38 / 18%; Journal of Applied Behavior Analysis 27 / 70%. Show n, stacked successful/failed/mixed, and a selection-bias caveat block ("replicators pick surprising findings"). Data HAVE. Effort S. Brilliance 4.

**B5 Most independent replicators / labs.** Parse author_r JSON in FLoRA (top surnames today are dominated by mega-projects: Frank 154, Mathur 149, Boyce 140, Nosek 97 …) — needs ORCID/OpenAlex author IDs to be fair. Data PARTIAL (names yes; IDs only for originals in the enrichment file). Effort M. Brilliance 3.

**B6 Independence ledger.** FReD author_overlap: 62% of attempts are fully independent teams; independent attempts succeed 41% vs 52% when original authors are involved. Badge per attempt + a summary page. Data HAVE. Effort S. Brilliance 4.

**B7 Preregistration dividend (live).** Legacy FReD rows with a prereg link succeed 52% vs 47% without (n=271 vs 1,156); current FReD prereg_r filled on 1,175 rows. Show as a live number with CI, not a slogan. Data HAVE. Effort S. Brilliance 3.

**B8 Subfield base-rate board.** FReD discipline × reported_success and FLoRA discipline (via journal map disciplines.json) — the RP:P "social 25% vs cognitive 50%" story with current denominators. Data HAVE. Effort S. Brilliance 3.

**B9 Country / institution of replicators.** From OpenAlex authorships of doi_r (needs a fetch: 2,148 unique doi_r ≈ 22 calls at 100 IDs each ≈ $0.02). Map of where replication work happens. Data FETCH (cheap). Effort M. Brilliance 3.

### C. Education

**C1 ★ "What your intro textbook still teaches."** Per famous effect, a maintained table: taught in OpenStax Psychology 2e? in Noba? with a quote and section link, plus the effect's verdict. Operationalises Ferguson & Brown 2025 as a structured table (U6: no such table exists anywhere). Data: docx names (HAVE) + OpenStax/Noba text (open licence, FETCH + hand-check ~60 effects). Effort M-L. Brilliance 5.

**C2 Curriculum path.** A 10-lesson sequence built from the site's own pages: what replication is → three lenses → why p ≤ .005 matters (FReD: 52% vs 37% for .005-.05) → interactions vs main effects → multi-site projects → forecasting your own beliefs → contribute a replication. Each lesson ends in a game round scoped to that lesson. Data HAVE. Effort M. Brilliance 4.

**C3 Classroom mode.** Teacher creates a room code; students play the same 10 items; live class histogram of predictions vs outcome; export CSV. (Needs shared state: Supabase.) Data HAVE. Effort M. Brilliance 4.

**C4 Printable one-pagers.** Per effect, a print-CSS page: claim sentence, original stats, forest strip, verdict box, three-sentence "what we now think", QR to page. Data HAVE. Effort S. Brilliance 3.

**C5 ★ "Read the actual claim".** Every original in FReD has claim_text_o (2,131 rows) with page number — show the literal sentence from the paper next to the replication's outcome_quote. Two quotations, face to face. This is the three-lenses idea at sentence level. Data HAVE. Effort S. Brilliance 5.

**C6 Glossary-as-cards.** Small telescopes, prediction interval, z-curve, closeness, RRR, Registered Report — each a card that appears inline on hover, seeded with the real number from the page you're on. Data HAVE. Effort S. Brilliance 3.

**C7 Student-replication tier.** Boyce et al. 2023 (176 legacy rows) and the RSOS 140-row student mega-paper, CREP, Expra: show as a distinct "course replication" evidence tier rather than hiding them. Data HAVE. Effort S. Brilliance 3.

### D. Tools (things that make people come back)

**D1 ★ Paste-a-reference-list checker (web).** Paste a bibliography / DOIs / a manuscript's reference section; get back every original with a replication record (FORRT has this only as a Zotero plugin + prefix API). Match by DOI, then by Crossref bibliographic lookup for bare references. Data HAVE (FLoRA + FReD pairs; rep-api.forrt.org for parity). Effort M. Brilliance 5.

**D2 Bookmarklet / browser extension.** On any journal page or Google Scholar result: a small banner "3 replications: 1 failed, 2 mixed → see record". Uses the site's static /api/doi/<hash>.json. Data HAVE. Effort S-M. Brilliance 4.

**D3 ★ Embeddable badge + card.** `<img src=/badge/<doi-hash>.svg>` renders "Replication record: 6 attempts · 1 successful · 4 failed · 1 mixed" (SVG built at build time) and an oEmbed card for Substack / Wikipedia talk pages. Data HAVE. Effort S. Brilliance 4.

**D4 "This week in replication" RSS + newsletter.** Diff FLoRA weekly (it grows ~4 releases/week; 1,126 → 2,815 rows Mar-Sep 2026) plus our review-queue accepts; generate a digest with the week's new outcome quotes. Data HAVE (needs the fetch job). Effort S-M. Brilliance 4.

**D5 Static JSON API + bulk downloads.** /api/effect/<id>.json, /api/doi/<hash>.json (FORRT prefix-lookup compatible), /downloads/effects.csv, attempts.csv, BibTeX per page (FReD ships bibtex_o/r). Data HAVE. Effort S. Brilliance 3.

**D6 Zotero / Obsidian / BibTeX export.** One-click export of an effect's full evidence set as a .bib or an Obsidian markdown vault with links back. Data HAVE. Effort S. Brilliance 3.

**D7 ★ Seeded power & small-telescopes calculator.** On each effect page: "to detect this effect (r = 0.14 after shrinkage) at 80/90/95% power you need N = …"; the small-telescopes threshold r33 at the original N; prediction interval for a new attempt — all pre-filled from the row (port replication_outcomes.R). Data HAVE (1,056 r-convertible rows with Ns). Effort M. Brilliance 5.

**D8 Compare-two tool.** Side-by-side of any two effects (or two journals, or two decades) with shared axes. Data HAVE. Effort S. Brilliance 2.

**D9 Faceted search across entities.** Effect / paper / author / project / topic (OpenAlex subfield) / outcome / decade / journal / closeness / prereg — Pagefind + MiniSearch, never inlined into page props. Data HAVE. Effort M. Brilliance 3.

### E. Community (without depending on community)

**E1 ★ Follow an effect.** Email/RSS subscription per effect or per topic; fires when FLoRA or the review queue adds an attempt. Cheap because generated from the weekly diff. Data HAVE. Effort M. Brilliance 4.

**E2 ★ The Wanted list.** Important-but-untested findings: high cited_by_count originals in the OpenAlex cache with zero FLoRA attempts + FORRT's own 686-row "Additional Studies to be added" backlog + the 9-row "Check regularly for Replication" sheet. Visitors upvote; the list is exported as a public CSV for CREP / PSA / course instructors. Data HAVE. Effort M. Brilliance 4.

**E3 Propose a replication → FORRT template.** A form that outputs a filled datasubmission_template.xlsx row and a FLoRA-column CSV, and logs it in our review queue; explicit "contribute back" path. Data HAVE (template). Effort S-M. Brilliance 3.

**E4 ★ Public review queue, accept/reject from the effect page.** Every effect page has an "open candidates" tab fed by OpenAlex cites:<original> + replication-language filter (U7: 92 of 130 title hits were not in FLoRA). Reviewer decisions are stored with provenance and become classifier training data. Data FETCH (cheap; ~$0.001/call). Effort M-L. Brilliance 5.

**E5 Forecasts on untested effects (crowd prior).** Users give a probability that a Wanted-list finding would replicate; settle when a replication lands; show calibration over time (the Transparent Replications + Metaculus loop, generalised). Data HAVE + shared state. Effort M. Brilliance 4.

**E6 Original-author reply slot.** A structured, moderated field on each effect page where original authors can link a response (many exist: RRR commentaries). Curated overlay, not free comments. Data PARTIAL. Effort S. Brilliance 2.

### F. Analysis dashboards

**F1 ★ Predictors of replication, live.** The Altmejd/Gordon findings recomputed on the merged table each build: p ≤ .005 → 52% vs .005-.05 → 37% (FReD reported_success; n=790/970); author overlap; prereg; N buckets (flat: 44-47%); discipline; decade; effect-size magnitude; interaction vs main effect (needs a coded flag — tag from claim_text_o via LLM with review state). Each as a small chart with CI and the source rows linked. Data HAVE. Effort M. Brilliance 5.

**F2 Base-rate dashboard.** FLoRA 41/36/22 overall; by source (replications 41.5/33/25; COS 40/43/16; SCORE 45/40/14); by 5-year bucket; mega-paper toggle (RSOS 140, RP:P 92, X-Phi 39, ML2 24, SSRP 21) so one paper cannot dominate. Data HAVE. Effort S. Brilliance 3.

**F3 ★ Seven-criteria disagreement matrix.** For the 1,056 rows, compute all seven R-package criteria; show a heat-strip per effect and a site-wide "how often do criteria disagree?" figure. Nobody shows this. Data HAVE. Effort M. Brilliance 5.

**F4 Closeness explorer.** Legacy closeness_* (165 rows coded; instructions exact 95 / close 67; stimuli mostly "close" 123) vs outcome; "do closer replications succeed more?" with honest n. Data HAVE (small). Effort S. Brilliance 3.

**F5 Effect-size scatter with hover-to-page.** r_o vs r_r for 733 rows (or 1,056 converted), diagonal, coloured by outcome, click → effect page; the Explorer's best chart, done as one island. Data HAVE. Effort S. Brilliance 3.

**F6 Coverage & honesty page.** What fraction of FLoRA pairs lack effect sizes (1,843 of 2,526), how many originals have only one attempt, FReD-vs-FLoRA outcome disagreement (6.7%), what we could not resolve. Data HAVE. Effort S. Brilliance 3 (but trust 5).

**F7 Z-curve / p-curve per journal or per effect family.** Port from the Explorer for legacy rows with test statistics (teststatistic_orig 734). Data HAVE. Effort M. Brilliance 2.

### G. AI (assistive, always provenance-tagged)

**G1 Chat over the corpus with citations.** RAG over effect pages + outcome quotes + abstracts (1,420 on disk); every answer cites rows; "I don't know" when the record is empty. Data HAVE. Effort M-L. Brilliance 3 (commodity, but expected).

**G2 ★ Auto-drafted plain-language claims with review flags.** For each of 2,131 claim_text_o sentences, draft a one-line lay claim ("Holding a warm cup makes you judge strangers as warmer"); status = machine-draft until a reviewer approves; approved drafts feed the game. Data HAVE. Effort M. Brilliance 4.

**G3 Interaction-vs-main-effect tagger.** LLM tags claim_text_o as main/interaction/moderation with confidence + review state; unlocks the 20%-vs-53% predictor live. Data HAVE. Effort S-M. Brilliance 4.

**G4 Outcome-sentence miner.** Semantic Scholar citation contexts for each original → sentences like "failed to be replicated (Panero et al., 2016)" shown as a "what later papers say" panel and as discovery evidence. Data FETCH (free, 1 rps). Effort M. Brilliance 4.

**G5 Alias resolver.** LLM + reviewer merges effect names across legacy 'effect' (443), Reversals sheet (583), docx (362), FORRT R&R (558) into stable effect IDs with alias lists (no taxonomy). Data HAVE. Effort M. Brilliance 4.

### H. Design & identity

**H1 ★ Replication weather glyph.** A single small glyph per effect encoding (a) attempts count as rings, (b) outcome mix as sectors (successful ultramarine / failed vermilion / mixed hatched), (c) independence as an outer stroke, (d) shrinkage as fill height. Reads at 16 px in lists and 120 px on the page; it *is* the favicon of every effect page and the badge (D3). Data HAVE. Effort M. Brilliance 5.

**H2 ★ Effect trading cards.** Card = name, claim sentence, year/journal, original N and r, weather glyph, verdict, "fame" (cites), rarity by attempts. Print sheet + share image (OG image generated at build). Also the game's visual unit. Data HAVE. Effort M. Brilliance 4.

**H3 Timeline scrubber.** Site-wide year slider: the record as of 2011 / 2015 / 2020 / today — how verdicts changed as attempts accumulated (from year_r). Data HAVE. Effort M. Brilliance 4.

**H4 Typographic verdict system.** Verdict words as set type: REPLICATED / MIXED / FAILED / REVERSED / UNTESTED in a display face with the criterion named beneath ("by significance; by CI-consistency: mixed"). Ink on paper, vermilion for failed, ultramarine for success, hatched for mixed. Data HAVE. Effort S. Brilliance 3.

**H5 Sound of the record (easter egg).** Optional: sonify a citation curve on the story page. Effort S. Brilliance 2.

### I. Integrations

**I1 Wikipedia / Wikidata.** Export per-effect record as Wikidata-ready statements and a "cite this record" snippet for Wikipedia's Replication_crisis and effect articles, which currently name only ~7 psych effects (U6). Data HAVE. Effort M. Brilliance 4.

**I2 FORRT parity API.** Serve the exact rep-api.forrt.org record JSON shape statically so the Zotero plugin could point at us as a mirror, and so our review-queue accepts can be diffed against FORRT. Data HAVE. Effort S. Brilliance 3.

**I3 Retraction Watch overlay.** Join Retraction Watch CSV (CC-BY, daily) and OpenAlex is_retracted (5 of our cached originals) to flag retracted originals/replications. Data FETCH (free). Effort S. Brilliance 3.

**I4 OSF "in progress" feed.** OSF registrations with the Replication Recipe template but no post-completion after 3 years → "file drawer?" flag on the effect; PsyArXiv replication preprints (623) as "preprint" tier. Data FETCH. Effort M. Brilliance 3.

### J. The game (required feature) — visionary variants

**J1 ★ Calibration game with Brier scoring.** Probability slider (not binary), three outcomes with partial credit for mixed, stratified ~50% base rate per session, running Brier score and calibration curve vs laypeople 59% / stats-informed 67% / surveys 66% / markets 73% / repliCATS 76%. Data HAVE (985 successful / 787 failed FReD rows with claim_text_o; FLoRA quotes for the reveal). Effort M. Brilliance 5.

**J2 ★ Progressive-cue mode.** Guess after the claim sentence; then the p-value bucket is revealed (52% vs 37%), then N, then prereg, then journal base rate, then independence — re-guess at each step; the game *teaches the predictors* by letting you feel your own update. Data HAVE. Effort M. Brilliance 5.

**J3 Daily "Replicle".** One effect per day for everyone (seeded by date), shareable emoji grid of your five cue-stage guesses, streaks in localStorage. Data HAVE. Effort S. Brilliance 4.

**J4 Fame tier / difficulty.** Items tagged by cited_by_count: "textbook classics" vs "deep cuts"; hardest tier = famous-and-failed. Data HAVE. Effort S. Brilliance 3.

**J5 Versus mode / classroom (see C3).** Shared room, live histogram. Effort M. Brilliance 4.

**J6 Reveal = three lenses.** After the guess: author verdict (outcome_quote), numerical record (r_o → r_r, seven criteria), design differences (closeness / prereg / independence), then the citation curve ("the field kept citing it"). Data HAVE. Effort S (given pages exist). Brilliance 4.

---

## 2. Ranking method

Score = brilliance × (data-in-hand ? 1 : 0.6) × (1 / effort weight S=1, M=1.3, L=1.8), then hand-adjusted for (i) distinctiveness vs FORRT Explorer / Atlas / Zotero plugin, (ii) synergy with the required game and the three lenses, (iii) credibility risk. Ideas that only re-skin the Explorer (F5, F7, D8, G1) rank low despite being expected.

## 3. Top 12 (suggested build order)

1. **C5 + H1 — Claim-sentence-vs-outcome-quote as the atomic unit, with the weather glyph.** Cheapest, most distinctive: two real quotations face to face (2,131 claim sentences; 100% quote coverage in FLoRA) and one glyph that becomes badge, favicon, OG image and game card. Everything else hangs off it.
2. **J1 + J2 + J6 — The calibration game with progressive cues and a three-lens reveal.** Required feature; every existing quiz is a frozen 21-item binary set — a living, probabilistic, cue-revealing game generated per build is a genuine first (U6). Add J3 daily mode once stable.
3. **A1 — Rise & Fall citation curves with attempt markers.** 1,583 originals ready; "the field kept citing it" is the emotional core and the reveal's last beat.
4. **A2 + A3 — The Graveyard and The Survivors.** Editorial front doors; typography-led; docx statuses + GS counts + quotes make them buildable in days. Provenance caveat: docx status is an Oct-2021 snapshot; merge with FLoRA/FReD before showing a verdict.
5. **F3 + D7 — Seven-criteria matrix and the seeded power / small-telescopes calculator.** The numerical lens done properly; shows that "replicated?" depends on the criterion; no competitor does it.
6. **A5 — Built on a Failed Foundation (dependency graph).** 263 edges into failed originals; unique to our citation cache; a story nobody has told with data.
7. **D1 + D2 + D3 — Reference-list checker, bookmarklet, badge.** Utility that brings researchers back weekly and spreads the glyph across the web; parity with FORRT's Zotero plugin but on the open web.
8. **F1 — Predictors of replication, live with denominators.** p-bucket, independence, prereg, N, decade, discipline recomputed each build; doubles as the game's cue table.
9. **B1 + B2 + B4 + B6 — Leaderboards with denominators.** Most-cited-unreplicated, biggest shrinkage, journals (n, mix, caveat), independence ledger. Cheap, shareable, honest.
10. **E4 + D4 + E1 — Public review queue on effect pages, weekly diff, follow-an-effect.** The discovery pipeline made visible and useful; reviewer decisions are training data and FORRT contributions.
11. **C1 — What your textbook still teaches.** The one education idea that becomes a maintained *table* (OpenStax / Noba) nobody has; strong press/teacher appeal.
12. **E2 + E5 — Wanted list with crowd forecasts.** Turns visitors into a prior on untested findings; closes the loop with the game's calibration scores.

Deferred but cheap: A6, A7, B7, F2, F6 (coverage/honesty — actually mandatory, not visionary), H4, I2, I3, J4. Deferred and costly: G1, C3/J5 (shared state), B9, I1, A8 (writing).

## 4. Homepage concept — "The Record, today"

Above the fold (paper background, ink type, one accent per zone):
- **Masthead:** site name + tagline, and a live counter row with denominators: "2,526 replication attempts · 2,589 original findings · 41% successful · 36% failed · 22% mixed — as of <FLoRA snapshot date>".
- **The Daily (J3):** one trading card (H2) — claim sentence, year, journal, N. A probability slider. "Did it replicate?" Guess → reveal (three lenses + citation curve). Share grid.
- **Two editorial doors:** THE GRAVEYARD (vermilion rule) / THE SURVIVORS (ultramarine rule), each showing three glyphs and names.
- **A strip of weather glyphs** for "recently added attempts" (weekly diff); hover reveals the outcome quote.

Below the fold:
- **Rise & Fall of the week:** one citation curve with markers (rotating from the top-cited failed originals).
- **Base rates with denominators** (F2 mini) and **Predictors** (F1 mini: the p-bucket bar).
- **Check your reading list** (D1 input box) + **Get the badge** (D3).
- **Open candidates** count and link to the review queue (E4); **Wanted** top 5 (E2).
- Footer: provenance (FReD/FLoRA versions + hashes, CC-BY citation string from output_citation.txt), API, downloads, "contribute to FORRT".

Tone: field guide, not dashboard. One number per sentence; every number links to its rows.

## 5. Candidate names + taglines (collision checks via WebSearch, 2026-09-07)

| Name | Tagline | Collision notes |
|---|---|---|
| **Retested** (retested.org / .science) | "Every psychology finding, tested again." | Searches for "retested" replication site/app and retest.org / retest.science returned no product or site; generic word (software "retesting" blogs only). Best candidate. |
| **Twice** (twice.science) | "A result counts when it happens twice." | No hits for twice.science; common word, weak SEO, strong wordmark. |
| **Does It Hold?** (doesithold.org) | "The replication record of psychology, effect by effect." | Exact domain not searched; nearest neighbour *HoldsUp* (holdsup.app) is a podcast fact-checking product by Aiteklabs (13,877 claims, 310 episodes) — avoid "Holds Up"/"HoldsUp" outright. |
| **The Rerun** (rerun.science) | "Psychology's findings, run again." | No site found; "Re-run, Repeat, Reproduce…" is a 2017 paper title only. Slight TV connotation (intended). |
| **Encore** (encore.science) | "Findings worth a second performance." | NOT searched; likely generic collisions (Encore software brands). Lowest priority. |

Rejected on collision: "Replication Record" / "Replication Database" (FORRT's own JOPD paper title and Shiny app), "Second Look" (secondlookresearch.com, UChicago AI-safety replications), "Holds Up" (holdsup.app), "Replicant" (Blade Runner), "Half-Life" (Valve; keep "effect half-life" as a feature name only).

## 6. Notes for the synthesis agent (constraints respected / risks)

- No new taxonomy: topics = FReD discipline + OpenAlex subfield + curated tags; effect identity = stable IDs + alias lists (G5), with provenance and review state on every inferred label.
- Every leaderboard must carry n and a selection-bias caveat; journal rates in particular (replicators choose surprising findings).
- docx statuses / GS counts are an Oct-2021 snapshot; display as "curated 2021" and merge with current FLoRA/FReD before verdicts.
- citation_by_outcome_analysis.json outcomes derive from legacy `result` (341 originals); recompute from the merged layer before publishing A5 / B1.
- counts_by_year in the cache covers 2012-2025 only; a re-fetch (OpenAlex, ~$0.002 per 100 works) gives fuller curves and citer-year data for before/after tests.
- Shared-state features (C3, E1 email, E2 votes, E5 forecasts) need Supabase; everything else is static-buildable in Astro.
- Never copy the 51 scripts with live keys; port the cursor/backoff/normalize_doi patterns only.

---

## Appendix A — numbers verified in this session (file → figure)

- **docx_parsed_entries.json**: 362 entries; status (normalised) replicated 113 / mixed 116 / not replicated 102 / reversed 10 / unknown 21; GS citation counts parsed for 266; 354 entries have dated critiques. Top not-replicated by GS: low self-esteem → poor mental health 13,722; Pygmalion 13,625; ToM under 4 (false belief) 9,112; ego depletion 7,141; 5-HTT G×E 6,223; elderly priming 5,938 (reversed); oxytocin-trust 4,800; men's competition preference 4,001; Dunbar's number 3,168; moral priming 3,072; ACE 2,870; depressive realism 2,855 (reversed); imposter phenomenon 2,709; hostility priming 2,409; physical warmth 1,894. Top replicated: reference framing / magnitude effect 76,664; certainty effect / overweighting small probabilities 75,571; classical anchoring 46,154; Asian disease 25,330; Dunning-Kruger 8,376.
- **citation_by_outcome_analysis.json**: 185 success (mean 661 / median 256 cites) vs 156 failure (mean 441 / median 156.5); 37 high-profile failures led by availability heuristic 1973 (9,660).
- **openalex_original_enrichment_full.json**: 1,623 records, 1,583 with counts_by_year (2012-2025), 5 retracted. Bargh 1996: 2,348 cites; per-year 2012 117 … 2019 131, 2020 148, 2021 92, 2022 76, 2023 64, 2024 68, 2025 82. Power posing 2010: 831; peak 2017 94 → 2025 39. Kidd & Castano 2013: 1,522; peak 2018 188 → 2025 84.
- **citation_dois.json**: results 1,688 (1,687 with DOI); 1,148 internal reference edges; 263 edges into originals coded as failures (187 distinct citing originals); most-depended-on failed originals: 10.1126/science.1222426 (32), availability 1973 (21), Higgins 1977 (18), Bargh 2001 (14), Zhong & Liljenquist 2006 (13), Bargh 1996 (12). Citing-DOI lists present for 1,622 originals, median 122.
- **output_flora.csv** replication rows (2,526): outcome_quote 100% non-null; oa_url_r 60%; lag year_r − year_o median 7, mean 9.6, max 135, 9% ≥ 20 y; oldest originals 1880 Ebbinghaus, 1898 Triplett, 1926 Terman, 1935 Stroop. By decade of original: 1970s 51 attempts / 29% successful; 1980s 76 / 53%; 1990s 155 / 37%; 2000s 712 / 39%; 2010s 1,283 / 43%; 2020s 224 / 44%. journal_o (n ≥ 25): Psych Sci 224 / 28%; JPSP 151 / 29%; PNAS 73 / 41%; Science 66 / 36%; AER 42 / 48%; JEP:LMC 42 / 40%; Cognition 39 / 41%; JEP:General 39 / 23%; JCR 38 / 18%; JESP 34 / 29%; Nature 29 / 31%; JABA 27 / 70%; Nature Genetics 26 / 38%. Originals with ≥3 attempts 29, ≥5 attempts 5. Top author_r surnames dominated by mega-projects (Frank 154, Mathur 149, Miske 143, Loomas 142, Boyce 140, Nosek 97).
- **archive/2025-11-30_COSdata_validated.xlsx** (2,164 rows): r_o & r_r both 733; median |r_r|/|r_o| 0.58; 46% shrink > 50%; median |r_o| 0.30, |r_r| 0.14. author_overlap non-null 1,676; 62% fully independent; independent success 41% (n=1,344) vs 52% (n=820). p_o ≤ .005 → 52% successful (n=790); .005-.05 → 37% (970); > .05 → 42% (242). n_o buckets ≤50 47%, 51-100 44%, 101-250 46%, >250 44%. claim_text_o non-null 2,131.
- **FReD_2.4.1 Data sheet** (4,659 rows): closeness_* coded on 165 rows (instructions exact 95 / close 67; stimuli close 123 / exact 27); power non-null 834, median 0.976, 4% < .8; result: informative failure 726 / success 678 / inconclusive 18 / practical failure 3; prereg link present 271 rows → 52% success vs 47% (1,156); orig_journal (n ≥ 30) Psych Sci 210 / 29%, JPSP 204 / 34% (+47 rows / 64% under a lowercase variant — normalise), JESP 82 / 26%, Science 74 / 61%, Cognitive Psychology 73 / 27%, Group Dynamics 72 / 83%, JEP 66 / 23%, JCR 45 / 13%, Cognition 44 / 48%, PSPB 42 / 95%, JDM 39 / 82%; effect names: Anchoring 552, unconscious-thought 243, girls-math stereotype 70, commitment priming 64, SVO 52, verbal overshadowing 52, moral priming 44, intelligence priming 40, imagined contact 36, framing 36.
- **Third-party raw on disk**: osc_2015_rpp_data.csv 168×138; ml4_results.csv 17 sites; manybabies_mb1_data.csv 19,603 rows / 67 labs (U3).
