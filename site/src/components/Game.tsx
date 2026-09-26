// "Did it replicate?" — calibration game. Cards never contain answers; each reveal is fetched after lock-in.
import { useEffect, useMemo, useRef, useState } from 'preact/hooks';

interface Item {
  id: string; tier: 'study' | 'famous' | 'found'; claim: string; method?: string | null; written?: boolean; context_ready?: boolean;
  year: number | null; journal: string | null; discipline: string | null; effect_name?: string;
  cues: { n?: number | null; p?: string | null; r?: number | null; cited_by?: number | null; gs_citations?: number | null };
}
interface Rep { authors: string | null; year: number | null; journal: string | null; doi: string | null; n: number | null; r: number | null; quote: string | null }
interface Reveal {
  id: string; answer: 'successful' | 'failed'; title_o?: string; authors_o?: string; replications: Rep[];
  finding: string | null; effect: { slug: string; name: string } | null; curated_status?: string; critiques?: string; original_paper?: string;
  effect_label?: string | null; unverified?: boolean; how_found?: string;
}
interface Played { id: string; p: number; y: 0 | 1; hit: 0 | 1; brier: number; cues: number; day?: string; candidate?: 1 }

const ROUND = 10;
const KEY = 'retested.game.v1';
const DAILY_BASE_RATE = (ROUND / 2 / ROUND) * 100;

// Random modes use a small deterministic PRNG once a session seed is chosen.
function rng(seed: number) {
  return () => { seed |= 0; seed = (seed + 0x6d2b79f5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
const hash = (s: string) => [...s].reduce((h, c) => (Math.imul(h, 31) + c.charCodeAt(0)) | 0, 7);
const today = () => new Date().toISOString().slice(0, 10);
const fr = (x: number | null | undefined) => (x == null ? '–' : (x < 0 ? '−' : '') + Math.abs(x).toFixed(2).replace(/^0/, ''));
const points = (brier: number) => Math.round(100 * (1 - 4 * brier)); // 100 = certain & right, 0 = 50/50, −300 = certain & wrong

function load(): Played[] {
  try {
    const stored = JSON.parse(localStorage.getItem(KEY) || '[]');
    return Array.isArray(stored) ? stored.filter((x): x is Played => !!x && typeof x.id === 'string') : [];
  } catch { return []; }
}
function save(x: Played[]) { try { localStorage.setItem(KEY, JSON.stringify(x.slice(-2000))); } catch { /* private mode */ } }

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Request failed (${response.status}).`);
  return response.json() as Promise<T>;
}

// This mirrors pipeline.game.context_ready. Keep the browser defensive in case a stale or partial deploy ever
// serves a schedule and card payload from different builds.
function playable(item: Item): boolean {
  return item.context_ready === true && !!item.written && item.claim.trim().length >= 30 && !!item.method?.trim();
}

function dailyDeck(items: Item[], schedules: Record<string, string[]>, day: string): Item[] {
  const byId = new Map(items.map((item) => [item.id, item]));
  const ids = schedules[day.slice(5)] ?? [];
  const deck = ids.map((id) => byId.get(id)).filter((item): item is Item => !!item);
  if (deck.length !== ROUND) throw new Error(`The daily deck for ${day} is incomplete.`);
  return deck;
}

export default function Game({ base }: { base: string }) {
  const [items, setItems] = useState<Item[] | null>(null);
  const [dailySchedules, setDailySchedules] = useState<Record<string, string[]> | null>(null);
  const [mode, setMode] = useState<'daily' | 'endless' | 'famous' | 'found' | null>(null);
  const [deck, setDeck] = useState<Item[]>([]);
  const [i, setI] = useState(0);
  const [p, setP] = useState(50);
  const [cues, setCues] = useState(0);
  const [reveal, setReveal] = useState<Reveal | null>(null);
  const [round, setRound] = useState<Played[]>([]);
  const [history, setHistory] = useState<Played[]>([]);
  const [copied, setCopied] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loadAttempt, setLoadAttempt] = useState(0);
  const [revealError, setRevealError] = useState<string | null>(null);
  const [locking, setLocking] = useState(false);
  const [manualShare, setManualShare] = useState<string | null>(null);

  useEffect(() => {
    let current = true;
    setLoadError(null);
    Promise.all([
      getJson<Item[]>(base + 'generated/game/items.json'),
      getJson<Record<string, string[]>>(base + 'generated/game/daily.json'),
    ]).then(([cards, schedules]) => {
      if (current) { setItems(cards); setDailySchedules(schedules); }
    }).catch(() => {
      if (current) setLoadError('The game deck could not load. Your saved results are still on this device.');
    });
    setHistory(load());
    return () => { current = false; };
  }, [base, loadAttempt]);

  const start = (m: 'daily' | 'endless' | 'famous' | 'found') => {
    if (!items || !dailySchedules) return;
    setLoadError(null);
    const r = rng(hash(String(Date.now())));
    // 'found' is a deck of its own on purpose. These replications sit outside Retested's counted record; nobody has
    // reviewed them, and they succeed more often than the counted ones — mixing them in would quietly move the
    // base rate a player is calibrating against.
    const want = m === 'famous' ? 'famous' : m === 'found' ? 'found' : 'study';
    try {
      let pool = items.filter((x) => x.tier === want && playable(x));
      if (m === 'daily') {
        pool = dailyDeck(items, dailySchedules, today());
        if (pool.some((item) => !playable(item))) throw new Error('The daily deck is missing card context.');
      } else {
        const seen = new Set(history.map((h) => h.id));
        const fresh = pool.filter((x) => !seen.has(x.id));
        pool = shuffle(fresh.length >= ROUND ? fresh : pool, r).slice(0, ROUND);
      }
      if (pool.length !== ROUND) throw new Error('There are not enough fully explained cards for this round.');
      setMode(m); setDeck(pool); setI(0); setRound([]); next(m === 'daily' ? DAILY_BASE_RATE : 50);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : 'The game deck is unavailable.');
    }
  };
  const next = (baseRate = 50) => { setP(baseRate); setCues(0); setReveal(null); setRevealError(null); setCopied(false); setManualShare(null); };

  const card = deck[i];
  const lock = async () => {
    if (!card || locking) return;
    setLocking(true); setRevealError(null);
    try {
      const rv = await getJson<Reveal>(`${base}generated/game/r/${card.id}.json`);
      const y = rv.answer === 'successful' ? 1 : 0;
      const q = p / 100;
      const brier = (q - y) ** 2;
      const rec: Played = { id: card.id, p: q, y: y as 0 | 1, hit: ((q >= 0.5 ? 1 : 0) === y ? 1 : 0) as 0 | 1,
        brier, cues, day: mode === 'daily' ? today() : undefined, candidate: mode === 'found' ? 1 : undefined };
      const h = [...history, rec];
      setHistory(h); save(h); setRound([...round, rec]); setReveal(rv);
    } catch {
      setRevealError('The result could not load. Your answer has not been recorded; try again.');
    } finally {
      setLocking(false);
    }
  };

  const done = mode && i >= deck.length;
  const total = round.reduce((s, x) => s + points(x.brier), 0);
  const stats = useMemo(() => calib(history.filter((x) => !x.candidate && !x.id.startsWith('d'))), [history]);

  if (!items || !dailySchedules) return loadError ? (
    <div class="card ink" role="alert"><p>{loadError}</p><button class="btn" onClick={() => { setItems(null); setDailySchedules(null); setLoadAttempt((n) => n + 1); }}>Try again</button></div>
  ) : <p class="faint" role="status">Loading the deck…</p>;

  if (!mode || done) {
    const share = done ? shareText(round, mode!, total) : '';
    const shareResult = async () => {
      try {
        if (navigator.share) {
          await navigator.share({ title: 'Retested · Did it replicate?', text: share });
          setCopied(true);
        } else if (navigator.clipboard?.writeText) {
          await navigator.clipboard.writeText(share);
          setCopied(true);
        } else setManualShare(share);
      } catch {
        setManualShare(share);
      }
    };
    return (
      <div class="gstart">
        {done && (
          <div class="card ink gsum" role="status" aria-live="polite">
            <div class="label">Round complete</div>
            <p class="big num">{total > 0 ? '+' : ''}{total} points</p>
            <p class="emo" aria-label="round summary">{round.map((x) => (points(x.brier) >= 40 ? '🟦' : points(x.brier) >= 0 ? '🟨' : '🟥')).join('')}</p>
            <p class="muted">{(() => { const calls = round.filter((x) => Math.abs(x.p - 0.5) > 0.001); return calls.length ? `${calls.filter((x) => x.hit).length} of ${calls.length} calls went the right way` : 'You sat on the fence every time'; })()}. Blue = confident and right, yellow = hedged, red = confidently wrong.</p>
            <button class="btn" onClick={() => { void shareResult(); }}>{copied ? 'Shared ✓' : 'Share result'}</button>
            {manualShare && <><p class="faint">Copy this result manually:</p><textarea aria-label="Game result to copy" readOnly value={manualShare} onFocus={(e) => e.currentTarget.select()} onClick={(e) => e.currentTarget.select()} style={{ width: '100%', minHeight: '5.5rem', boxSizing: 'border-box' }} /></>}
          </div>
        )}
        {loadError && <div class="card ink" role="alert"><p>{loadError}</p><button class="btn" onClick={() => setLoadError(null)}>Dismiss</button></div>}
        <div class="gmodes">
          <button class="gm" onClick={() => start('daily')}><b>Today's ten</b><span>The same ten cards for everyone, today. Eight real studies, two famous effects.</span></button>
          <button class="gm" onClick={() => start('endless')}><b>Ten more studies</b><span>Random original studies you haven't seen, from {items.filter((x) => x.tier === 'study' && playable(x)).length} with a clear replication verdict and an explained original experiment.</span></button>
          <button class="gm" onClick={() => start('famous')}><b>Famous effects</b><span>{items.filter((x) => x.tier === 'famous' && playable(x)).length} curated effects with a plain-language original-study explanation.</span></button>
          {items.some((x) => x.tier === 'found' && playable(x)) && (
            <button class="gm" onClick={() => start('found')}><b>Unreviewed candidate studies</b><span>{items.filter((x) => x.tier === 'found' && playable(x)).length} candidates found by Retested’s search. This is a separate, unreviewed deck—not part of your calibration record—and does not establish absence from all FORRT data.</span></button>
          )}
        </div>
        {stats.n >= 10 && <Calibration s={stats} />}
      </div>
    );
  }

  return (
    <div class="gplay">
      <div class="gtop mono"><span>Card {i + 1} / {deck.length}</span><span>{total > 0 ? '+' : ''}{total} pts</span></div>
      <article class="gcard card ink">
        <div class="label">{card.tier === 'famous' ? 'Famous effect' : card.tier === 'found' ? 'Unreviewed candidate · separate from Retested’s calibration record' : 'Original study'}{card.discipline && ` · ${card.discipline}`}{card.year && ` · ${card.year}`}</div>
        {card.effect_name && <h3 class="gname">{card.effect_name}</h3>}
        <p class="gclaim">{card.claim}</p>
        {card.method && <div class="gcontext"><div class="label">What the original study did</div><p class="gmethod">{card.method}</p></div>}
        {card.tier === 'found' && <p class="gunver">This candidate is separate because nobody has reviewed its original–later link or outcome. Its result is an automated abstract reading, not a Retested verdict.</p>}
        {card.journal && <p class="faint gj">Published in <i>{card.journal}</i></p>}
        <div class="gcues">
          {card.tier === 'study' && !reveal && cues === 0 && (card.cues.n || card.cues.p || card.cues.r != null) && (
            <button class="btn ghost" onClick={() => setCues(1)}>Show the original's numbers</button>
          )}
          {(cues > 0 || reveal) && (
            <p class="mono gnums">
              {card.cues.n != null && <span>N = {card.cues.n}</span>}
              {card.cues.p && <span>{card.cues.p}</span>}
              {card.cues.r != null && <span>effect r = {fr(card.cues.r)}</span>}
              {card.cues.cited_by != null && <span>{card.cues.cited_by.toLocaleString()} citations</span>}
            </p>
          )}
          {card.tier === 'famous' && card.cues.gs_citations != null && <p class="mono gnums"><span>≈{card.cues.gs_citations.toLocaleString()} Google Scholar citations</span></p>}
        </div>

        {!reveal ? (
          <div class="gguess">
            <label for="pp" class="gq">{card.tier === 'found' ? 'How likely is it that this unreviewed candidate reported the stated result?' : 'How likely is it that later replications found this effect?'}</label>
            <div class="gslider">
              <span class="claim mono">0%</span>
              <input id="pp" type="range" min={1} max={99} value={p} onInput={(e) => setP(+(e.target as HTMLInputElement).value)} aria-valuetext={`${p} percent`} />
              <span class="obs mono">100%</span>
            </div>
            <p class="gp"><b class="num">{p}%</b> <span class="faint">{p < 20 ? 'Surely not' : p < 40 ? 'Probably not' : p <= 60 ? 'Coin flip' : p <= 80 ? 'Probably' : 'Surely'}</span></p>
            <button class="btn" onClick={() => { void lock(); }} disabled={locking}>{locking ? 'Loading result…' : 'Lock it in'}</button>
            {revealError && <p class="gunver" role="alert">{revealError}</p>}
            <p class="faint gnote">Scored by Brier: confident and right earns up to 100, a 50/50 guess earns 0, confident and wrong costs up to 300.</p>
          </div>
        ) : (
          <RevealView rv={reveal} rec={round[round.length - 1]} base={base} onNext={() => { setI(i + 1); next(mode === 'daily' ? DAILY_BASE_RATE : 50); }} last={i + 1 >= deck.length} />
        )}
      </article>
    </div>
  );
}

function RevealView({ rv, rec, base, onNext, last }: { rv: Reveal; rec: Played; base: string; onNext: () => void; last: boolean }) {
  const resultRef = useRef<HTMLDivElement>(null);
  const ok = rv.answer === 'successful';
  const pts = points(rec.brier);
  const verdict = rv.unverified
    ? (ok ? 'Candidate reported the result' : 'Candidate did not report the result')
    : (ok ? 'Replicated' : 'Did not replicate');
  useEffect(() => { resultRef.current?.focus(); }, []);
  return (
    <div class="greveal">
      <div ref={resultRef} tabIndex={-1} role="status" aria-live="polite" aria-atomic="true">
        <div class={`stamp ${ok ? 't-ok' : 't-bad'}`}>{verdict}{rv.unverified && ' · unreviewed'}</div>
        <p class="gpts num">{pts > 0 ? '+' : ''}{pts} <span class="faint">you said {Math.round(rec.p * 100)}%</span></p>
      </div>
      {rv.how_found && <p class="gunver">{rv.how_found}</p>}
      {rv.replications.slice(0, 2).map((r) => (
        <div class="grep">
          <p class="mono faint">{[r.authors, r.year, r.journal].filter(Boolean).join(' · ')}{r.n ? ` · N = ${r.n.toLocaleString()}` : ''}{r.r != null ? ` · r = ${fr(r.r)}` : ''}</p>
          {r.quote && <blockquote class="q">“{r.quote.replace(/^["“\s]+|["”\s]+$/g, '').slice(0, 280)}{r.quote.length > 280 ? '…' : ''}”</blockquote>}
        </div>
      ))}
      {rv.curated_status && <p class="muted">Curated verdict: <b>{rv.curated_status}</b>{rv.critiques ? ` — ${rv.critiques.replace(/^Critiques?:\s*/i, '').slice(0, 220)}…` : ''}</p>}
      <p class="glinks">
        {rv.title_o && <span class="faint">Original: {rv.authors_o ? rv.authors_o + ', ' : ''}<i>{rv.title_o}</i>. </span>}
        {rv.effect && <a href={`${base}effect/${rv.effect.slug}/`} target="_blank">Full record: {rv.effect.name} ↗</a>}
        {!rv.effect && rv.finding && <a href={`${base}finding/${rv.finding}/`} target="_blank">Full record ↗</a>}
        {rv.unverified && <a href={`${base}queue/`} target="_blank">See it in the review queue ↗</a>}
      </p>
      <button class="btn" onClick={onNext}>{last ? 'See my score' : 'Next card →'}</button>
    </div>
  );
}

function shuffle<T>(a: T[], r: () => number): T[] {
  const b = [...a];
  for (let k = b.length - 1; k > 0; k--) { const j = Math.floor(r() * (k + 1)); [b[k], b[j]] = [b[j], b[k]]; }
  return b;
}

function shareText(round: Played[], mode: string, total: number) {
  const row = round.map((x) => (points(x.brier) >= 40 ? '🟦' : points(x.brier) >= 0 ? '🟨' : '🟥')).join('');
  const kind = mode === 'found' ? 'unreviewed candidate round' : mode === 'daily' ? today() : '';
  return `Retested · Did it replicate? ${kind}\n${row}\n${total > 0 ? '+' : ''}${total} points · ${location.origin}${location.pathname}`;
}

function calib(h: Played[]) {
  const bins = [0, 1, 2, 3, 4].map((b) => ({ lo: b * 0.2, n: 0, yes: 0, sum: 0 }));
  let brier = 0;
  for (const x of h) {
    const y = x.y ?? (x.hit ? (x.p >= 0.5 ? 1 : 0) : (x.p >= 0.5 ? 0 : 1));
    const b = bins[Math.min(4, Math.floor(x.p * 5))];
    b.n++; b.yes += y; b.sum += x.p; brier += x.brier;
  }
  const calls = h.filter((x) => Math.abs(x.p - 0.5) > 0.001);
  return { n: h.length, brier: h.length ? brier / h.length : 0, bins, hit: calls.length ? calls.filter((x) => x.hit).length / calls.length : 0 };
}

function Calibration({ s }: { s: ReturnType<typeof calib> }) {
  const W = 260, H = 200, pad = 28;
  const X = (v: number) => pad + v * (W - pad - 8), Y = (v: number) => H - pad - v * (H - pad - 8);
  return (
    <div class="card gcal">
      <div class="label">Your prediction record · {s.n} counted cards</div>
      <p><b class="num">{Math.round(s.hit * 100)}%</b> of your calls right · mean Brier <b class="num">{s.brier.toFixed(3)}</b> <span class="faint">(0.25 = always saying 50%)</span></p>
      <svg viewBox={`0 0 ${W} ${H}`} class="fig" role="img" aria-label="Your stated probability versus how often those effects replicated">
        <line x1={X(0)} y1={Y(0)} x2={X(1)} y2={Y(1)} stroke="var(--rule-2)" stroke-dasharray="3 3" />
        <line x1={X(0)} y1={Y(0)} x2={X(1)} y2={Y(0)} stroke="var(--ink-3)" />
        <line x1={X(0)} y1={Y(0)} x2={X(0)} y2={Y(1)} stroke="var(--ink-3)" />
        {s.bins.filter((b) => b.n > 0).map((b) => <circle cx={X(b.sum / b.n)} cy={Y(b.yes / b.n)} r={3 + Math.sqrt(b.n)} fill="var(--obs)" opacity=".75" />)}
        <text x={X(0.5)} y={H - 6} text-anchor="middle">your probability</text>
        <text x="10" y={Y(0.5)} transform={`rotate(-90 10 ${Y(0.5)})`} text-anchor="middle">actually replicated</text>
      </svg>
      <p class="faint" style="font-size:.82rem">Dots on the dashed line mean your 70% really happens 70% of the time. Laypeople in published studies call about 59% right; prediction markets about 73%.</p>
    </div>
  );
}
