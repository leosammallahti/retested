import { useEffect, useRef, useState } from 'preact/hooks';

type BroadCategory = 'replicated' | 'mixed' | 'failed' | 'unclear';

export interface FindingGuessProps {
  /** Base-aware answer payload fetched only after the visitor reveals. */
  revealUrl: string;
  /** Base-aware, noindex page containing the complete source dossier. */
  fullRecordHref: string;
  /**
   * Optional stable local identifier. When omitted, the browser path is used,
   * which is unique for the generated finding pages.
   */
  storageId?: string;
  /** Optional, already base-aware link to another local finding page. */
  nextFindingHref?: string;
  /** Optional accessible label for the next-finding link. */
  nextFindingLabel?: string;
}

interface FindingReveal {
  schema_version: 1;
  record: {
    code: string;
    label: string;
    n_attempts: number;
    successful: number;
    mixed: number;
    failed: number;
  };
}

interface Choice {
  category: BroadCategory;
  label: string;
}

const CHOICES: Choice[] = [
  { category: 'replicated', label: 'Replicated / mostly replicated' },
  { category: 'mixed', label: 'Mixed / contested' },
  { category: 'failed', label: 'Failed / mostly failed' },
  { category: 'unclear', label: 'No clear result / no linked attempt' },
];

// These are the site-wide record codes from `fmt.ts` / the build pipeline. In
// particular, a reversal belongs in the broadly failed group, while a one-study
// record remains distinguishable in the exact label shown after reveal.
const CATEGORY_BY_CODE: Record<string, BroadCategory> = {
  replicated: 'replicated',
  largely_replicated: 'replicated',
  single_success: 'replicated',
  contested: 'mixed',
  single_mixed: 'mixed',
  failed: 'failed',
  largely_failed: 'failed',
  reversed: 'failed',
  single_failure: 'failed',
  unclear: 'unclear',
  untested: 'unclear',
  // Defensive aliases for incomplete/non-standard source records.
  inconclusive: 'unclear',
  not_coded: 'unclear',
};

// This deliberately contains no answer, record code, title, URL parameters,
// or timing used for analytics. It is a small, on-device remembering aid.
const PROGRESS_KEY = 'retested.finding-progress.v1';

interface ProgressEntry {
  guess?: BroadCategory;
  revealedAt?: string;
  skipped?: boolean;
}

type ProgressLedger = Record<string, ProgressEntry>;

function isCategory(value: unknown): value is BroadCategory {
  return value === 'replicated' || value === 'mixed' || value === 'failed' || value === 'unclear';
}

function cleanEntry(value: unknown): ProgressEntry | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  const raw = value as Record<string, unknown>;
  const entry: ProgressEntry = {};
  if (isCategory(raw.guess)) entry.guess = raw.guess;
  if (typeof raw.revealedAt === 'string' && raw.revealedAt.length <= 40) entry.revealedAt = raw.revealedAt;
  if (raw.skipped === true) entry.skipped = true;
  return entry.guess || entry.revealedAt ? entry : null;
}

function loadProgress(): { ledger: ProgressLedger; available: boolean } {
  try {
    const raw = localStorage.getItem(PROGRESS_KEY);
    if (!raw) return { ledger: {}, available: true };
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return { ledger: {}, available: true };
    const ledger: ProgressLedger = {};
    for (const [key, value] of Object.entries(parsed)) {
      // A path/explicit identifier is short in normal use. This also prevents a
      // malformed local value from creating an unexpectedly large UI payload.
      if (key.length > 500) continue;
      const entry = cleanEntry(value);
      if (entry) ledger[key] = entry;
    }
    return { ledger, available: true };
  } catch {
    return { ledger: {}, available: false };
  }
}

function saveProgress(ledger: ProgressLedger): boolean {
  try {
    localStorage.setItem(PROGRESS_KEY, JSON.stringify(ledger));
    return true;
  } catch {
    // Private browsing and restrictive privacy settings can reject writes.
    return false;
  }
}

function siteRelativeHref(value: string | undefined): string | null {
  // The parent computes this with the site's base-path helper. Keep this
  // component from becoming an unreviewed external-navigation surface.
  if (!value || !value.startsWith('/') || value.startsWith('//')) return null;
  return value;
}

function plural(n: number, word: string) {
  return `${n} ${word}${n === 1 ? '' : 's'}`;
}

function countSummary({ n_attempts: attempts, successful, mixed, failed }: FindingReveal['record']) {
  const parts: string[] = [];
  if (typeof attempts === 'number') parts.push(plural(attempts, 'linked attempt'));
  const outcomes = [
    typeof successful === 'number' && successful > 0 ? `${successful} replicated` : null,
    typeof mixed === 'number' && mixed > 0 ? `${mixed} mixed` : null,
    typeof failed === 'number' && failed > 0 ? `${failed} did not replicate` : null,
  ].filter((part): part is string => part !== null);
  if (outcomes.length) parts.push(outcomes.join(', '));
  else if (attempts && attempts > 0) parts.push('no coded success, mixed, or failure verdict');
  return parts.join(' · ');
}

/**
 * A small, record-level calibration interaction. It deliberately compares only
 * broad categories: the exact record label and outcome counts remain available
 * after reveal, rather than being flattened into a right/wrong binary score.
 */
export default function FindingGuess(props: FindingGuessProps) {
  const [guess, setGuess] = useState<BroadCategory | null>(null);
  const [reveal, setReveal] = useState<FindingReveal | null>(null);
  const [revealError, setRevealError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [ledger, setLedger] = useState<ProgressLedger>({});
  const [storageKey, setStorageKey] = useState<string | null>(null);
  const [storageAvailable, setStorageAvailable] = useState<boolean | null>(null);
  const resultRef = useRef<HTMLDivElement>(null);
  const groupId = `finding-guess-${(props.storageId || 'record').replace(/[^a-zA-Z0-9_-]/g, '-')}`;
  const prior = storageKey ? ledger[storageKey] : undefined;
  const nextFindingHref = siteRelativeHref(props.nextFindingHref);
  const fullRecordHref = siteRelativeHref(props.fullRecordHref);
  const revealUrl = siteRelativeHref(props.revealUrl);
  const explored = Object.values(ledger).filter((entry) => !!entry.revealedAt).length;
  const guessed = Object.values(ledger).filter((entry) => !!entry.guess).length;

  // Read after hydration so no visitor data participates in the static page.
  // `storageId` is available for future route migrations; today the pathname is
  // the reliable per-finding identity without a parent-page change.
  useEffect(() => {
    const key = props.storageId?.trim() || location.pathname;
    const loaded = loadProgress();
    setStorageKey(key);
    setLedger(loaded.ledger);
    setStorageAvailable(loaded.available);
    const saved = loaded.ledger[key];
    if (saved?.guess) setGuess(saved.guess);
  }, [props.storageId]);

  const updateProgress = (change: ProgressEntry) => {
    if (!storageKey) return;
    const next = { ...ledger, [storageKey]: { ...ledger[storageKey], ...change } };
    setLedger(next);
    if (storageAvailable !== false && !saveProgress(next)) setStorageAvailable(false);
  };

  const choose = (category: BroadCategory) => {
    setGuess(category);
    updateProgress({ guess: category, skipped: false });
  };

  const fetchReveal = async (skip: boolean) => {
    if (!revealUrl || loading || (!skip && !guess)) return;
    setLoading(true);
    setRevealError(null);
    try {
      const response = await fetch(revealUrl, { credentials: 'same-origin' });
      if (!response.ok) throw new Error(`request failed: ${response.status}`);
      const payload = await response.json() as FindingReveal;
      if (payload?.schema_version !== 1 || !payload.record || typeof payload.record.code !== 'string'
          || typeof payload.record.label !== 'string' || typeof payload.record.n_attempts !== 'number') {
        throw new Error('invalid result payload');
      }
      setReveal(payload);
      const revealedAt = new Date().toISOString();
      if (skip) {
        setGuess(null);
        // Replace a saved but unrevealed choice so skips remain distinguishable.
        if (storageKey) {
          const next = { ...ledger, [storageKey]: { skipped: true, revealedAt } };
          setLedger(next);
          if (storageAvailable !== false && !saveProgress(next)) setStorageAvailable(false);
        }
      } else if (guess) {
        updateProgress({ guess, skipped: false, revealedAt });
      }
    } catch {
      setRevealError('The result could not load. Your guess has not been marked as revealed; try again.');
    } finally {
      setLoading(false);
    }
  };

  // Put focus on the announced result rather than unexpectedly moving a
  // keyboard user down the page. The explicit control below moves to <summary>.
  useEffect(() => {
    if (reveal) resultRef.current?.focus();
  }, [reveal]);

  if (reveal) {
    const actual = CATEGORY_BY_CODE[reveal.record.code];
    const counts = countSummary(reveal.record);
    const selected = guess ? CHOICES.find((choice) => choice.category === guess) : null;
    const matches = !!selected && actual != null && selected.category === actual;
    const comparison = selected
      ? actual == null
        ? 'This record does not have a recognized broad-category mapping, so this is not scored.'
        : matches
          ? 'Your selection aligns with this record’s broad category.'
          : 'Your selection differs from this record’s broad category.'
      : 'You chose to reveal the record without making a selection.';

    return (
      <section class="finding-guess" aria-labelledby={`${groupId}-title`}>
        <div ref={resultRef} tabIndex={-1} role="status" aria-live="polite" aria-atomic="true">
          <h3 id={`${groupId}-title`}>Record revealed</h3>
          <p><b>{reveal.record.label}</b></p>
          <p>{comparison}</p>
          {counts && <p class="faint">Record summary: {counts}.</p>}
        </div>
        <div class="finding-guess-actions">
          {fullRecordHref && <a class="btn ghost" href={fullRecordHref}>Read the full source and attempt record</a>}
          {nextFindingHref && <a class="btn ghost" href={nextFindingHref}>{props.nextFindingLabel || 'Another finding'}</a>}
        </div>
        <ProgressNote prior={prior} explored={explored} guessed={guessed} storageAvailable={storageAvailable} />
      </section>
    );
  }

  return (
    <section class="finding-guess" aria-labelledby={`${groupId}-title`}>
      <h3 id={`${groupId}-title`}>What do you expect this record to show?</h3>
      <p class="faint">Choose a broad category, then reveal the record. This is a calibration prompt, not a binary score.</p>
      <ProgressNote prior={prior} explored={explored} guessed={guessed} storageAvailable={storageAvailable} />
      <div role="radiogroup" aria-labelledby={`${groupId}-title`}>
        {CHOICES.map((choice) => {
          const id = `${groupId}-${choice.category}`;
          return (
            <label key={choice.category} htmlFor={id} class="finding-guess-choice">
              <input
                id={id}
                type="radio"
                name={groupId}
                value={choice.category}
                checked={guess === choice.category}
                onChange={() => choose(choice.category)}
              />
              {choice.label}
            </label>
          );
        })}
      </div>
      <p class="finding-guess-actions">
        <button class="btn" type="button" onClick={() => { void fetchReveal(false); }} disabled={!guess || loading}>{loading ? 'Loading result…' : 'Reveal record'}</button>
        <button class="btn ghost" type="button" onClick={() => { void fetchReveal(true); }} disabled={loading}>{guess ? 'Discard guess and reveal' : 'Reveal without a guess'}</button>
      </p>
      {revealError && <p role="alert">{revealError}</p>}
    </section>
  );
}

function ProgressNote({ prior, explored, guessed, storageAvailable }: {
  prior?: ProgressEntry;
  explored: number;
  guessed: number;
  storageAvailable: boolean | null;
}) {
  if (storageAvailable === false) {
    return <p class="faint" role="status">Private progress cannot be saved in this browser. Nothing is sent anywhere.</p>;
  }
  if (storageAvailable === null) return null;
  const priorText = prior?.revealedAt
    ? prior.guess
      ? `Previously explored: you guessed ${CHOICES.find((choice) => choice.category === prior.guess)?.label.toLowerCase()}.`
      : 'Previously explored without a guess.'
    : prior?.guess
      ? `Saved selection: ${CHOICES.find((choice) => choice.category === prior.guess)?.label}. You have not revealed this record yet.`
      : null;
  return (
    <p class="faint finding-guess-progress">
      {priorText && <>{priorText} </>}
      On this device: {explored} explored · {guessed} guessed. Private to this browser; no tracking.
    </p>
  );
}
