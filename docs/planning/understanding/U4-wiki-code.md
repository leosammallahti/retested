# U4 — Audit of the existing wiki/ Astro site ("Replication Families")

Audited path: C:\Users\OMISTAJA\PsychologyReplication\wiki (built Aug 11-13 2026). Date of audit: 2026-09-07.
Everything below was verified by reading the files / running Python over them. Numbers are actual.

## 0. One-paragraph verdict

The wiki is a two-day MVP scaffold: a pleasant "museum / field guide" visual skin over a nearly empty data model. Of the 6,006 built pages, 6,004 are placeholders that show a title, authors, journal, year and a "Metrics Pending" box; only the single hand-written family page (literary fiction -> theory of mind) has real editorial content. The data pipeline reads FLoRA only (2,521 rows), never got FReD (the downloaded "fred_effect.xlsx" is a 1x1 sheet), and derives nothing (no effects, no outcomes, no effect sizes — the `outcome` column of FLoRA is not even carried into the index). The code is competent-but-sloppy Astro (fs reads at build time, catch-all dynamic routes, one Preact island), with several real bugs (undefined CSS variables, duplicate route files, dead nav links, stale tests). Keep: the stack choice (Astro + a small island framework), the provenance-snapshot idea, the palette/tone as a starting point, and the "Replication Family + three lenses" editorial concept (strong, but must be data-driven not hand-written). Throw away: essentially all page code, the normalize script, the schema, dist/, the placeholder pages, the tests.

## 1. Inventory (verified)

- package.json: astro ^7.2.1, @astrojs/preact ^6.0.2, preact ^10.29.8, fuse.js ^7.5.0, papaparse ^5.5.4, d3-fetch ^3.0.1 (imported nowhere in src), zod ^4.4.3. Dev: playwright 1.62, @playwright/test, vitest 4.1, tsx, xlsx 0.18.5, @types/node 26. npm scripts: only dev/build/preview/astro. fetch-data / normalize-data are NOT wired into scripts (run ad hoc with tsx) -> violates the "one-command data build" non-negotiable.
- astro.config.mjs: 4 lines — preact() integration, dev server port 3000/host true. No `site`, no `base`, no `output`, no adapter, no sitemap, no build tuning.
- README.md = untouched Astro "minimal starter" boilerplate. CLAUDE.md = AGENTS.md (hard-linked, 874 bytes) = generic Astro dev-server notes. .gitignore is Astro default. No git repo.
- node_modules IS installed (Aug 13). (BRIEF said "no node_modules installed" — incorrect.)
- src/ (10 files): layouts/Layout.astro; components/SearchBox.tsx (Preact+Fuse); styles/index.css (200 lines); lib/schema.ts (+ schema.test.ts, 2 vitest cases); pages: index.astro, explore.astro, attempt/[id].astro, attempt/[...id].astro, paper/[id].astro, paper/[...id].astro, family/[id].astro, collections/[id].astro.
- scripts/: fetch-data.ts (downloads 4 URLs, writes snapshots.json with url/sha256/size/retrievedAt/license), normalize-data.ts (FLoRA csv -> search_index.json + derived_db.json).
- data/sources/ (retrieved 2026-08-12T23:38Z):
  - flora.csv 8,565,862 B from raw.githubusercontent.com/forrtproject/FReD-data/main/output/flora.csv (sha256 ba0b6f88...). 2,521 rows parsed.
  - fred_effect.xlsx 1,083,820 B from https://osf.io/2tbvd/download — BUT openpyxl shows ONE sheet "Sheet 1", 1 row x 1 col, header `entry_id`. i.e. empty/placeholder. Result: `fred_effects: []` in derived_db.json.
  - fred_codebook.pdf 8,863 B from https://osf.io/download/g7r9z/ — actually an XLSX (starts with PK, `file` says "Microsoft Excel 2007+"), mis-named. It is the FReD codebook spreadsheet, not a PDF.
  - disciplines.json 30,817 B from forrt.org/flora-explorer/data/disciplines.json — a map {discipline: [journal names...]} ("Psychology": ["psychological science", ...]). Useful for journal->discipline tagging of FLoRA rows; never used by the site.
- data/generated/: search_index.json 1,318,526 B (2,521 objects, keys: id, doi_original, doi_replication, title, authors, journal, year, source='flora'); derived_db.json 1,368,988 B = {registry: <same 2,521>, fred_effects: []}. Stats: 0 empty doi_o, 0 empty doi_r, 2,335 unique doi_o, 1,855 unique doi_r, 186 duplicate `id`s (id = doi_o, and many originals have several replications), 0 "Unknown Title", 0 empty authors. `outcome`, `type`, `source`, `outcome_quote`, oa_url etc. are DROPPED at normalize time — the index knows nothing about whether anything replicated.
- data/curated/family-literary-fiction.json: id, title, target_claim, original_experiments [1 DOI], replication_attempts [3 DOIs], curation_state "reviewed", evidence_timeline [3 events], lenses {author_reports, numerical_records, design_differences}. Note `lenses` is NOT in ReplicationFamilySchema, and the page never validates against the schema anyway.
- dist/ (built Aug 13 13:32): 6,006 HTML files: paper/ 4,150, attempt/ 1,850, collections/ 3, family/ 1, explore/ 1, index 1; 26.9 MB total. _astro/: Layout CSS 4.8 KB, SearchBox.js 29 KB, preact 10 KB, signals 7.8 KB, hooks 2.5 KB, client 2.7 KB. dist/explore/index.html is 1,720,562 B because the entire index is serialised inline as the `props` attribute of the Preact island (client:load). dist/paper/10.1126-science.1239918 and dist/attempt/10.1037-pspa0000064 exist from the dead stub routes.
- Screenshots (Aug 13 13:39, from screenshot.js via Playwright): home.png, explore.png (1.8 MB), family.png, collection.png, paper.png, attempt.png. Viewed home/family/collection/attempt.
- tests/explore.spec.ts: 3 Playwright tests; two assert strings ("Showing", "30-Second Overview") that do not exist in the pages -> stale/failing. playwright-report/index.html (515 KB) exists from a run on Aug 13 02:43.
- Misc: .vscode/, .astro/ cache, vitest.config.ts, playwright.config.ts (baseURL :3000, webServer npm run dev).

## 2. Information architecture (as designed vs as built)

Designed (from the code and Layout nav):
- Home ("Entrances": By Topic, By Method, Search; a Featured family; 3 curated collections)
- /explore — Fuse.js full-text search over the FLoRA registry, sidebar "Filters" (placeholder text: "URL-based filters can be implemented here")
- /family/[id] — the editorial unit: target claim, evidence timeline, original experiments, attempts, three lenses, "current understanding"
- /paper/[doi] — bibliographic container (claims to show experiments/claims/family membership)
- /attempt/[doi] — replication attempt record (claims to show design deltas, sample, prereg, effect sizes)
- /collections/[id] — famous-effects, multi-lab, cross-cultural
- nav: /collections (index), /about, footer /contribute

Real vs placeholder:
| Route | Status |
|---|---|
| / | real but thin; two of three "Entrances" link to `/explore?facet=topic|method` which the explore page ignores |
| /explore | REAL (the only functional data feature): search over title/authors/doi/journal, 50 results, q synced to URL. No filters, no outcome shown, no facets. Result links go to `/paper/<doi>/index.html` (hacky). |
| /family/family-reading-literary-fiction | REAL content, hand-written JSON, no linkage to FLoRA rows (DOIs link out to doi.org, not to internal pages) |
| /paper/* (4,150) | PLACEHOLDER: title/authors/journal/year + "not yet curated" box. Replication papers ALSO get a /paper page (type "Replication Attempt Document"), so a replication DOI appears at both /paper and /attempt. |
| /attempt/* (1,850) | PLACEHOLDER: header + "Detailed Metrics Pending" |
| /collections/* (3) | PLACEHOLDER: "Collection Data Pending... migrating legacy taxonomy" |
| /collections, /about, /contribute | DO NOT EXIST (nav links 404) |
| attempt/[id].astro, paper/[id].astro | dead duplicate stub routes coexisting with [...id].astro; they emit `10.1126-science.1239918` style pages |

Conclusion: the IA is paper-centric (routes keyed by DOI) with an effect/claim-centric aspiration (families) that has exactly one instance. There is no effect entity, no project entity (Many Labs etc.), no author/topic entity, no outcome anywhere.

## 3. Visual design system — precise description and grade

Tokens (src/styles/index.css, "Elegant Museum Palette"):
- Backgrounds: --color-bg-base #f7f6f2 (warm aged paper), --color-bg-surface #ffffff (placards).
- Ink: primary #1a1a1a, secondary #595959, tertiary #8c8c8c.
- Accents: vermilion #d83e27 (+ light #fbebe9), ultramarine #1b2663 (+ light #e8eaf0).
- Borders: #e2dfd5, dark #c2bead.
- Fonts: --font-serif 'Playfair Display' (loaded from Google Fonts: 400/600/700 + italic 400), --font-sans 'Inter' (400/600/700), --font-mono 'JetBrains Mono','Fira Code' — NOT loaded, so mono falls back to Courier New (visible in screenshots: badges "ATTEMPT RECORD", timeline years, DOI links render in Courier).
- Spacing scale --space-1..8 = 0.25/0.5/1/1.5/2.5/4/6 rem. Transition cubic-bezier(0.16,1,0.3,1) 0.4s.
- Type: body = Playfair Display 1.1rem/1.6 (serif body!), headings = Inter 600 with negative tracking, h1 clamp(2.5rem,5vw,4rem), h4 uppercase small-caps style, links ultramarine with 20% underline -> vermilion on hover. Components: .card (white, 1px border, lift+shadow on hover), .badge (pill, mono uppercase), .timeline (1px rule, hollow vermilion dots), search input (square, 4px ultramarine focus ring). Container max 1100px.
- Tone: "field guide", museum placard, editorial/magazine; sans display headlines + serif body (inverted from the common pairing).

Bugs in the design implementation (verified):
- Pages use `var(--spacing-*)` (index.astro x10, explore.astro x4, Layout footer) but the tokens are `--space-*`. Every such margin/gap resolves to nothing. Visible in home.png: "Entrances" h2 rides directly on the card row; footer is jammed against content on all pages.
- `--color-ink-light` and `--color-ink-faint` are used (Layout footer, explore header) but never defined -> transparent borders / default color.
- Mono font never loaded (see above).
- Header/footer/pages are almost entirely inline `style=""` attributes; the CSS file's classes cover maybe a third of what is styled. No dark mode, no responsive breakpoints (family page is a fixed `1fr 350px` grid; home is a fixed `1fr 1fr`), no print styles.
- Playfair Display as the 1.1rem body face is a readability mistake (high-contrast display face, thin hairlines at text sizes); it looks handsome in the screenshot but is tiring for a wiki of tables and numbers. Also no tabular figures anywhere despite the site being about effect sizes.

Grade: B- as a mood board, D+ as an implemented system. The palette (warm paper + ink + vermilion/ultramarine) and the placard/field-guide tone are distinctive, calm, appropriately serious, and worth keeping as the visual identity direction. The implementation (token bugs, inline styles, wrong body face, unloaded mono, no semantic outcome colours, no data-viz palette) should be rewritten. Specifically: keep the 5 accent/ink hues and the paper ground; swap body to a text serif with tabular numerals (e.g. Source Serif 4 / Newsreader / Literata) or make body Inter and headings serif; load a real mono (JetBrains Mono / IBM Plex Mono) since DOIs, n, d, p values are everywhere; add a semantic outcome palette (successful / mixed / failed / other) that is colour-blind safe and distinct from the two brand accents; add dark theme tokens.

## 4. Code quality

Good:
- Correct Astro basics: `getStaticPaths()` with `props` to pass data (no re-reading per page), rest-param route `[...id]` so DOIs with slashes work, one island (`client:load`) only where interactivity is needed, plain .astro for static pages.
- fetch-data.ts records provenance (url, sha256, size, retrievedAt, license, citation) — good pattern to keep.
- Windows-illegal-char filtering for DOI paths shows awareness of filesystem limits.
- Zod chosen for schemas; a vitest test exists.

Bad:
- Data loading duplicated: `fs.readFile(...search_index.json)` + try/catch copy-pasted into explore, paper, attempt. No shared `src/lib/data.ts`; no Astro content collections / `getCollection` (Astro 5+ content layer with a `file()` loader would be the idiomatic approach and gives type-safety for free).
- normalize-data.ts throws away FLoRA's most important columns (outcome, type, source, outcome_quote, oa_url, apa refs, language). Author parsing uses regex over stringified JSON. `id = doi_o` yields 186 duplicate ids -> duplicate Preact keys. `crypto.randomUUID()` used without importing crypto (works only because Node exposes global `crypto`).
- Schemas (Effect, Experiment, ReplicationFamily, Paper) are aspirational — nothing on the site instantiates Effect or Experiment; the family JSON has a `lenses` field the schema does not know about and no page ever calls `.parse()`.
- Duplicate route files: paper/[id].astro AND paper/[...id].astro (same for attempt). The [id] versions are dead stubs with hard-coded params; both build.
- Each replication DOI is generated under BOTH /paper and /attempt — 4,150 + 1,850 pages from 2,521 rows, ~4,190 distinct DOIs; when the same DOI appears in multiple rows, getStaticPaths pushes the same path repeatedly (Astro silently keeps one).
- SearchBox: the whole 1.3 MB index is inlined into explore.html as escaped-JSON props (page = 1.72 MB), then Fuse builds an index in the browser on every load. Should be a separately fetched, pre-built index (or Pagefind / MiniSearch with a serialised index).
- Links built as `/paper/${doi}/index.html`; hard-coded fallback stubs in getStaticPaths; nav to non-existent /collections, /about, /contribute; `explore?facet=` params ignored.
- CSS variable typos (see 3). Tests assert text that is not on the pages. README is starter boilerplate. d3-fetch dependency unused. No `site` in config -> no canonical URLs / sitemap; no `base` -> would break on GitHub Pages project URLs.
- No lint/format config, no CI, no git.

Is "dynamic routes generating ~6,000 pages" the right approach? Yes in principle — static generation is the right shape for this content (public, read-mostly, citable URLs, free hosting) and Astro handles 5–20k pages comfortably (this build produced 6,006 pages; build time is dominated by the fs read + template render, seconds to a couple of minutes). But two things must change: (a) one page per entity that actually has content — effects/findings, papers (original OR replication, not both), projects, plus JSON endpoints — rather than 6k pages of "pending"; (b) data should enter via a typed loader (content collections or a single `lib/data.ts` that loads the normalized DB once and memoises), not per-page fs reads. Route keys should be stable slugs/ids (e.g. FReD `id`/ FLoRA hash prefix) with DOI stored as metadata, because raw DOIs contain characters that are illegal on Windows paths (the code already had to filter `<>:"\|?*`) and some contain `//`.

## 5. The "Replication Family" concept and the three lenses — editorial assessment

What it is (from family/[id].astro + curated JSON): a Family = one target claim + the original experiment(s) + all attempts, presented as (1) an "Evolution of Evidence" timeline, (2) a sidebar of DOIs, (3) a "Five-Minute View" with three lenses — *What authors reported* (the verbal conclusions: replicated / failed), *What numerical records show* (effect sizes, CIs, n), *How designs differed* (closeness: samples, stimuli, measures, context) — and (4) a "Current understanding & next steps" box. Badges distinguish curation state: imported / candidate / reviewed.

Assessment: this is the strongest idea in the folder and maps almost perfectly onto the FORRT data model:
- FReD already has per-effect rows with es_original/es_replication, n_original/n_replication, p-values, CI bounds, and eight `closeness_*` columns (instructions/measures/stimuli/procedure/location/renumeration/participants/exclusions/language/nationality) + same_design/same_test/preregistration/power — i.e. lens 2 and lens 3 can be COMPUTED for every effect, not hand-written.
- Lens 1 (author reports) = FLoRA `outcome` + `outcome_quote` + `outcome_quote_source` — the verbatim quote is exactly "what authors reported".
- The FReD R package's seven success criteria (significance_r, significance_agg, consistency_ci, consistency_pi, homogeneity, homogeneity_significance, small_telescopes) are precisely the "numerical record" lens, and showing that the verdict DEPENDS on the criterion is a genuinely brilliant, honest angle nobody else's explorer does.
- The three-lens split is also the pedagogical core of the guessing game: show the original (lens 0), let the user guess, then reveal lens 1 vs lens 2 vs lens 3.
Weaknesses as implemented: it exists once, hand-written, unlinked to the registry, with a schema that doesn't match; the timeline is prose; "Current understanding" is unsourced editorial opinion; "family" is a fuzzy word (is it an effect? a claim? a paper?). Recommendation: keep the concept at the centre but rename/define it rigorously — Finding (claim) -> Original study/experiment -> Attempts; make the three lenses auto-generated from data with an optional curated overlay (evidence timeline prose, "current understanding" with citations), and make the curation-state badge a first-class, honest signal (imported / auto-derived / human-reviewed).

## 6. What to throw away vs keep

Throw away (do not port): all src/pages/*, Layout.astro, SearchBox.tsx, normalize-data.ts, schema.ts (+test), tests/, screenshot.js, playwright-report/, test-results/, dist/, data/generated/*, data/sources/fred_effect.xlsx (empty) and the mis-named fred_codebook.pdf, README.md/CLAUDE.md/AGENTS.md boilerplate, d3-fetch dependency, the 3 placeholder collections, the duplicate [id] routes. The 5 PNG screenshots can be archived as a record of the previous look.

Keep / reuse (with paths):
- The provenance-snapshot pattern in wiki/scripts/fetch-data.ts (url, sha256, bytes, retrievedAt, license, citation -> snapshots.json). Rewrite, but keep the idea and extend with version/commit of the FReD-data repo.
- Design tokens in wiki/src/styles/index.css (palette hexes, spacing scale, card/badge/timeline patterns, the "field guide" subtitle) as the seed of the new design system — fix the bugs, change the body face, add outcome + chart palettes.
- wiki/data/curated/family-literary-fiction.json as the first worked example of a curated overlay (Kidd & Castano 2013 -> Panero 2016, Samur 2017, etc.); its `lenses`/`evidence_timeline` shape is a good template for a curated overlay format.
- wiki/data/sources/disciplines.json (journal -> discipline map from FORRT's FLoRA explorer) — useful for tagging FLoRA rows by discipline.
- The DOI-path lesson: Windows-illegal chars and `//` in DOIs -> use hashed/slugged ids for routes.
- The "curation_state: imported | candidate | reviewed" enum.
- The stack (see 7).

## 7. Stack recommendation: keep Astro (+ Preact or Svelte islands); do not move to Next/Nuxt/Docusaurus/Hugo/plain HTML

Requirements: ~5k static pages, client-side search, an interactive guessing game, charts, zero backend budget, GitHub Pages / Cloudflare Pages hosting.
- Static generation: Astro's SSG is the best fit — file-based routing, `getStaticPaths` at scale, content collections with custom loaders (load the normalized JSON once, typed with Zod), zero JS by default so 5k pages are cheap, `astro build` output deploys to GH Pages (set `site` + `base`) or Cloudflare Pages unchanged. Next.js static export can do it but ships React runtime on every page and fights you on `base`; Hugo/Eleventy are fine for text but poor for typed data + islands; Docusaurus/Starlight are doc-shaped, not data-shaped.
- Search: keep it client-side but pre-built: Pagefind (indexes the built HTML, loads index chunks lazily, works on GH Pages) for full-text, plus a small MiniSearch/FlexSearch JSON index for structured entity search (effects, authors, DOIs). Do NOT inline the index into HTML props as the current site does.
- Game: one island (Preact/Svelte/Solid) reading a pre-built `game.json` (effects with description + original study, answer hidden until reveal); progress in localStorage; optional shareable score via URL hash. No backend needed. Supabase (connected MCP) is optional for leaderboards/contribution queue later, but the non-negotiables do not require it.
- Charts: static SVG rendered at build time (Astro component or d3 in the frontmatter) for per-effect forest plots / original-vs-replication scatter — cacheable, no JS, printable; a small island (Observable Plot or d3 in Preact) only for interactive explorer charts.
- Island framework: Preact is fine (10 KB, already chosen). Svelte would give slightly smaller islands and nicer state for the game; Solid similar. Not worth re-deciding — keep Preact unless the team prefers Svelte. Add Tailwind? Not needed; a hand-written token CSS (fixed) is more in keeping with the identity; Astro scoped styles instead of inline `style=`.
- Build-time data: a separate `data/` package (Python or TS) produces `normalized/*.json|parquet` reproducibly (`npm run data`), and the site only reads normalized output. Astro content layer `file()`/custom loader + Zod schema = single source of truth for types.
- Hosting: Cloudflare Pages preferred over GitHub Pages (no `base` path headaches, 20k-file limit is fine for 5–10k pages, free, fast). If GitHub Pages, set `base: '/repo'` and use `import.meta.env.BASE_URL` in every link.
- Node 22 satisfies Astro 7's engine requirement (>=22.12).

## 8. Facts table (for other agents)

- 2,521 FLoRA rows in the site's Aug-12 snapshot (BRIEF's current snapshot has 2,815 incl. 289 reproductions — the site's normalize step does not distinguish `type`).
- 2,335 unique original DOIs, 1,855 unique replication DOIs, 186 originals with >1 attempt (duplicate ids).
- Built pages: 6,006 (paper 4,150 / attempt 1,850 / other 6); dist 26.9 MB; explore.html 1.72 MB.
- Client JS: ~53 KB (SearchBox 29 KB incl. Fuse, preact 10 KB, signals 7.8 KB, hooks 2.5 KB, client 2.7 KB).
- CSS bug: `--spacing-*` used 15 times, defined 0 times; `--color-ink-light/faint` used 3 times, defined 0 times.
- Fonts loaded: Inter 400/600/700, Playfair Display 400/600/700/400i; JetBrains Mono referenced, not loaded.
- FReD file in wiki/data/sources is empty (1x1); real FReD is at C:\Users\OMISTAJA\PsychologyReplication\data\raw\forrt\fred-data\output_FReD.xlsx (1.08 MB, downloaded 2026-09-07).
- fetch-data used https://osf.io/2tbvd/download (FReD) and https://osf.io/download/g7r9z/ (codebook) — both returned something other than what was expected; prefer the GitHub FReD-data repo raw files.
