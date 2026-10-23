// Build-time access to the pipeline bundle (../data/build). Never imported by client islands.
import fs from 'node:fs';
import path from 'node:path';

const BUILD = path.resolve(process.cwd(), '..', 'data', 'build');
const cache = new Map<string, unknown>();

function readOptional<T>(name: string): T | null {
  if (!cache.has(name)) {
    const file = path.join(BUILD, name);
    cache.set(name, fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')) : null);
  }
  return cache.get(name) as T | null;
}

function read<T>(name: string): T {
  if (!cache.has(name)) {
    const file = path.join(BUILD, name);
    if (!fs.existsSync(file)) throw new Error(`Missing ${file}. Run \`npm run data\` (python -m pipeline build) first.`);
    cache.set(name, JSON.parse(fs.readFileSync(file, 'utf8')));
  }
  return cache.get(name) as T;
}

export type Outcome = 'successful' | 'failed' | 'mixed' | 'inconclusive' | 'not_coded';

export interface Record_ { code: string; label: string; k: number; n_attempts: number; successful: number; failed: number; mixed: number; inconclusive: number; not_coded: number }
export interface Numeric { r: number; ci: [number, number]; pi: [number, number] | null; tau: number; i2: number | null; k_papers: number; k_rows: number; r_original: number | null; ratio: number | null; label: { code: string; label: string } }
export interface Lenses {
  record: Record_; numeric: Numeric | null; disagree: boolean;
  criteria: Record<string, { success: number; failure: number; na: number }> | null;
  design: { preregistered: number; independent: number; overlap_known: number; closeness: Record<string, string> | null };
  n_reproductions: number; first_replication_year: number | null; last_replication_year: number | null; total_replication_n: number | null;
}
export interface FredRow {
  row: number; study_o: string | null; study_r: string | null; description: string | null; claim_text_o: string | null; discipline: string | null;
  r_o: number | null; r_r: number | null; n_o: number | null; n_r: number | null; p_o: number | null; p_r: number | null; es_type_o: string | null;
  criteria: Record<string, string | null>; reported_success: Outcome; quote: string | null; prereg_r: string | null;
}
export interface LegacyRow { effect: string | null; r_o: number | null; r_r: number | null; n_o: number | null; n_r: number | null; outcome: Outcome; result_raw: string | null; closeness: Record<string, string>; preregistration: string | null; power: number | null; validated: unknown; osf_link: string | null }
export interface Attempt {
  id: string; doi_o: string; rep_key: string; doi_r: string | null; type: 'replication' | 'reproduction';
  sources: string[]; outcomes_by_source: Record<string, Outcome>; outcome: Outcome; outcome_raw?: string; sources_disagree: boolean;
  rows: FredRow[]; legacy_rows: LegacyRow[]; projects: string[]; legacy_only?: boolean;
  title_r?: string; year_r?: number; journal_r?: string; authors_r?: string; url_r?: string; oa_url_r?: string;
  quote?: string; quote_source?: string; author_overlap_pct?: number; flora_source?: string;
  retested_review?: { candidate_id: string; reviewed_by: string; reviewed_on: string;
    original_source_url: string; original_claim_quote: string; original_source_type?: "empirical_study" | "meta_analysis" | "review" | "other" | null; replication_source_url: string;
    replication_target_quote: string; outcome_quote: string; outcome_quote_source: string; review_note?: string | null };
}
export interface Paper { doi: string; slug: string; title?: string; year?: number; journal?: string; authors?: string; ref?: string; oa_url?: string; openalex?: { cited_by: number; counts_by_year: Record<string, number>; is_retracted: boolean; topic: string; subfield: string; field: string } }
export interface FindingExplanation {
  original: { claim: string; method: string; population: string; outcome_measure: string };
  source: { url: string; evidence: { location: string; quote: string; supports: ('claim' | 'method' | 'population' | 'outcome_measure')[] }[] };
  review: { state: 'source_reviewed'; reviewed_by: string; reviewed_on: string };
  provenance: { kind: 'manual_source_review'; promoted_pair_doi_r: string | null };
}
export interface FindingGameContext {
  claim: string;
  method: string;
  review_state: 'plain_language_game_context_not_source_reviewed';
}
export interface Finding { doi_o: string; slug: string; attempts: string[]; effects?: string[]; lenses: Lenses; page: boolean; explanation?: FindingExplanation; game_contexts?: FindingGameContext[] }
export interface Famous { status: string | null; status_raw: string | null; description: string | null; original_paper: string | null; original_year: number | null; critiques: string | null; original_es: string | null; replication_es: string | null; gs_citations: number | null }
export interface Effect { id: string; key: string; slug: string; name: string; aliases: string[]; name_sources?: string[]; discipline: string | null; description: string | null; famous: Famous | null; originals: string[]; attempts: string[]; shared_attempts: string[]; lenses: Lenses }
export interface Share { n: number; successful: number; failed: number; mixed: number; success_share: number | null; success_ci: [number, number] | null }
// The hand-read audit of the verdicts themselves: data/curated/outcome_audit.csv, scored by `pipeline outcomes`.
// Per-band accuracy of the link between a find and the original it re-tests: data/curated/original_audit.csv,
// scored by `pipeline originals`. `unclear` reads stay in the denominator.
export interface LinkAudit { n_read: number; right: number; n_pool: number; share: number | null;
  unread_bands: string[]; by_band: Record<string, { n: number; right: number; in_pool: number; precision: number }> }
export interface OutcomeAudit { n_read: number; n_pool: number; flipped: number; raw_success_share: number | null;
  corrected_success_share: number | null; corrected_n?: number;
  by_verdict: Record<string, { n: number; right: number; precision: number }> }
export interface EffectCard { slug: string; name: string; discipline: string | null; record: Record_; fame: number; numeric: Pick<Numeric, 'r' | 'ci' | 'ratio' | 'r_original' | 'label'> | null; famous_status: string | null }
export interface FindingContextCoverage {
  denominator: number;
  source_reviewed_explanation: number;
  plain_language_game_context: number;
  fallback_source_reviewed_claim: number;
  fallback_forrt_coded_claim: number;
  fallback_named_effect: number;
  fallback_title_only: number;
  no_context: number;
}
export interface Stats {
  counts: Record<string, number>; overall: Share;
  by_replication_year: Record<string, Share>; by_original_decade: Record<string, Share>; by_discipline: Record<string, Share>; by_journal: Record<string, Share>;
  predictors: Record<string, Share>;
  shrinkage: { n_rows: number; median_ratio: number; q25: number; q75: number; share_below_half: number; share_sign_flip: number };
  uncounted: { finds: number; linked: number; with_verdict: number; distinct_originals: number; overall: Share;
    by_evidence: Record<string, Share>; by_independence: Record<string, Share>; by_design: Record<string, Share>;
    preregistered: Share; by_year: Record<string, Share>; audit: OutcomeAudit | null;
    link_audit: { shown: LinkAudit | null; page: LinkAudit | null; linked: LinkAudit | null } };
  effect_record_counts: Record<string, number>; finding_record_counts: Record<string, number>;
  finding_context_coverage: FindingContextCoverage;
  lists: { graveyard: EffectCard[]; survivors: EffectCard[]; contested: EffectCard[]; most_tested: EffectCard[] };
}

export interface ReconciliationSummary {
  schema_version: string;
  scope: string;
  counts: {
    retested_reviewed_source_rows: number;
    retested_normalized_pairs: number;
    retested_built_overlays: number;
    retested_additions: number;
    forrt_summary_records: number;
    forrt_pair_records: number;
    forrt_later_status_records: number;
    certified_new_to_forrt: number;
    effect_relations_resolved: number;
    studies_resolved: number;
    samples_resolved: number;
    bibliographic_relations: Record<string, number>;
    retested_addition_bibliographic_relations: Record<string, number>;
  };
  coverage: {
    comparison_state: string;
    assurance_complete: boolean;
    semantic_queries_reviewed: number;
    semantic_decisions_incomplete_evidence: number;
    semantic_decisions_missing_rationale: number;
    semantic_decisions_missing_locations: number;
    comparison_blocks: Record<string, 'complete' | 'partial' | 'not_started' | string>;
    assurance_blockers: string[];
  };
  validation: { structurally_valid: boolean; assurance_complete: boolean; problems: string[] };
  input_hashes: Record<string, string>;
}

export interface Candidate {
  id: string; doi_r: string | null; title_r: string | null; year_r: number | null; journal_r: string | null; authors_r?: string | null;
  doi_o: string | null; title_o: string | null; year_o: number | null;
  outcome: string | null; outcome_quote: string | null; outcome_confidence: string | number | null;
  link_confidence: string | null; link_method?: string | null;
  link_evidence?: { score?: number; text_sim?: number | null; authors_matched?: string; year_delta?: number; runner_up?: { doi_o: string; title_o: string | null; score: number } | null; source_url?: string; evidence?: string } | null;
  original_studies?: { doi_o: string; title_o: string; year_o: number | null; source_url: string; evidence: string }[] | null;
  original_named?: { authors: string | null; year: number | null; description: string | null } | null;
  type: string | null; field?: string | null; group: 'replication' | 'other_behavioural' | 'registration';
  evidence_tier?: string; search_tier?: 'high' | 'medium'; rule_score?: number; found_by?: string[]; screen_reason?: string | null;
  landing_page?: string | null; osf_id?: string | null;
  authors_o?: string | null; journal_o?: string | null; cited_by_o?: number | null;
  retracted_o?: boolean | null; abstract_o?: string | null;
  if_accepted?: { from: string; from_label: string; to: string; to_label: string; changes: boolean; k_before: number; k_after: number } | null;
  declared_design?: { word: string; fidelity: 'high' | 'low' | 'unclear'; said_in: string } | null;
  preregistered?: { is_registration: boolean; date: string | null; osf_kind: string; source: string } | null;
  independence?: { verdict: 'independent' | 'shares_author' | 'possible_shared_name'; shared: string[]; distinctive: string[]; shared_frequency: Record<string, number>; n_replication_authors: number; n_original_authors: number } | null;
  rep_already_known: boolean; original_in_wiki: boolean; effect: { slug: string; name: string } | null;
  abstract: string | null; models: string[]; origin: 'forrt_flora_extractor' | 'retested_discovery'; review_state: string;
}
export interface VerdictIfAccepted { from: string; from_label: string; to: string; to_label: string; changes: boolean; n_accepted: number; k_before: number; k_after: number }
export interface Pending { by_finding: Record<string, Candidate[]>; by_effect: Record<string, Candidate[]>; verdict_if_accepted: Record<string, VerdictIfAccepted>; effect_verdict_if_accepted: Record<string, VerdictIfAccepted> }

export const effects = () => read<Effect[]>('effects.json');
export const findings = () => read<Record<string, Finding>>('findings.json');
export const attempts = () => read<Record<string, Attempt>>('attempts.json');
export const papers = () => read<Record<string, Paper>>('papers.json');
export const stats = () => read<Stats>('stats.json');
export const citation = () => read<{ forrt: string }>('citation.json').forrt;
export const candidates = () => read<Candidate[]>('candidates.json');
export const pending = () => read<Pending>('pending.json');
export const reconciliation = () => read<ReconciliationSummary>('reconciliation_registry.summary.json');

let _effById: Map<string, Effect> | undefined;
export const effectById = (id: string) => (_effById ??= new Map(effects().map((e) => [e.id, e]))).get(id);

// The wiki story of a page (data/build/wiki.json, written by `python -m pipeline wiki`). Absent for pages without one.
export interface StoryScene { id: string; label: string | null; study: string | null; quote: string; did: string; found: string; level: string | null; writer: string | null; written_on: string | null }
export interface StoryPaper { doi: string; title: string | null; authors: string | null; year: number | null; journal: string | null; cited_by: number | null; retracted: boolean; ref: string | null }
export interface StoryWhy { text: string; kind: string; from: string; who?: string | null }
export interface StoryAttempt {
  id: string; type: string; authors: string | null; year: number | null; journal: string | null; title: string | null; doi: string | null;
  open_url: string | null; url: string | null; outcome: Outcome; sources_disagree: boolean; outcomes_by_source: Record<string, string>;
  line: string | null; did: string | null; found: string | null; written_from: string | null; written_check: 'read' | 'sampled' | null; their_words: string; their_words_from: string | null; tested_study: string[]; tested_paper: string | null;
  n: number | null; r: number | null; ci: [number, number] | null; preregistered: boolean | null; independent: boolean | null;
  reviewer_sentences: string[]; why: StoryWhy[]; reviewed_on: string | null; reviewer_links: { original: string | null; replication: string | null } | null; in: string[];
}
export interface StoryGroup { original: StoryPaper | null; original_quote: string; scenes: StoryScene[]; attempts: StoryAttempt[]; why: StoryWhy[] }
export interface Story {
  kind: 'effect' | 'finding'; slug: string; name?: string; doi?: string;
  scenes: StoryScene[]; scene_from?: string | null;
  verdict: { code: string; label: string; headline: string; detail: string; counts: Record<string, number>; n_attempts: number };
  groups: StoryGroup[]; sure: { text: string; from: string }[];
  numbers: { text: string; pooled_r: number; ci: [number, number]; original_r: number | null; ratio_text: string | null; label: string } | null;
  multi_original: boolean; same_paper_twice: string[];
  explanation?: { claim: string; method: string; population: string; measure: string; source_url: string; reviewed_on: string } | null;
  game_contexts?: FindingGameContext[]; effects?: string[];
}
export const storyFor = (kind: 'effect' | 'finding', slug: string): Story | null =>
  readOptional<{ effects: Record<string, Story>; findings: Record<string, Story> }>('wiki.json')?.[kind === 'effect' ? 'effects' : 'findings']?.[slug] ?? null;
