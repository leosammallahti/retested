// "Did it replicate?" as a phone feed: one finding per screen, one tap to guess, then the result.
// Cards never contain answers; each result is fetched after the tap. On a static site that is a casual
// anti-spoiler boundary, not access control.
import type { RefObject } from 'preact';
import { useEffect, useRef, useState } from 'preact/hooks';

interface Item {
  id: string; tier: 'study' | 'famous' | 'found'; claim: string; method?: string | null; written?: boolean; context_ready?: boolean;
  year: number | null; discipline: string | null; effect_name?: string;
}
interface Rep { authors: string | null; year: number | null; journal: string | null; n: number | null; r: number | null; quote: string | null }
interface Reveal {
  id: string; answer: 'successful' | 'failed'; title_o?: string; authors_o?: string; replications: Rep[];
  finding: string | null; effect: { slug: string; name: string } | null; curated_status?: string; critiques?: string;
}
interface Played { id: string; said: 0 | 1; y: 0 | 1 }
interface Stored { seen: string[]; plays: Played[] }

const KEY = 'retested.feed.v1';
const OLD_KEY = 'retested.game.v1'; // the earlier scored game: read only, so cards already played are not dealt first

const fr = (x: number | null | undefined) => (x == null ? '–' : (x < 0 ? '−' : '') + Math.abs(x).toFixed(2).replace(/^0/, ''));
const clip = (s: string, n: number) => (s.length > n ? s.slice(0, n).replace(/\s+\S*$/, '') + '…' : s);

// Several sources put their coding rule in the quote column ("Coded as not replicated: Replicate = 0 ...",
// "Subjective replication success rating = 0 ..."). That is not the replicators' wording, so the feed shows only real
// prose and leaves the note to the full record.
const CODING_NOTE = /^(\[?coded |subjective replication success rating|replicated = (yes|no)|(ticked|crossed) in |rep\d+ (s|study)|\[in supplementary)|the row is recorded as|binary (success )?indicator/i;
function usable(quote: string | null): string | null {
  const t = (quote ?? '').replace(/\s+/g, ' ').replace(/^["“\s]+|["”\s]+$/g, '');
  return t && !CODING_NOTE.test(t) ? t : null;
}

// "Critiques: Floyd and Young 2021 [n=12, citations=1 (GS, January 2023)]." -> "Floyd and Young 2021"
function citedWork(s: string | undefined): string {
  if (!s) return '';
  return s.replace(/^Critiques?:\s*/i, '').replace(/\[[^\]]*\]/g, ' ').replace(/\([^)]*\)/g, ' ')
    .replace(/\s+/g, ' ').replace(/\s+([.,;])/g, '$1').replace(/[.,;\s]+$/, '').trim();
}

function read(key: string): unknown {
  try { return JSON.parse(localStorage.getItem(key) || 'null'); } catch { return null; }
}
function load(): Stored {
  const s = read(KEY) as Partial<Stored> | null;
  const old = read(OLD_KEY);
  const oldIds = Array.isArray(old) ? old.map((x) => x?.id).filter((x): x is string => typeof x === 'string') : [];
  return {
    seen: [...(Array.isArray(s?.seen) ? s.seen : []), ...oldIds],
    plays: Array.isArray(s?.plays) ? s.plays.filter((x) => x && typeof x.id === 'string') : [],
  };
}
function save(s: Stored) {
  try { localStorage.setItem(KEY, JSON.stringify({ seen: s.seen.slice(-3000), plays: s.plays.slice(-3000) })); } catch { /* private mode */ }
}

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Request failed (${response.status}).`);
  return response.json() as Promise<T>;
}

// Mirrors pipeline.game.context_ready: only cards with a written claim and an explained original experiment are dealt.
function playable(item: Item): boolean {
  return item.tier !== 'found' && item.context_ready === true && !!item.written && item.claim.trim().length >= 30 && !!item.method?.trim();
}

function shuffle<T>(a: T[]): T[] {
  const b = [...a];
  for (let k = b.length - 1; k > 0; k--) { const j = Math.floor(Math.random() * (k + 1)); [b[k], b[j]] = [b[j], b[k]]; }
  return b;
}

// Cards not yet shown first, then the rest, so the feed never runs out.
function order(items: Item[], seen: Set<string>): Item[] {
  const pool = items.filter(playable);
  return [...shuffle(pool.filter((x) => !seen.has(x.id))), ...shuffle(pool.filter((x) => seen.has(x.id)))];
}

export default function Feed({ base }: { base: string }) {
  const [queue, setQueue] = useState<Item[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [count, setCount] = useState(4);
  const [tally, setTally] = useState({ n: 0, right: 0 });
  const [first, setFirst] = useState(false);
  const store = useRef<Stored>({ seen: [], plays: [] });
  const seen = useRef<Set<string>>(new Set());

  useEffect(() => {
    let current = true;
    setLoadError(null);
    store.current = load();
    seen.current = new Set(store.current.seen);
    setTally({ n: store.current.plays.length, right: store.current.plays.filter((p) => p.said === p.y).length });
    setFirst(store.current.plays.length === 0);
    getJson<Item[]>(base + 'generated/game/items.json').then((items) => {
      if (!current) return;
      const q = order(items, seen.current);
      if (!q.length) setLoadError('There are no cards to show right now.');
      else setQueue(q);
    }).catch(() => {
      if (current) setLoadError('The cards could not load.');
    });
    return () => { current = false; };
  }, [base, attempt]);

  const persist = () => save({ seen: [...seen.current], plays: store.current.plays });

  const onActive = (index: number, id: string) => {
    if (!seen.current.has(id)) { seen.current.add(id); persist(); }
    setCount((c) => (index >= c - 3 ? c + 4 : c));
  };
  const onAnswer = (rec: Played) => {
    store.current.plays = [...store.current.plays, rec];
    persist();
    setTally({ n: store.current.plays.length, right: store.current.plays.filter((p) => p.said === p.y).length });
    setFirst(false);
  };

  if (!queue) {
    return (
      <div class="fstatus" role={loadError ? 'alert' : 'status'}>
        <p>{loadError ?? 'Loading…'}</p>
        {loadError && <button class="fbtn fgo" onClick={() => { setQueue(null); setAttempt((n) => n + 1); }}>Try again</button>}
      </div>
    );
  }

  return (
    <>
      <div class="ftop">
        <a class="fbrand" href={base}>Retested</a>
        {tally.n > 0 && <span class="ftally mono" aria-label={`${tally.right} right out of ${tally.n}`}>{tally.right}/{tally.n}</span>}
      </div>
      <div class="feed" role="feed" aria-label="Psychology findings">
        {queue.slice(0, count).map((item, i) => (
          <Card key={item.id} item={item} index={i} base={base} hint={first && i === 0} onActive={onActive} onAnswer={onAnswer} />
        ))}
      </div>
    </>
  );
}

interface CardProps {
  item: Item; index: number; base: string; hint: boolean;
  onActive: (index: number, id: string) => void; onAnswer: (rec: Played) => void;
}

function Card({ item, index, base, hint, onActive, onAnswer }: CardProps) {
  const [said, setSaid] = useState<0 | 1 | null>(null);
  const [rv, setRv] = useState<Reveal | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const el = useRef<HTMLElement>(null);
  const result = useRef<HTMLDivElement>(null);
  const report = useRef(onActive);
  report.current = onActive;

  // The card counts as seen once it crosses the middle of the screen, even if it is skipped.
  useEffect(() => {
    if (!el.current || typeof IntersectionObserver === 'undefined') { report.current(index, item.id); return; }
    const io = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) report.current(index, item.id);
    }, { rootMargin: '-45% 0px -45% 0px' });
    io.observe(el.current);
    return () => io.disconnect();
  }, [index, item.id]);

  useEffect(() => { if (rv) result.current?.focus({ preventScroll: true }); }, [rv]);

  const answer = async (choice: 0 | 1) => {
    if (busy || rv) return;
    setBusy(true); setSaid(choice); setErr(null);
    try {
      const r = await getJson<Reveal>(`${base}generated/game/r/${item.id}.json`);
      setRv(r);
      onAnswer({ id: item.id, said: choice, y: r.answer === 'successful' ? 1 : 0 });
    } catch {
      setSaid(null);
      setErr('The result could not load, so your answer was not recorded. Try again.');
    } finally {
      setBusy(false);
    }
  };

  const next = () => {
    const target = el.current?.nextElementSibling;
    const calm = matchMedia('(prefers-reduced-motion: reduce)').matches;
    target?.scrollIntoView({ behavior: calm ? 'auto' : 'smooth', block: 'start' });
  };

  const label = [item.tier === 'famous' ? 'Famous effect' : 'Original study', item.discipline, item.year].filter(Boolean).join(' · ');

  return (
    <article ref={el} class={`fcard${rv ? ' done' : ''}`} aria-posinset={index + 1} aria-setsize={-1}>
      <div class="fbody">
        <p class="flabel mono">{label}</p>
        {item.effect_name && <h2 class="fname">{item.effect_name.replace(/\*+/g, '').trim()}</h2>}
        <div class="fpart">
          <p class="fkey mono">What they tested</p>
          <p class="fclaim">{item.claim}</p>
        </div>
        {item.method && (
          <div class="fpart">
            <p class="fkey mono">How they tested it</p>
            <p class="fmethod">{item.method}</p>
          </div>
        )}
      </div>
      <div class="fdock">
        {!rv ? (
          <>
            <p class="fq" id={`q-${item.id}`}>Did it replicate?</p>
            <div class="fchoices" role="group" aria-labelledby={`q-${item.id}`}>
              <button class={`fbtn yes${said === 1 ? ' picked' : ''}`} disabled={busy} onClick={() => { void answer(1); }}><span aria-hidden="true">✓</span> Replicated</button>
              <button class={`fbtn no${said === 0 ? ' picked' : ''}`} disabled={busy} onClick={() => { void answer(0); }}><span aria-hidden="true">✕</span> Didn’t</button>
            </div>
            {err && <p class="ferr" role="alert">{err}</p>}
            {hint && !err && <p class="fhint mono" aria-hidden="true">Swipe up to skip ↑</p>}
          </>
        ) : (
          <Result rv={rv} said={said!} base={base} box={result} onNext={next} />
        )}
      </div>
    </article>
  );
}

function Result({ rv, said, base, box, onNext }: { rv: Reveal; said: 0 | 1; base: string; box: RefObject<HTMLDivElement>; onNext: () => void }) {
  const ok = rv.answer === 'successful';
  const right = (said === 1) === ok;
  const reps = rv.replications.map((r) => ({ ...r, quote: usable(r.quote) })).filter((r) => r.quote || r.authors).slice(0, 2);
  const record = rv.effect ? `${base}effect/${rv.effect.slug}/` : rv.finding ? `${base}finding/${rv.finding}/` : null;
  const source = [rv.authors_o, rv.title_o].filter(Boolean).join(', ');
  // Famous effects come from a curated list, not from attempt records: keep the names of the later tests and drop the bracketed counts.
  const later = reps.length ? '' : citedWork(rv.critiques);
  return (
    <div class="fresult">
      <div ref={box} tabIndex={-1} role="status" aria-live="polite" aria-atomic="true" class="fverdict-box">
        <p class={`fverdict ${ok ? 'yes' : 'no'}`}><span aria-hidden="true">{ok ? '✓' : '✕'}</span> {ok ? 'It replicated' : 'It did not replicate'}</p>
        <p class={`fgrade mono ${right ? 'right' : 'wrong'}`}>{right ? 'You called it' : 'Not this time'}</p>
      </div>
      {reps.map((r) => (
        <figure class="frep">
          <figcaption class="mono">{[r.authors, r.year].filter(Boolean).join(' ')}{r.n ? ` · N = ${r.n.toLocaleString()}` : ''}{r.r != null ? ` · r = ${fr(r.r)}` : ''}</figcaption>
          {r.quote && <blockquote>“{clip(r.quote, 230)}”</blockquote>}
        </figure>
      ))}
      {later && <p class="fcurated"><b>Later tests:</b> {clip(later, 200)}</p>}
      <p class="flinks">
        {source && <span class="fsource">Original: {clip(source, 140).replace(/[.\s]+$/, '')}</span>}
        {record && <a href={record} target="_blank" rel="noopener">Full record ↗</a>}
      </p>
      <button class="fbtn fgo" onClick={onNext}>Next <span aria-hidden="true">↓</span></button>
    </div>
  );
}
