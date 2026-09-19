# D4 — The Discovery Engine: extending the corpus beyond FORRT and keeping it alive

Author: designer D4 (discovery engineer). Date: 2026-09-07. Status: design v1 (complete; numbers verified against files on disk and the U1/U7 live tests; anything marked EST is an extrapolation that the evaluation harness must replace with a measurement).

Inputs read: BRIEF.md, _DIGEST.md, U7-discovery.md (full), U1-harvester.md (sections 3-4), U5 data dictionary (digest), plus direct file checks listed in section 0.

---

## 0. Ground truth I verified myself (2026-09-07)

| Fact | Value | Where |
|---|---|---|
| FLoRA rows / replications | 2,815 / 2,526 | data/raw/forrt/fred-data/output_flora.csv |
| Unique replication `doi_r` per `year_r` | 2015 84 · 2016 103 · 2017 88 · 2018 141 · 2019 133 · 2020 178 · 2021 139 · 2022 131 · 2023 131 · 2024 137 · 2025 119 · 2026 74 (partial) | same, `type==replication`, DOI normalised |
| Share of those with "replicat" in `title_r` | 2015 .60 · 2018 .66 · 2021 .71 · 2023 .74 · 2024 .76 · 2025 .83 · 2026 .93 | same |
| FORRT's own OpenAlex route (`source=openalex`) per year | 2021 23 · 2022 16 · 2023 9 · 2024 15 · 2025 11 · 2026 3 | same |
| Replication DOIs that are PsyArXiv/OSF preprints | 65 contain `osf.io`, 34 start `10.31234` | same |
| `outcome_quote_source` | abstract 1,741 · OSF report 153 · full_text 35 · Abstract 29 · table 23 · supplementary/data-file variants ~200 | same |
| Old harvester file | 125 rows; 24 in FLoRA `doi_r`, 1 in `doi_o`; U1 judged ~86 genuine | output/final_2021_psychology_replications.csv |
| FORRT flora-validation export (live download today) | 263 rows x 37 cols; type replication 257; outcome successful 103 / failed 78 / mixed 74; source openalex 258; 249 of 263 `doi_r` already in FLoRA; columns include `screen_categories` (values `clearly_declared`, `context_transfer`), `outcome_reasoning`, `outcome_llm_model`, `pdf_source`, `parse_method`, `doi_r_published` | https://raw.githubusercontent.com/forrtproject/flora-validation/main/data/validated_export.csv (saved to scratchpad) |
| FORRT backlog "Additional Studies to be added" | sheet 1: 475 rows (191 Individual Study, 22 Preregistration, 14 Multiple Studies, 161 untyped), `doi_replication` filled 189, `doi_original` 185, "Data entered into ReD?" filled 8; sheet 2 (Google-form intake): 210 rows, all "Replication (different data)", 209 marked "Copied to Data?"=1 | FReD_2.4.1_2025-06-25.xlsx |
| FORRT "Check regularly for Replication" list | 9 rows: Transparent Replications (clearerthinking), I4R Replication Reports, ZBW Lab2, … last checked 1.2.2024 | same workbook |
| FORRT 2026-03-21 FLoRA snapshot | 1,507 rows; `self_identified_replication` True 1,493 / NaN 14 — no negatives, unusable as a negative set | data/raw/forrt/osf/flora_osf_2026-03-21.csv |
| docx famous effects | 362; 0 DOIs; `original_paper` field holds quoted title + first author + year + GS citation count | docx_parsed_entries.json |
| FLoRA inclusion rule (verbatim intent) | must self-identify as a replication before reporting results, must name the target study, must replicate a study/experiment (not a single association); registrations, Google-docs and blog posts excluded; outcome = how the replication authors characterise their results, usually in the abstract | output_flora_faq.md lines 78-91 |

Two consequences that shape everything below:

1. FORRT's discovery route ("replication" keyword in OpenAlex + R extraction + human validation, with an LLM outcome step judging by `outcome_llm_model`/`outcome_reasoning` columns) is already an LLM-assisted pipeline, but it delivers only 3-23 pairs/year. FORRT's own backlog sheet has 189 replication DOIs sitting uncoded. There is head-room, and the contribution format is known exactly (section 9).
2. Title-only discovery is capped at 60-83% recall depending on year (the "replicat" share above). The citation-graph route is the only route that reaches the remaining 17-40%, and it also yields the (doi_o, doi_r) pair directly instead of a lonely doi_r.

---

## 1. Design principles (non-negotiable)

1. **The unit of discovery is the pair** `(doi_o, doi_r, outcome, outcome_quote, outcome_quote_source)` — FLoRA's own row. A candidate paper without a resolved original is not "done"; it is a candidate for the resolver, not for the queue.
2. **Measure first, crawl second.** The evaluation harness (section 3) exists before any source module is allowed to run at scale. A pull request that touches a source, the scorer, the resolver, or a triage prompt must carry a harness report; the gate refuses regressions.
3. **Raw is immutable, decisions are git-tracked YAML, everything else is regenerable.** No hand-edited generated files (BRIEF non-negotiable 1). SQLite/Parquet caches can be deleted and rebuilt from raw + YAML.
4. **Provenance on every row:** which source(s) surfaced it, which model/prompt judged it, who accepted it, when, and whether FORRT has since taken it in.
5. **Cheap by construction:** OpenAlex under the free $1/day (or the free key's 10x), Semantic Scholar 1 rps with a free key, OSF 100 req/h keyless, LLM via Message Batches. Weekly steady state costs cents.
6. **Contribute back.** Accepted pairs are exported in FORRT's own column sets and submitted monthly; when FORRT merges a pair the wiki's badge flips from "community-added, pending FORRT" to "in FORRT since <release>".
7. **Never copy the old scripts** (51 files contain live keys). Port ideas listed in U1 as fresh code.

---

## 2. Architecture and repository layout

```
discovery/                         # Python package (3.13), CLI entry `python -m discovery`
  __init__.py
  config.py                        # paths, budgets, mailto, API keys from env only
  ids.py                           # DOI/OpenAlex/OSF id normalisation
  models.py                        # dataclasses: Seed, RawHit, Candidate, Target, TriageResult, Decision
  seeds.py                         # seed set construction + OpenAlex id resolution
  sources/
    base.py                        # Source protocol + state handling
    openalex_cites.py              # S1  citation-graph crawl
    openalex_title.py              # S2  field-wide title/abstract keyword crawl per year
    openalex_venues.py             # S3  venue-native feeds (AMPPS, RSOS, Collabra, Meta-Psych, CRSP, JOPD, PCI-RR via OpenAlex)
    osf_preprints.py               # S4  PsyArXiv / MetaArXiv / SocArXiv / EdArXiv
    osf_registrations.py           # S5  OSF Registries incl. Replication Recipe template
    s2_contexts.py                 # S6  Semantic Scholar citation contexts (outcome evidence + third-party verdicts)
    external_lists.py              # S7  Curate Science snapshot, OpenMKT, ReplicationWiki, Transparent Replications, I4R, FORRT backlog sheet, FORRT validated_export
    crossref_meta.py               # metadata only: canonical DOI record, relations (preprint<->article), update-to (retractions)
  enrich.py                        # abstract cascade (OpenAlex inverted index > Crossref > PubMed > S2), references, venue, topics
  resolve.py                       # original-study resolution (references ∩ seeds, author-year in text, Crossref bibliographic)
  prefilter.py                     # word-boundary regex noise filters + non-article DOI exclusion
  scoring.py                       # candidate priority score (features -> 0..1) used to order triage and the queue
  triage/
    schema.py                      # strict JSON schema (pydantic) for TriageResult
    prompts/v1.md                  # versioned system prompt (FLoRA criteria verbatim + few-shot)
    run.py                         # Batches API client, cache by (content_hash, prompt_version, model_id)
    verify.py                      # quote-in-text check, target consistency check
  dedup.py                         # vs FLoRA (weekly refresh), FReD, accepted/rejected decisions, preprint<->journal collapse
  queue.py                         # build review queue; read/write decision YAML; promotion
  export_forrt.py                  # FLoRA-column CSV, validated_export-column CSV, datasubmission_template.xlsx
  reverse.py                       # reverse discovery for effects with zero attempts
  crawl.py                         # weekly orchestrator, per-source cursors, budget meter, idempotent by (source, week)
  report.py                        # weekly markdown/JSON crawl report
  serve.py                         # local review server (writes YAML) used by the wiki's /review pages in dev mode
  eval/
    harness.py                     # recall-by-year, pair recall, precision on labelled sets, outcome replay
    gate.py                        # compares a report to eval/baseline.json; non-zero exit on regression
    fixtures/                      # recorded API cassettes + pinned FLoRA snapshot hash (offline, deterministic)
    labels/                        # git-tracked labelled sets (see 3.2)
    reports/                       # generated harness reports, one per commit hash

data/discovery/                    # raw + caches (gitignored except state/ and reports/)
  state/<source>.json              # cursors: last_from_date, per-seed cited_by_count_seen, sha256 of external lists
  raw/<source>/<YYYY-WW>.jsonl     # immutable hits as returned by the API (one line per hit, with fetched_at)
  cache/candidates.sqlite          # rebuildable: candidates, enrichment, triage results, features
  cache/flora_snapshots/<date>.csv # weekly FLoRA refresh with sha256
  reports/<YYYY-WW>.md             # auto crawl summary

curated/discovery/                 # git-tracked, human-owned
  decisions/<candidate_id>.yaml    # one decision file per candidate (append-only `events` list inside)
  reverse/<effect_id>.yaml         # reverse-discovery search logs per effect
  submissions/<YYYY-MM>-forrt.csv  # what we sent to FORRT, when, and the reply/issue link
  labels/                          # precision gold sets (also symlinked into discovery/eval/labels)
```

Data-flow: `raw hits -> candidates (per doi_r/url_r) -> enrich -> prefilter -> resolve originals -> score -> triage (LLM) -> verify -> dedup -> queue -> decision YAML -> overlay CSV -> normalized layer -> site (+ FORRT export)`.

The normalized layer (owned by another design) receives `curated/overlays/community_replications.csv` (generated by `queue.promote()`; never hand-edited) with the FLoRA columns plus provenance columns.

---

## 3. Evaluation harness — built FIRST

### 3.1 Metrics

| Metric | Definition | Ground truth |
|---|---|---|
| `recall_paper@year` | unique FLoRA replication `doi_r` with `year_r==Y` found by a source (or by the union) ÷ all FLoRA `doi_r` for Y | FLoRA snapshot pinned by sha256 (2,148 unique doi_r; per-year counts in section 0) |
| `recall_pair@year` | FLoRA `(doi_o, doi_r)` pairs for which we found doi_r AND the resolver produced doi_o | same |
| `recall_ceiling@year` | for title sources: share of FLoRA titles matching the query vocabulary (the structural cap) | FLoRA `title_r` |
| `precision@label_set` | share of candidates with `is_replication_attempt=yes` that a human labelled genuine | section 3.2 sets |
| `outcome_agreement` | LLM outcome vs FLoRA outcome on FLoRA rows whose `outcome_quote_source` is abstract (1,741 rows) — "triage replay" | FLoRA |
| `quote_grounding` | share of LLM `outcome_quote` found verbatim (or ≥0.95 token-ratio) in the supplied text | mechanical |
| `resolver_accuracy` | resolved `doi_o` == FLoRA `doi_o` on FLoRA pairs whose doi_r we re-process | FLoRA |
| `cost` | OpenAlex `meta.cost_usd` summed, S2 calls, LLM tokens, per source per week | API responses |
| `yield` | new (not in FLoRA, not previously decided) pairs per source per week, and after triage | pipeline |

Every metric is reported by source, by year, and for the union, with Wilson 95% intervals.

### 3.2 Labelled sets (git-tracked, `curated/discovery/labels/`)

1. `precision_2021_harvester.csv` — the 125-row file, labelled row by row (U1 did a 30-row sample and an overall judgement of ~86 genuine; the first review session labels all 125 with the review UI; the 24 already in FLoRA are auto-positive). Columns: `doi, label (genuine|meta|non_article|off_field|unclear), original_doi_if_known, note, labeller, labelled_at`.
2. `outcome_replay_flora.csv` — derived, not hand-made: FLoRA rows with abstract-sourced quotes (1,741) plus the 263-row FORRT `validated_export.csv` (outcome + quote + `screen_categories`). Used for `outcome_agreement`, `quote_grounding`, `resolver_accuracy`.
3. `hard_negatives.csv` — grows from reviewer rejections (every reject with reason is a label). Seeded with U1's counter-example 10.1177/09567976211005767 (meta-study) and the 39 non-genuine rows of set 1.
4. `famous_effects_links.csv` — the 362 famous effects' resolved original DOIs (from the D-team's Crossref title lookup), used by reverse discovery tests.

### 3.3 Fixtures and determinism

- `discovery/eval/fixtures/flora_<date>.csv` pinned with sha256 in `baseline.json`.
- API cassettes: the harness records OpenAlex/OSF/S2 responses for a fixed panel (e.g. 300 FLoRA doi_o seeds stratified by citation count + years 2019/2021/2024 for title crawls) into JSONL cassettes; `harness.py --offline` replays them so recall numbers are reproducible; `--record` refreshes monthly and logs the diff.
- The old harvester's `crossref_state_*.json` cursors are NOT reused (stale Elasticsearch cursors).

### 3.4 The gate

`python -m discovery.eval.gate --report eval/reports/<commit>.json --baseline eval/baseline.json`

Refuses (exit 2) if any of: union `recall_paper` for 2019-2025 drops > 1 percentage point; `precision@precision_2021_harvester` drops > 2 points; `outcome_agreement` drops > 2 points; `quote_grounding` < 0.98; weekly projected OpenAlex cost > budget. A pre-commit hook and CI job run the gate whenever files under `discovery/sources/`, `discovery/resolve.py`, `discovery/scoring.py`, `discovery/prefilter.py` or `discovery/triage/prompts/` change. Raising the baseline requires a `--accept-new-baseline` run with a one-line justification appended to `eval/BASELINE_LOG.md`.

### 3.5 Signatures

```python
# discovery/eval/harness.py
def load_ground_truth(flora_csv: Path, *, replications_only: bool = True) -> GroundTruth
    # GroundTruth: doi_r_by_year: dict[int, set[str]]; pairs: set[tuple[str, str]]; titles: dict[str, str]; sha256: str

def recall_by_year(found: Iterable[RawHit | Candidate], truth: GroundTruth, years: range) -> dict[int, RecallRow]
    # RecallRow(found:int, total:int, recall:float, ci_low:float, ci_high:float)

def pair_recall(candidates: Iterable[Candidate], truth: GroundTruth, years: range) -> dict[int, RecallRow]

def title_ceiling(truth: GroundTruth, vocabulary: list[re.Pattern], years: range) -> dict[int, float]

def precision_on_labels(triaged: Iterable[TriageResult], labels: pd.DataFrame) -> PrecisionRow

def outcome_replay(triager: Triager, truth_rows: pd.DataFrame, *, sample: int | None = None) -> ReplayRow
    # ReplayRow(n, outcome_agreement, quote_grounding, resolver_accuracy, confusion: dict)

def run_full(config: EvalConfig, *, offline: bool = True) -> EvalReport   # writes eval/reports/<git_sha>.json

# discovery/eval/gate.py
def compare(report: EvalReport, baseline: EvalReport, thresholds: Thresholds) -> GateResult   # .ok, .violations[]
```

---

## 4. Sources, ranked (what, why, expected yield, cost)

Rank = expected new genuine pairs per unit of cost after triage. All per-year yields are EST until the harness reports them.

| # | Source | Query primitive | Pre-LLM precision | Recall role | Cost/week | EST net-new genuine per year |
|---|---|---|---|---|---|---|
| S1 | OpenAlex `cites:` crawl of every seed original | `filter=cites:W1|…|W100,title.search:replicat*` (+ `title_and_abstract.search` for seeds < 300 citations), `from_publication_date` | 35-50% (U7: 92/130 title hits not in FLoRA on 50 seeds) | reaches the 17-40% of replications with no "replicat" in title; returns the pair directly | ~60 list calls ≈ $0.06 | 60-120 papers (first pass: 1,500-3,000 pairs for review, U7 EST) |
| S2 | OpenAlex field-wide keyword crawl per year | `primary_topic.field.id:32|20|33|14|28,title.search:replication|replicate|replicated|replicating,publication_year:Y` (+ `title_and_abstract.search:"failed to replicate"|"direct replication"|"conceptual replication"|"registered replication report"|"many labs"`) | 40-60% | catches replications of originals not in seeds (FORRT's own method) | 5-10 calls | 80-150 papers (470-510 works/yr in field 32 vs FLoRA's ~130; old harvester found 62 genuine non-FLoRA papers for 2021 with a worse primitive) |
| S3 | Venue-native feeds through OpenAlex source ids | `primary_location.source.id:S…,from_publication_date` for AMPPS, RSOS, Collabra, Meta-Psychology, CRSP, JOPD, Cortex RRs, Psych Science RRs, Social Psychology, JESP; plus `title.search:"registered report"` | ~80% for RRR/CRSP, ~20% for general venues (post-filter by S2 vocabulary) | catches RRs whose titles never say "replication" | 10 calls | 10-30 papers |
| S4 | OSF Preprints (PsyArXiv, MetaArXiv, SocArXiv, EdArXiv) | `api.osf.io/v2/preprints/?filter[provider]=psyarxiv&filter[date_published][gte]=…` then local keyword filter on title+description | ~60% | 6-18 months lead; ~623 total "replication" titles ≈ 60-80/yr | 3-5 pages | 20-40 unique papers (half later get journal DOIs → collapsed) |
| S5 | OSF Registrations | `/v2/registrations/?filter[title]=replication&filter[date_registered][gte]=…`; client-side filter on `registration_supplement` = Replication Recipe (pre/post-completion); LLM over `registered_meta` | ~30% (datasets, course projects) | unique: unpublished/student/CREP/Expra replications and the "file drawer" (registered, never reported) | 5-10 pages | 30-60 registrations/yr; NOT contributable to FLoRA (their rule) but shown as a separate evidence tier |
| S6 | Semantic Scholar citation contexts | `/graph/v1/paper/DOI:{doi_o}/citations?fields=contexts,intents,externalIds&limit=200` for seeds with citation deltas; regex `replicat|failed to (find|replicate)|did not replicate|reproduc` | ~70% when matched; ~2% of citations match | outcome evidence and third-party verdicts ("failed to be replicated (Panero 2016)") that name both papers | ~1,000 calls at 1 rps | 10-30 pairs/yr + outcome quotes for hundreds |
| S7 | External lists | Curate Science (OSF sub-dataset on disk, 831 rows), OpenMKT (47, CSV export), ReplicationWiki (Semantic MediaWiki `api.php?action=ask`; HTTP 500 today — retry monthly), Transparent Replications (14 reports, ResearchBox), I4R reports list, FORRT backlog sheet (189 replication DOIs), FORRT validated_export.csv (263) | ~95% | narrow; value = curated outcomes and effect-level numbers | monthly, hash-compare | 20-50 pairs one-off, ~10/yr after |
| S8 | Crossref (metadata only) | `/works/{doi}` for canonical record, `relation.is-preprint-of/has-preprint`, `update-to` | n/a | preprint↔article collapse, retraction flags | 10/s single-DOI | 0 discovery; prevents duplicates |

Not used: Crossref `query.title` discovery (dominated by S2; U1 measured 17% recall), Scite/PubPeer (paid/keyed signal layers, per-DOI link only), PCI-RR scraping (bot-blocked; covered via S3 `registered report`), Google Scholar (ToS).

**Seeds for S1/S6** = FLoRA `doi_o` (2,589) ∪ FReD `doi_o` (786, mostly overlapping) ∪ legacy FReD 2.4.1 `doi_original` (1,635 normalised; 937 are in neither current file) ∪ the 362 famous effects' originals (after title→DOI resolution) ∪ `original_doi` of every accepted candidate. EST 3,500-4,000 seeds → 35-40 OR'd calls per pass.

**Combined steady-state EST: 150-250 net-new replication papers/year beyond FLoRA (300-500 pairs, since multi-study papers yield several pairs), plus 30-60 registrations/yr in the separate tier.** Sanity anchors: FLoRA adds ~130 published replications/yr; the old harvester alone found 62 genuine 2021 papers FLoRA lacked at harvest time; S1 finds 92 non-FLoRA title hits from only 50 seeds. The first backfill pass (2010-2026) is EST 1,500-3,000 pairs for review — about 25-50 hours of human review at 1 min/candidate with the UI in section 8, spread over months, prioritised by score.

---

## 5. Source modules — contracts and signatures

```python
# discovery/models.py
@dataclass(frozen=True)
class Seed:
    doi: str                      # normalised
    openalex_id: str | None
    cited_by_count: int | None
    origin: Literal["flora", "fred", "fred_legacy", "famous", "accepted"]
    effect_ids: tuple[str, ...]   # wiki effect ids this original belongs to

@dataclass
class RawHit:                     # exactly what a source returned, plus minimal envelope
    source: str                   # "openalex_cites" | "openalex_title" | ... 
    fetched_at: str               # ISO UTC
    week: str                     # "2026-W37"
    identifier: str               # doi (normalised) or url/osf id when no DOI
    identifier_kind: Literal["doi", "url", "osf_registration", "osf_preprint", "openalex"]
    seed_doi: str | None          # for cites/contexts sources
    payload: dict                 # raw API record (select-slimmed)

@dataclass
class Target:                     # one original the candidate claims to replicate
    ref_text: str | None          # "Bargh, Chen & Burrows (1996), Experiment 2"
    doi_o: str | None
    resolution: Literal["cited_seed", "reference_list_author_year", "crossref_bibliographic", "llm_only", "unresolved"]
    resolution_confidence: float
    study_o: str | None           # "Study 2"
    outcome: Literal["successful", "failed", "mixed", "not_reported", "n/a"] | None
    outcome_quote: str | None
    outcome_quote_source: Literal["abstract", "full_text", "osf_report", "registration", "contexts"] | None

@dataclass
class Candidate:
    candidate_id: str             # sha1("doi_r|" + identifier) - stable across weeks
    identifier: str; identifier_kind: str
    doi_r: str | None; url_r: str | None
    title: str | None; abstract: str | None; abstract_source: str | None
    year: int | None; venue: str | None; issn: tuple[str, ...]
    work_type: str | None         # OpenAlex type; "article", "preprint", "erratum"...
    openalex_id: str | None; referenced_works: tuple[str, ...]
    primary_topic: dict | None    # OpenAlex topic/subfield/field
    sources: list[RawHit]         # every hit that surfaced it (provenance)
    seed_dois: set[str]           # originals it cites that are seeds
    contexts: list[dict]          # S2 own-paper and third-party contexts
    targets: list[Target]
    features: dict[str, float]
    score: float | None
    triage: TriageResult | None
    dedup: DedupStatus | None     # in_flora / in_fred / decided / preprint_of_known / new
```

```python
# discovery/sources/base.py
class Source(Protocol):
    name: str
    def fetch(self, *, seeds: Sequence[Seed] | None, since: date | None, state: SourceState, budget: Budget) -> Iterator[RawHit]: ...
    def cursor_after(self, hits: Sequence[RawHit], state: SourceState) -> SourceState: ...

class SourceState(TypedDict, total=False):
    last_from_date: str; per_seed: dict[str, dict]; list_sha256: dict[str, str]; last_run: str

def load_state(name: str) -> SourceState
def save_state(name: str, state: SourceState) -> None      # atomic write; ONE process per state file (U1 lesson)
def write_raw(hits: Iterable[RawHit], source: str, week: str) -> Path   # data/discovery/raw/<source>/<week>.jsonl, append-safe

# discovery/sources/openalex_cites.py
def batches_of_seed_ids(seeds: Sequence[Seed], size: int = 100) -> Iterator[list[str]]
def build_cites_filter(ids: Sequence[str], *, mode: Literal["title", "title_abstract"], from_date: date | None) -> str
def fetch_citing_replications(seeds, *, state, budget, backfill_days: int = 30) -> Iterator[RawHit]
    # Q1 title pass for all seeds with cited_by_count delta; Q2 abstract pass only if cited_by_count < 300
    # select=id,doi,title,publication_year,type,primary_topic,referenced_works,abstract_inverted_index,is_retracted,primary_location,cited_by_count

# discovery/sources/openalex_title.py
VOCABULARY: list[str]   # title: replication|replicate|replicated|replicating|"registered replication report"|"many labs"|"multi-site"|"multisite"; abstract phrases: "failed to replicate"|"direct replication"|"conceptual replication"|"replication attempt"|"we replicated"|"replication and extension"
FIELDS = (32, 20, 33, 14, 28)   # Psychology, Economics, Social Sciences, Business, Neuroscience
def fetch_year(year: int, *, mode: Literal["title", "abstract_phrases"], state, budget) -> Iterator[RawHit]   # cursor=* deep paging, per_page=200
def fetch_incremental(since: date, *, state, budget) -> Iterator[RawHit]

# discovery/sources/openalex_venues.py
VENUES: dict[str, str]   # name -> OpenAlex source id, resolved once via /sources?search= and cached in state
def fetch_since(since: date, *, state, budget) -> Iterator[RawHit]

# discovery/sources/osf_preprints.py
PROVIDERS = ("psyarxiv", "metaarxiv", "socarxiv", "edarxiv", "osf")
def fetch_since(since: date, *, state, token: str | None) -> Iterator[RawHit]   # page[size]=100, sort=-date_published; respects 100 req/h keyless
def collapse_version(doi: str) -> str                                            # 10.31234/osf.io/2wpqe_v1 -> 10.31234/osf.io/2wpqe

# discovery/sources/osf_registrations.py
def fetch_since(since: date, *, state, token: str | None) -> Iterator[RawHit]   # filter[title]=replication OR filter[tags]; client-side registration_supplement filter
def parse_replication_recipe(registered_meta: dict) -> RecipeAnswers            # item1..item37 mapping ported from rr_scraper_links.R; closeness = sum(7 items; exact 2/close 1/different -1)

# discovery/sources/s2_contexts.py
def fetch_contexts(doi_o: str, *, offset: int, api_key: str | None) -> tuple[list[dict], int | None]
def replication_context_hits(contexts: Iterable[dict]) -> Iterator[RawHit]       # keyword regex on contexts; emits (citing doi, seed doi, sentence)
def third_party_verdicts(contexts) -> Iterator[Verdict]                          # sentences naming original AND a replication (Author, Year) -> feeds resolve.py and the wiki's "what the literature says" panel

# discovery/sources/external_lists.py
class ExternalList(Protocol):  name: str; url: str | Path; license: str
    def download(self) -> bytes; def parse(self, raw: bytes) -> Iterator[RawHit]   # emits pairs with outcome when the list has one
LISTS = [CurateScienceSnapshot, OpenMKT, ReplicationWiki, TransparentReplications, I4RReports, ForrtBacklogSheet, ForrtValidatedExport]
def refresh(lists=LISTS, *, state) -> Iterator[RawHit]   # sha256-compare, emit only when changed

# discovery/sources/crossref_meta.py
def work(doi: str) -> dict | None
def relations(doi: str) -> dict[str, list[str]]          # is-preprint-of / has-preprint / is-version-of
def update_to(doi: str) -> list[dict]                    # retraction / correction notices
```

Rate/etiquette constants live in `config.py`: OpenAlex `mailto`, optional `OPENALEX_API_KEY`; Crossref UA with mailto, ≤3 list req/s; S2 `x-api-key`, 1 rps; OSF `Authorization: Bearer` optional. All fetchers use exponential backoff on 429/5xx and write to raw JSONL before any parsing (crash-safe).

---

## 6. Candidate construction, prefilter, resolution, scoring

```python
# discovery/ids.py
def normalize_doi(raw: object) -> str | None          # lowercase; strip https://(dx.)doi.org/, doi:, trailing punctuation, percent-decode; PsyArXiv _vN collapse
def is_non_article_doi(doi: str, title: str | None, work_type: str | None) -> bool
    # APA .supp suffix; titles starting "Supplemental Material for", "Corrigendum", "Correction to", "Erratum", "Retraction", "Commentary on", "Reply to", "Response to"; OpenAlex type in {erratum, editorial, letter, paratext, retraction, supplementary-materials}
def openalex_id_from(work: dict) -> str

# discovery/enrich.py
def abstract_cascade(cand: Candidate) -> tuple[str | None, str | None]   # OpenAlex inverted index -> Crossref -> PubMed e-utils -> S2; returns (text, source)
def reinvert(inv: dict[str, list[int]]) -> str
def enrich(cand: Candidate) -> Candidate                                   # fills abstract, references, venue, issn, topic

# discovery/prefilter.py
NOISE = [r"\bDNA replication\b", r"\bviral replication\b", r"\bdata replication\b", r"\breplication fork\b", r"\bblockchain\b", ...]   # WORD-BOUNDARY regexes (U1: substring lists rejected 8.1% of genuine titles)
META = [r"\breplication crisis\b", r"\bhow to measure\b", r"\bsimulation study\b", ...]                                              # routes to a 'meta-science' collection, not the bin
def prefilter(cand: Candidate) -> Literal["keep", "drop_noise", "drop_non_article", "route_meta"]
    # a candidate that cites a seed is NEVER dropped by NOISE alone (topic can be off for GWAS-style seeds; let the LLM decide)

# discovery/resolve.py
AUTHOR_YEAR = re.compile(r"\b([A-Z][\w'’-]+(?:,? (?:&|and) [A-Z][\w'’-]+|(?: et al\.?)))?\s*\((\d{4}[a-z]?)\)")
def author_year_mentions(text: str) -> list[tuple[str, int]]
def resolve_targets(cand: Candidate, seeds_by_doi: Mapping[str, Seed], seeds_by_openalex: Mapping[str, Seed]) -> list[Target]
    # 1) referenced_works ∩ seed OpenAlex ids  -> resolution="cited_seed" (conf .95 if author-year also appears in title/abstract, .7 otherwise)
    # 2) author-year mentions in title/abstract matched against the candidate's own reference list (Crossref reference[] or OpenAlex referenced_works metadata) -> "reference_list_author_year" (.85)
    # 3) Crossref query.bibliographic on the ref string -> "crossref_bibliographic" (.6, needs LLM confirmation)
    # 4) else "unresolved"
def resolve_famous_original(entry: dict) -> tuple[str | None, float]      # for the 362: Crossref query.bibliographic on the quoted title + surname + year; accept if title ratio>=0.9 and year within ±1

# discovery/scoring.py
FEATURES = ("cites_seed", "seed_is_famous", "n_seeds_cited", "title_strong_phrase", "title_any_replicat", "abstract_first_person_replicate",
            "abstract_outcome_cue", "venue_prior", "topic_field_in_scope", "is_preprint", "s2_context_hit", "third_party_verdict",
            "n_sources", "in_external_list", "registration_recipe", "work_type_article")
def features(cand: Candidate, priors: Priors) -> dict[str, float]         # priors: venue frequency from FLoRA journal_r (recomputed weekly; PLOS ONE / Sci Reports / RSOS never blacklisted)
def score(features: dict[str, float], weights: Weights) -> float           # logistic; weights fitted on labelled sets (3.2) by eval/harness; frozen per version and logged in provenance
```

`score` orders (a) which candidates go to the LLM first when the LLM budget is capped and (b) the review queue. It never auto-accepts on its own.

---

## 7. LLM triage

### 7.1 Input package per candidate (≈1,200-1,800 tokens)

title, abstract (full, not truncated), year, venue, work type, up to 3 cited seeds (title/first author/year/doi), up to 5 S2 context sentences (own-paper first, then third-party), the FLoRA inclusion criteria verbatim (system prompt, cached), and the candidate's author-year mentions. For S5 registrations: the `registered_meta` answers (item1 target statement, closeness items, post-completion outcome items).

### 7.2 Output schema (strict; `output_config.format` JSON schema, pydantic-validated)

```json
{
  "schema_version": "triage.v1",
  "is_replication_attempt": "yes | no | unclear",
  "replication_type": "direct | close | conceptual | reproduction | multi_site | replication_and_extension | none",
  "self_identifies_before_results": true,
  "is_meta_or_commentary": false,
  "targets": [
    {
      "ref_text": "Kidd & Castano (2013), Experiment 1-5",
      "original_doi": "10.1126/science.1239918 | null",
      "doi_basis": "cited_seed | reference_list | text_only | none",
      "study_o": "string | null",
      "outcome": "successful | failed | mixed | not_reported | n_a",
      "outcome_quote": "verbatim sentence(s) from the supplied text",
      "outcome_quote_source": "abstract | full_text | registration | contexts"
    }
  ],
  "discipline": "social | cognitive | developmental | clinical | personality | neuro | economics | marketing | management | education | linguistics | xphi | other",
  "confidence": 0.0,
  "reasons": "one line",
  "model_id": "filled by run.py",
  "prompt_version": "filled by run.py",
  "content_hash": "filled by run.py"
}
```

Rules encoded in `prompts/v1.md`: outcome only from quoted text (no inference); `not_reported` when the text does not characterise results; "replication and extension" counts as a replication; methods/commentary/meta-science → `no` + `is_meta_or_commentary=true`; a target gets `original_doi` only when `doi_basis` is `cited_seed` or `reference_list` (text-only mentions stay null and go to the resolver's Crossref step); multi-study papers list every target; reproductions (same data) are typed `reproduction`.

### 7.3 Verification (`triage/verify.py`)

- `quote_grounded(quote, text) -> bool` (exact substring, else token-ratio ≥ 0.95 after whitespace/unicode normalisation) — failing quotes flag `quote_not_found` and force review.
- `targets_consistent(result, cand)`: every `original_doi` with basis `cited_seed` must be in `cand.seed_dois`; `reference_list` must be in the candidate's resolved references.
- Outcome vocabulary mapped to FLoRA's exactly (`successful|failed|mixed`; `not_reported` → FLoRA "descriptive only"/"uninformative" decided by reviewer).

### 7.4 Routing

| Condition | Route |
|---|---|
| `yes`, confidence ≥ .90, ≥1 target with resolved DOI (basis cited_seed/reference_list) and grounded quote, not in FLoRA | queue tier **A** ("one-click accept"; still human-confirmed; 10% re-audited quarterly) |
| `yes` or `unclear`, .50-.90, or unresolved target, or quote not found | queue tier **B** (full review) |
| `no`, confidence ≥ .80 | auto-reject, kept in cache for recall audits; sampled 5%/week into tier B as a recall check |
| `is_meta_or_commentary` | `collections/meta-science` overlay candidate (separate, low-priority queue) |
| `unclear` from the first model | escalate to the stronger model at higher effort, then route by the second result |

### 7.5 Cost and models

Per U7 (claude-api skill prices cached 2026-06-24): Sonnet-class via Batches ≈ $2.25 per 1,000 candidates, Opus-class ≈ $5.63; prompt caching of the system prompt cuts input by ~40%. First backfill EST 8,000-12,000 candidates → $20-70; weekly 100-300 → cents. Recommendation: Sonnet-class with adaptive thinking at low effort for the bulk, Opus-class at high effort for escalations (outcome wording such as "smaller but significant" is where cheap models drift — do not use a Haiku-class model for outcome). Model ids are read from config at run time and stored in every result; re-triage of the whole cache when a prompt or model changes is a single command and shows up in the harness before merge.

```python
# discovery/triage/run.py
def content_hash(cand: Candidate) -> str
def build_input(cand: Candidate, *, max_contexts: int = 5) -> TriageInput
def triage_batch(cands: Sequence[Candidate], *, model_id: str, prompt_version: str, effort: str, cache: TriageCache) -> list[TriageResult]   # Message Batches; skips cache hits
def escalate(result: TriageResult, cand: Candidate, *, model_id: str) -> TriageResult
# discovery/triage/verify.py
def quote_grounded(quote: str, text: str, *, min_ratio: float = 0.95) -> bool
def verify(result: TriageResult, cand: Candidate) -> TriageResult   # sets flags: quote_not_found, target_inconsistent
```

---

## 8. Dedup, review queue, decisions, promotion

### 8.1 Dedup (`dedup.py`)

```python
def refresh_flora(url: str = "https://raw.githubusercontent.com/forrtproject/FReD-data/main/output/flora.csv") -> FloraSnapshot   # weekly; sha256; stored under data/discovery/cache/flora_snapshots/
def known_pairs(snapshot: FloraSnapshot, fred: pd.DataFrame, legacy: pd.DataFrame) -> KnownIndex   # sets of doi_r, doi_o, (doi_o,doi_r), url_r, alt identifiers, 3-char md5 hashes
def collapse_preprint(cand: Candidate) -> Candidate     # via Crossref relation / OSF attributes.doi / OpenAlex primary_location.version; keep both ids in cand.aliases
def classify(cand: Candidate, known: KnownIndex, decisions: DecisionIndex) -> DedupStatus
    # new | in_flora (pair) | doi_r_in_flora_new_pair | in_fred_only | preprint_of_known | previously_decided(accepted|rejected) | reappeared_after_reject (source changed)
```
`doi_r_in_flora_new_pair` is kept: a known replication paper can still contribute an unlisted (doi_o, doi_r) pair (multi-study papers).

### 8.2 Decision store (git-tracked YAML, one file per candidate)

`curated/discovery/decisions/<candidate_id>.yaml`
```yaml
candidate_id: 3f9c…            # sha1 of the normalised identifier
doi_r: 10.1177/0956797621989733
url_r: null
title_r: "…"
status: accepted               # accepted | rejected | deferred | needs_original | meta_science
pairs:                          # one entry per accepted target
  - doi_o: 10.1037/0022-3514.71.2.230
    study_o: "Experiment 2"
    outcome: failed
    outcome_quote: "…verbatim…"
    outcome_quote_source: abstract
    replication_type: direct
    discipline: social
provenance:
  sources: [openalex_cites, osf_preprints]
  seed_dois: [10.1037/0022-3514.71.2.230]
  triage: {model_id: "…", prompt_version: triage.v1, confidence: 0.93, content_hash: "…"}
  score: 0.87
forrt:
  status: pending              # pending | submitted | merged_upstream | rejected_upstream
  submitted_in: null           # curated/discovery/submissions/2026-10-forrt.csv
  merged_release: null         # set automatically when the pair appears in a FLoRA refresh
events:                         # append-only
  - {at: 2026-09-14T10:02:00Z, who: leo, action: accept, note: "quote checked against abstract"}
```
Reject reasons are an enum (`not_a_replication | meta_or_commentary | non_article | off_field | duplicate | no_target | outcome_unclear | other`) so they become labels for `hard_negatives.csv` automatically.

### 8.3 Review UI inside the wiki

Route `/review/` in the Astro site, built from `data/discovery/cache/queue.json` (generated by `queue.build()`), one page per candidate `/review/<candidate_id>/` plus list views by tier, source, score, year and seed effect. Each page shows: title/venue/year/OA link; abstract with the LLM `outcome_quote` highlighted; the proposed targets with the seed original's title and the wiki effect it belongs to; the S2 contexts; the dedup status; the triage JSON collapsed; buttons **Accept**, **Accept with edits** (edit outcome/quote/target/study), **Reject (reason)**, **Defer**, **Needs original**.

Write path (the site is static): the buttons POST to `discovery serve` (localhost:8787, `serve.py`, a ~150-line stdlib HTTP server) which validates and writes the YAML file and rebuilds `queue.json`; the page reloads. In dev this is `npm run review` (starts serve.py + `astro dev`). Optional hosted mode: the same island posts to a Supabase table `review_decisions` (RLS: allow-listed reviewer emails); `discovery sync-decisions` pulls rows into YAML and git is still the source of truth. The public build ships the read-only queue ("candidates awaiting review", counts by tier) — transparency about what the wiki has and has not yet judged — but no write buttons.

Every effect page and every original-paper page also gets an **Open candidates** tab listing tier-A/B candidates whose targets resolve to that original (U7 idea), linking into `/review/<id>/`.

```python
# discovery/queue.py
def build(cands: Iterable[Candidate], decisions: DecisionIndex, *, tiers=("A","B","meta")) -> QueueSnapshot   # writes cache/queue.json
def load_decisions(root: Path) -> DecisionIndex
def record(decision: Decision, root: Path) -> Path                    # validates enum/quote/doi; appends event; atomic write
def promote(decisions: DecisionIndex, *, out_csv: Path) -> pd.DataFrame
    # accepted pairs -> curated/overlays/community_replications.csv with FLoRA columns + origin=community, provenance columns, forrt_status
def mark_merged_upstream(decisions: DecisionIndex, snapshot: FloraSnapshot) -> list[str]   # flips forrt.status when the pair appears in FLoRA
# discovery/serve.py
def main(port: int = 8787, decisions_root: Path = ...) -> None       # POST /decision {candidate_id, action, edits...}; GET /queue.json
```

### 8.4 Promotion and badges

`community_replications.csv` rows enter the normalized layer with `origin=community` and are rendered with the badge **"Community-added · pending FORRT"** (vermilion outline) → **"Submitted to FORRT <date>"** → **"In FORRT since <release>"** (ultramarine fill). A mouse-over shows sources, model/prompt, reviewer initials and date. Registrations (S5) never get FLoRA badges; they render in an **"Registered / in progress"** tier with the OSF link and the Replication Recipe answers, and after 3 years without a report they show **"registered 2022, no report found as of <date>"** (file-drawer signal).

---

## 9. Export back to FORRT

Three targets, all generated by `export_forrt.py` from decision YAML:

1. **Pair-level (FLoRA):** CSV in the column set FORRT's own `validated_export.csv` uses (`doi_r, doi_o, oa_work_id_r, oa_work_id_o, url_r, url_o, ref_r, ref_o, abstract_r, year_r, year_o, type, outcome, outcome_quote, outcome_quote_source, source, doi_r_published, alt_identifier_r, study_r, title_r, study_o, title_o, screen_categories, outcome_reasoning, outcome_llm_model, bibtex_ref_o, bibtex_ref_r`), `source="psychrepwiki"`. FORRT merges this file into FLoRA by common columns (prepare_flora.qmd lines 229-249), so a pull request/issue on `forrtproject/flora-validation` or `FReD-data` with this CSV is the lowest-friction path. Fallback: the "Additional Studies to be added" Google-form columns (Type of Reference, Field, Description, Reference original APA+DOI, Reference replication APA+DOI, Type of Study, Outcome, Outcome quote + page).
2. **Effect-level (FReD):** `datasubmission_template.xlsx` sheet `data` for accepted candidates whose reviewer also entered `es_original`/`es_replication` (converted to Pearson r with the ported R-package rules), `n_original`, `n_replication`, closeness items, `osf_link`, `result`, `ref_original`, `ref_replication`, `tags`, `subjects`, `source`, `notes`.
3. **Submission log:** `curated/discovery/submissions/<YYYY-MM>-forrt.csv` + a line in `SUBMISSIONS.md` with the issue/PR URL and FORRT's reply; `mark_merged_upstream` closes the loop.

```python
def export_flora_pairs(decisions: DecisionIndex, *, since: date | None) -> pd.DataFrame
def export_validated_export_format(decisions, *, since) -> pd.DataFrame
def export_fred_template(decisions, template_xlsx: Path, out_xlsx: Path) -> Path
def log_submission(df: pd.DataFrame, *, channel: Literal["github_issue","email","web_form"], url: str | None) -> Path
```

Attribution: every export and every wiki page carries the FLoRA/FReD CC-BY citation from `output_citation.txt`.

---

## 10. Weekly incremental crawl (`crawl.py`)

`python -m discovery crawl --week 2026-W37` (idempotent per week; rerun rewrites only that week's raw files).

1. `dedup.refresh_flora()`; recompute venue priors; `mark_merged_upstream`.
2. `seeds.build()`: union of seeds; resolve new DOIs to OpenAlex ids (`filter=doi:a|b|…` 50 per call); fetch `cited_by_count` for all seeds in the same calls (≈70 calls); persist `cited_by_count_seen`.
3. S1 for seeds with a citation delta (or never crawled), `from_publication_date = last_run − 30 days` (OpenAlex backfills); title pass for all, abstract pass for < 300 citations.
4. S2 incremental (`from_publication_date`), S3 venues, S4 preprints, S5 registrations (`date_registered ≥`), S6 contexts for seeds with deltas (bounded at 1,000 calls/week), S7 monthly.
5. Build/merge candidates; enrich; prefilter; resolve; score.
6. Dedup → new candidates only → triage (Batches) → verify → route.
7. `queue.build()`; `report.write_week()` (counts per source, cost, yield, recall spot-check against the FLoRA refresh: any pair FORRT added this week that we had not surfaced is logged as a **miss** with its source — the harness's live recall).
8. Monthly (first crawl of the month): S7 refresh, `export_forrt`, and a reverse-discovery sweep (section 11).

Budget meter: `Budget(openalex_usd_per_day=0.9, s2_calls_per_week=1000, osf_calls_per_hour=90, llm_usd_per_week=5)`; every fetcher debits it using `meta.cost_usd` where available and stops cleanly (state saved) when exhausted — the next week resumes from cursors. EST weekly OpenAlex cost with ~3,800 seeds: ~40 (seed metadata) + ~80 (S1) + ~10 (S2/S3) list calls ≈ $0.13 keyless; the first backfill (S1 for all seeds with cursor paging over ~7,000 title hits + S2 for 2010-2026 ≈ 5,000-6,000 works at 200/page) is ≈ 300-400 calls ≈ $0.40 — fits one free day; with the free API key it is 10x more head-room anyway.

Concurrency rule (from the U1 crash): one process per state file; the CLI takes a lock file in `data/discovery/state/.lock`.

```python
def crawl_week(week: str, *, sources: Sequence[str] = ALL, budget: Budget, dry_run: bool = False) -> WeekReport
def backfill(years: range, *, sources: Sequence[str], budget: Budget) -> None        # first pass; chunked per year and seed batch; resumable
```

Scheduling: a Windows Task Scheduler / cron entry or a GitHub Actions workflow (secrets from env) running `crawl --week` every Monday and pushing the raw/state/report changes; decisions remain human commits.

---

## 11. Reverse discovery ("no replication found as of <date>")

Targets: the famous effects with zero linked attempts after the D-team's linking pass, FReD originals in the legacy-only set (937 DOIs in neither current FReD nor FLoRA), and any effect a reader flags ("has this been replicated?").

```python
# discovery/reverse.py
@dataclass
class ReverseSearchLog:
    effect_id: str; doi_o: str; openalex_id: str | None; searched_at: str
    queries: list[dict]        # {source, query, n_results, n_candidates_after_prefilter, cost_usd}
    candidates: list[str]      # candidate_ids pushed to the queue
    registrations: list[str]   # OSF registration ids naming this original (in-progress tier)
    verdict: Literal["candidates_found", "registered_only", "none_found"]
    next_check: str            # searched_at + 90 days (or + 30 if cited_by_count grew >10%)

def reverse_search(effect_id: str, doi_o: str, *, budget: Budget) -> ReverseSearchLog
    # S1 title+abstract cites pass for this single seed (no citation cap); S6 contexts full scan; S5 registrations with author-year + effect name; S4 preprints with author-year; S2 title search with the effect's alias names
def sweep(effect_ids: Sequence[str], *, budget) -> list[ReverseSearchLog]   # monthly, those past next_check
def render_statement(log: ReverseSearchLog) -> str
    # "No replication attempt found as of 7 Sep 2026 — searched 1,624 citing works (OpenAlex), 412 citation sentences (Semantic Scholar), OSF registrations and PsyArXiv. 1 registration (2024) names this study; no report yet."
```

The statement is stored in `curated/discovery/reverse/<effect_id>.yaml` and rendered on the effect page with the date; it is a falsifiable claim with a search log behind it, which is the honest alternative to silence. Reverse-search logs also feed a **"Most wanted"** list (most-cited originals with `verdict=none_found`, using OpenAlex `cited_by_count`), which is the file-drawer-hunting page for the wiki.

---

## 12. Yield model per year (EST; to be replaced by harness output)

| Route | Candidates/yr | Precision after triage | Genuine/yr | Already in FLoRA | Net new/yr |
|---|---|---|---|---|---|
| S2 field-wide title (fields 32+20+33+14+28) | 600-800 (470-510 in field 32 alone) | 45-60% | 300-420 | ~110 (FLoRA's title-bearing share) | 80-150 papers |
| S1 cites crawl (incremental) | 300-600 | 40-60% | 150-300 | large overlap with S2 | 60-120 papers (the no-"replicat"-in-title tail + pairs for known papers) |
| S3 venues | 100-200 | 60-80% | 60-140 | mostly in S2 | 10-30 |
| S4 preprints | 60-80 | ~60% | 40-50 | half collapse into S2 later | 20-40 |
| S5 registrations | 150-300 | ~30% | 50-90 | n/a (excluded by FORRT) | 30-60 (separate tier) |
| S6 contexts | pairs for existing candidates | ~70% | 20-40 pairs | many known | 10-30 |
| S7 lists | one-off 300-500 | ~95% | — | mostly known | 20-50 once, ~10/yr |
| **Union (papers, FLoRA-eligible)** | | | | | **150-250/yr** (300-500 pairs) |

Backfill 2010-2026 (17 years, S1+S2 dominant): EST 1,500-3,000 new pairs for review; human review ≈ 25-50 h total at 1 min/candidate, front-loaded by score so the first 500 reviewed carry most of the value.

Recall targets for the harness (union of sources, offline cassettes): `recall_paper@2021 ≥ 0.85` (old harvester: 0.171), `recall_pair@2021 ≥ 0.70` after the resolver; `precision@precision_2021_harvester ≥ 0.80`; `outcome_agreement ≥ 0.90` on the abstract-sourced FLoRA rows (FReD↔FLoRA human coders agree 93.3%, so 0.90 is the realistic ceiling band).

---

## 13. Build order (what to implement, in sequence)

1. `ids.py`, `models.py`, `eval/harness.py` with `load_ground_truth` + `recall_by_year` + `title_ceiling` + the 125-row labelling task in the review UI (labels set 1). Ship the first harness report with zero sources — the baseline that everything must beat.
2. `sources/openalex_title.py` for 2019/2021/2024 + cassette recording; report recall/ceiling. Then `openalex_cites.py` on a 300-seed panel; report `recall_pair`. Gate goes live.
3. `enrich.py`, `prefilter.py`, `resolve.py`, `scoring.py`; `resolver_accuracy` on FLoRA pairs.
4. `triage/` with `outcome_replay` on the 1,741 abstract-sourced FLoRA rows + the 263 validated_export rows; tune prompt v1 until `outcome_agreement ≥ .90`, `quote_grounding ≥ .98`.
5. `dedup.py`, `queue.py`, `serve.py`, the `/review/` pages and badges; promote the 62 genuine non-FLoRA 2021 harvester papers and the FORRT backlog's 189 DOIs as the first queue (seed material already on disk).
6. `crawl.py` weekly with budget meter; `report.py`; S4/S5/S6/S3/S7 added one at a time, each with a harness delta.
7. `export_forrt.py` and the first monthly submission; `reverse.py` sweep over famous effects with zero attempts.

---

## 14. Risks and mitigations

- **OpenAlex pricing changes** (now per-call): budget meter + free key; S2/S1 degrade gracefully to fewer seeds per week (famous effects first). Crossref keyword search is the emergency fallback (documented, measured at 17% recall — not a plan).
- **Seed contamination** (some FLoRA originals are GWAS/medical from SSRP-style projects) inflates S1 noise: prefilter never drops seed-citers, but scoring uses `topic_field_in_scope` and the LLM sees the seed; measure per-seed precision and cap abstract-pass on noisy seeds.
- **Multi-study mega-reports** (RSOS Boyce 140 rows, RP:P 92): the resolver must emit many targets from one paper; tier-B review handles them as a batch page ("all pairs from this paper").
- **Preprint/article double counting**: Crossref relation + OSF `attributes.doi` + OpenAlex `primary_location.version`; FLoRA's own `output_preprint_dedup_candidates.csv` pattern shows FORRT also struggles here — send them our collapsed aliases.
- **Reviewer burnout**: weekly queue capped at ~50 by score; everything else waits; the public queue page shows the backlog honestly.
- **Model drift**: results carry `model_id`/`prompt_version`; re-triage is a command; the harness compares before merge.
- **Keys in code**: none — env only; a secrets scan in CI (the old repo has 51 files with live keys; never imported).
