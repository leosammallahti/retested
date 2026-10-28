
---

## 4. Entity model, identifiers, URL scheme

> **Supersession note (2026-09-26).** This is the historical target architecture. The current implementation boundary and incremental reconciliation registry are defined in [`docs/REPLICATION_REGISTRY.md`](../../REPLICATION_REGISTRY.md). In particular, v1 canonicalizes only original/later **paper pairs** plus attributed source assertions; it does not yet canonicalize effect, claim, study, sample, or result identity across sources. Keep this section for its design history and later-phase ideas.

### 4.1 Entities (grain · sources · expected count at first build)

| Entity | One row means | Sources | Expected count |
|---|---|---|---|
| **Effect** | A named phenomenon people talk about ("Macbeth effect"); owns aliases, claims, narrative, record + numerical verdict | legacy `effect` (414 normalized names), Reversals sheet (583), R&R sheet (584), docx (361), curated | ~749 auto clusters → **~720 named effects** after review of 59 fuzzy merges `[D1]` |
| **Finding** | One original paper (doi_o, or url/handle id) with ≥1 attempt; the promotion tier decides whether it has a page | union of doi_o across FLoRA (2,589), FReD (786), legacy (1,698), R&R (479) | **3,820 distinct original DOIs** `[D1]`; ~3,229 with ≥1 attempt with a verdict; ~700 belong to named effects; **~900–1,000 promoted** (≥2 attempts: 285 `[D1]`; FReD-coded originals: 786 `[U5]`; game items; curated) EST |
| **Claim** | (doi_o × study_o × claim text) — the FReD-to-effect bridge | FReD `study_o` + `claim_text_o` (865 distinct (doi_o, study_o); 1,743 claim texts `[D1]`), legacy `study_original` | ~2,000 FReD-backed; FLoRA-only originals carry one implicit paper-level claim |
| **Paper** | A DOI (or `url:`/`hdl:` id) in any role | all | **7,491 DOIs** (3,820 originals + 3,730 replications, 59 both) + ~600 URL-only works `[D1]` |
| **Attempt (pair)** | (original paper, replication-or-reproduction paper) — FLoRA grain; carries type, outcome, quote, source, filter flags | FLoRA 2,815; FReD 859 pairs; legacy +1,094; R&R 472 | **4,550 distinct pairs; 3,672 with a verdict** (success 1,096 / failure 948 / mixed 590 / inconclusive 1,038) `[D1]` |
| **Attempt (effect row)** | One effect tested in one replication study vs one original — FReD grain; carries n, es, p, criteria | FReD archive 2,164; legacy-only 3,234 | 5,398 rows; **1,103 tier A** (r + N both sides) from current FReD `[D2]` + ~362 legacy-only tier A `[U5]` |
| **Project** | Coordinated multi-study effort | legacy `source` (34 labels), FLoRA mega `doi_r`, `fred_id` prefixes, FORRT's 25-project list | ~35, hand-registered YAML |
| **Person** | ORCID/OpenAlex author | FLoRA/FReD author JSON, OpenAlex authorships | ~15,000 strings; pages for ~1,000–1,500 |
| **Topic** | A facet value (§9) | FORRT discipline, OpenAlex topic/subfield, curated tag, Cognitive Atlas paradigm | ~30 + ~150 + ~100 + ~120 |
| **Collection** | Editorial list or saved query | `data/curated/collections/*.yaml` | ~15 at launch |
| **GameItem** | One original study playable in the game | §8 | 693 now → ~2,000 |
| **Candidate** | A discovered (doi_r, target(s), outcome, quote) not yet in FORRT or our overlay | §11 | rolling; ~5,600 at day one from FORRT's feeds |

Relationships: `Effect 1—* Claim *—1 Paper(original)`; `Claim 1—* Attempt(effect row) *—1 Attempt(pair) *—1 Paper(replication)`; `Finding 1—1 Paper(original)`; `Finding *—0..1 Effect` (a multi-effect original links to several effects through its claims); `Attempt(pair) *—0..1 Project`; `Effect *—* Topic/Paradigm/Collection/Effect(related, reversed_by, sibling_of_same_original, builds_on)`.

Reproductions are attempts with `type = reproduction` and their own vocabulary; they never feed replication status; they feed a separate "Reproducibility" badge on the finding/effect page `[D1][D2]`.

### 4.2 Identifier rules (port of D5 §4 with D1's opaque effect ids)

- `normalize_doi(s)`: strip whitespace, percent-decode, strip `https://`, `http://`, `dx.`, `doi.org/`, `doi:` (case-insensitive), cut at first whitespace, strip FORRT's scraping garbage ("digital object identifier", "get rights and content", "[Opens in new window]"), strip trailing `.,;)`, lowercase, must start with `10.` else `None` (pseudo-DOIs such as `korbmacher_2022` become `url:` ids). `doi_key` additionally collapses `//` → `/` and removes PsyArXiv `_vN`. `doi_hash3` = first 3 hex of md5(doi) — verified equal to FLoRA's `doi_o_hash` on 2,000/2,000 rows `[A-24]`.
- `id_r_key = doi_key(doi_r) or "url:" + normalized url_r` (FORRT's own coalesce rule).
- **Effect**: `fx_<8 base32>` from the ledger; key kinds `name:<norm>` (named) — no effect is ever created from an unnamed group (that is a Finding). Slug = kebab of canonical name (≤60 chars, disambiguated by qualifier, e.g. `moral-priming-cleanliness`). Merges: `merged_into` + `registry/redirects.csv`.
- **Finding**: `fd_` + sha1(doi_o_key)[:10]; slug `f/<paper_slug>`; ledger-tracked so a later DOI change (legacy `DOI_changed`) becomes a redirect.
- **Claim**: `cl_` + sha1(doi_o_key|study_norm|claim_key)[:10]; anchor only (`#claim-…`).
- **Paper**: `p:` + doi_key or `p:url:` + sha1(url)[:12]; `paper_slug` per D5 §4.2 (`10.1126_science.1239918`; collision → `-` + sha1[:6]).
- **Attempt (pair)**: `pair_` + sha1(doi_o_key|id_r_key)[:12]. **Attempt (effect row)**: `att_` + sha1(attempt_key)[:12] with `attempt_key = doi_o_key|id_r_key|study_o_norm|study_r_norm|effect_ordinal` (COS within-entry `effect_id`, legacy `_a/_b` suffix, else 1). Legacy rows matching (pair, study, ordinal) merge into the same attempt and contribute closeness/power/CI with `source=fred_legacy_2.4.1`.
- **Project**: hand slug (`many-labs-2`, `rpp-2015`, `rrr-ego-depletion`). **Person**: ORCID → OpenAlex id → `au_` + sha1(family|given-initial). **Topic**: `disc:<slug>`, `oa:T<id>`, `oa:sub:<id>`, `tag:<slug>`, `pd:<slug>` (Cognitive Atlas id kept).
- All upstream ids (`fred_id`, `fred_id_old`, COS `entry_id/effect_id`, legacy `id/rowid`, FLoRA row, R&R `FORRT_n`) live inside `ExternalIds` and are never primary keys `[D5]`.
- Ledger law: `data/curated/registry/*.csv` are committed, append-only, written only by `pipeline registry`; the build refuses to run if an id would be re-assigned or a slug collides `[D1][D5]`.

### 4.3 URL scheme

```
/                                    home ("The Record, today")
/effects/                            browse (facets: status, discipline, topic, paradigm, project, decade, attempts, citations)
/effect/{slug}/                      the core page (§7.1); anchors #claim-…, #att-…, #candidates
/effect/{slug}/data.json             the effect's full record (also at /api/v1/effect/{id}.json)
/findings/                           "Unnamed findings" index: paginated, grouped by original paper; facets by discipline/year/outcome
/finding/{paper_slug}/               promoted finding page (§7.2); un-promoted findings resolve to /findings/?doi=… (client-side jump to the row)
/paper/{paper_slug}/                 THIN paper page, only for (a) originals of named effects, (b) project reports / mega-papers; everyone else → atlas link (§4.6)
/project/{slug}/  /person/{slug}/  /topic/{id}/  /discipline/{slug}/  /paradigm/{slug}/  /collection/{slug}/
/journal/{slug}/  /year/{yyyy}/
/graveyard/  /survivors/  /reversals/  /rise-and-fall/   editorial doors (D6 A1–A3, A9)
/stats/{overview,criteria,shrinkage,predictors,by-discipline,by-year,projects,journals,data-quality,methods}
/play/  /play/daily/{yyyy-mm-dd}/  /play/{mode}/  /forecast/ (Phase 3)
/candidates/  /candidates/{id}/     public read-only review queue; /review/ (dev-only write UI)
/check/                              paste-a-reference-list checker (client-side against /api/v1/doi/)
/about/ /methods/ /data/ /changelog/ /contribute/ /rules/status/
/doi/?q=10.1126/science.1239918      client-side DOI resolver → our finding/effect + atlas + doi.org links
/api/v1/index.json  /api/v1/effect/{id}.json  /api/v1/finding/{id}.json  /api/v1/doi/{hash3}.json (FORRT record shape)
/api/v1/bundle/{table}.parquet|.json  /badge/{hash3}.svg  /feed.xml  /sitemap-index.xml
```

Redirects: GitHub Pages has no server redirects, so merged/renamed slugs produce a page with `<meta http-equiv="refresh">` + canonical.

### 4.4 What is reachable where (the D-1 guarantee, as a test)

`test_reachability.py`: for every FLoRA row and every FReD row in the bundle, at least one of these HTML pages contains its `pair_id`/`att_id` anchor: an effect page, a promoted finding page, or an `/findings/` index page; and its `/api/v1/doi/{hash3}.json` record exists. Zero exceptions.

### 4.5 Finding promotion rule (deterministic, logged)

A Finding gets a standalone page when any holds: (1) belongs to a named effect (then the effect page is canonical; the finding page is skipped when the effect has exactly one original); (2) ≥2 attempt pairs; (3) ≥1 FReD numeric row (tier A/B); (4) it is a game item; (5) `data/curated/findings/<slug>.md` exists; (6) OpenAlex `cited_by_count` ≥ 500. Expected: ~900–1,000 pages EST (upper bound 786 FReD originals + 285 multi-attempt + curated, minus overlap with named effects).

### 4.6 Thin paper pages

Only for originals of named effects and for project reports (papers with ≥10 pairs as `doi_r`: 10 today `[U5]`). Content: citation, role badges, the effects/claims it hosts with status pills, the pairs it appears in, citation sparkline, retraction flag, links: **atlas page**, doi.org, OA URL, FORRT JSON. Everything else about a paper is on the atlas — we say so in one line.
