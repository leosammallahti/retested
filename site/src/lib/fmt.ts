// Formatting and vocabulary helpers shared by pages and islands (no Node imports here).

export const BASE = (import.meta.env.BASE_URL || '/').replace(/\/?$/, '/');
export const u = (p: string) => BASE + p.replace(/^\//, '');

export const atlasUrl = (doi: string) => `https://forrt.org/flora-replication-atlas/doi/${doi}/`;
export const doiUrl = (doi: string) => `https://doi.org/${doi}`;

export type Tone = 'ok' | 'bad' | 'mix' | 'na';

export const OUTCOME: Record<string, { label: string; tone: Tone }> = {
  successful: { label: 'Replicated', tone: 'ok' },
  failed: { label: 'Did not replicate', tone: 'bad' },
  mixed: { label: 'Mixed', tone: 'mix' },
  inconclusive: { label: 'Inconclusive', tone: 'na' },
  not_coded: { label: 'Not coded yet', tone: 'na' },
};

export const RECORD_TONE: Record<string, Tone> = {
  replicated: 'ok', largely_replicated: 'ok', single_success: 'ok',
  contested: 'mix', single_mixed: 'mix',
  largely_failed: 'bad', failed: 'bad', reversed: 'bad', single_failure: 'bad',
  unclear: 'na', untested: 'na',
};

export const RECORD_BLURB: Record<string, string> = {
  replicated: 'Every replication with a verdict found the effect.',
  largely_replicated: 'Most replications found the effect.',
  contested: 'Replications disagree with one another.',
  largely_failed: 'Most replications did not find the effect.',
  failed: 'No replication with a verdict found the effect.',
  reversed: 'Later work suggests the effect goes the other way or has a different cause (curated judgement).',
  single_success: 'One replication, and it found the effect. One attempt is a thin record.',
  single_failure: 'One replication, and it did not find the effect. One attempt is a thin record.',
  single_mixed: 'One replication, with mixed results.',
  unclear: 'Replications exist, but none has a coded verdict yet.',
  untested: 'No replication attempt is linked to this effect in the counted record yet.',
};

export const NUMERIC_TONE: Record<string, Tone> = { robust: 'ok', smaller: 'mix', negligible: 'bad', reversed: 'bad', inconclusive: 'na' };

export const CRITERIA_LABELS: Record<string, string> = {
  significance_r: 'Replication is significant, same direction',
  significance_agg: 'Original + replication pooled is significant',
  consistency_ci: "Original falls inside replication's 95% CI",
  consistency_pi: "Replication falls inside original's prediction interval",
  homogeneity: 'Original and replication statistically consistent',
  homogeneity_significance: 'Consistent and jointly significant',
  small_telescopes: 'Replication rules out a tiny effect (small telescopes)',
};

export const DISPLAY_SOURCE: Record<string, string> = { flora: 'FLoRA', fred: 'FReD', legacy: 'FReD legacy 2.4.1', retested: 'Retested reviewed', read: 'Read for Retested', reviewed: 'Checked by Retested' };

/** APA-style r: no leading zero, sign kept. */
export const fr = (x: number | null | undefined, d = 2) =>
  x == null || !isFinite(x) ? '–' : (x < 0 ? '−' : '') + Math.abs(x).toFixed(d).replace(/^0/, '');

export const pct = (x: number | null | undefined, d = 0) => (x == null ? '–' : (x * 100).toFixed(d) + '%');
export const int = (x: number | null | undefined) => (x == null ? '–' : Math.round(x).toLocaleString('en-US'));

export function pBucket(p: number | null | undefined): string | null {
  if (p == null || !isFinite(p)) return null;
  if (p <= 0.001) return 'p ≤ .001';
  if (p <= 0.005) return 'p ≤ .005';
  if (p <= 0.05) return 'p < .05';
  return 'p > .05';
}

export const clip = (s: string | null | undefined, n: number) => (!s ? '' : s.length <= n ? s : s.slice(0, n - 1).replace(/\s+\S*$/, '') + '…');

export const cleanQuote = (s: string | null | undefined) => {
  if (!s) return '';
  const t = s.trim().replace(/\s+/g, ' ');
  const pairs: Record<string, string> = { '"': '"', "'": "'", '“': '”', '‘': '’' };
  return t.length > 1 && pairs[t[0]] === t[t.length - 1] ? t.slice(1, -1).trim() : t;
};

/** Curated descriptions are often fragments ("that hearing about old age..."): make them a sentence. */
export function asClaim(s: string | null | undefined): string | null {
  if (!s) return null;
  let t = cleanQuote(s).replace(/​/g, '').replace(/^(that|claim:)\s+/i, '').replace(/^\*+|\*+$/g, '').trim();
  if (t.length < 12) return null;
  t = t[0].toUpperCase() + t.slice(1);
  return /[.!?]$/.test(t) ? t : t + '.';
}

/** "Wallrich, L.*, & Röseler, L.*, Hartmann, H., ... (2026). Title" -> "Wallrich, Röseler, Hartmann et al. (2026). Title" */
export function shortCitation(c: string): string {
  const m = c.match(/^(.*?)\s*\((\d{4})\)\.?\s*(.*)$/s);
  if (!m) return c;
  const fams = [...m[1].matchAll(/(?:^|,\s*&?\s*|&\s*)([^,&]+?),\s*[A-Z]\./g)].map((x) => x[1].trim()).filter(Boolean);
  const who = fams.length > 3 ? `${fams.slice(0, 3).join(', ')} et al.` : m[1];
  return `${who} (${m[2]}). ${m[3].split(/\n\s*\n/)[0].trim()}`;
}
