import { useEffect, useRef, useState } from 'preact/hooks';

type BroadCategory = 'replicated' | 'mixed' | 'failed' | 'unclear';

export interface FindingGuessProps {
  /** The canonical record code, for example `largely_replicated`. */
  recordCode: string;
  /** The record's exact, human-readable label. Shown only after reveal. */
  recordLabel: string;
  /** The id of the related record element to expose and move focus to on reveal. */
  recordId: string;
  /** Optional helpful context, revealed with the record rather than before a guess. */
  attempts?: number;
  successful?: number;
  mixed?: number;
  failed?: number;
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

function plural(n: number, word: string) {
  return `${n} ${word}${n === 1 ? '' : 's'}`;
}

function countSummary({ attempts, successful, mixed, failed }: FindingGuessProps) {
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
  const [revealed, setRevealed] = useState(false);
  const resultRef = useRef<HTMLDivElement>(null);
  const groupId = `finding-guess-${props.recordId.replace(/[^a-zA-Z0-9_-]/g, '-')}`;
  const actual = CATEGORY_BY_CODE[props.recordCode];
  const counts = countSummary(props);

  // The sibling record is normally a native <details>. `open` gives no-JS
  // visitors a useful disclosure as well, without relying on locked CSS.
  const openRecord = (moveFocus = false) => {
    const record = document.getElementById(props.recordId);
    if (!record) return;
    if (record instanceof HTMLDetailsElement) record.open = true;
    else {
      record.hidden = false;
      record.removeAttribute('aria-hidden');
    }
    if (moveFocus) {
      const summary = record.querySelector('summary');
      if (summary instanceof HTMLElement) summary.focus();
      else {
        if (!record.hasAttribute('tabindex')) record.setAttribute('tabindex', '-1');
        record.focus();
      }
    }
  };

  const reveal = () => {
    setRevealed(true);
    openRecord();
  };
  const revealWithoutGuess = () => {
    setGuess(null);
    setRevealed(true);
    openRecord();
  };

  // Put focus on the announced result rather than unexpectedly moving a
  // keyboard user down the page. The explicit control below moves to <summary>.
  useEffect(() => {
    if (revealed) resultRef.current?.focus();
  }, [revealed, props.recordId]);

  // Attempt anchors remain usable when the record becomes a <details>: opening
  // its enclosing record on load/hash changes lets the browser expose the
  // target it has navigated to.
  useEffect(() => {
    const openForHash = () => {
      const hash = location.hash.slice(1);
      if (!hash) return;
      let target: HTMLElement | null = null;
      try { target = document.getElementById(decodeURIComponent(hash)); } catch { return; }
      const record = document.getElementById(props.recordId);
      if (target && record && (target === record || record.contains(target))) openRecord();
    };
    openForHash();
    addEventListener('hashchange', openForHash);
    return () => removeEventListener('hashchange', openForHash);
  }, [props.recordId]);

  if (revealed) {
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
          <p><b>{props.recordLabel}</b></p>
          <p>{comparison}</p>
          {counts && <p class="faint">Record summary: {counts}.</p>}
        </div>
        <button class="btn ghost" type="button" onClick={() => openRecord(true)}>Read the full record</button>
      </section>
    );
  }

  return (
    <section class="finding-guess" aria-labelledby={`${groupId}-title`}>
      <h3 id={`${groupId}-title`}>What do you expect this record to show?</h3>
      <p class="faint">Choose a broad category, then reveal the record. This is a calibration prompt, not a binary score.</p>
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
                onChange={() => setGuess(choice.category)}
              />
              {choice.label}
            </label>
          );
        })}
      </div>
      <p>
        <button class="btn" type="button" onClick={reveal} disabled={!guess} aria-controls={props.recordId}>Reveal record</button>
        <button class="btn ghost" type="button" onClick={revealWithoutGuess} aria-controls={props.recordId}>Reveal without a guess</button>
      </p>
    </section>
  );
}
