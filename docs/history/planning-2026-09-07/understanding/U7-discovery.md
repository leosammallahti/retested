# U7 — Discovering NEW replication studies beyond FORRT

Date: 2026-09-07. Author: subagent U7. All numbers below were produced by live API calls or by reading files on disk on this date unless marked "(web/doc)".
Mailto used for polite pools: leosammallahti@gmail.com.

## 0. Baseline: what FORRT already covers (verified from disk)

File: `C:\Users\OMISTAJA\PsychologyReplication\data\raw\forrt\fred-data\output_flora.csv`
- 2,815 rows = 2,526 replications + 289 reproductions.
- Unique `doi_o` (originals) = 2,589; unique `doi_r` (replications) = 2,148. `doi_o` missing in 13 rows, `doi_r` missing in 204 rows (unpublished/OSF-only reports).
- `source` column: replications 1,522, COS 716, reproductions 284, openalex 200, SCORE 88, openalex_snapshot 4, i4r 1.
- `year_r` tail: 2023: 283, 2024: 181, 2025: 239, 2026: 147 — FORRT is still adding ~150-280 per year, so any crawler must dedup against a moving target.
- Top `journal_r`: Royal Society Open Science 166, OSF 121, Science 110 (SSRP/Camerer), J Applied Econometrics 91, Nature Human Behaviour 49, AMPPS 48, Rev Phil & Psych 39, PLOS ONE 34, Frontiers in Psychology 31, Psychological Science 29, JESP 29, Social Psychology 26.
- FORRT's own discovery method (from `output_flora_faq.md` line 78): "A systematic search of OpenAlex has been conducted, using the keyword 'replication' with automated extraction with R code and manual validation by a human ... This is continuing over time. Reproductions are taken from the Replication Network list and from the Institute for Replication reports."
- FLoRA inclusion criteria (faq line 91): must self-identify as a replication BEFORE reporting results; must name the target study; must replicate a study/experiment, not a single association. Outcome = Successful / Failed / Mixed "based on how the replication authors characterise their results, usually in the abstract". These criteria are exactly what an LLM triage stage must encode.

## (a) OpenAlex API — PRIMARY ENGINE

Base: `https://api.openalex.org/works?filter=...&mailto=leosammallahti@gmail.com`
Docs moved: `https://help.openalex.org/api/` (old docs.openalex.org redirects). Authentication page: `https://help.openalex.org/api/authentication/`; pricing `https://help.openalex.org/access/pricing/`.

Rate limits / pricing (web/doc, fetched today):
- Max 100 requests/second. Every response now carries `meta.cost_usd` (observed `0.001` for a filtered list call).
- Free: $1 of API usage per day per account, resets midnight UTC; free API key = 10x the keyless daily budget. Pay-as-you-go in $1 prepaid increments (expire after 3 months). Annual plans $5k ($20/day) and up. At $0.001/list call, $1/day = ~1,000 list calls/day keyless; get the free key (10x) for a weekly crawl.
- Per-filter OR values: max 100 (`cites:W1|W2|...` up to 100 IDs per call). `per-page` max 200 observed working (docs say 100 for some endpoints; 200 worked today on /works). Basic paging limit 10,000; use `cursor=*` for deeper paging.
- `select=` works to slim payloads (`id,doi,title,publication_year,type,abstract_inverted_index,primary_topic,is_retracted,cited_by_count,referenced_works`).

Live query results (today):
1. `filter=title.search:replication,publication_year:2015-2026&group_by=publication_year` (ALL fields):
   2015 5301, 2016 6230, 2017 6292, 2018 7339, 2019 7479, 2020 8873, 2021 8858, 2022 8605, 2023 9725, 2024 5783, 2025 9818, 2026 23784 (2026 inflated by DNA-replication/biology noise and preprint versions).
2. Same + `primary_topic.field.id:32` (Psychology field):
   2015 194, 2016 204, 2017 258, 2018 348, 2019 338, 2020 413, 2021 343, 2022 336, 2023 383, 2024 394, 2025 468, 2026 509. Total 4,188 works 2015-2026. `has_abstract:true` subset = 3,088 of 4,188 (74% have `abstract_inverted_index`).
3. `title_and_abstract.search:replication` + field 32 + 2015-2026: 34,019 (too broad; use as recall backstop only after citation filter).
4. `title_and_abstract.search:"failed to replicate"` + field 32 + 2015-2026: 367.
5. `title.search:"registered replication report"` (all years): 90.
6. `is_retracted:true,primary_topic.field.id:32`: 2,198 retracted psychology works (useful as a wiki signal layer; `is_retracted` is populated).
7. Topics taxonomy: `GET /topics?filter=field.id:32` -> 144 topics in field 32 (Psychology), subfields: Social Psychology 52, Clinical Psychology 38, Experimental and Cognitive Psychology 24, Developmental and Educational Psychology 20, Applied Psychology 7, Neuropsychology and Physiological Psychology 2, General Psychology 1. Also relevant fields for FReD scope: Economics/Econometrics (field 20), Social Sciences (33), Neuroscience (28), Business/Management (14). Use `primary_topic.subfield.id` for wiki "discipline" facets.
8. PsyArXiv as an OpenAlex source: `sources?search=psyarxiv` -> S4306401687 "PsyArXiv (OSF Preprints)" works_count 8,566 (OpenAlex indexes only part of PsyArXiv; see (d)).

Citation-based discovery (the high-precision method) — live test:
- Kidd & Castano 2013 = W2159585297, cited_by_count 1,624, abstract present, not retracted.
- `filter=cites:W2159585297,title_and_abstract.search:replication` -> 43 works; top hits are exactly the known replications: Panero et al. 2016 (10.1037/pspa0000064), Samur et al. 2018 (10.1177/1948550618775410), van Kuijk et al. 2018 (10.1525/collabra.117), Camerer 2018 SSRP, plus the Kidd & Castano 2017 rebuttal (10.1037/pspa0000072).
- OR syntax verified: `cites:W2159585297|W2113633599,title_and_abstract.search:replication` returns a combined count in one call.
- Yield estimate on first 50 FLoRA `doi_o` (49 resolved; total cited_by 25,637, mean 523, max 4,266):
  - citing works with "replication" in TITLE: 130 (one cursor page of 200);
  - citing works with "replication" in title OR abstract: 1,183.
  - Of the 130 title hits, 92 are NOT already in FLoRA as `doi_r` or `doi_o`. Inspection shows the 92 split into (i) genuine unlisted replications/extensions, (ii) methods papers ("The Replication Recipe", "Replication-Extension Studies"), (iii) off-field noise because some FLoRA originals are GWAS/medical (Camerer/SSRP-style originals cite-bomb). So raw precision of "cites original AND 'replication' in title" is roughly 30-50% before LLM triage; recall for published direct replications is very high (every known Kidd & Castano replication surfaced).
  - Extrapolation: 2,589 originals -> ~26 calls of 100 IDs each per pass (title-only) = trivial; ~6,700 title candidates, ~60,000 title+abstract candidates (with heavy duplication from big multi-study reports). Title-only pass first; abstract pass only for originals with < 300 citations to avoid noise.
- Abstracts: `abstract_inverted_index` is returned in `/works` (must be re-inverted client-side); 74% availability in the psych-replication slice.

Recommended OpenAlex query set (weekly):
- Q1 `cites:{100 FLoRA/curated original IDs},title.search:replicat*` (OpenAlex search stems automatically; "replication" matched "Replicating" in results).
- Q2 `cites:{ids},title_and_abstract.search:replication|replicate|replicated,from_publication_date:{last_run}`.
- Q3 `primary_topic.field.id:32|20|33,title.search:replication,from_publication_date:{last_run}` (field-wide new titles, ~40/week).
- Q4 `title.search:"registered replication report"|"many labs"|"multi-site replication"|"registered report"` field 32.
- Q5 `is_retracted:true,ids.openalex:{our original IDs}` monthly, to flag retracted originals.

## (b) Crossref REST API

Base `https://api.crossref.org/works`, UA header `PsychRepWiki/0.1 (mailto:leosammallahti@gmail.com)` for the polite pool.
- Rate limits (web/doc, changed 2025-12-01): public pool 1 list req/s, polite pool 3 list req/s with 3 concurrent; single-DOI 10/s. Header `x-rate-limit-limit` / `x-rate-limit-interval`.
- No subject filter on /works; ISSN filter works; `query.bibliographic`, `query.title`; cursor paging via `cursor=*`; `filter=from-pub-date:YYYY-MM-DD,until-pub-date:...,type:journal-article,issn:...`.
- Live: `query.bibliographic=replication` 2024 journal-articles = 2,300 (all fields, relevance-scored, very noisy). `query.title=replication` + issn 1745-6916 (Perspectives on Psych Science) 2024 = 0; issn 2474-7394 (AMPPS) 2024 = 5.
- What the old harvester did (`C:\Users\OMISTAJA\PsychologyReplication\harvest_crossref_replications.py`): year-sliced Crossref `query.title` for ~15 phrases ("registered replication report", "preregistered replication", "replication of", "direct replication", "failed replication", ...) restricted to an ISSN whitelist derived from FReD journals (`crossref_issn_whitelist_from_fred.csv`), cursor paging with a JSON checkpoint (`crossref_harvest_state.json`), then OpenAlex topic-code filtering (`openalex_utils.py`) to keep psychology. Output: `output/final_2021_psychology_replications.csv` = 166 rows for 2021 only; never scaled beyond one year.
- Verdict: Crossref adds little over OpenAlex for discovery (no topics, no citations-to filter, no abstracts for most publishers). Keep Crossref only for (1) DOI metadata canonicalisation (`/works/{doi}`), (2) `relation` metadata (`is-preprint-of`, `has-preprint`) to link PsyArXiv preprints to journal versions, (3) `update-to` retraction/correction notices.

## (c) Semantic Scholar Graph API — citation CONTEXT mining

Endpoint: `https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}/citations?fields=title,year,intents,contexts,isInfluential,externalIds&limit=200&offset=N`.
- Rate limit (web/doc): keyless = shared pool, throttled; free API key (form at `https://www.semanticscholar.org/product/api#api-key-form`) = 1 req/s dedicated; higher on request. Today's keyless call returned 200 with no rate headers.
- Live test on Kidd & Castano (DOI 10.1126/science.1239918), first page of 200 citing papers: 87/200 had at least one `contexts` sentence; 4/200 had a context matching /replicat|failed to|did not find/. Sample contexts:
  - "Although the positive effects of short-term interventions (Kidd & Castano, 2013) failed to be replicated (Panero et al., 2016), there is meta-analytical evidence of a small ... improvement" (10.1080/10409289.2025.2516989)
  - "Note, however, that a replication by Kuijik et al. (2018) yielded results consistent with those of Kidd and Castano (2013)." (10.1177/17540739241233601, intents ['result','background'])
  - "...though some studies have failed to find significant effects" (fNIRS paper, 10.1038/s41539-025-00327-0)
- Interpretation: contexts are useful in two ways. (1) Direct: a citing paper whose context says "we replicated / we failed to replicate X" is a replication candidate with outcome evidence. (2) Indirect / "community verdict": third-party sentences ("failed to be replicated (Panero 2016)") name BOTH the original and the replication and state the outcome — this can seed original->replication->outcome triples and is a good feature for the guessing game ("what does the literature say happened?"). `intents` ('result','methodology','background') is sparsely filled; do not depend on it.
- Coverage: contexts exist only where S2 has full text (~40-45% of citing papers here). Precision of the keyword filter is high but recall is modest. Cost: 1,624 citations / 200 = 9 calls for one heavily cited original; for 2,589 originals x mean 523 citations = ~7,000 calls = ~2 hours at 1 rps. Cache results; re-crawl only originals with citation-count deltas (`cited_by_count` from OpenAlex).
- Alternative bulk route: S2 Datasets API (`/datasets/v1/release/latest`) exposes a `citations` dataset with contexts and intents for offline processing (web/doc) — heavier, but avoids the per-paper crawl.

## (d) Preprint servers (PsyArXiv / OSF Preprints)

Endpoint: `https://api.osf.io/v2/preprints/?filter[provider]=psyarxiv&filter[title]=replication&page[size]=100` (JSON:API; unauthenticated 100 req/h per FORRT's scraper comment; OSF docs allow higher with a personal token via `Authorization: Bearer`).
- Live: 623 PsyArXiv preprints with "replication" in title; page[size]=5 test showed items from 2026-09-05 back, e.g. "No evidence for Nonconscious Goal Pursuit in Novel Environments: A Replication of Eitam et al." (10.31234/osf.io/2wpqe_v1), "Debunking decreases mistaken causal inferences: A direct replication of Irving et al." (10.31234/osf.io/am6rg_v3). Versioned DOIs (`_v1`, `_v3`) must be collapsed to the base DOI.
- Useful attributes: `date_published`, `title`, `description` (abstract), `tags`, `subjects`, `links.preprint_doi`, `relationships.primary_file`, and `attributes.doi` (peer-reviewed publication DOI when the author added it) -> link preprint to journal version.
- Also filter `filter[provider]=metaarxiv|socarxiv|edarxiv|osf` and sort `-date_published` with `filter[date_published][gte]=YYYY-MM-DD` for incremental crawl.
- Yield: 623 total ~ 60-80/year; preprints are the earliest signal (often 6-18 months before journal version) and are exactly what FLoRA's "source=openalex" route misses (OpenAlex indexes only ~8.5k PsyArXiv works).

## (e) Registered Reports and preregistration registries

OSF Registries: `https://api.osf.io/v2/registrations/?filter[title]=replication&page[size]=100` -> 5,466 registrations with "replication" in title (live). Attributes include `registration_supplement` (template name, e.g. "OSF Preregistration", "Qualitative Preregistration", "Replication Recipe (Brandt et al., 2013): Pre-Registration"/"Post-Completion"), `registered_meta` (form answers), `date_registered`, `subjects`, `tags`. `registration_supplement` is NOT a filterable field (400 error today), so filter client-side. Sample hits today: "Expra-Gruppe 2 2026 – Replication Exp. 1 Wirth et al. 2018" (student course replications — a big untapped source), "Replication Data for ..." (false positive: dataset registrations).
- FORRT's own scraper (`C:\Users\OMISTAJA\PsychologyReplication\data\raw\forrt\osf\registries-subproject\rr_scraper_links.R`): reads a manually compiled list of 139 OSF Replication-Recipe registration URLs (`RR_URLs.xlsx`), hits `/v2/registrations/{id}/` and `/contributors/`, honours 100 req/h, extracts `registered_meta.item1..item28` (pre-registration: item1 = "I am trying to replicate the effect from DeWall & Bushman (2009; Exp 2) ...", items 17-23 = closeness answers Exact/Close/Different) and `item29..item37` (post-completion: original effect sizes, links), then codes closeness = sum over 7 items (Exact=2, Close=1, Different=-1). Output `RR_processeddata.csv` = 95 rows x 89 cols (verified). So the yield of the Replication Recipe template route was ~95 usable replications from ~139 links, manually seeded. Automating the seeding via the title filter (5,466 hits) + LLM triage of `registered_meta` text would scale this.
- PCI Registered Reports (`https://rr.peercommunityin.org/`): site blocks bots today (Anubis "Access Denied"); no public API found. Fallback: their recommended RRs get DOIs via the partner journals and Crossref `relation`; harvest via OpenAlex `title.search:"registered report"` + funder/venue filters, or a manual monthly check of the "Recommended" list.
- Venue watchlists (use OpenAlex `primary_location.source.id` + `title.search`): AMPPS (Registered Replication Reports moved from PoPS to AMPPS; OpenAlex title search "registered replication report" = 90 works), Royal Society Open Science (166 FLoRA rows already; hosts Boyce et al. and many RRs), Collabra: Psychology, Meta-Psychology, Nature Human Behaviour, PLOS ONE (had a "Replication" collection), Journal of Experimental Social Psychology, Social Psychology (the 2014 special issue), Comprehensive Results in Social Psychology (RR-only journal), Cortex (RR pioneer), Psychological Science (RRs since 2023), Experimental Psychology, Journal of Open Psychology Data.

## (f) External replication lists to ingest and align

On disk already (verified today):
- `data\raw\forrt\osf\sub-datasets\220627_red_curatescience.xlsx`: 831 rows x 23 cols (id, description, es_original, es_replication, n_original, n_replication, closeness, osf_link, contributors, result, ref_original, ref_replication, tags, subjects, source, notes, es_orig/es_rep parsed values + types). Curate Science is largely already merged into FReD legacy; use for cross-check only.
- `xphil_for_fred.xlsx` 40 rows (XPhi Replicability Project), `core_for_fred.xlsx` 221 rows (CORE JDM), `camereretal2018.xlsx` 21 rows (SSRP), `220621_red_template_osc2015.xlsx` 168 rows (RP:P), `220622_red_is.xlsx` 4 rows; root `osc_2015_rpp_data.csv`, `ml4_full_data.csv`, `manybabies_mb1_data.csv`.
- `docx_parsed_entries.json`: 362 hand-curated famous effects (fields name/description/discipline/status/original_paper/critiques/original_es/replication_es). These 362 are the highest-value SEED SET for citation-based discovery: resolve each `original_paper` to an OpenAlex ID, then run Q1/Q2 — the famous effects are where new replications keep appearing.
External (web/doc):
- OpenMKT full marketing replications: `https://openmkt.org/blog/frm_display/replications-full/` — 47 replications, columns "Original study, Study #, Replication study, Unambiguous success, Replication sample, Original journal, Date replication became available, Project, Notes, Original sample"; CSV export button at page bottom (form-based, scrape with a browser session).
- Data Replicada (Data Colada): `https://datacolada.org/archives/category/data-replicada` — blog posts; each has OSF/Dropbox data, AsPredicted prereg; ~15 posts; hand-curate.
- ReplicationWiki (`replication.uni-goettingen.de`, Semantic MediaWiki): export via `api.php?action=ask&query=[[Category:Replication]]|?...&format=json` or `Special:Ask` CSV; 515+ economics/social-science entries; overlaps I4R/FLoRA reproductions.
- LOOPR = Life Outcomes Of Personality Replication (Soto 2019, `https://osf.io/d3xb7/`, DOI 10.1177/0956797619831612): 78 trait-outcome associations, ~85% replicated; FReD labels these "Soto" (28 studies / 74 replications per `data_sources_analysis.md`).
- FORRT's own list of 25 large-scale projects with OSF links: `https://forrt.org/replication-hub/large-scale-replication-projects/` (RP:P osf.io/ezcuj, CORE osf.io/5z4a8, ML1 osf.io/wx7ck, ML2 osf.io/8cd4r, ML3 osf.io/ct89g, ML4 osf.io/8ccnw, ML5 osf.io/7a6rd, SSRP, ManyBabies manybabies.org, Hagen Cumulative Science osf.io/d7za8, CREP crep-psych.org, Boyce 2023 10.1098/rsos.231240, Boyce 2024 10.31234/osf.io/an3yb, EERP 10.1126/science.aaf0918, MTRP 10.1038/s41562-024-02062-9, SCORE cos.io/score, etc.). Most are already inside FLoRA via source=COS/SCORE/replications; ingest the project-level data files mainly for effect-level numbers (ES, N per site) that FLoRA lacks.
- Psychological Science Accelerator (psysciacc.org, GitHub `psysciacc`): PSA001-PSA008 have public OSF data; not all are replications (PSA001 face ratings, PSA002 object orientation replication, PSA006 trolley). Ingest per-project.
- Alignment rule: match on normalised DOI pair (doi_o, doi_r); fallback fuzzy match on (first author surname, year, title trigram) as FLoRA's `hash` prefixes do; store `source_list` provenance for every pair.

## (g) Scite.ai / PubPeer as signals

- Scite: 800M+ "citation statements" classified supporting / mentioning / contrasting; API is application-only via sales@scite.ai (web); personal plan $20/user/month has no bulk API. Contrasting-citation counts per original DOI would be a strong "replication trouble" signal and a fun game feature, but licensing prevents redistribution. Verdict: optional, paid, not in the core pipeline; the S2 `contexts` route in (c) is the free approximation.
- PubPeer: FAQ says "We (will soon) have an API. Contact us to request a key." (web, `https://pubpeer.com/static/faq`); the Zotero/EndNote integrations use a keyed endpoint that returns comment counts per DOI. Use only as a per-original flag ("has PubPeer discussion") on wiki pages after obtaining a key; never as a discovery source.
- Retraction Watch: now bundled into Crossref (`/works/{doi}` `update-to` and the RW dataset via Crossref Labs) and OpenAlex `is_retracted` (2,198 psych works). Free, include.

## (h) LLM triage stage

Input per candidate: `title`, `abstract` (re-inverted OpenAlex index or OSF description), `publication_year`, `type`, `venue`, the seed original(s) it cites (title/authors/year), up to 5 Semantic Scholar `contexts` sentences (own-paper contexts where available), and the FLoRA inclusion criteria verbatim.

Output schema (use `output_config.format` structured outputs, `strict`):
```json
{
  "is_replication": "yes|no|unclear",
  "replication_type": "direct|close|conceptual|reproduction|multi-site|meta|none",
  "original_doi": "string|null",
  "original_ref_text": "string|null",
  "outcome": "successful|failed|mixed|not_reported|n/a",
  "outcome_quote": "verbatim sentence from abstract supporting outcome",
  "self_identifies_before_results": true,
  "discipline": "social|cognitive|developmental|clinical|personality|neuro|economics|marketing|other",
  "confidence": 0.0,
  "reasons": "one line"
}
```
Rules in the system prompt: quote-only outcome evidence (no inference beyond text), `outcome=not_reported` when the abstract does not characterise results, treat "replication and extension" as replication, treat methods/commentary/meta-science papers as `no`, map `original_doi` only if the abstract or contexts name the target with author-year and the cited seed matches.

Human-review queue design:
- Tiers: auto-accept if `is_replication=yes`, confidence >= 0.9, original resolved to a seed DOI, and outcome quoted -> goes to `curated/candidates_accepted.csv` pending weekly human spot-check (10%). Review queue if confidence 0.5-0.9 or original unresolved. Auto-reject < 0.5 but keep in `rejected.parquet` for recall audits.
- Queue store: a `candidates` table (Supabase or SQLite) with columns candidate_id, doi_r, doi_o, source_method (openalex_cites | openalex_title | osf_preprint | osf_registry | s2_context | external_list), llm_json, llm_model, llm_version, status (new|accepted|rejected|needs_review|submitted_to_forrt), reviewer, reviewed_at, notes. A small review UI (the wiki's admin page) shows title, abstract with the quoted outcome sentence highlighted, the seed original, contexts, and buttons Accept / Fix original / Reject / Defer. Every decision is an append-only event so the pipeline is reproducible.

Cost per 1,000 candidates (prices from the claude-api skill, cached 2026-06-24; first-party API rates):
- Assume ~1,500 input tokens per candidate (title+abstract ~450, contexts ~300, seed metadata ~150, shared system prompt ~600 which is cacheable) and ~150 output tokens.
- `claude-haiku-4-5` ($1 / $5 per MTok): 1.5M in = $1.50 + 0.15M out = $0.75 -> $2.25 per 1,000; with Message Batches (50% off) ~$1.13.
- `claude-sonnet-5` ($2 / $10): $3.00 + $1.50 = $4.50 per 1,000; batch ~$2.25.
- `claude-opus-5` ($5 / $25): $7.50 + $3.75 = $11.25 per 1,000; batch ~$5.63.
- Prompt caching of the 600-token system prompt cuts input by ~40% further. A full first pass over ~10,000 candidates (title-pass citations + field titles + preprints + registries) therefore costs roughly $11 (Haiku, batch) to $56 (Opus, batch); the weekly increment (~100-300 candidates) is cents. Recommendation: Sonnet 5 via Batches for the bulk pass with `thinking: {type:"adaptive"}` and `output_config.effort: "low"`; escalate `unclear` cases (expected ~15%) to Opus 5 at effort `high`. Do not use Haiku for outcome classification — outcome wording ("partially replicated", "smaller but significant") is where cheap models drift.

## (i) Weekly incremental crawl design

Layout (fits the raw -> normalized -> curated -> site layers):
```
data/discovery/
  state/
    openalex_cites.json        {seed_id: {last_run, cited_by_count_seen, cursor}}
    openalex_title.json        {last_from_publication_date}
    osf_preprints.json         {last_date_published}
    osf_registrations.json     {last_date_registered}
    s2_contexts.json           {doi_o: {offset, citationCount_seen}}
    external_lists.json        {list_name: sha256 of last download}
  raw/YYYY-WW/                 one JSONL per source per week (immutable)
  candidates.sqlite            dedup + LLM results + review events
  reports/YYYY-WW.md           auto-generated crawl summary
```
Steps (one command `discover --week`):
1. Seeds = union of FLoRA `doi_o`, the 362 curated originals, and any accepted candidate's `original_doi`. Resolve to OpenAlex IDs once; cache.
2. OpenAlex cites-pass: for seeds whose current `cited_by_count` > `cited_by_count_seen`, run Q1 (title) and, if cited_by_count < 300, Q2 (abstract), with `from_publication_date` = last run minus 30 days (OpenAlex backfills). Batches of 100 seed IDs per call. ~30-60 calls/week; cost < $0.10.
3. OpenAlex field-pass Q3/Q4 with `from_publication_date` (~40-60 new works/week).
4. OSF preprints + registrations with `filter[date_published][gte]` / `filter[date_registered][gte]`; 100 req/h keyless is enough (~3-5 pages/week).
5. Semantic Scholar contexts: only for seeds with citation deltas; 1 rps with key.
6. External lists: re-download monthly, hash-compare, diff.
7. Dedup: normalise DOIs (lowercase, strip `https://doi.org/`, strip PsyArXiv `_vN`), collapse preprint<->journal via Crossref/OSF `relation`; drop any (doi_o, doi_r) pair present in current FLoRA (re-download FLoRA weekly — it grows ~3-5 rows/week) or already decided in `candidates.sqlite`.
8. LLM triage of new candidates (Batches API), write results, route to queue.
9. Human review session; accepted rows enter `curated/overlay_replications.csv` (the wiki build merges FLoRA + overlay).
10. Monthly: export accepted rows in FORRT submission format (see j) and log the submission.
Idempotency: every step is keyed by (source, week); rerunning a week rewrites only that week's raw files.

## (j) Contribution path back to FORRT

- Submission page: `https://forrt.org/replication-hub/submit/` ("If you have conducted a replication study that has not yet been included, please submit it using the form below"; use the References Annotator `https://forrt.org/FReD/` / FReD Annotator Shiny app first to check duplicates). FLoRA page (`https://forrt.org/replication-hub/flora/`) says for contributing/using data "reach out to us" (FORRT replication-hub team; the FReD paper authors Röseler et al.; GitHub `forrtproject/FReD`). Bulk contributions in practice go as a spreadsheet + email/GitHub issue, not the one-at-a-time web form.
- Template (verified): `C:\Users\OMISTAJA\PsychologyReplication\data\raw\forrt\osf\sub-datasets\datasubmission_template.xlsx`, sheets `data`, `variables`, `closeness_scoring`. Required columns (sheet `data`, row 2 = variable names, row 1 = descriptions):
  `id` (row number, 1 per replication study), `description` (short description of the main phenomenon/hypothesis), `es_original` (converted to Pearson r), `es_replication` (Pearson r), `n_original`, `n_replication`, `closeness` (Brandt et al. 2014 replication-recipe score; sheet `closeness_scoring` gives 7 dropdown items scored exact=2/close=1/different=-1), `osf_link` (OSF project or post-completion report), `contributors` (last names, comma-separated), `result` (informative failure to replicate | informative success to replicate | inconclusive | practical failure to replicate), `ref_original` (full APA7 incl. study number), `ref_replication` (full APA7 incl. study number), `tags` (up to 10), `subjects` (field of the original), `source` (website, public dataset, OSF registries, personal correspondence, ...), `notes`.
- Our overlay schema should therefore capture, beyond the DOI pair, the FReD-required numerics (r-converted effect sizes, Ns, closeness items) so accepted candidates can be exported to this template without rework. For FLoRA-only (no statistics) contributions the minimum is doi_o, doi_r, outcome, outcome_quote, outcome_quote_source — the exact FLoRA columns.

## Ranking of methods (precision / recall / cost)

| Rank | Method | Precision (pre-LLM) | Recall for published replications | Cost | Notes |
|---|---|---|---|---|---|
| 1 | OpenAlex `cites:{seed}` + title "replicat*" | ~35-50% raw; >90% after LLM | very high for direct replications of KNOWN originals (all Kidd&Castano replications found) | ~$0.001/call, 30 calls/week | Best precision/recall/cost; needs seed list (FLoRA 2,589 + 362 curated) |
| 2 | OpenAlex field-32 title search "replication" | ~40-60% | high for anything self-labelled; finds replications of originals NOT in seeds | 4,188 works 2015-2026, ~8/week | This is FORRT's own method; we add topic subfields + LLM |
| 3 | OSF Preprints (PsyArXiv) title/abstract | ~60% | earliest signal; 623 total | 100 req/h keyless | Adds 6-18 month lead; needs preprint->journal linking |
| 4 | OSF Registrations title "replication" + registered_meta | ~30% (many datasets/course projects) | unique coverage of unpublished/student replications (CREP, Expra courses) | 5,466 hits, 100 req/h | Mirrors FORRT scraper (95 rows from 139 links); needs LLM on registered_meta |
| 5 | OpenAlex `cites:` + abstract search | ~10-20% | very high | ~$0.001/call but 10x candidates | Only for low-citation seeds |
| 6 | Semantic Scholar citation contexts | ~70% when keyword matches; only ~2% of citations match | modest (full-text coverage ~45%) | free w/ key, 1 rps | Best for OUTCOME evidence and "community verdict", not discovery volume |
| 7 | External lists (OpenMKT, Data Replicada, ReplicationWiki, LOOPR, PSA, ML1-5, docx 362) | ~95% | narrow, mostly already in FLoRA | manual/monthly | Value = effect-level numbers + curation quality, not new pairs |
| 8 | Crossref query.title + ISSN whitelist | ~20% | medium | 3 req/s polite | Dominated by OpenAlex; keep for DOI/relation/retraction metadata |
| 9 | Venue watchlists (AMPPS RRR, RSOS, Collabra, Meta-Psychology, PCI RR) | ~80% | narrow | manual/OpenAlex source filter | Cheap add-on to method 2 |
| 10 | Scite contrasting citations / PubPeer | high as signal | not a discovery source | paid / keyed | Signal layer only |

Overall pipeline expectation: first full pass yields on the order of 6,000-8,000 title-level candidates from method 1 + ~4,000 from method 2 + ~600 preprints + a few hundred registry hits; after dedup vs FLoRA and LLM triage, plausibly 1,500-3,000 new (doi_o, doi_r) pairs for human review at an LLM cost of roughly $10-60. Weekly steady state: 100-300 candidates, cents of API cost, ~1 hour of human review.
