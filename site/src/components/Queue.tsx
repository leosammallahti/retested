// Review queue: machine-found replication candidates (FORRT flora-extractor) awaiting a human.
// Decisions are kept in this browser and exported as CSV in FLoRA's submission columns.
import { useEffect, useMemo, useState } from 'preact/hooks';

interface Cand {
  id: string; doi_r: string; title_r: string | null; year_r: number | null; journal_r: string | null;
  doi_o: string | null; title_o: string | null; year_o: number | null; outcome: string | null; outcome_quote: string | null;
  outcome_confidence: string | null; link_confidence: string | null; type: string | null; rep_already_known: boolean; original_in_wiki: boolean;
  effect: { slug: string; name: string } | null; abstract: string | null; models: string[];
}
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
  const [show, setShow] = useState<'open' | 'decided'>('open');
  const [page, setPage] = useState(0);

  useEffect(() => { fetch(base + 'generated/queue/candidates.json').then((r) => r.json()).then(setAll); setDec(readD()); }, []);

  const list = useMemo(() => {
    if (!all) return [];
    const qq = q.toLowerCase().trim();
    return all.filter((c) =>
      (scope === 'all' || c.original_in_wiki) &&
      (show === 'open' ? !dec[c.id] : !!dec[c.id]) &&
      (!qq || [c.title_r, c.title_o, c.doi_r, c.doi_o, c.effect?.name].join(' ').toLowerCase().includes(qq)));
  }, [all, dec, q, scope, show]);

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
      return [c.doi_o, c.doi_r, c.title_o, c.title_r, d.outcome ?? c.outcome, c.outcome_quote, 'abstract', 'accepted by human reviewer', d.at, 'forrt_flora_extractor via Retested'].map(esc).join(',');
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
                {c.effect && <a class="chip" href={`${base}effect/${c.effect.slug}/`}>{c.effect.name}</a>}
                {c.rep_already_known && <span class="chip warn">replication paper already known for another original</span>}
                {d && <span class={`chip ${d.v === 'accept' ? '' : 'claim'}`}>you: {d.v}</span>}
              </div>
              <div class="qpair">
                <div><div class="label">Replication{c.year_r ? ` · ${c.year_r}` : ''}</div><a href={`https://doi.org/${c.doi_r}`} rel="noopener">{c.title_r ?? c.doi_r}</a>{c.journal_r && <div class="faint jr">{c.journal_r}</div>}</div>
                <div><div class="label">Claimed original{c.year_o ? ` · ${c.year_o}` : ''}</div>{c.doi_o ? <a href={`https://doi.org/${c.doi_o}`} rel="noopener">{c.title_o ?? c.doi_o}</a> : <span class="faint">not resolved</span>}</div>
              </div>
              {c.outcome_quote && <blockquote class="q">“{c.outcome_quote}”</blockquote>}
              {c.abstract && <details><summary class="faint">Abstract</summary><p class="abs">{c.abstract}{c.abstract.length >= 699 ? '…' : ''}</p></details>}
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
                <span class="mono faint qm">{[c.link_confidence && `link: ${c.link_confidence}`, c.outcome_confidence && `outcome: ${c.outcome_confidence}`].filter(Boolean).join(' · ')}</span>
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
