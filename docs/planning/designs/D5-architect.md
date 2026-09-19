# D5 — Systems architecture: repo layout, pipeline, stack, anti-rot discipline

Designer: D5 (systems architect). Date: 2026-09-07. Inputs: BRIEF.md, _DIGEST.md, U1/U3/U4/U5/U6/U7 reports, plus direct verification on disk (secrets grep, id-format inspection of FReD_2.4.1 `Data` and the COS archive, installed-tooling check). Every number below is either quoted from a reader report or measured in this session; nothing is estimated without saying so.

Status of this file: DESIGN (raw material for the integrator agent). Sections are ordered by how early they are needed: decisions -> layout -> contracts -> ids/urls -> build/tests/CI -> migration -> docs -> anti-rot -> Phase-1 modules.

---

## 0. Decisions in one screen

| Area | Decision | One-line reason |
|---|---|---|
| Pipeline language | Python 3.13, package `pipeline/` with a Typer CLI | Already installed and proven on the data: pandas 2.3.0, pydantic 2.12.5, duckdb 1.4.4, openpyxl 3.1.5, pyarrow 20, rapidfuzz 3.14, httpx 0.28, typer 0.21, jsonschema 4.24, pytest 8.4 (verified in this session). Stats (7 FReD criteria) port 1:1 to numpy and have an oracle in the COS archive (`statistical_success`, `r_o`, `r_r`). |
| DataFrames | pandas for xlsx/csv ingest + row-wise transforms; DuckDB for joins, integrity SQL, notebooks; Parquet as the interchange format between stages | 5k-row tables; the win is not speed but *declarative integrity checks* (`SELECT ... WHERE effect_id NOT IN (...)`) that read the same Parquet the site consumes. |
| Contracts | pydantic v2 models -> JSON Schema (exported to `pipeline/schemas/*.json`) -> TypeScript types for the site (`json-schema-to-typescript`) | One source of truth; a contract change fails both the Python export and the Astro loader. |
| Env/locking | `uv` (pyproject.toml + uv.lock); `requirements.lock` exported for people without uv | Reproducible; the current `.venv` is Python 3.12 (`.venv/lib/python3.12`) while the system is 3.13 — exactly the drift we are eliminating. |
| Site | Astro 7, static output, content-layer loaders reading `data/build/` | Already chosen (U4); cheapest path to ~10k typed pages. |
| Islands | Preact (+ @preact/signals) | ~10 KB runtime (U4 measured 10,470 B), TSX, and charts written as Preact components render statically by default and hydrate only where marked — one chart codebase for static and interactive. Svelte would be equally small but adds a second component syntax next to `.astro`; React is 3-4x heavier for no gain. |
| Search | Pagefind for full text over effect/project/topic pages; MiniSearch (lazy, sharded JSON) for entity typeahead (effects, papers, persons, DOIs) | Pagefind loads only the index chunks a query touches; MiniSearch gives fielded autocomplete. Never inline an index into page props again (U4: 1.72 MB explore.html). |
| Charts | Build-time SVG (Preact components rendered by Astro at build); exactly one hydrated island (the explorer scatter) reuses the same components; no Chart.js/Plotly/D3 bundle (scales are ~40 lines of TS) | Forest plots, timelines, scatter, bars are static per page; print-quality; zero JS for 95% of pages. |
| Hosting | **GitHub Pages** (Actions deploy) with a custom domain or a user-site repo name so there is no `base` path; Cloudflare optionally as DNS/CDN in front. Cloudflare Pages rejected as primary. | Cloudflare Pages caps a deployment at 20,000 files. Estimated output (Section 5.4): ~10.5k HTML + ~2.8k Pagefind fragments + ~4.5k JSON = ~18k files today and growing weekly. GitHub Pages has no file-count cap (1 GB soft size limit; our dist is ~30-60 MB). A file-budget test still runs so a migration to any capped host stays possible. |
| Supabase | Optional, Phase 3, only for crowd data (game guesses, forecasts on unreplicated effects); never on the read path | The site must build and function with zero services; crowd aggregates are pulled into `data/build/crowd.json` by a pipeline command, so the site stays static. |
| Discovery store | DuckDB file + Parquet under `data/discovery/` (gitignored) and append-only JSONL decision logs under `data/curated/decisions/` (committed) | Human decisions are the valuable, tiny part -> git. Candidate pools are large and regenerable -> not git. |
| `data/build` in git | **Not committed**. Only `data/build/SUMMARY.json` (row counts, hashes, source manifest digest) is committed as the baseline for the "counts never silently drop" test. Full bundles are attached to GitHub Releases (`data-YYYY-MM-DD`) by CI. | Generated files in git invite hand edits (the exact rot the brief forbids) and bloat history. |
| `data/raw` in git | MANIFEST.json + small text files (codebooks, .qmd, .R, .md, CITATION) committed; re-fetchable binaries > 2 MB gitignored and restored by `pipeline fetch --verify`; irreplaceable local assets (2.4.1 xlsx 5.5 MB, the docx 1.7 MB, docx_parsed_entries.json) committed once because OSF returned 502/1x1 placeholders in the past (U4, U5). | Reproducible without a 500 MB/year history. |

---

## 1. Why Python + pandas + pydantic + DuckDB (and not the alternatives)

1. **The data is spreadsheet-shaped and small**: FReD 2,164 x 56 (+ COS archive 2,164 x 44), FReD 2.4.1 4,659 data rows x 100 across 20 sheets, FLoRA 2,815 x 35. pandas + openpyxl read all of it in seconds; Polars is not installed and buys nothing at this size.
2. **The statistics have a reference implementation in R** (`fred-r-package/replication_outcomes.R`, `effect_size_transformations.R`). Porting to numpy is a few hundred lines, and the COS archive provides a test oracle: 733 rows with precomputed `r_o` and `r_r`, and 901 rows with `statistical_success` (446 TRUE / 455 FALSE). A TypeScript pipeline (the old `wiki/scripts/normalize-data.ts`) had no stats stack and silently dropped the outcome columns (U4). Running R in CI is possible but adds a second toolchain for one module; we port and test against the oracle instead.
3. **pydantic v2** gives validated records, JSON Schema export for free, and typed provenance blocks; the site's zod/TS types are generated from that schema rather than hand-mirrored (the old `schema.ts` drifted from its own curated JSON — U4).
4. **DuckDB** reads Parquet/CSV/JSON in place, so the integrity tests, the notebooks, and the discovery dedup all query the same files with SQL and no server. It replaces the 60 ad hoc "groupby and dump a csv" scripts in the root (U3 §2).
5. **Everything is already installed** (verified: pandas 2.3.0, pydantic 2.12.5, duckdb 1.4.4, openpyxl 3.1.5, pyarrow 20.0.0, rapidfuzz 3.14.1, httpx 0.28.1, typer 0.21.1, jsonschema 4.24.0, pytest 8.4.1 on Python 3.13.3; Node v22.15.0).

Rejected: Node-only pipeline (no stats, xlsx pain, U4's failure), R-only (owner's environment has no R toolchain on record; the site build is Node anyway), a database-first design (Supabase/Postgres as source of truth) because it makes the build depend on a service and the data is versioned files by nature.

---

## 2. Repository layout (precise)

```
PsychologyReplication/                     # becomes the git repo root
  README.md                                # 1 screen: what, build command, layer law, links to docs/
  LICENSE-CODE (MIT)  LICENSE-DATA (CC-BY-4.0 + FORRT attribution)  CITATION.cff
  CONTRIBUTING.md                          # curation workflow + PR rules
  .gitignore  .gitattributes  .editorconfig  .env.example  .pre-commit-config.yaml
  .gitleaks.toml                           # secrets scan config
  pyproject.toml  uv.lock  requirements.lock
  package.json  package-lock.json          # root scripts only: build, dev, test, refresh
  .github/workflows/  ci.yml  refresh.yml  deploy.yml  discover.yml
  .claude/settings.local.json              # keep (owner's tool settings)

  data/
    raw/                                   # LAYER 1: immutable snapshots. Never edited, never read by the site.
      MANIFEST.json                        # union manifest (moved up from data/raw/forrt/MANIFEST.json; schema in 3.11)
      forrt/                               # exists today (fred-data/, fred-r-package/, osf/)
      local/                               # one-off local assets that are not re-downloadable
        forrt-rr-list/                     # Psychology Replications (1).docx, docx_parsed_entries.json, psychology_replications.csv/.json
        llm-suggestions/                   # effect_names_2025-12.csv (2 cols from fred_enriched.csv), xy_extraction_2025-12.json — provenance: machine-suggested, unreviewed
        forrt-web/                         # flora_explorer_disciplines.json (from wiki/data/sources/disciplines.json)
      third-party/                         # public, re-downloadable; pinned URLs in MANIFEST
        rpp2015/  ml4/  manybabies-mb1/  cogatlas/
    cache/                                 # LAYER 1b: API response caches keyed by DOI/ID; gitignored; MANIFEST-cache.json committed
      openalex/  crossref/  s2/  abstracts/ legacy-2025-12/   # the five big JSON files from Dec 2025 land here as-is
    curated/                               # LAYER 3: human-authored YAML/CSV overlays. Only humans (or a reviewed PR) edit these.
      effects/*.yaml                       # one per named effect: names, aliases, status verdict prose, merges, links to originals
      projects/*.yaml                      # ML1..5, OSC2015, RRR1..10, SSRP, CORE, OpAQ, XPhi, PSA00x, Boyce2023, ...
      registry/effect_ids.csv              # append-only id ledger (Section 4.3)
      registry/project_ids.csv
      vocab/discipline_map.csv  es_type_map.csv  pval_type_map.csv  outcome_map.csv  subfield_overrides.csv
      links/docx_title_to_doi.csv          # resolved (title -> DOI) with method + confidence + reviewer
      overlays/replications.csv            # accepted discovered pairs in FLoRA column set (+ our provenance cols)
      decisions/*.jsonl                    # append-only review events (candidate_id, decision, reviewer, ts, note)
      game/exclusions.csv  game/blocklist_projects.csv
    build/                                 # LAYER 4: generated. gitignored except SUMMARY.json. Rebuilt by `pipeline build`.
      SUMMARY.json                         # committed baseline (row counts per table, sha256 of inputs, pipeline version)
      normalized/*.parquet                 # stage outputs (fred_attempts, flora_pairs, legacy_attempts, ...)
      bundle/*.json  bundle/*.parquet      # the site bundle (Section 3.10)
      reports/*.md                         # build report, merge report, discovery weekly report
    discovery/                             # LAYER 2b: candidate pools + crawl state; gitignored; regenerable
      state/*.json  raw/YYYY-WW/*.jsonl  candidates.duckdb  seed-pools/   (U7 §i layout adopted verbatim)

  pipeline/                                # Python package (Section 9)
    __init__.py  __main__.py  cli.py  config.py  models.py  ids.py  manifest.py  log.py
    fetch/  normalize/  registry/  score/  enrich/  game/  discover/  export/  validate/
    schemas/*.json                         # generated from models.py; committed; test asserts freshness
  tests/                                   # pytest; fixtures are tiny CSV excerpts, not the full files
  notebooks/                               # dated experiments: YYYY-MM-DD-slug/ with README.md; never imported by pipeline/
  site/                                    # Astro 7 (Section 5)
  docs/                                    # Section 7
  archive/                                 # Section 6: the old mess, secrets scrubbed, with README.md index
  _planning/                               # this planning round; moves to docs/decisions/planning-2026-09/ when the build starts
```

Layer law (enforced by tests, Section 5.6): `site/` imports only from `data/build/bundle/`; `pipeline/` writes only to `data/build/`, `data/cache/`, `data/discovery/`; nothing writes to `data/raw/` except `pipeline fetch`; nothing but humans write to `data/curated/` except `pipeline registry` (append-only ledgers) and `pipeline review` (append-only decisions).

---

## 3. Data contracts (pydantic v2 -> JSON Schema)

Conventions: all ids are strings; all DOIs stored in canonical form (Section 4.1); every inferred/derived field lives inside a `Provenance`-tagged wrapper; nullable means "unknown", never "not applicable" (use enums for that). Field names follow FORRT where FORRT has a name (`doi_o`, `doi_r`, `es_value_o`, `reported_success`, `outcome_quote`) so contribute-back is a column projection.

```python
# pipeline/models.py  (excerpt: shapes, not full docstrings)
from typing import Literal, Optional
from pydantic import BaseModel, Field, HttpUrl

Source = Literal["fred_current","fred_cos_archive","fred_legacy_2.4.1","flora","forrt_rr_docx",
                 "forrt_reversals_sheet","openalex","crossref","s2","osf","curated","llm","discovery"]
ReviewState = Literal["imported","machine","candidate","reviewed","disputed"]

class Provenance(BaseModel):
    source: Source
    source_id: Optional[str] = None      # row id / sheet id / API id in that source
    retrieved: Optional[str] = None      # ISO date of the snapshot (from MANIFEST)
    method: Optional[str] = None         # e.g. "rapidfuzz.ratio>=90", "crossref.query.bibliographic", "llm:claude-sonnet-5@2026-06"
    confidence: Optional[float] = None   # 0..1 for inferred values
    review_state: ReviewState = "imported"
    reviewer: Optional[str] = None
    note: Optional[str] = None

class Label(BaseModel):                  # any inferred label (topic, discipline, effect name, outcome)
    value: str
    prov: Provenance

class Paper(BaseModel):
    id: str                               # "p:" + doi_key, or "p:url:" + sha1(url)[:12] when no DOI (FReD has 197 doi_r-less rows; FLoRA 200)
    slug: str                             # URL-safe (Section 4.2)
    doi: Optional[str]                    # canonical DOI
    doi_key: Optional[str]                # match key ('//' collapsed, see 4.1)
    doi_hash3: Optional[str]              # first 3 hex of md5(doi) — FORRT/Zotero-API compatible
    url: Optional[str]                    # url_r/url_o when no DOI
    title: str
    authors: list["AuthorRef"]            # from FORRT JSON author arrays; person_id resolved later
    journal: Optional[str]; year: Optional[int]; volume: Optional[str]; issue: Optional[str]; pages: Optional[str]
    apa_ref: Optional[str]; bibtex: Optional[str]
    language: Optional[str]
    oa_url: Optional[str]; is_retracted: Optional[bool]; retraction: Optional["RetractionInfo"]
    openalex_id: Optional[str]; abstract: Optional[Label]      # abstract carries provenance (pubmed/openalex/crossref/s2)
    topics: list[Label] = []              # OpenAlex topics/subfields; curated overrides carry source="curated"
    roles: list[Literal["original","replication","reproduction","meta","both"]]
    prov: list[Provenance]

class AuthorRef(BaseModel):
    family: str; given: Optional[str]; sequence: Optional[str]; person_id: Optional[str]; orcid: Optional[str]

class OriginalStudy(BaseModel):
    id: str                               # "os:" + doi_key [+ ":" + study_norm]
    paper_id: str
    study_label: Optional[str]            # raw study_o ("1a", "Experiment 1")
    study_norm: Optional[str]             # normalized ("1a")
    claim_text: Optional[str]             # claim_text_o (FReD, 98.5% filled) — the game card text source
    claim_page: Optional[str]
    n: Optional[float]
    es: Optional["EffectSize"]            # raw + converted r + CI
    p: Optional["PValue"]
    design: Optional["DesignFlags"]       # nested, interaction (curated/LLM), within/between, preregistered (prereg_o)
    effect_ids: list[str] = []
    prov: list[Provenance]

class EffectSize(BaseModel):
    value_raw: Optional[str]              # verbatim ("F(1, 37) = 6.40")
    value: Optional[float]; type_raw: Optional[str]; type: Optional[str]   # normalized via es_type_map
    r: Optional[float]; r_method: Optional[str]                            # converted per effect_size_transformations.R; None if not convertible
    ci_lower: Optional[float]; ci_upper: Optional[float]; ci_level: Optional[float]
    prov: Provenance

class PValue(BaseModel):
    value: Optional[float]; relation: Literal["=","<",">","<=",">=","unknown"]; tails: Optional[Literal[1,2]]; prov: Provenance

class DesignFlags(BaseModel):
    nested: Optional[bool]; preregistered: Optional[bool]; prereg_url: Optional[str]
    interaction: Optional[Label]; sample_type: Optional[Label]; online: Optional[Label]

class Attempt(BaseModel):                 # effect-level replication attempt (FReD/legacy grain)
    id: str                               # "att:" + sha1(attempt_key)[:12]  (Section 4.4)
    attempt_key: str                      # human-readable composite (doi_o_key|id_r_key|study_o|study_r|effect_ordinal)
    pair_id: str                          # -> ReplicationPair
    original_id: str                      # -> OriginalStudy
    effect_id: Optional[str]              # -> Effect (None for FLoRA-only pairs)
    replication_paper_id: str
    project_id: Optional[str]
    study_label_r: Optional[str]
    n: Optional[float]; es: Optional[EffectSize]; p: Optional[PValue]; design: Optional[DesignFlags]
    author_overlap_pct: Optional[float]   # independence
    closeness: Optional["Closeness"]      # legacy Brandt items (163-180 filled) + legacy `closeness` total
    power: Optional[float]                # legacy (833 filled)
    reported: Optional["ReportedOutcome"] # authors' own verdict (FReD reported_success / legacy result / FLoRA outcome)
    criteria: Optional["Criteria"]        # our computed 7 criteria (only when r on both sides + Ns)
    verdict: "Verdict"                    # summary used by pages and the game
    ids: "ExternalIds"                    # every upstream id this row had
    granularity: Literal["effect","paper"]
    prov: list[Provenance]

class ExternalIds(BaseModel):
    fred_id: Optional[str]; fred_id_old: Optional[str]; cos_entry_id: Optional[int]; cos_effect_id: Optional[int]
    legacy_id: Optional[str]; legacy_rowid: Optional[str]; flora_row: Optional[int]; osf_link: Optional[str]

class Closeness(BaseModel):
    instructions: Optional[int]; measures: Optional[int]; stimuli: Optional[int]; procedure: Optional[int]
    location: Optional[int]; remuneration: Optional[int]; participants: Optional[int]; exclusions: Optional[int]
    language: Optional[int]; nationality: Optional[int]; total: Optional[int]; same_design: Optional[bool]; same_test: Optional[bool]
    prov: Provenance

class ReportedOutcome(BaseModel):
    outcome: Literal["successful","failed","mixed","statistically successful but flawed","descriptive only",
                     "uninformative","informative failure","inconclusive","practical failure","not_reported"]
    outcome_norm: Literal["success","failure","mixed","other"]
    quote: Optional[str]; quote_source: Optional[str]; prov: Provenance

class Criteria(BaseModel):                # port of replication_outcomes.R; each field None when not computable
    significance_r: Optional[Literal["success","failure","OS not significant"]]
    significance_agg: Optional[bool]; consistency_ci: Optional[bool]; consistency_pi: Optional[bool]
    homogeneity: Optional[bool]; homogeneity_significance: Optional[str]; small_telescopes: Optional[bool]
    r_o: float; r_r: float; n_o: float; n_r: float; agreement: Optional[float]   # share of computable criteria saying success
    version: str                          # e.g. "fred-r-port-1.0" so recomputation is traceable

class Verdict(BaseModel):
    label: Literal["success","failure","mixed","other","unknown"]
    basis: Literal["reported","criteria","curated","none"]
    disagreement: bool                    # reported vs criteria disagree (U5: 93.3% agree FReD vs FLoRA; show when not)
    prov: Provenance

class ReplicationPair(BaseModel):         # paper-level relation = FLoRA grain = the discovery unit
    id: str                               # "pair:" + sha1(doi_o_key + "|" + id_r_key)[:12]
    original_paper_id: str; replication_paper_id: str
    type: Literal["replication","reproduction"]
    outcome: Optional[ReportedOutcome]
    flora_source: Optional[str]; flora_filter_flags: list[str] = []   # from output_flora_filter_log (invalid_identifier, boyce_exclusion, ...)
    attempt_ids: list[str] = []
    in_fred: bool; in_flora: bool; in_legacy: bool; in_overlay: bool
    prov: list[Provenance]

class Effect(BaseModel):                  # the spine
    id: str                               # "fx:" + slug (Section 4.3)
    slug: str
    name: Label                           # canonical name with provenance (curated > reversals sheet > legacy effect > LLM suggestion)
    aliases: list[Label] = []
    description: Optional[Label]          # FReD description / docx description
    discipline: Optional[Label]; disciplines: list[Label] = []
    topics: list[Label] = []              # OpenAlex-derived via original papers + curated tags
    original_ids: list[str]; attempt_ids: list[str]; pair_ids: list[str]; project_ids: list[str] = []
    status: Optional[Label]               # docx status (replicated/mixed/not replicated/reversed) — curated overlay
    curated: Optional["EffectCuration"]   # prose: current understanding, critiques, evidence timeline (from YAML)
    stats: "EffectStats"                  # computed: n attempts, n success/failure/mixed, r pooled, shrinkage, years
    prov: list[Provenance]

class EffectCuration(BaseModel):
    summary: Optional[str]; critiques: Optional[str]; timeline: list["TimelineEvent"] = []
    lenses: Optional[dict]                # {author_reports, numerical_records, design_differences} free-form markdown
    citations: list[str] = []; updated: Optional[str]; reviewer: Optional[str]

class Project(BaseModel):
    id: str; slug: str; name: str; kind: Literal["many-labs","rrr","reproducibility-project","accelerator","student","registry","other"]
    year: Optional[int]; osf_url: Optional[str]; paper_ids: list[str]; attempt_ids: list[str]; pair_ids: list[str]
    source_labels: list[str]              # legacy `source` values that map here (ML1, OSC 2015, RRR1..)
    raw_data: Optional[dict]              # pointers to third-party per-site files (rpp2015, ml4, mb1) for drill-down
    prov: list[Provenance]

class Person(BaseModel):
    id: str; slug: str; family: str; given: Optional[str]; orcid: Optional[str]; openalex_id: Optional[str]
    paper_ids: list[str]; roles: dict[str,int]      # {"original": n, "replication": n}
    prov: list[Provenance]

class Topic(BaseModel):
    id: str                               # "topic:T10234" (OpenAlex topic) | "subfield:3202" | "disc:social-psychology" | "tag:anchoring"
    kind: Literal["openalex_topic","openalex_subfield","discipline","tag","cogatlas"]
    name: str; parent_id: Optional[str]; effect_ids: list[str]; paper_ids: list[str]; prov: list[Provenance]

class GameItem(BaseModel):
    id: str                               # "gi:" + attempt_id or pair_id
    attempt_id: Optional[str]; pair_id: str; effect_id: Optional[str]
    card: "GameCard"                      # what the player sees before answering
    answer: Literal["success","failure","mixed"]
    answer_prov: Provenance
    reveal: "GameReveal"                  # three lenses + quote + links
    cues: dict                            # p_bucket, n_o, es_type, interaction flag, discipline, year, prereg, journal — for progressive-hint modes
    difficulty: Optional[float]           # from crowd data when available
    base_rate_stratum: str                # for stratified sampling (~50% base rate per session)
    excluded: bool; exclude_reason: Optional[str]
    version: str                          # bundle version for score comparability

class GameCard(BaseModel):
    text: str; year: int; journal: Optional[str]; n: Optional[float]; discipline: Optional[str]; stats_line: Optional[str]

class GameReveal(BaseModel):
    outcome_quote: Optional[str]; quote_source: Optional[str]; r_o: Optional[float]; r_r: Optional[float]
    criteria_agreement: Optional[float]; closeness_total: Optional[int]; independent_team: Optional[bool]
    effect_slug: Optional[str]; paper_slug_o: str; paper_slug_r: str; citations_by_year: Optional[list[list[int]]]

class Candidate(BaseModel):               # discovery unit (U1/U7): the pair, not the paper
    id: str                               # "cand:" + sha1(doi_r_key + "|" + (doi_o_key or ""))[:12]
    doi_r: Optional[str]; url_r: Optional[str]; doi_o: Optional[str]; original_ref_text: Optional[str]
    title_r: str; abstract_r: Optional[str]; year_r: Optional[int]; venue_r: Optional[str]; openalex_id_r: Optional[str]
    source_method: Literal["openalex_cites","openalex_title","osf_preprint","osf_registry","s2_context","external_list","crossref","manual"]
    seed_ids: list[str] = []              # which seed originals led here
    contexts: list[str] = []              # S2 citation sentences
    llm: Optional["LlmTriage"]            # strict JSON (U7 §h schema), with model id + version + prompt hash
    status: Literal["new","auto_accepted","needs_review","accepted","rejected","deferred","submitted_to_forrt","in_flora"]
    decisions: list["Decision"] = []
    first_seen_week: str; last_seen_week: str
    in_flora: bool                        # recomputed weekly against the refreshed FLoRA

class Decision(BaseModel):
    ts: str; reviewer: str; action: Literal["accept","reject","defer","fix_original","note"]; doi_o: Optional[str]; note: Optional[str]

class Bundle(BaseModel):                  # data/build/bundle/index.json — the site's manifest
    version: str                          # "YYYY-MM-DD.N" (+ git sha)
    built_at: str; pipeline_version: str; sources: dict[str, dict]     # {"flora": {"retrieved": ..., "sha256": ..., "rows": 2815}, ...}
    counts: dict[str, int]                # effects, papers, originals, attempts, pairs, projects, persons, topics, game_items, candidates
    files: dict[str, str]                 # table name -> filename + sha256
    license: str; citation: str
```

### 3.10 The site bundle (`data/build/bundle/`)
One JSON array per contract (`effects.json`, `papers.json`, `originals.json`, `attempts.json`, `pairs.json`, `projects.json`, `persons.json`, `topics.json`, `game_items.json`, `candidates_public.json`) + `index.json` (Bundle) + Parquet mirrors of each + `search/entities-{type}.json` shards for MiniSearch. Cross-references are ids only; the site's loaders build lookup maps. Text fields are already HTML-entity-decoded and JATS-stripped (FReD is not: U5 §9.6).

### 3.11 MANIFEST schema (`data/raw/MANIFEST.json`, extends the existing file)
`{retrieved_on, license, citation_file, upstream{...}, files:[{path, bytes, sha256, source_url, retrieved, mutable: bool, notes}]}` — the existing FORRT manifest already has `path/bytes/sha256/source_url`; add `retrieved` per file and `mutable` (true for FORRT outputs that change weekly, false for version-history and local assets). `data/cache/MANIFEST-cache.json` uses the same shape plus `key_space` ("doi"/"openalex_id") and `n_keys`.

---

## 4. Identity rules

### 4.1 DOI normalization (port `openalex_utils.normalize_doi`, extend with FORRT's `clean_doi` rules)
`normalize_doi(s) -> Optional[str]`: strip whitespace; percent-decode; strip `https://`, `http://`, `dx.`, `doi.org/`, `doi:` prefixes (case-insensitive); cut at first whitespace; strip FORRT-observed scraping garbage ("digital object identifier", "get rights and content", "[Opens in new window]"); strip trailing `.,;)`; lowercase; must start with `10.` else return None (pseudo-DOIs like `korbmacher_2022` become `url`-type ids, not DOIs). `doi_key(doi)` = canonical DOI with `//` collapsed to `/` (FORRT's own dedup treats `10.1037//0022-3514.68.5.793` and `10.1037/0022-3514.68.5.793` as the same paper — U5 §3.4) and PsyArXiv `_vN` version suffix removed. We store both: `doi` (as published) and `doi_key` (for joins). `doi_hash3(doi)` = first 3 hex chars of md5(doi) exactly as FORRT computes `doi_o_hash`, so our `/api/v1/doi/{hash3}.json` is Zotero-plugin compatible.

### 4.2 Slugs (URL segments)
Windows-illegal and URL-hostile characters (`< > : " / \ | ? *`, `(`, `;`) occur in DOIs (U4 lesson). `paper_slug(doi_key)`: replace `/` with `_`, then replace any run of characters outside `[a-z0-9._-]` with `-`, trim `-`. Example: `10.1126/science.1239918` -> `10.1126_science.1239918`; `10.1002/(sici)1099-0771(199912)12:4<275::aid-bdm323>3.0.co;2-m` -> `10.1002_-sici-1099-0771-199912-12-4-275-aid-bdm323-3.0.co-2-m`. Collisions are checked at build; on collision append `-` + sha1(doi_key)[:6]. Papers without DOI: `u-` + sha1(url)[:12]. `effect_slug(name)`: ASCII-fold, lowercase, non-alnum -> `-`, max 80 chars, uniqueness guaranteed by the ledger (4.3). Project/person/topic slugs likewise; OpenAlex ids (`T10234`, `A5023...`) are used verbatim for topics/persons when available.

### 4.3 Effect ids: the ledger, not a formula
Effects come from three name sources (legacy `effect` column: 443 names on 2,623 rows; `Reversals Effects` sheet: 583 rows; docx: 362; overlap docx/sheet 218 exact) plus unnamed FReD effect rows (current FReD has no effect-name column). Rules:
1. `data/curated/registry/effect_ids.csv` (`effect_id, slug, key_kind, key, created, created_by, merged_into`) is append-only. `pipeline registry` assigns an id the first time it sees a key and never reuses or renumbers. Keys: `name:<normalized name>` for named effects; `study:<doi_o_key>:<study_norm>:<description_hash8>` for unnamed FReD effect rows; merges are recorded as `merged_into` (never deletion), and the old slug becomes a redirect.
2. Named-effect slugs are readable (`fx:ego-depletion`); unnamed ones are `fx:u-<sha1[:10]>` and get a generated display name from `description` with `review_state="machine"`.
3. LLM-suggested names (the two columns from `fred_enriched.csv`, ~1,750 rows) never create ids by themselves; they are attached as `aliases` with `source="llm"`, `review_state="machine"`.
4. FLoRA-only originals (1,843 pairs without effect-size coding) do NOT create effects; they hang off the paper page as "findings without effect coding" until a curator names them or FReD codes them (this keeps effect pages honest and the page count sane).
5. Legacy ids (`Arb234`, `curatescience676`, `av_351`, `add_ai224`, `osc12`, `OpAQ_406`, ... 3,441 distinct on 4,659 rows; 15 prefix patterns measured), current `fred_id` (`Boyce_etal2023150_1`, `XPHI15_1`), `fred_id_old` (`XPHI15_d`), COS `entry_id`/`effect_id` all coexist inside `Attempt.ids` — they are never used as our primary keys because they are neither stable nor complete (fred_id 99.8% filled, matches legacy id for only 645 of 1,116).

### 4.4 Attempt and pair ids (composite, content-derived, stable)
`id_r_key = doi_key(doi_r) or ("url:" + normalized url_r)` (FORRT's own join key is `coalesce(url_r, doi_r)`). `pair_id = "pair:" + sha1(doi_o_key + "|" + id_r_key)[:12]`. `attempt_key = doi_o_key + "|" + id_r_key + "|" + study_o_norm + "|" + study_r_norm + "|" + effect_ordinal` where `effect_ordinal` is the COS within-entry `effect_id` for current rows, the legacy id suffix (`_a/_b`) for legacy rows, else `1`; `attempt_id = "att:" + sha1(attempt_key)[:12]`. Legacy rows that match a current row by (doi pair, study, ordinal) merge into the same attempt (the 1,548 joinable rows; U5) and contribute closeness/power/CI fields with `source="fred_legacy_2.4.1"`; the 3,234 unmatched legacy rows become their own attempts with `prov.source="fred_legacy_2.4.1"` and a visible "legacy coding" badge. A per-build `data/build/reports/merge_report.md` lists every legacy row that was neither matched nor kept (must be 0 unless explicitly excluded via vocab).

### 4.5 URL scheme (site)
```
/                               home
/effects/                       browse (facets: discipline, topic, status, project, decade) — static facet pages + client filter
/effect/{slug}/                 the core page: three lenses, forest plot, timeline, attempts (anchors #att-xxxx), candidates tab
/paper/{paper_slug}/            paper page (original and/or replication roles), studies as sections (#study-1a), pairs, citations sparkline
/attempt/{att_id}/              NOT a page: 301-free anchor on the effect page (/effect/{slug}/#att-{id}) or paper page; JSON only
/project/{slug}/                project page with per-site drill-down where raw data exists
/person/{slug}/                 only for persons with >= 3 papers in the bundle (budget rule); others resolve to a search link
/topic/{id}/  /discipline/{slug}/
/game/  /game/{mode}/           modes: classic (binary+mixed), calibrated (probability slider), cues (progressive hints)
/candidates/                    public review queue (read-only) + weekly report
/about/ /methods/ /data/ /changelog/ /contribute/
/doi/?q=10.1126/science.1239918 client-side DOI resolver (reads /api/v1/doi/{hash3}.json) — DOIs cannot be routes
/api/v1/index.json  /api/v1/effect/{slug}.json  /api/v1/doi/{hash3}.json  /api/v1/bundle/{table}.parquet (download links)
/feed.xml (new pairs), /sitemap-index.xml
```
Redirect/alias policy: an effect slug is permanent; merges produce `/effect/{old}/` pages that meta-refresh + canonical to the new slug (GitHub Pages has no server redirects).

---

## 5. Build, tests, CI

### 5.1 One command
`npm run build` at the root = `uv run pipeline build && npm --prefix site run build`. `pipeline build` runs, in order and idempotently: `fetch --verify` (checks sha256 of everything in MANIFEST; `--refresh` re-downloads mutable files and rewrites MANIFEST) -> `normalize` -> `merge-legacy` -> `registry` -> `score` -> `enrich --cache-only` (network enrich is a separate `enrich --online` step, never part of `build`) -> `game-items` -> `export` -> `validate`. Each stage writes Parquet to `data/build/normalized/` and a stage stamp (input hashes) so re-runs skip unchanged stages; `--force` rebuilds all. `pipeline build --offline` is what CI runs (no network at all); a build that needs network is a bug.

### 5.2 Stage outputs (row-count expectations from the readers, used as test baselines)
| Stage | Output | Expected rows (2026-09-07 snapshot) |
|---|---|---|
| normalize fred | `fred_attempts.parquet` | 2,164 (COS archive rows, augmented by output_FReD.xlsx by row order after asserting doi_o + es_value_o equality) |
| normalize flora | `flora_pairs.parquet` | 2,815 (2,526 replication + 289 reproduction); filter flags attached for 358 rows |
| normalize legacy | `legacy_attempts.parquet` | 4,659 data rows minus junk rows (mime-type column shifts; count reported, not silently dropped) |
| merge-legacy | `attempts.parquet` | 2,164 current + (4,659 - 1,548 matched) legacy-only, minus explicit exclusions; join by DOI pair + study + ordinal; expected matched ~1,548 (1,544 also by fred_id == legacy id stem) |
| pairs | `pairs.parquet` | union of FLoRA pairs (2,815), FReD pairs (859 distinct doi pairs; 678 already in FLoRA), legacy pairs, overlay pairs |
| score | `criteria.parquet` | ~1,061 attempts with r on both sides (1,056 with Ns) get 7 criteria; oracle check vs COS `statistical_success` on 901 rows |
| registry | `effects.parquet` | named effects ~(443 legacy ∪ 583 sheet ∪ 362 docx) after alias merging + unnamed FReD groups; exact count is a build output, baseline recorded in SUMMARY.json |
| game-items | `game_items.parquet` | candidates: FReD rows with claim_text_o + clear success/failure (985 + 787) minus exclusions (JOM block 100/103 successful, Soto 60, mega-paper skew) — the game designer's rules decide; the architecture only guarantees the exclusion table is curated CSV |

### 5.3 Test list (`tests/`, pytest; all run in CI, all offline)
1. `test_schemas.py` — every bundle file validates against `pipeline/schemas/*.json`; the committed schemas equal a fresh export from `models.py` (freshness).
2. `test_ids.py` — `normalize_doi` table-driven cases (the U1 variants: `doi:`, `dx.doi.org`, `[Opens in new window]`, percent-encoding, trailing punctuation, `//`, PsyArXiv `_v2`); slug determinism; slug uniqueness across the bundle; `doi_hash3` equals FLoRA's `doi_o_hash` for all 2,815 rows.
3. `test_integrity.py` (DuckDB SQL) — every `attempt.original_id/effect_id/pair_id/replication_paper_id/project_id` resolves; every `effect.attempt_ids` back-resolve; no pair without both papers; no effect without >= 1 original; no orphan persons/topics.
4. `test_counts.py` — new `SUMMARY.json` vs committed baseline: any table dropping > 1% or any source file's row count dropping at all fails unless the PR passes `--accept-baseline` and adds a `docs/CHANGELOG-DATA.md` line (the "row counts never silently drop" rule). Also asserts the FORRT-derived invariants that must hold on this snapshot family: FLoRA type counts, FReD reported_success total = row count, legacy matched rows within ±5% of 1,548.
5. `test_merge.py` — legacy rows: matched + kept + explicitly excluded == 4,659; no legacy row silently lost; closeness/power/CI fields only ever come with `source="fred_legacy_2.4.1"` provenance.
6. `test_score.py` — conversions vs `effect_size_transformations.R` cases (d, g, OR, eta2, f, f2, r2, t, F(1,df), z, chi2(1)); `r_o/r_r` recomputed equal to the COS archive's precomputed values within 1e-3 on the 733 rows that have both; `significance_r` agreement with COS `statistical_success` on 901 rows reported and floored (baseline measured on first run, then must not fall).
7. `test_vocab.py` — every raw discipline / es_type / pval_type / outcome value in the inputs has a row in the curated map (unknown value = failing test, not a silent "other").
8. `test_provenance.py` — every `Label` and every inferred field has `prov.source`; every `review_state="machine"` value has `method` and `confidence`.
9. `test_no_orphan_pages.py` (site, vitest) — every entity in the bundle has exactly one page URL and every internal `href` in `dist/` resolves to a file (full internal link check, no network).
10. `test_page_budget.py` — count files in `site/dist/`; warn > 30,000, fail > 60,000 (GitHub Pages has no cap; the budget exists so a move to a capped host remains possible); also enforce `person` page rule.
11. `test_secrets.py` — gitleaks (pre-commit + CI) plus a Python regex scan over the whole tree excluding `archive/**` (which is scrubbed once and then verified by the same scan, so archive is included after scrubbing).
12. `test_repo_hygiene.py` — root allowlist (only the entries in Section 2 may exist at the repo root); no `*.py` outside `pipeline/`, `tests/`, `notebooks/`, `archive/`, `site/`; no file in `data/build/` is tracked by git except `SUMMARY.json`; `data/raw/**` mtime never newer than its MANIFEST entry unless `pipeline fetch --refresh` ran (stamp file).
13. `test_docs_numbers.py` — docs use `{{counts.*}}` placeholders rendered from `SUMMARY.json`; any literal number in `docs/*.md` inside a `<!-- verified -->` block must match the current build within tolerance, else the doc is stale.
14. `test_external_links.py` (weekly workflow only, not on PR) — lychee over `dist/` for external URLs with a 30-day cache; failures produce a report, not a red build.
15. `test_game_items.py` — no item whose answer is not in {success,failure,mixed}; no item from a blocklisted project; per-stratum base rates within the game designer's tolerances; reveal fields non-empty.

### 5.4 Page and file budget (measured inputs, estimated outputs)
Inputs: FLoRA distinct doi_o 2,589 + doi_r 2,148; FReD doi_o 786 (2,080 FReD rows have doi_o in FLoRA); legacy adds 1,110 original DOIs absent from current FReD. Estimate: ~6,000-6,800 paper pages, ~1,500-2,500 effect pages, ~30 project pages, ~1,000-1,500 person pages under the >= 3 papers rule, ~200 topic/discipline pages, ~20 static, plus JSON: per-effect (~2.5k) + `doi/{hash3}` (<= 4,096; FLoRA has 1,920 distinct doi_o_hash) + Pagefind fragments for indexed pages (effects, projects, topics ~2.8k). Total ~18k-22k files. This is why Cloudflare Pages (20,000-file cap) is not the primary host, and why attempts and low-degree persons do not get standalone HTML pages.

### 5.5 CI (`.github/workflows/`)
- `ci.yml` (push, PR): checkout -> uv sync (cached) -> `ruff check` + `ruff format --check` -> gitleaks -> `pytest -m "not network"` -> `uv run pipeline build --offline` (uses committed small raw + LFS-free restore of big raw from the latest `data-raw-*` Release asset when not present) -> `npm ci` + `npm run build` in `site/` -> vitest (link/orphan/page-budget) -> upload `site/dist` and `data/build/bundle` as artifacts.
- `refresh.yml` (cron Monday 05:00 UTC + manual): `pipeline fetch --refresh` -> if MANIFEST changed: `pipeline build` -> `pipeline diff --against main` writes `data/build/reports/refresh-YYYY-MM-DD.md` (new/removed pairs, outcome changes, new FORRT sources) -> open PR "data refresh YYYY-MM-DD" with the report as body and the updated `SUMMARY.json`; the PR runs `ci.yml`. Data reaches `main` only through this PR (a human merges; auto-merge allowed if counts only grow and tests pass).
- `deploy.yml` (push to main): build as in ci -> `actions/upload-pages-artifact` -> `actions/deploy-pages`; also creates Release `data-YYYY-MM-DD` with `bundle/*.parquet|json` + `SUMMARY.json` + the raw FORRT snapshot tarball (so `data/raw` big files are restorable and citable).
- `discover.yml` (cron Monday 06:00 UTC, after refresh; needs `OPENALEX_API_KEY`, `S2_API_KEY`, `ANTHROPIC_API_KEY`, `CONTACT_EMAIL` secrets): `pipeline discover --week` -> `pipeline triage --batch` -> commits nothing under `data/`, uploads `candidates.duckdb` snapshot as artifact, and opens/updates a single rolling PR "discovery queue" that adds `data/build/reports/discovery-YYYY-WW.md` and a `candidates_public.json` delta. Human review runs locally (`pipeline review`) and commits JSONL decisions.
- Secrets: never in files; `.env.example` lists names; `pipeline.config.Settings` reads env only; the old scripts' `OPENROUTER`/`OPENAI_API_KEY` literals (51 files) are scrubbed before archiving (Section 6).

### 5.6 Layer-law enforcement (mechanical, not aspirational)
- `site/astro.config.mjs` resolves data only via an alias to `../data/build/bundle`; a vitest test greps `site/src` for any `data/raw|data/curated|data/cache` path.
- `pipeline/config.py` exposes `Paths` with `raw` opened read-only (a `RawPath` wrapper whose `open("w")` raises); the only writer is `pipeline.fetch`.
- pre-commit: ruff, gitleaks, `check-added-large-files --maxkb=10240`, a hook that rejects staged files under `data/build/` (except SUMMARY.json) and under `data/raw/**` unless the commit message starts with `data:`.

---

## 6. Migration of the existing tree (every root entry)

Conventions: **archive/<topic>/** keeps history with an index README; **data/raw/local/** is for irreplaceable inputs; **data/cache/** for API caches (gitignored, listed in MANIFEST-cache.json); **TRASH** = move to `archive/_trash-2026-09/` (listed in `archive/README.md`), owner deletes the folder after 30 days — nothing is deleted outright in the migration commit. **SCRUB** = the file contains a live key; `pipeline.migrate.scrub` replaces the literal with `<REDACTED-OPENROUTER-KEY>`/`<REDACTED-OPENAI-KEY>` before the move and the secrets test verifies. The OpenRouter and OpenAI keys must be **rotated by the owner** regardless (they have been on disk since Dec 2025).

Secrets scrub list (verified by grep this session; 52 files): `CATEGORIZATION_IMPROVEMENT_PLAN.md` and 51 `.py`: create_taxonomy.py, create_taxonomy_v2.py, emergent_clustering.py, enrich_effect_names.py, enrich_osc2015.py, extract_disagreements.py, find_optimal_clusters.py, full_emergent_pipeline.py, hierarchical_clustering.py, improve_clusters.py, label_clusters.py, process_effects.py, recluster_optimal.py, recluster_with_optimal_k.py, test_alternative_approaches.py, test_classification_approach.py, test_effect_ablation.py, test_emergent_approach.py, test_enrichment_methods.py, test_methodology_only.py, test_multidimensional_taxonomy.py, test_prompt_strategies.py, test_random_sample.py, test_semantic_extraction.py, test_single_question.py, test_taxonomy_agreement.py, test_taxonomy_v10.py, v11, v12, v13, v14, v15, v15a, v15c, v15d, v15e, v15f, v15g, v16, v17, v2, v2_datadriven, v3, v3_refined, v4, v5, v6_multilabel, v7_observable, v8_delta, v9, test_v10a_updated.py. The portable scripts (openalex_utils.py, harvest_crossref_replications.py, fetch_all_abstracts.py, collect_citation_dois.py, collect_citations.py, fetch_study_metadata.py, fetch_openalex_original_dois.py, analyze_openalex_topics.py, analyze_citations.py) are clean.

### 6.1 Root files -> destination
| Root entry | Destination | Note |
|---|---|---|
| `README.md`, `START_HERE.md`, `QUICK_START.md`, `PROJECT_STATUS.md`, `TECHNICAL_REFERENCE.md`, `SEARCH_EXPANSION_SUMMARY.md` | `archive/harvester/docs/` | aspirational, unmeasured claims (U1); new root README replaces |
| `ENRICHMENT_COVERAGE_README.md` | `archive/enrichment/docs/` + copied to `docs/reference/enrichment-coverage-2025-12.md` with a "measured Dec 2025" header | the one doc with real numbers |
| `CATEGORIZATION_IMPROVEMENT_PLAN.md` | SCRUB -> `archive/taxonomy-experiments/docs/` | contains a key |
| `Potentialcategories1`, `prompt_for_taxonomy_rethink.md`, `research_agent_prompt.md`, `taxonomy_feedback_report.md`, `taxonomy_improvement_brief.md`, `taxonomy_improvement_brief_v2.md`, `taxonomy_validation_report.md`, `v10_brief_for_refinement.md`, `v16_failure_report.md`, `v4_feedback_for_taxonomy_agent.md`, `v7_feedback_brief.md`, `v8_feedback_brief.md`, `v9_breakthrough_report.md`, `v9_final_report.md` | `archive/taxonomy-experiments/docs/` | lessons summarized once in `docs/decisions/ADR-0003-no-llm-taxonomy.md` |
| `data_sources_analysis.md`, `replication_projects_reference.md`, `replication_projects_sources.md`, `replication_projects_research_brief.md`, `missing_studies_analysis.md` | `docs/research-notes/2025-12/` | genuine notes (U6 values them); header "unverified, written 2025-12" |
| `Getting Started with FORRT.docx` | `docs/reference/forrt/Getting_Started_with_FORRT_2024-11.docx` | FORRT onboarding doc |
| `Psychology Replications (1).docx` | `data/raw/local/forrt-rr-list/Psychology_Replications_2025-12-23.docx` | SRC; MANIFEST entry, mutable=false |
| `docx_parsed_entries.json`, `psychology_replications.csv`, `psychology_replications.json` | `data/raw/local/forrt-rr-list/` | SRC + its earlier parse (reconcile in `normalize/rr_docx.py`) |
| `canonical_effect_names.json`, `all_known_effects.txt` | TRASH | regenerable duplicates |
| `fred_database_english.csv` | `archive/data-derived/legacy-fred/` | column-identical to 2.4.1 `Data` (canonical raw is `data/raw/forrt/osf/version-history/FReD_2.4.1_2025-06-25.xlsx`); TRASH after the merge test proves equality |
| `fred_database_english.xlsx`, `fred_database_english.json` (invalid JSON), `fred_replication_database.xlsx`, `fred_main_database.csv/.json`, `forrt_fred_data.csv` | TRASH | duplicates/superseded (U3) |
| `forrt_replications_reversals.csv/.json` | `archive/data-derived/legacy-fred/` | = sheet "FORRT R&R (editable)"; pipeline reads the xlsx sheet directly |
| `fred_enriched.csv` | extract cols 101-102 -> `data/raw/local/llm-suggestions/effect_names_2025-12.csv` (id, suggested_name, model, provenance); file itself -> `archive/data-derived/` | LLM names are aliases with review_state=machine |
| `fred_enriched_openalex.csv`, `fred_enriched_with_abstracts.csv`, `fred_per_effect.csv`, `fred_per_experiment.csv`, `fred_per_original_study.csv` | `archive/data-derived/` | regenerable; the new build supersedes |
| `full_extraction_progress.json` | `data/raw/local/llm-suggestions/xy_extraction_2025-12.json` | only copy of the X->Y decomposition (2,445 rows), provenance machine |
| `openalex_original_enrichment_full.json` (40 MB) | `data/cache/legacy-2025-12/openalex_original_enrichment_full.json` | cache; MANIFEST-cache entry (fetched 2025-12-28, key space legacy doi_original 1,623) |
| `abstract_enrichment.json`, `citation_dois.json`, `citation_data.json`, `study_metadata.json` | `data/cache/legacy-2025-12/` | caches (1,420 abstracts; 1,688-DOI citation lists; 200-DOI citer metadata; 550-DOI S2/Crossref) |
| `openalex_original_enrichment.json`, `*_sample.json` (2), `fetch_progress.json`, `enrichment_progress.json` | TRASH | subsets/checkpoints |
| `citation_analysis_summary.json`, `fred_internal_citations.json`, `citation_by_outcome_analysis.json`, `top_100_cited_references.csv/.json`, `replication_predictors_analysis.json`, `projects_to_research.json` | `archive/enrichment/analyses-2025-12/` | recomputed by `pipeline enrich` with current outcomes; `projects_to_research.json` seeds `data/curated/projects/*.yaml` once |
| `osc_2015_rpp_data.csv`, `osc_2015_enrichment.csv/.json` | `data/raw/third-party/rpp2015/` (+ bridge csv) | MANIFEST source_url osf.io/ezcuj (github CenterForOpenScience/rpp) |
| `ml4_full_data.csv`, `ml4_results.csv` | `data/raw/third-party/ml4/` | github.com/raklein/ml4 |
| `manybabies_mb1_data.csv` | `data/raw/third-party/manybabies-mb1/` | github.com/manybabies/mb1-analysis-public; latin-1 noted in MANIFEST |
| `manybabies_labs.csv`, `manybabies_mb1_metadata.csv`, `fred_extdata.csv`, `fred_rpackage_data.csv` (404 stubs), `dataset_publication.zip` (OSF 500 JSON), `osf_page.html` | TRASH | broken downloads |
| `replication_database.zip` | rename -> `docs/reference/forrt/red_sosci_ingest.R` | actually an R script (FORRT ReD ingest) |
| `psychology_replications_expanded_crossref.csv`, `crossref_issn_whitelist_from_fred.csv` | `data/discovery/seed-pools/` (gitignored) + copy of the ISSN list to `data/curated/vocab/journal_prior_2025-12.csv` | first review-queue seed; recompute prior from FLoRA journal_r |
| `crossref_harvest_state.json` | TRASH | stale cursors |
| `abstract_coverage_test_50.csv`, `additional_enrichments_test_50.csv`, `new_enrichment_test_50.csv`, `enrichment_test_100.csv`, `av_crossref_titles_sample.csv` | `archive/enrichment/api-tests/` | conclusions live in the coverage README |
| `analysis_sample.json/.txt`, `disagreement_studies.txt`, `taxonomy_v17_output.txt`, `v10a_updated_output.txt`, all `taxonomy*.json`, `*_results.json`, `*_clusters.json`, `optimal_k_analysis.json`, `cluster_quality_analysis.json`, `classification_results.json`, `methodology_classification_test.json`, `multidim_taxonomy_test.json`, `single_question_results.json`, `emergent_results.json`, `alternative_approaches_results.json`, `prompt_strategy_comparison.json`, `test_semantic_results.json`, `v10a_updated_results.json` | `archive/taxonomy-experiments/results/` | two are invalid JSON (emergent_clusters.json, taxonomy_v8_results.json) — kept as-is, noted |
| Harvester scripts: `harvest_crossref_replications.py`, `harvest_2021_comprehensive.py`, `harvest_multiple_years.py`, `run_all_searches.py`, `simple_replication_search.py`, `expand_replications_crossref.py`, `expanded_search_queries.py`, `merge_crossref_outputs.py`, `create_final_2021_dataset.py`, `filter_high_confidence.py`, `verify_quality.py`, `check_duplicates.py`, `check_results.py`, `check_search_progress.py`, `compare_search_strategies.py` | `archive/harvester/scripts/` | portable pieces re-implemented in `pipeline/discover/` (U1 list) |
| Enrichment scripts: `openalex_utils.py`, `fetch_all_abstracts.py`, `fetch_openalex_original_dois.py`, `fetch_study_metadata.py`, `collect_citation_dois.py`, `collect_citations.py`, `analyze_citations.py`, `analyze_openalex_topics.py`, `backfill_tldrs.py`, `enrich_with_abstracts.py`, `test_abstract_coverage_50.py`, `test_additional_enrichments_50.py`, `test_all_sources_100.py`, `test_enrichment_100.py`, `test_enrichment_sample.py`, `test_exact_coverage.py`, `test_new_enrichments_50.py`, `test_new_sources_missing_dois.py`, `check_descriptions.py` | `archive/enrichment/scripts/` | `normalize_doi`, backoff, abstract cascade, cites collector re-implemented (with tests) in `pipeline/ids.py` and `pipeline/enrich/` |
| Taxonomy scripts: the 51 SCRUB files (list above; includes `enrich_effect_names.py`, `enrich_osc2015.py`, `process_effects.py`) plus the key-free `create_analysis_sample.py` and `analyze_cluster_quality.py` | SCRUB (51) -> `archive/taxonomy-experiments/scripts/`; the 2 clean ones move unscrubbed | never imported |
| `output/` | `final_2021_psychology_replications.csv`, `simple_replications_2021.csv` -> `data/discovery/seed-pools/`; rest -> `archive/harvester/output/` (state json/.tmp/tmp_issn*/test_* -> TRASH) | |
| `logs/` | `archive/harvester/logs/` | UTF-16 fragments |
| `cogatlas/` | `cognitive_atlas_keywords.csv` + `README.md` + `KEYWORD_LIST_REPORT.txt` -> `data/raw/third-party/cogatlas/`; `cognitive_atlas_keywords_simple.json`, `demo_tagger.py` -> `archive/enrichment/cogatlas/` | README references 5 missing files; note in MANIFEST |
| `openalex_analysis/` | `work_groupings.csv` -> `data/cache/legacy-2025-12/openalex_work_groupings_2025-12.csv`; everything else -> `archive/enrichment/openalex_analysis/` | crosstabs regenerable |
| `__pycache__/`, `.mypy_cache/` | delete outright (build residue, no content) | |
| `.venv/` | TRASH after `uv sync` creates the new env | it is Python 3.12; system is 3.13 |
| `.claude/` | keep at root | owner settings |
| `data/raw/forrt/` | stays; `MANIFEST.json` moves up to `data/raw/MANIFEST.json` and gains `retrieved`/`mutable`; `osf/FReD_osf_2tbvd.xlsx` and `osf/wiki_home.md` (502 stubs) -> TRASH and removed from MANIFEST; `osf/data-archive/` and `osf/rkj4x/` (empty dirs) removed | |
| `wiki/` | see 6.2 | |
| `_planning/` | stays until the build starts, then `docs/decisions/planning-2026-09/` (all reader reports + designs + brief) | the record of why |

### 6.2 `wiki/` -> `site/` and `archive/wiki-v1/`
| Entry | Destination |
|---|---|
| `src/styles/index.css` | `archive/wiki-v1/src/`; tokens (palette, spacing scale) re-typed into `site/src/styles/tokens.css` with the U4 fixes (define `--space-*` only, add `--color-ink-light/faint`, outcome palette, mono font, dark tokens) |
| `src/pages/**`, `src/layouts/Layout.astro`, `src/components/SearchBox.tsx`, `src/lib/schema.ts(+test)` | `archive/wiki-v1/src/` (no code reuse) |
| `scripts/fetch-data.ts`, `scripts/normalize-data.ts` | `archive/wiki-v1/scripts/` (snapshot pattern reborn as `pipeline/manifest.py`) |
| `data/curated/family-literary-fiction.json` | converted to `data/curated/effects/literary-fiction-theory-of-mind.yaml` (first worked example; keeps `curation_state`) |
| `data/sources/disciplines.json` | `data/raw/local/forrt-web/flora_explorer_disciplines.json` |
| `data/sources/flora.csv` + `snapshots.json` | `archive/wiki-v1/data/` (2026-08-12 snapshot, 2,521 rows; useful only as a historical diff) |
| `data/sources/fred_effect.xlsx` (1x1 placeholder), `fred_codebook.pdf` (mis-named xlsx), `data/generated/*` | TRASH |
| `home.png`, `family.png`, `explore.png`, `collection.png`, `paper.png`, `attempt.png` | `archive/wiki-v1/screenshots/` |
| `dist/`, `node_modules/`, `.astro/`, `playwright-report/`, `test-results/`, `tests/explore.spec.ts`, `screenshot.js`, `README.md`, `CLAUDE.md`, `AGENTS.md`, `package*.json`, configs | delete outright (regenerable or boilerplate); new `site/` is scaffolded fresh with Astro 7 + @astrojs/preact + pagefind + minisearch |

### 6.3 Migration is a pipeline command, not a manual afternoon
`pipeline migrate --plan` prints the table above as it applies to the actual tree (unknown files are listed as "UNPLANNED" and block execution); `pipeline migrate --apply` performs moves, scrubs, writes `archive/README.md` (index with original path, new path, reason, size, sha256) and `archive/_trash-2026-09/README.md`, then runs the secrets scan over the whole tree and fails if anything is left. The plan is committed as `docs/decisions/ADR-0002-migration-2026-09.md` with the generated table.

---

## 7. Docs set (what exists, who writes it, how it stays true)

| File | Content | Truth mechanism |
|---|---|---|
| `README.md` | 20 lines: purpose, `npm run build`, layer law, links | numbers via `{{counts.*}}` placeholders rendered by `pipeline docs` |
| `docs/ARCHITECTURE.md` | this design, trimmed to what was built; diagram of layers | reviewed on every ADR |
| `docs/DATA-MODEL.md` | generated from `pipeline/schemas/*.json` (field tables + enum values) | `pipeline docs` regenerates; test fails if stale |
| `docs/DATA-SOURCES.md` | generated from `data/raw/MANIFEST.json` + `MANIFEST-cache.json`: table of every input, URL, retrieved date, sha256, license, rows | generated |
| `docs/PIPELINE.md` | stages, inputs/outputs, how to run one stage, how a refresh PR is produced | hand-written; commands are doctested by `tests/test_cli_help.py` (every documented subcommand exists) |
| `docs/IDS-AND-URLS.md` | Section 4 as reference | tests in `test_ids.py` cite the doc examples |
| `docs/CURATION-GUIDE.md` | how to add/merge an effect YAML, resolve a docx title, review a candidate, what `review_state` means | YAML examples are validated by `test_schemas.py` |
| `docs/DISCOVERY.md` | the U7 pipeline as implemented, evaluation harness numbers (recall vs FLoRA by year, precision on labelled sample) | numbers generated into `data/build/reports/discovery-eval.md` and embedded |
| `docs/GAME.md` | item construction rules, scoring, versioning of item pools | rules encoded as `data/curated/game/*.csv` + tests |
| `docs/RUNBOOK.md` | weekly: merge refresh PR, review candidates, monthly FORRT export; what to do when FORRT changes columns | each step is a CLI command |
| `docs/CHANGELOG-DATA.md` | one line per merged refresh/curation PR with count deltas | required by `test_counts.py` when baselines move |
| `docs/decisions/ADR-*.md` | ADR-0001 stack, 0002 migration, 0003 no LLM taxonomy (facets + provenance instead), 0004 effect identity ledger, 0005 hosting/file budget, 0006 data-in-git policy | new stack change = new ADR |
| `docs/reference/` | FORRT codebooks (copied, with source), enrichment coverage 2025-12, R-package criteria formulas with our port's test table | |
| `archive/README.md` | generated index of the archive | generated by `pipeline migrate` |
| `CONTRIBUTING.md` | PR rules, pre-commit, the root allowlist, "no numbers in prose without a generator" | |

---

## 8. Anti-rot rules (each one is enforced by something, not by goodwill)

1. **Layer law**: raw is immutable (MANIFEST sha256; read-only wrapper), build is never committed (pre-commit hook + hygiene test), curated is YAML/CSV edited by humans (schema-validated), the site reads only the bundle (grep test).
2. **Root allowlist**: the repo root may contain only the entries in Section 2; `test_repo_hygiene.py` fails otherwise. No script, csv, json or "v17" will ever live at the root again.
3. **No orphan scripts**: every `.py` under `pipeline/` is reachable from a CLI subcommand or imported by one; experiments go to `notebooks/YYYY-MM-DD-slug/` with a README stating question/result/date, and `pipeline/` may not import from `notebooks/` (import-linter contract).
4. **Provenance or it did not happen**: any inferred value (name, topic, discipline, outcome, DOI link) is a `Label` with `source/method/confidence/review_state`; the site renders the review state badge. This is the direct answer to the 17 taxonomy iterations: labels are cheap, unlabeled provenance is the rot.
5. **Counts are a contract**: `SUMMARY.json` baseline + `test_counts.py`; drops require an explicit flag and a changelog line.
6. **Docs cannot lie about numbers**: placeholders rendered from the build; literal numbers must sit in verified blocks that tests re-check.
7. **Secrets**: env only; gitleaks in pre-commit and CI; archive scrubbed and re-scanned; keys rotated at migration.
8. **Pinned everything**: uv.lock, package-lock.json, exact CDN-free dependencies in `site/`, pipeline version stamped into every bundle.
9. **One door for data changes**: only `refresh.yml` PRs and curation PRs change what the site shows; no manual edits to generated files, no "quick fix" commits to `data/build`.
10. **Deletion protocol**: TRASH folder with README and a date; deleted for real after 30 days by the owner.
11. **Ids are forever**: ledger append-only; merges leave redirects; tests forbid id reuse.
12. **Reversible machine steps**: every LLM output stored with model id, prompt hash, date; re-runnable; never overwrites a human decision (decisions are append-only JSONL, latest wins).
13. **ADR or it is not a decision**: stack/host/format changes require an ADR referencing what it replaces.
14. **Offline build**: `pipeline build --offline` must succeed from raw + cache alone; network stages are separate commands with their own state files (one state file per process — the crash in U1 must not recur).

---

## 9. Phase-1 module list with signatures

Phase 1 = "FORRT + legacy + curated docx -> validated bundle -> Astro site with effect/paper/project/topic pages + game v1". Discovery beyond seeds is Phase 2 (only `discover.seeds` is Phase 1).

```python
# pipeline/cli.py  (Typer)
app = typer.Typer()
@app.command() def fetch(refresh: bool = False, verify: bool = True, only: list[str] = []) -> None
@app.command() def normalize(stage: str = "all", force: bool = False) -> None      # fred | flora | legacy | rr_docx | third_party
@app.command() def merge_legacy(force: bool = False) -> None
@app.command() def registry(assign: bool = True, report: bool = True) -> None
@app.command() def score(force: bool = False) -> None
@app.command() def enrich(online: bool = False, source: list[str] = ["openalex","crossref","s2","abstracts"], limit: int | None = None) -> None
@app.command() def game_items(force: bool = False) -> None
@app.command() def export(bundle_dir: Path = Paths.bundle) -> None
@app.command() def validate(strict: bool = True) -> None
@app.command() def build(offline: bool = True, force: bool = False, accept_baseline: bool = False) -> None
@app.command() def diff(against: str = "main") -> None
@app.command() def docs() -> None
@app.command() def migrate(plan: bool = True, apply: bool = False) -> None
@app.command() def discover(week: str | None = None, sources: list[str] = [...]) -> None   # Phase 2; Phase 1 only `--seeds`
@app.command() def review(candidate: str | None = None) -> None                          # Phase 2

# pipeline/config.py
class Settings(BaseSettings): contact_email: str; openalex_api_key: str | None; s2_api_key: str | None; anthropic_api_key: str | None; supabase_url: str | None; supabase_anon_key: str | None
@dataclass(frozen=True) class Paths: root: Path; raw: RawPath; cache: Path; curated: Path; build: Path; bundle: Path; discovery: Path; schemas: Path
def load_paths(root: Path | None = None) -> Paths

# pipeline/manifest.py
class ManifestEntry(BaseModel): path: str; bytes: int; sha256: str; source_url: str | None; retrieved: str | None; mutable: bool; notes: str | None
class Manifest(BaseModel): retrieved_on: str; license: str; citation_file: str; upstream: dict[str,str]; files: list[ManifestEntry]
def load_manifest(path: Path) -> Manifest
def verify_manifest(m: Manifest, root: Path) -> list[str]            # returns mismatches; [] == ok
def sha256_file(path: Path) -> str
def update_entry(m: Manifest, path: Path, source_url: str | None, retrieved: str, mutable: bool) -> Manifest

# pipeline/ids.py
def normalize_doi(s: str | None) -> str | None
def doi_key(doi: str) -> str
def doi_hash3(doi: str) -> str                                       # md5 prefix, FORRT-compatible
def paper_slug(doi_key: str) -> str
def url_id(url: str) -> str                                          # "url:" + normalized
def effect_slug(name: str) -> str
def normalize_study_label(s: str | None) -> str | None               # "Experiment 1" -> "1", "Study 3" -> "3", "1a" -> "1a"
def pair_id(doi_o_key: str, id_r_key: str) -> str
def attempt_key(doi_o_key: str, id_r_key: str, study_o: str | None, study_r: str | None, ordinal: int | str) -> str
def attempt_id(attempt_key: str) -> str
def person_slug(family: str, given: str | None, openalex_id: str | None) -> str

# pipeline/fetch/forrt.py
FORRT_FILES: list[tuple[str, str, bool]]                             # (relative path, source_url, mutable)
def fetch_forrt(paths: Paths, refresh: bool, only: list[str]) -> Manifest
def fetch_third_party(paths: Paths, refresh: bool) -> Manifest       # rpp2015, ml4, mb1, cogatlas — pinned URLs

# pipeline/normalize/fred.py
def load_fred_current(paths: Paths) -> pd.DataFrame                  # output_FReD.xlsx (2,164 x 56)
def load_fred_cos_archive(paths: Paths) -> pd.DataFrame              # 2025-11-30_COSdata_validated.xlsx (2,164 x 44)
def align_current_to_archive(cur: pd.DataFrame, cos: pd.DataFrame) -> pd.DataFrame   # asserts doi_o and es_value_o equal row-wise; merges augmentation cols
def parse_es(value_raw: str | float | None, es_type_raw: str | None) -> EffectSize
def parse_pval(value: float | None, type_raw: str | None, tails_raw: str | None) -> PValue
def parse_author_json(s: str | None) -> list[AuthorRef]
def clean_text(s: str | None) -> str | None                          # html entities, JATS, PDF linebreaks
def build_fred_attempts(df: pd.DataFrame, vocab: Vocab) -> tuple[list[Attempt], list[OriginalStudy], list[Paper], list[ReplicationPair]]

# pipeline/normalize/flora.py
def load_flora(paths: Paths) -> pd.DataFrame                         # output_flora.csv (2,815 x 35)
def load_flora_filter_log(paths: Paths) -> pd.DataFrame              # 358 flagged rows
def build_flora_pairs(df: pd.DataFrame, flags: pd.DataFrame, vocab: Vocab) -> tuple[list[ReplicationPair], list[Paper]]

# pipeline/normalize/legacy.py
def load_legacy_241(paths: Paths, sheet: str = "Data") -> pd.DataFrame            # skips the 2 description rows; reports junk rows
def load_reversals_sheet(paths: Paths) -> pd.DataFrame                            # 583 x 6
def load_rr_editable_sheet(paths: Paths) -> pd.DataFrame                          # 1,406 x 73 (effect name -> DOI pair bridge)
def build_legacy_attempts(df: pd.DataFrame, vocab: Vocab) -> list[Attempt]        # granularity effect, source fred_legacy_2.4.1
def merge_legacy(current: list[Attempt], legacy: list[Attempt]) -> MergeResult    # MergeResult(matched, legacy_only, excluded, report_md)

# pipeline/normalize/rr_docx.py
def load_docx_entries(paths: Paths) -> list[DocxEntry]               # 362 entries; normalizes status strings (U3 §6.1 table)
def reconcile_with_csv_parse(entries, csv_rows) -> list[DocxEntry]   # 437-row parse adds 75 (Neuroscience etc.)
def extract_original_title(entry: DocxEntry) -> str | None           # 329 quoted titles
def resolve_title_to_doi(title: str, surname: str | None, year: int | None, cache: Cache) -> tuple[str | None, Provenance]  # rapidfuzz vs FLoRA/FReD/legacy first, Crossref query.bibliographic second (online only)

# pipeline/normalize/vocab.py
class Vocab: discipline: dict[str,str]; es_type: dict[str,str]; pval_type: dict[str,str]; outcome: dict[str,str]; subfield_overrides: dict[str,str]
def load_vocab(paths: Paths) -> Vocab
def normalize_discipline(v: str | None, vocab: Vocab) -> Label | None
def normalize_es_type(v: str | None, vocab: Vocab) -> str | None
def normalize_outcome(v: str | None, vocab: Vocab) -> ReportedOutcome | None
def unknown_values(df: pd.DataFrame, col: str, mapping: dict) -> list[str]       # used by test_vocab

# pipeline/registry/effects.py
class EffectLedger:                                                  # data/curated/registry/effect_ids.csv
    def load(path) -> "EffectLedger"; def get_or_assign(key_kind: str, key: str, slug_hint: str, created_by: str) -> str; def merge(old: str, new: str, by: str) -> None; def save() -> None
def name_sources(legacy: pd.DataFrame, reversals: pd.DataFrame, docx: list[DocxEntry], curated_yaml: list[EffectYaml]) -> list[NameCandidate]
def cluster_names(cands: list[NameCandidate], threshold: int = 92) -> list[list[NameCandidate]]   # rapidfuzz, conservative; human merges via YAML
def build_effects(ledger, attempts, originals, names, curated_yaml) -> list[Effect]
def group_unnamed_fred(originals: list[OriginalStudy], attempts: list[Attempt]) -> dict[str, list[str]]  # study:<doi>:<study>:<desc_hash> keys

# pipeline/registry/projects.py
def load_project_yaml(paths) -> list[Project]
def assign_projects(attempts, pairs, projects) -> None               # via legacy `source`, fred_id prefix, FLoRA mega doi_r, curated lists

# pipeline/score/convert.py   (port of effect_size_transformations.R)
def to_r(value: float | None, es_type: str, n: float | None = None, df1: float | None = None, df2: float | None = None) -> tuple[float | None, str]
def parse_test_statistic(raw: str) -> TestStat | None                # "F(1, 37) = 6.40", "t(58) = 2.1", "X2(1, N = 45) = 43.02", "z = 2.94"
def r_ci(r: float, n: float, level: float = .95) -> tuple[float, float]
def p_from_r(r: float, n: float) -> float

# pipeline/score/criteria.py  (port of replication_outcomes.R)
def significance_r(r_o, n_o, r_r, n_r, p_o: float | None) -> str | None
def significance_agg(r_o, n_o, r_r, n_r) -> bool | None
def consistency_ci(r_o, r_r, n_r) -> bool | None
def consistency_pi(r_o, n_o, r_r, n_r) -> bool | None
def homogeneity(r_o, n_o, r_r, n_r) -> bool | None
def homogeneity_significance(r_o, n_o, r_r, n_r, p_o) -> str | None
def small_telescopes(r_o, n_o, r_r) -> bool | None
def compute_criteria(a: Attempt, o: OriginalStudy) -> Criteria | None
def derive_verdict(a: Attempt, c: Criteria | None, curated: dict | None) -> Verdict

# pipeline/score/effect_stats.py
def effect_stats(effect: Effect, attempts: list[Attempt]) -> EffectStats   # counts by outcome, pooled r (FE), shrinkage, first/last year, independence share

# pipeline/enrich/cache.py
class Cache:                                                         # data/cache/<source>/<key>.json, atomic writes, manifest counts
    def get(source: str, key: str) -> dict | None; def put(source: str, key: str, obj: dict) -> None
def import_legacy_caches(paths: Paths) -> None                       # splits the five Dec-2025 JSON files into per-key entries
# pipeline/enrich/openalex.py
def openalex_work_by_doi(doi: str, settings, cache) -> dict | None
def reconstruct_abstract(inverted_index: dict) -> str
def topics_from_work(work: dict) -> list[Label]
# pipeline/enrich/crossref.py
def crossref_bibliographic(query: str, settings, cache) -> list[dict]
def crossref_work(doi: str, settings, cache) -> dict | None          # relations, update-to (retractions)
# pipeline/enrich/abstracts.py
def abstract_cascade(doi: str, settings, cache) -> Label | None      # pubmed > crossref > openalex > s2 (U1 measured order)
# pipeline/enrich/persons.py
def resolve_persons(papers: list[Paper], cache) -> list[Person]

# pipeline/game/items.py
def build_game_items(attempts, pairs, originals, effects, papers, exclusions: pd.DataFrame, blocklist: pd.DataFrame, version: str) -> list[GameItem]
def stratify(items: list[GameItem]) -> dict[str, list[str]]

# pipeline/discover/seeds.py  (Phase 1 part of discovery)
def build_seed_set(pairs, papers, docx_links) -> pd.DataFrame        # doi_o union: FLoRA 2,589 + docx-resolved + curated
def flora_recall_ground_truth(flora: pd.DataFrame) -> pd.DataFrame   # doi_r by year_r (the U1 evaluation harness)

# pipeline/export/bundle.py
def write_bundle(paths, effects, papers, originals, attempts, pairs, projects, persons, topics, game_items, candidates_public, sources) -> Bundle
def write_search_shards(paths, effects, papers, persons) -> None
def write_api_doi_lookup(paths, papers, pairs) -> None               # FORRT-style hash3 records
def write_summary(paths, bundle: Bundle) -> None                     # data/build/SUMMARY.json

# pipeline/validate/
def validate_schemas(paths) -> list[str]; def validate_integrity(paths) -> list[str] (DuckDB SQL); def validate_counts(paths, accept_baseline: bool) -> list[str]
def scan_secrets(root: Path, exclude: list[str]) -> list[str]

# pipeline/models.py -> pipeline/schemas/*.json
def export_schemas(out_dir: Path) -> None                            # TypeAdapter(...).json_schema() per contract
```

Site-side Phase-1 modules (TypeScript):
- `site/src/content.config.ts` — one `file()`/custom loader per bundle table, validated with zod generated from `pipeline/schemas` (`npm run gen:types`).
- `site/src/lib/bundle.ts` — `loadBundle()`, lookup maps, `resolveHref(entity)`.
- `site/src/lib/charts/` — `ForestPlot.tsx`, `EffectScatter.tsx`, `OutcomeTimeline.tsx`, `CitationSparkline.tsx`, `scales.ts` (Preact, SSR by default).
- `site/src/islands/` — `Explorer.tsx` (client:visible), `Game.tsx` (client:load on /game only), `Typeahead.tsx` (client:idle, MiniSearch shards), `DoiResolver.tsx`.
- `site/scripts/postbuild.mjs` — pagefind over `dist/` (only pages with `data-pagefind-body`), page-budget count, link check.

Phase-1 exit criteria: `npm run build` passes all Section-5.3 tests except 14; SUMMARY.json baseline committed; effect, paper, project, topic pages render for every bundle entity; game v1 serves stratified items from `game_items.json`; docs generated; archive indexed; secrets scan clean; refresh.yml produces a PR on a forced run.

---

## 10. Open questions for the integrator (not blockers)
1. Custom domain availability decides whether GitHub Pages needs a user-site repo name (`<user>.github.io`) to avoid a `base` path; either way `import.meta.env.BASE_URL` is used everywhere so switching is free.
2. Whether legacy-only attempts (3,234) should be shown by default or behind a "include legacy coding" toggle — architecture supports both via `prov.source` filtering.
3. Person pages threshold (>= 3 papers) is a budget knob, not a product decision.
4. Supabase crowd tables (Phase 3) need an RLS design; anon insert-only + weekly aggregate pull keeps the site static.
