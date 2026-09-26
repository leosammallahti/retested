// Review queue: machine-found replication candidates awaiting a human, from two sources — FORRT's own
// flora-extractor and our keyword/citation search screened by DeepSeek.
// Decisions are kept in this browser and exported as CSV in FLoRA's submission columns.
import { useEffect, useMemo, useRef, useState } from 'preact/hooks';

interface Cand {
  id: string; doi_r: string | null; title_r: string | null; year_r: number | null; journal_r: string | null; authors_r?: string | null;
  doi_o: string | null; title_o: string | null; year_o: number | null; outcome: string | null; outcome_quote: string | null;
  outcome_confidence: string | number | null; link_confidence: string | null; type: string | null; rep_already_known: boolean; original_in_wiki: boolean;
  effect: { slug: string; name: string } | null; abstract: string | null; models: string[];
  origin: 'forrt_flora_extractor' | 'retested_discovery';
  group: 'replication' | 'other_behavioural' | 'registration';
  link_method?: string | null; evidence_tier?: string; search_tier?: 'high' | 'medium'; found_by?: string[]; screen_reason?: string | null;
  declared_design?: { word: string; fidelity: string } | null;
  preregistered?: { is_registration: boolean; date: string | null } | null;
  independence?: { verdict: string; shared: string[]; distinctive: string[] } | null;
  if_accepted?: { from_label: string; to_label: string; changes: boolean; k_before: number; k_after: number } | null;
  authors_r?: string | null; osf_id?: string | null; landing_page?: string | null; year_o?: number | null;
  authors_o?: string | null; journal_o?: string | null; cited_by_o?: number | null; retracted_o?: boolean | null;
  duplicates?: string[]; duplicate_originals_disagree?: boolean;
  link_evidence?: { score?: number; text_sim?: number | null; authors_matched?: string; year_delta?: number; runner_up?: { doi_o: string; title_o: string | null; score: number } | null; source_url?: string; evidence?: string } | null;
  original_studies?: { doi_o: string; title_o: string; year_o: number | null; source_url: string; evidence: string }[] | null;
  original_named?: { authors: string | null; year: number | null; description: string | null } | null;
}
const ORIGIN: Record<string, string> = {
  forrt_flora_extractor: "FORRT's extractor",
  retested_discovery: 'Found by Retested',
};
const GROUP: Record<string, string> = {
  replication: 'psychology replication',
  other_behavioural: 'other behavioural science',
  registration: 'registered protocol, no results yet',
};
const HOW: Record<string, string> = {
  'cited by this paper': 'the model picked this original from the papers cited here — about half such links are wrong',
  library_author_year: 'author + year matched in this wiki',
  openalex_author_year: 'author + year searched in OpenAlex',
  reference_scan: 'the described finding matched against the papers this replication cites',
};
type Decision = {
  v: 'accept' | 'reject' | 'unsure'; outcome?: string; rationale?: string; evidence?: string; at: string; updated_at?: string;
};
type NoteDraft = { rationale: string; evidence: string };
type CandidateSnapshot = {
  id: string;
  identity: { doi_r: string | null; title_r: string | null; year_r: number | null; doi_o: string | null; title_o: string | null; year_o: number | null };
  provenance: { origin: Cand['origin']; group: Cand['group']; link_method: string | null; link_confidence: string | null; search_tier: string | null; found_by: string[] };
  evidence: { machine_outcome: string | null; outcome_quote: string | null; abstract: string | null; link_evidence: Cand['link_evidence']; original_studies: Cand['original_studies'] };
};
type ReviewPacket = {
  schema: 'retested.queue.review-packet'; version: 1; exported_at: string; source: { candidate_count: number }; reviews: { candidate: CandidateSnapshot; decision: Decision }[];
};
const KEY = 'retested.queue.v1';
const PAGE = 25;

const decisionFrom = (value: unknown): Decision | null => {
  if (!value || typeof value !== 'object') return null;
  const d = value as Record<string, unknown>;
  if (d.v !== 'accept' && d.v !== 'reject' && d.v !== 'unsure' || typeof d.at !== 'string' || Number.isNaN(Date.parse(d.at))) return null;
  const text = (v: unknown) => typeof v === 'string' && v.length <= 12000 ? v : undefined;
  // `note` was used by an early local-draft format. Preserve it as a rationale rather than losing a reviewer's work.
  return { v: d.v, outcome: text(d.outcome), rationale: text(d.rationale) ?? text(d.note), evidence: text(d.evidence), at: d.at, updated_at: text(d.updated_at) };
};
const readD = (): Record<string, Decision> => {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) || '{}');
    if (!raw || typeof raw !== 'object') return {};
    return Object.fromEntries(Object.entries(raw).flatMap(([id, d]) => {
      const parsed = decisionFrom(d); return parsed ? [[id, parsed]] : [];
    }));
  } catch { return {}; }
};
const saveD = (d: Record<string, Decision>) => { try { localStorage.setItem(KEY, JSON.stringify(d)); } catch { /* ignore */ } };
const textOrNull = (v: unknown): string | null => typeof v === 'string' ? v : null;
const numberOrNull = (v: unknown): number | null => typeof v === 'number' && Number.isFinite(v) ? v : null;

const snapshot = (c: Cand): CandidateSnapshot => ({
  id: c.id,
  identity: { doi_r: c.doi_r, title_r: c.title_r, year_r: c.year_r, doi_o: c.doi_o, title_o: c.title_o, year_o: c.year_o },
  provenance: { origin: c.origin, group: c.group, link_method: c.link_method ?? null, link_confidence: c.link_confidence, search_tier: c.search_tier ?? null, found_by: c.found_by ?? [] },
  evidence: { machine_outcome: c.outcome, outcome_quote: c.outcome_quote, abstract: c.abstract, link_evidence: c.link_evidence ?? null, original_studies: c.original_studies ?? null },
});

const samePaper = (doiA: string | null, titleA: string | null, yearA: number | null, doiB: string | null, titleB: string | null, yearB: number | null) => {
  if (doiA || doiB) return doiA?.trim().toLowerCase() === doiB?.trim().toLowerCase();
  return titleA?.trim().toLowerCase() === titleB?.trim().toLowerCase() && yearA === yearB;
};
const matchesCurrent = (c: Cand, s: CandidateSnapshot) => s.id === c.id && s.provenance.origin === c.origin
  && samePaper(s.identity.doi_r, s.identity.title_r, s.identity.year_r, c.doi_r, c.title_r, c.year_r)
  && samePaper(s.identity.doi_o, s.identity.title_o, s.identity.year_o, c.doi_o, c.title_o, c.year_o);

const parsePacket = (raw: unknown): { packet?: ReviewPacket; error?: string } => {
  if (!raw || typeof raw !== 'object') return { error: 'The file is not a review packet.' };
  const p = raw as Record<string, unknown>;
  if (p.schema !== 'retested.queue.review-packet' || p.version !== 1 || !Array.isArray(p.reviews)) return { error: 'This is not a supported Retested review packet (schema v1).' };
  if (!p.reviews.length) return { error: 'The packet has no decisions to import.' };
  const reviews: ReviewPacket['reviews'] = [];
  for (const row of p.reviews) {
    if (!row || typeof row !== 'object') return { error: 'A review row is malformed.' };
    const r = row as Record<string, unknown>, c = r.candidate as Record<string, unknown> | null, identity = c?.identity as Record<string, unknown> | null, provenance = c?.provenance as Record<string, unknown> | null;
    const decision = decisionFrom(r.decision);
    if (!c || !identity || !provenance || typeof c.id !== 'string' || !decision
      || (provenance.origin !== 'forrt_flora_extractor' && provenance.origin !== 'retested_discovery')
      || typeof identity.doi_r !== 'string' && identity.doi_r !== null || typeof identity.title_r !== 'string' && identity.title_r !== null || numberOrNull(identity.year_r) !== identity.year_r
      || typeof identity.doi_o !== 'string' && identity.doi_o !== null || typeof identity.title_o !== 'string' && identity.title_o !== null || numberOrNull(identity.year_o) !== identity.year_o) return { error: 'A review row is missing a valid candidate identity or decision.' };
    reviews.push({ candidate: {
      id: c.id,
      identity: { doi_r: textOrNull(identity.doi_r), title_r: textOrNull(identity.title_r), year_r: numberOrNull(identity.year_r), doi_o: textOrNull(identity.doi_o), title_o: textOrNull(identity.title_o), year_o: numberOrNull(identity.year_o) },
      provenance: { origin: provenance.origin, group: provenance.group === 'other_behavioural' || provenance.group === 'registration' ? provenance.group : 'replication', link_method: textOrNull(provenance.link_method), link_confidence: textOrNull(provenance.link_confidence), search_tier: textOrNull(provenance.search_tier), found_by: Array.isArray(provenance.found_by) && provenance.found_by.every((x) => typeof x === 'string') ? provenance.found_by : [] },
      evidence: (c.evidence && typeof c.evidence === 'object') ? c.evidence as CandidateSnapshot['evidence'] : { machine_outcome: null, outcome_quote: null, abstract: null, link_evidence: null, original_studies: null },
    }, decision });
  }
  return { packet: { schema: 'retested.queue.review-packet', version: 1, exported_at: typeof p.exported_at === 'string' ? p.exported_at : '', source: { candidate_count: numberOrNull((p.source as Record<string, unknown> | null)?.candidate_count) ?? 0 }, reviews } };
};

export default function Queue({ base }: { base: string }) {
  const [all, setAll] = useState<Cand[] | null>(null);
  const [dec, setDec] = useState<Record<string, Decision>>({});
  const [drafts, setDrafts] = useState<Record<string, NoteDraft>>({});
  const [packetStatus, setPacketStatus] = useState('');
  const importInput = useRef<HTMLInputElement>(null);
  const [q, setQ] = useState('');
  const [scope, setScope] = useState<'known' | 'all'>('known');
  const [origin, setOrigin] = useState<'all' | 'forrt_flora_extractor' | 'retested_discovery'>('all');
  const [group, setGroup] = useState<'replication' | 'other_behavioural' | 'registration' | 'all'>('replication');
  const [tier, setTier] = useState<'all' | 'high' | 'medium'>('all');
  const [impact, setImpact] = useState<'all' | 'changes'>('all');
  const [show, setShow] = useState<'open' | 'decided'>('open');
  const [page, setPage] = useState(0);

  useEffect(() => { fetch(base + 'generated/queue/candidates.json').then((r) => r.json()).then(setAll); setDec(readD()); }, []);

  const list = useMemo(() => {
    if (!all) return [];
    const qq = q.toLowerCase().trim();
    return all.filter((c) =>
      (scope === 'all' || c.original_in_wiki) &&
      (origin === 'all' || c.origin === origin) &&
      (group === 'all' || c.group === group) &&
      (tier === 'all' || c.search_tier === tier) &&   // FORRT's rows carry no tier of ours, so a tier filter hides them
      (impact === 'all' || !!c.if_accepted?.changes) &&
      (show === 'open' ? !dec[c.id] : !!dec[c.id]) &&
      (!qq || [c.title_r, c.title_o, c.doi_r, c.doi_o, c.effect?.name].join(' ').toLowerCase().includes(qq)));
  }, [all, dec, q, scope, show, origin, group, tier, impact]);

  const draftFor = (c: Cand, d?: Decision): NoteDraft => drafts[c.id] ?? { rationale: d?.rationale ?? '', evidence: d?.evidence ?? '' };
  const updateDraft = (id: string, key: keyof NoteDraft, value: string) => setDrafts((old) => ({
    ...old,
    [id]: {
      ...(old[id] ?? { rationale: dec[id]?.rationale ?? '', evidence: dec[id]?.evidence ?? '' }),
      [key]: value,
    },
  }));
  const decide = (c: Cand, v: Decision['v'], outcome?: string) => {
    const note = draftFor(c);
    const d = { ...dec, [c.id]: { v, outcome: outcome ?? c.outcome ?? undefined, rationale: note.rationale || undefined, evidence: note.evidence || undefined, at: new Date().toISOString() } };
    setDec(d); saveD(d);
  };
  const saveNotes = (c: Cand, d: Decision) => {
    const note = draftFor(c, d), next = { ...dec, [c.id]: { ...d, rationale: note.rationale || undefined, evidence: note.evidence || undefined, updated_at: new Date().toISOString() } };
    setDec(next); saveD(next);
  };
  const undo = (c: Cand) => {
    const prior = dec[c.id];
    if (prior) setDrafts((old) => ({ ...old, [c.id]: { rationale: prior.rationale ?? '', evidence: prior.evidence ?? '' } }));
    const d = { ...dec }; delete d[c.id]; setDec(d); saveD(d);
  };

  const exportPacket = () => {
    if (!all) return;
    const byId = new Map(all.map((c) => [c.id, c]));
    const packet: ReviewPacket = {
      schema: 'retested.queue.review-packet', version: 1, exported_at: new Date().toISOString(), source: { candidate_count: all.length },
      reviews: Object.entries(dec).flatMap(([id, decision]) => {
        const c = byId.get(id);
        if (!c) return [];
        const note = draftFor(c, decision);
        return [{ candidate: snapshot(c), decision: { ...decision, rationale: note.rationale || undefined, evidence: note.evidence || undefined } }];
      }),
    };
    const blob = new Blob([JSON.stringify(packet, null, 2)], { type: 'application/json' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `retested-review-packet-v1-${new Date().toISOString().slice(0, 10)}.json`; a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 0);
  };

  const importPacket = async (event: Event) => {
    const input = event.currentTarget as HTMLInputElement, file = input.files?.[0];
    input.value = '';
    if (!file || !all) return;
    try {
      const parsed = parsePacket(JSON.parse(await file.text()));
      if (!parsed.packet) { setPacketStatus(parsed.error!); return; }
      const byId = new Map(all.map((c) => [c.id, c]));
      const next = { ...dec }; let imported = 0, skipped = 0;
      for (const review of parsed.packet.reviews) {
        const current = byId.get(review.candidate.id);
        if (!current || !matchesCurrent(current, review.candidate)) { skipped++; continue; }
        const previous = next[current.id];
        if (!previous || Date.parse(review.decision.updated_at ?? review.decision.at) >= Date.parse(previous.updated_at ?? previous.at)) {
          next[current.id] = review.decision; imported++;
        } else skipped++;
      }
      if (imported) { setDec(next); saveD(next); }
      setPacketStatus(`Imported ${imported} decision${imported === 1 ? '' : 's'}${skipped ? `; skipped ${skipped} stale or non-matching row${skipped === 1 ? '' : 's'}` : ''}.`);
    } catch { setPacketStatus('Could not read that JSON review packet.'); }
  };

  const exportCsv = () => {
    if (!all) return;
    const byId = new Map(all.map((c) => [c.id, c]));
    // FLoRA's own column names, in its own order, so an accepted row can be submitted without rewriting it.
    // Everything after `source` is ours: provenance a FORRT curator needs in order to judge the row, and the two
    // fields FReD codes that we derive (prereg_r from OSF, author_overlap from both author lists).
    const FLORA = ['doi_o', 'title_o', 'year_o', 'doi_r', 'alt_identifier_r', 'title_r', 'author_r', 'journal_r',
                   'year_r', 'url_r', 'outcome', 'outcome_quote', 'outcome_quote_source', 'type', 'source'] as const;
    const EXTRA = ['prereg_r', 'author_overlap', 'retested_link_method', 'retested_link_confidence',
                   'retested_screen_tier', 'retested_found_by', 'retested_review_decision', 'retested_reviewed_at',
                   'retested_review_rationale', 'retested_review_evidence'] as const;
    const esc = (s: unknown) => `"${String(s ?? '').replace(/"/g, '""')}"`;
    const rows = Object.entries(dec).flatMap(([id, d]) => {
      const c = byId.get(id);
      if (d.v !== 'accept' || !c) return [];
      const overlap = c.independence?.verdict === 'shares_author' ? 'TRUE'
        : c.independence?.verdict === 'independent' ? 'FALSE' : '';
      const note = draftFor(c, d);
      return [[
        c.doi_o, c.title_o, c.year_o, c.doi_r, c.osf_id ? `osf.io/${c.osf_id}` : '', c.title_r, c.authors_r,
        c.journal_r, c.year_r, c.landing_page, d.outcome ?? c.outcome, c.outcome_quote,
        c.outcome_quote ? 'abstract' : '', c.type, `${c.origin} via Retested`,
        c.preregistered ? (c.preregistered.is_registration ? c.preregistered.date ?? 'TRUE' : 'FALSE') : '',
        overlap, c.link_method, c.link_confidence, c.search_tier, (c.found_by ?? []).join('+'),
        'accepted by local human review draft', d.at, note.rationale, note.evidence,
      ].map(esc).join(',')];
    });
    const blob = new Blob([[[...FLORA, ...EXTRA].join(','), ...rows].join('\n')], { type: 'text/csv' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `retested-accepted-${new Date().toISOString().slice(0, 10)}.csv`; a.click();
  };

  if (!all) return <p class="faint">Loading candidates…</p>;
  const nDec = Object.keys(dec).length, nAcc = Object.values(dec).filter((d) => d.v === 'accept').length;
  const pageList = list.slice(page * PAGE, page * PAGE + PAGE);

  return (
    <div>
      <div class="qbar">
        <input type="search" placeholder="Filter by title, DOI, effect…" value={q} onInput={(e) => { setQ((e.target as HTMLInputElement).value); setPage(0); }} aria-label="Filter candidates" />
        <select value={scope} onChange={(e) => { setScope((e.target as HTMLSelectElement).value as any); setPage(0); }} aria-label="Scope">
          <option value="known">Originals already in the wiki</option>
          <option value="all">All candidates</option>
        </select>
        <select value={origin} onChange={(e) => { setOrigin((e.target as HTMLSelectElement).value as any); setPage(0); }} aria-label="Source">
          <option value="all">Both sources</option>
          <option value="forrt_flora_extractor">FORRT's extractor</option>
          <option value="retested_discovery">Found by Retested</option>
        </select>
        <select value={group} onChange={(e) => { setGroup((e.target as HTMLSelectElement).value as any); setPage(0); }} aria-label="Kind">
          <option value="replication">Psychology replications</option>
          <option value="other_behavioural">Other behavioural science</option>
          <option value="registration">Registered protocols</option>
          <option value="all">All kinds</option>
        </select>
        <select value={tier} onChange={(e) => { setTier((e.target as HTMLSelectElement).value as any); setPage(0); }} aria-label="Search tier">
          <option value="all">Any search tier</option>
          <option value="high">Strong title/abstract signal</option>
          <option value="medium">Weaker signal (more false positives)</option>
        </select>
        <select value={impact} onChange={(e) => { setImpact((e.target as HTMLSelectElement).value as any); setPage(0); }} aria-label="Impact">
          <option value="all">Any impact</option>
          <option value="changes">Would change a verdict</option>
        </select>
        <select value={show} onChange={(e) => { setShow((e.target as HTMLSelectElement).value as any); setPage(0); }} aria-label="Status">
          <option value="open">Not yet reviewed</option>
          <option value="decided">My decisions</option>
        </select>
        <span class="mono faint">{list.length.toLocaleString()} shown · {nDec} reviewed · {nAcc} accepted</span>
        <span class="mono faint">Local review drafts — stored only in this browser until you export a packet.</span>
        <button class="btn ghost" disabled={!nAcc} onClick={exportCsv}>Export accepted (CSV)</button>
        <button class="btn ghost" disabled={!nDec} onClick={exportPacket}>Export all decisions (JSON)</button>
        <button class="btn ghost" onClick={() => importInput.current?.click()}>Import review packet</button>
        <input ref={importInput} type="file" accept="application/json,.json" hidden onChange={importPacket} />
        {packetStatus && <span class="mono faint" role="status">{packetStatus}</span>}
      </div>
      <ol class="qlist">
        {pageList.map((c) => {
          const d = dec[c.id];
          const note = draftFor(c, d);
          return (
            <li key={c.id} class="qitem">
              <div class="qhead">
                <span class={`stamp sm ${c.outcome === 'successful' ? 't-ok' : c.outcome === 'failed' ? 't-bad' : c.outcome === 'mixed' ? 't-mix' : 't-na'}`}>machine says: {c.outcome ?? 'no outcome'}</span>
                <span class="chip">{ORIGIN[c.origin]}</span>
                {c.group !== 'replication' && <span class="chip warn">{GROUP[c.group]}</span>}
                {c.evidence_tier === 'preprint' && <span class="chip">preprint</span>}
                {c.search_tier === 'medium' && <span class="chip warn">weaker signal</span>}
                {c.preregistered?.is_registration && <span class="chip">preregistered</span>}
                {c.declared_design && <span class={`chip${c.declared_design.fidelity === 'low' ? ' warn' : ''}`}>{c.declared_design.word} replication</span>}
                {c.independence?.verdict === 'shares_author' && <span class="chip warn">shares an author: {c.independence.distinctive.join(', ')}</span>}
                {c.independence?.verdict === 'independent' && <span class="chip">independent team</span>}
                {c.effect && <a class="chip" href={`${base}effect/${c.effect.slug}/`}>{c.effect.name}</a>}
                {c.rep_already_known && <span class="chip warn">replication paper already known for another original</span>}
                {d && <span class={`chip ${d.v === 'accept' ? '' : 'claim'}`}>you: {d.v}</span>}
              </div>
              <div class="qpair">
                <div><div class="label">Replication{c.year_r ? ` · ${c.year_r}` : ''}</div><a href={c.doi_r ? "https://doi.org/" + c.doi_r : c.landing_page || (c.osf_id ? "https://osf.io/" + c.osf_id : "#")} rel="noopener">{c.title_r ?? c.doi_r ?? c.landing_page ?? c.id}</a>{c.journal_r && <div class="faint jr">{c.journal_r}</div>}</div>
                <div>
                  <div class="label">Claimed original{c.year_o ? ` · ${c.year_o}` : ''}</div>
                  {c.doi_o
                    ? <a href={`https://doi.org/${c.doi_o}`} rel="noopener">{c.title_o ?? c.doi_o}</a>
                    : c.original_named?.authors
                      ? <span class="faint">named only: {c.original_named.authors} {c.original_named.year ?? ''} — no DOI resolved</span>
                      : <span class="faint">not resolved</span>}
                  {(c.authors_o || c.journal_o) && <div class="faint jr">{[c.authors_o, c.journal_o].filter(Boolean).join(' · ')}{c.cited_by_o ? ` · cited ${c.cited_by_o.toLocaleString()}×` : ''}</div>}
                  {c.retracted_o && <div><span class="chip warn">the original has been RETRACTED</span></div>}
                  {c.duplicates?.length ? <div class="faint jr mono">also deposited {c.duplicates.length} other time{c.duplicates.length === 1 ? '' : 's'} — versions or mirrors, collapsed into this row</div> : null}
                  {c.duplicate_originals_disagree && <div><span class="chip warn">those copies were matched to different originals — check this one</span></div>}
                  {c.original_named?.description && <div class="faint jr">“{c.original_named.description}”</div>}
                  {c.link_method && <div class="faint jr mono">{HOW[c.link_method] ?? c.link_method}</div>}
                  {c.link_evidence?.source_url && <div class="faint jr"><a href={c.link_evidence.source_url} rel="noopener">Source for this original</a>{c.link_evidence.evidence && <span> | {c.link_evidence.evidence}</span>}</div>}
                  {c.original_studies?.length ? <details><summary class="faint jr">{c.original_studies.length} original studies identified in this replication</summary><ul>{c.original_studies.map(o => <li><a href={"https://doi.org/" + o.doi_o}>{o.title_o || o.doi_o}</a>{o.year_o ? " (" + o.year_o + ")" : ""}<div class="faint jr">{o.evidence} | <a href={o.source_url} rel="noopener">source</a></div></li>)}</ul></details> : null}
                  {c.link_evidence?.runner_up && <div class="faint jr mono">next best: {c.link_evidence.runner_up.title_o ?? c.link_evidence.runner_up.doi_o}</div>}
                </div>
              </div>
              {c.outcome_quote && <blockquote class="q">“{c.outcome_quote}”</blockquote>}
              {c.abstract && <details><summary class="faint">Abstract</summary><p class="abs">{c.abstract}{c.abstract.length >= 699 ? '…' : ''}</p></details>}
              {c.if_accepted && (
                <p class={`impact${c.if_accepted.changes ? ' moves' : ''}`}>
                  {c.if_accepted.changes
                    ? <>Accepting this changes the record from <b>{c.if_accepted.from_label}</b> to <b>{c.if_accepted.to_label}</b> ({c.if_accepted.k_before} coded {c.if_accepted.k_before === 1 ? 'replication' : 'replications'} &rarr; {c.if_accepted.k_after}).</>
                    : <>Accepting this leaves the record at <b>{c.if_accepted.to_label}</b>, on {c.if_accepted.k_after} coded replications.</>}
                </p>
              )}
              <div class="qact">
                {!d ? (
                  <>
                    <button class="btn" onClick={() => decide(c, 'accept')}>Accept</button>
                    <select onChange={(e) => decide(c, 'accept', (e.target as HTMLSelectElement).value)} aria-label="Accept with corrected outcome">
                      <option value="">Accept, but outcome is…</option><option value="successful">successful</option><option value="failed">failed</option><option value="mixed">mixed</option>
                    </select>
                    <button class="btn ghost" onClick={() => decide(c, 'reject')}>Not a replication</button>
                    <button class="btn ghost" onClick={() => decide(c, 'unsure')}>Unsure</button>
                  </>
                ) : <button class="btn ghost" onClick={() => undo(c)}>Undo</button>}
                <span class="mono faint qm">{[c.link_confidence && `link: ${c.link_confidence}`, c.outcome_confidence && `outcome: ${c.outcome_confidence}`,
                  c.found_by?.length && `found by ${c.found_by.join(' + ')} search`, c.screen_reason].filter(Boolean).join(' · ')}</span>
              </div>
              <div class="qact" aria-label="Local review notes">
                <label>Rationale <textarea value={note.rationale} onInput={(e) => updateDraft(c.id, 'rationale', (e.target as HTMLTextAreaElement).value)} placeholder="Why accept, reject, or hold this row?" rows={2} /></label>
                <label>Evidence checked <textarea value={note.evidence} onInput={(e) => updateDraft(c.id, 'evidence', (e.target as HTMLTextAreaElement).value)} placeholder="Source, page, quote, or unresolved concern" rows={2} /></label>
                {d && <button class="btn ghost" onClick={() => saveNotes(c, d)}>Save local notes</button>}
              </div>
            </li>
          );
        })}
      </ol>
      <div class="qpager">
        <button class="btn ghost" disabled={page === 0} onClick={() => setPage(page - 1)}>← Previous</button>
        <span class="mono faint">page {page + 1} / {Math.max(1, Math.ceil(list.length / PAGE))}</span>
        <button class="btn ghost" disabled={(page + 1) * PAGE >= list.length} onClick={() => setPage(page + 1)}>Next →</button>
      </div>
    </div>
  );
}
