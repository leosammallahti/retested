# Replication reconciliation registry

## Status and boundary

`pipeline/reconciliation_registry.py` builds the evidence-first, additive v1 registry. It does not replace the legacy site graph in `pipeline/registry.py`, its generated `at_…` attempt IDs, site routes, count baselines, or the append-only `data/curated/registry/effect_ids.csv` ledger.

V1 has a deliberately limited answer:

> Which Retested and FORRT records identify the same **citable expressions** or ordered original/later **expression pair**, and what source-scoped claim-test/result evidence does Retested supply?

It does not materialize a canonical Work, effect, claim, study, sample, condition, population, estimand, or analytic result. Equivalence between citable expressions is represented only by a source-backed assertion. This is a practical boundary: paper-pair identity is already useful for reconciliation, while the broader identities require distinct evidence and review.

## Ontology

### Expression and Work

An **Expression** is a citable-identity record emitted by the registry. Only a normalized **DOI** is an exact expression identity in v1 (`identity_status: exact_doi_expression`). URL, OpenAlex, and alternate identifiers are retained as unresolved source/external identifiers; they are not exact expressions. A title is a record-scoped candidate, not an identity: the same normalized title in two source records deliberately yields separate `title-candidate` records. Every expression has `work_identity_status: "not_materialized"`.

A **Work** is the underlying intellectual report of which a preprint, journal article, repository version, or supplement may be an expression. V1 does **not** materialize `works[]`, choose a canonical Work representative, or collapse expressions into a version family. When evidence supports a relation, `work_identity_assertions[]` records an edge such as:

- `source_asserted_identifier_alias`: a source row supplies two identifiers for one side;
- `reviewed_same_work`: a source-adjudicated review connects two expressions on the original or later side.

Those edges preserve the source/adjudication and evidence. They do not rewrite an expression ID, imply transitive Work equivalence beyond the reviewed evidence, or make title/embedding similarity an identity decision.

An expression pair is ordered by role:

```
original expression ── pair ── later expression
```

The pair's `expression_pair_scope` is normally `distinct_expressions`. If a source reports the same expression record on both sides, the registry emits `source_reported_same_expression_anomaly` and `requires_identity_review: true`; it does **not** turn that anomaly into a claim about studies or a meaningful replication relation.

### Study and Sample

A **Study** is a design/execution unit within a report; a **Sample** is the units observed or recruited for that study. They are different concepts, and neither follows from a paper DOI or from a pair match.

V1 deliberately emits empty `studies[]` and `samples[]`. In imported Retested records:

- each `claim` has `study_id: null`;
- each `claim_test` has `replication_study_id: null` and `sample_ids: []`;
- each `result_assessment` has `result_id: null`.

The implementation does not currently export raw FReD/legacy `study_o`, `study_r`, `id_sample`, N, condition, or participant-overlap fields as registry observations. Those fields may inform a future, separately reviewed study/sample mapping, but must not be described as v1 output or used to infer identity today.

### Effect, claim, claim test, and result assessment

| Concept | V1 meaning and treatment |
|---|---|
| **Effect** | An editorial/named cluster from the existing append-only `fx_…` name ledger. `effects[]` is a compatibility reference with `identity_authority: legacy_append_only_name_ledger`; it is not proof of a universal effect, claim, study, or estimand identity. |
| **Claim** | Retested's source-reviewed original-report claim. `claims[]` is **source-scoped**: one claim is derived from a promoted source observation and is explicitly `source_scoped_claim_not_canonicalized`. Claims are not merged merely because effect labels or original expressions match. |
| **Claim test** | Retested's report-scoped later-report test of its source-scoped claim. `claim_tests[]` links that claim to original/later expressions, retains target assertions, and explicitly leaves study and sample identity unresolved. A claim test is not an effect-level reconciliation result. |
| **Result assessment** | Retested's reviewed outcome reading for a claim test. `result_assessments[]` retains outcome, quote, source URL, reviewer/date, and its source observation, while `result_id` remains null. It is an attributed assessment, not a canonical contrast/result entity or an automatic resolution of a FORRT outcome. |

Accordingly, a confirmed original/later expression pair does not resolve any `effect_relation`, `study_relation`, `sample_relation`, or `outcome_relation`: all four are `not_compared` in v1 overlap decisions. This is intentional, including where Retested and FORRT use different outcome labels or different claim scopes.

## Actual v1 document

The compact deterministic output is `data/build/reconciliation_registry.json`; its human-readable companion is `data/build/reconciliation_registry.summary.json`. Its implemented top-level tables are:

```
source_snapshots[]
expressions[]
work_identity_assertions[]
source_summary_records[]
pairs[]
source_observations[]
later_status_records[]
effects[]
claims[]
studies[]                 # empty in v1
samples[]                 # empty in v1
claim_tests[]
result_assessments[]
overlap_decisions[]
coverage{}
counts{}
validation{}
```

`counts.retested_addition_bibliographic_relations` repeats the mutually exclusive relation partition for only the pairs added to Retested's built pages. Public copy can therefore compute the supported overlap among additions from the evidence ledger instead of hard-coding a checkpoint number.

### Source snapshots and observations

`source_snapshots[]` is built from the source manifest in `pair_match_summaries.json`; each entry records source name, source status, policy-derived layer, path, SHA-256, and row counts. `source_summary_records[]` preserves the summary-record grain before source rows are connected to it, including identifiers, text components, observed-result text, every attributed source outcome label, and the upstream provenance IDs. `source_observations[]` then preserves the association between those provenance IDs/snapshot rows, summary record, expressions, and pair. Neither table is a copy of every raw source column, but the outcome labels needed to audit disagreement are retained rather than silently selecting a winner.

`later_status_records[]` keeps a later-expression record where the source has no usable original expression. Such a record is useful membership evidence but cannot become an ordered pair until original identity is evidenced.

### Pairs and same-expression source records

`pairs[]` joins records only at expression-pair granularity. It holds Retested/FORRT summary-record references, source-observation references, the observed FORRT statuses, and a policy-derived `best_forrt_membership_status`. That best status is a membership display rule, not an outcome or scientific-quality winner.

There are three separate bibliographic situations:

1. **Exact DOI-expression pair reported**: a frozen FORRT source directly reports the same normalized original and later DOI pair (`exact_expression_pair_reported`).
2. **Same Work asserted on one side**: an alias/version assertion connects original or later expressions but leaves them as distinct expression records. It may support a reviewed pair relation only when the corresponding pair evidence exists.
3. **Same later Work, different original**: `reviewed_same_later_work_different_original` records that the later report is known but this candidate original does not form the same pair. It cannot exclude another candidate or prove absence.

“Related but distinct,” unconfirmed, disputed, missing-original, an unretrieved candidate, title similarity, and embedding similarity are not positive same-pair evidence. An embedding only retrieves review candidates. A rejected candidate never proves that a Retested pair is absent from FORRT.

## Frozen scope and layers

The registry's comparison scope comes from `data/curated/registry/reconciliation_policy_v1.json`:

> A reproducible comparison of Retested reviewed records with the pinned FORRT corpus; it is not a claim of universal literature completeness.

The policy maps source statuses to layers:

| Policy layer | Source status |
|---|---|
| `retested_reviewed` | `source_reviewed` |
| `forrt_public` | `published` |
| `forrt_validated` | `validated` |
| `forrt_extractor` | `extractor` |
| `forrt_pending` | `pending_original_unresolved` |
| `forrt_unconfirmed` | `unconfirmed` |
| `forrt_disputed` | `disputed` |
| `forrt_unresolved` | `unresolved` |
| `forrt_historical` | `historical` |
| `forrt_diagnostic` | `diagnostic` |
| `local_unclassified` | `local` |

The policy also pins the current sources used for the comparison to named repository commits and SHA-256 digests. Structural validation fails if a required pinned snapshot is absent or disagrees with its declared digest/status. The registry never accepts an ephemeral `/tmp` source path.

Generation has no generated timestamp. Identical inputs produce identical JSON. The registry records descriptors and SHA-256 hashes for its pair summaries, promoted rows, built attempts, reconciled audit, **semantic review**, effect ledger, policy, and raw manifest. The raw manifest is parsed and validated against the policy's pinned paths, source statuses, commits, SHA-256s, and on-disk files.

## Deterministic IDs

IDs use the **full** SHA-256 digest of stable components, with a type prefix:

- `ex_`: one citable-identity record (only a DOI record is an exact expression identity);
- `pr_`: original expression ID, role separator, later expression ID;
- `sn_`: source name, path, and source digest;
- `ob_`: snapshot ID, source row, and summary-record ID;
- `wa_`: identifier alias or reviewed same-Work assertion;
- `cl_`: Retested source observation used for a source-scoped claim;
- `ct_`: source-scoped claim and later expression used for a report-scoped claim test;
- `ra_`: claim test and source observation used for a result assessment.

The implementation's identifiers intentionally do not derive from outcome, embedding score, title similarity, an effect label, a study label, or a sample ID. Current `at_…` and `fx_…` values remain legacy/build references; v1 neither reassigns nor turns them into cross-source scientific identities.

## Overlap decisions and assurance

`overlap_decisions[]` partitions every normalized Retested built pair. It records the legacy attempt ID, whether it is a pre-existing FORRT overlay or Retested addition, one allowed `bibliographic_relation`, the stated basis, and the remaining review requirements.

The current policy's bibliographic relations are:

```
exact_expression_pair_reported
reviewed_same_work_pair_versioned_expressions
reviewed_same_work_pair_expression_unresolved
title_or_alternate_identifier_pair_candidate
legacy_overlay_not_reproduced_in_frozen_sources
reviewed_same_later_work_different_original
later_work_reported_original_relation_unresolved
original_expression_reported_with_other_later
reviewed_original_work_in_pending_record
not_fully_compared
```

In the current frozen comparison, 814 Retested pairs are `exact_expression_pair_reported`; 38 are `reviewed_same_work_pair_expression_unresolved`; 20 are `reviewed_same_work_pair_versioned_expressions`; and 10 are `title_or_alternate_identifier_pair_candidate`. The first group is exact DOI-expression evidence. The next two are single-review Work assertions that keep expressions distinct; the last is explicitly a candidate, not an identity assertion. None resolves effect, study, sample, or outcome identity.

The document always declares `coverage.comparison_state: interim_partially_source_adjudicated` and `coverage.assurance_complete: false`. Its assurance blockers include the following limits:

- effect identity has not been compared for any paper-pair overlap;
- study and sample identity are intentionally unresolved for report-scoped claim tests;
- semantic review does not cover every non-exact query; and
- independent dual review/adjudication has not started.

The implementation also reports partial comparison blocks (alias/version graph, bibliographic fallback, semantic retrieval, and textless metadata audit). Registry evidence locators are rewritten to stable pinned/captured paths where possible, rather than carrying transient `/tmp` references. The semantic review is nonetheless incomplete as evidence: 60 decisions have incomplete evidence, comprising 30 without a rationale and 30 without evidence locations. Therefore a no-confirmed-match outcome is bounded to the declared frozen scope and comparison blocks; it is never a universal claim that FORRT or the literature contains no match. V1 has `effect_relations_resolved: 0` and `certified_new_to_forrt: 0` by construction.

## Commands and validation

Both the pipeline subcommand and direct module command are implemented:

```
python -m pipeline reconciliation-registry --check
python -m pipeline reconciliation-registry
python -m pipeline.reconciliation_registry --check
python -m pipeline.reconciliation_registry
python -m pipeline.reconciliation_registry \
  --output data/build/reconciliation_registry.json \
  --summary-output data/build/reconciliation_registry.summary.json
```

`--check` builds and validates in memory without writing. The command accepts explicit paths for summaries, promoted rows, attempts, reconciled audit, semantic review, effect ledger, policy, and raw manifest.

The ordinary `python -m pipeline build` now validates every declared raw-input hash, regenerates the deterministic pair summaries from manifest-pinned inputs after exporting the current attempt graph, then structurally validates and atomically writes both registry artifacts. Inputs use immutable upstream revisions where recoverable; compressed, content-addressed recovery assets preserve historical public payloads whose moving endpoints no longer expose the recorded bytes. Structural failure fails the build; incomplete assurance remains a truthful output state rather than a build error. The Astro site reads the compact summary for its generated `/coverage/` page.

Structural validation verifies, among other things:

1. the required snapshot hashes and policy statuses;
2. expression, pair, observation, claim, test, and assessment references;
3. correct handling of a same-expression source pair;
4. that claims cannot fabricate `study_id`;
5. that claim tests cannot fabricate study/sample IDs;
6. that result assessments cannot fabricate a canonical `result_id`;
7. that every normalized Retested built pair has exactly one overlap decision and relation counts conserve that partition; and
8. that the semantic-review hash, path, decision set, evidence, DOI pair, and positive candidate linkages agree with the reconciled ledger;
9. that no bare normalized-title identity or transient `/tmp` locator enters the registry;
10. that v1 does not claim resolved effect relations or certified novelty; and
11. that write mode cannot overwrite an input, alias its two outputs, or write a structurally invalid registry.

## Future ontology, not v1 output

A later phase may introduce canonical Work families, reviewed effect/claim identity, Study, Sample, condition, participant-overlap, and result/estimand entities. It needs explicit mapping rules, durable reviewed assertions, uncertainty/coverage reporting, and separate validation. It must not be inferred from a pair join, an `fx_…` name, raw source labels, a shared author, a title match, or embedding retrieval.
