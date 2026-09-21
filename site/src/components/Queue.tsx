// Review queue: machine-found replication candidates awaiting a human, from two sources — FORRT's own
// flora-extractor and our keyword/citation search screened by DeepSeek.
// Decisions are kept in this browser and exported as CSV in FLoRA's submission columns.
import { useEffect, useMemo, useState } from 'preact/hooks';

interface Cand {
  id: string; doi_r: string; title_r: string | null; year_r: number | null; journal_r: string | null; authors_r?: string | null;
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
  link_evidence?: { score: number; text_sim: number | null; authors_matched: string; year_delta: number; runner_up: { doi_o: string; title_o: string | null; score: number } | null } | null;
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
};
type Decision = { v: 'accept' | 'reject' | 'unsure'; outcome?: string; note?: string; at: string };
const KEY = 'retested.queue.v1';
const PAGE = 25;

const readD = (): Record<string, Decision> => { try { return JSON.parse(localStorage.getItem(KEY) || '{}'); } catch { return {}; } };
const saveD = (d: Record<string, Decision>) => { try { localStorage.setItem(KEY, JSON.stringify(d)); } catch { /* ignore */ } };

export default function Queue({ base }: { base: string }) {
  const [all, setAll] = useState<Cand[] | null>(null);
  const [dec, setDec] = useState<Record<string, Decision>>({});
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

  const decide = (c: Cand, v: Decision['v'], outcome?: string) => {
    const d = { ...dec, [c.id]: { v, outcome: outcome ?? c.outcome ?? undefined, at: new Date().toISOString() } };
    setDec(d); saveD(d);
  };
  const undo = (c: Cand) => { const d = { ...dec }; delete d[c.id]; setDec(d); saveD(d); };

  const exportCsv = () => {
    if (!all) return;
    const byId = new Map(all.map((c) => [c.id, c]));
    const cols = ['doi_o', 'doi_r', 'title_o', 'title_r', 'outcome', 'outcome_quote', 'out_quote_source', 'review_decision', 'reviewed_at', 'origin'];
    const esc = (s: unknown) => `"${String(s ?? '').replace(/"/g, '""')}"`;
    const rows = Object.entries(dec).filter(([, d]) => d.v === 'accept').map(([id, d]) => {
      const c = byId.get(id)!;
      return [c.doi_o, c.doi_r, c.title_o, c.title_r, d.outcome ?? c.outcome, c.outcome_quote, 'abstract', 'accepted by human reviewer', d.at, `${c.origin} via Retested`].map(esc).join(',');
    });
    const blob = new Blob([[cols.join(','), ...rows].join('\n')], { type: 'text/csv' });
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
        <button class="btn ghost" disabled={!nAcc} onClick={exportCsv}>Export accepted (CSV)</button>
      </div>
      <ol class="qlist">
        {pageList.map((c) => {
          const d = dec[c.id];
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
                <div><div class="label">Replication{c.year_r ? ` · ${c.year_r}` : ''}</div><a href={`https://doi.org/${c.doi_r}`} rel="noopener">{c.title_r ?? c.doi_r}</a>{c.journal_r && <div class="faint jr">{c.journal_r}</div>}</div>
                <div>
                  <div class="label">Claimed original{c.year_o ? ` · ${c.year_o}` : ''}</div>
                  {c.doi_o
                    ? <a href={`https://doi.org/${c.doi_o}`} rel="noopener">{c.title_o ?? c.doi_o}</a>
                    : c.original_named?.authors
                      ? <span class="faint">named only: {c.original_named.authors} {c.original_named.year ?? ''} — no DOI resolved</span>
                      : <span class="faint">not resolved</span>}
                  {c.original_named?.description && <div class="faint jr">“{c.original_named.description}”</div>}
                  {c.link_method && <div class="faint jr mono">{HOW[c.link_method] ?? c.link_method}</div>}
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
