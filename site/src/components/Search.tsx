import { useEffect, useMemo, useRef, useState } from 'preact/hooks';

interface Entry { t: 'effect' | 'finding'; s: string; n: string; a?: string[]; d?: string; doi?: string; au?: string; y?: number; k: number }

let cache: Promise<Entry[]> | null = null;
const load = (base: string) => (cache ??= fetch(base + 'generated/search.json').then((r) => r.json()));

const norm = (s: string) => s.toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g, '');

function score(e: Entry, q: string, words: string[]): number {
  const hay = norm([e.n, ...(e.a || []), e.au || '', e.doi || ''].join(' '));
  if (!words.every((w) => hay.includes(w))) return 0;
  let s = 1;
  const name = norm(e.n);
  if (name === q) s += 50;
  else if (name.startsWith(q)) s += 20;
  if (e.t === 'effect') s += 8;
  s += Math.min(e.k, 10);
  return s;
}

export default function Search({ base }: { base: string }) {
  const [q, setQ] = useState('');
  const [data, setData] = useState<Entry[] | null>(null);
  const [sel, setSel] = useState(0);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const close = (ev: MouseEvent) => { if (box.current && !box.current.contains(ev.target as Node)) setQ(''); };
    document.addEventListener('click', close);
    return () => document.removeEventListener('click', close);
  }, []);

  const hits = useMemo(() => {
    const qq = norm(q.trim());
    if (!data || qq.length < 2) return [];
    const words = qq.split(/\s+/);
    return data
      .map((e) => [score(e, qq, words), e] as const)
      .filter(([s]) => s > 0)
      .sort((a, b) => b[0] - a[0])
      .slice(0, 12)
      .map(([, e]) => e);
  }, [q, data]);

  const href = (e: Entry) =>
    e.t === 'effect' ? `${base}effect/${e.s}/` : `${base}finding/${e.s}/`;

  return (
    <div class="search" ref={box} role="search">
      <label class="sr" for="q">Search effects and papers</label>
      <input
        id="q"
        type="search"
        placeholder="Search effects, papers, DOIs…"
        value={q}
        autocomplete="off"
        onFocus={() => load(base).then(setData)}
        onInput={(ev) => { setQ((ev.target as HTMLInputElement).value); setSel(0); load(base).then(setData); }}
        onKeyDown={(ev) => {
          if (ev.key === 'ArrowDown') { setSel((s) => Math.min(s + 1, hits.length - 1)); ev.preventDefault(); }
          if (ev.key === 'ArrowUp') { setSel((s) => Math.max(s - 1, 0)); ev.preventDefault(); }
          if (ev.key === 'Enter' && hits[sel]) location.href = href(hits[sel]);
          if (ev.key === 'Escape') setQ('');
        }}
      />
      {hits.length > 0 && (
        <ul>
          {hits.map((e, i) => (
            <li key={e.t + e.s}>
              <a href={href(e)} class={i === sel ? 'on' : ''}>
                {e.n}
                <small>
                  {e.t === 'effect' ? `effect${e.d ? ' · ' + e.d : ''}` : `paper · ${[e.au, e.y].filter(Boolean).join(', ')}`}
                  {e.k ? ` · ${e.k} replication${e.k === 1 ? '' : 's'} with a verdict` : ''}
                </small>
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
