Work on **Retested** at `/root/retested` (NOT `/root/CoopContent` — different project). Read `CLAUDE.md`, then `docs/HANDOFF.md`, then `docs/BACKLOG.md`. `docs/LINK_AUDIT_20260919.md` holds every accuracy measurement the pipeline's decisions rest on — read it before trusting or changing any confidence band.

State: 3,607 psychology replications FORRT doesn't record, 3,037 linked to the original they re-test, 1,854 with an outcome. Clean tree, nothing running.

**Two standing owner constraints:**
- **No DeepSeek.** A summarisation pass is costed and ready but postponed until everything achievable without a model is done. OpenAlex is fine — cheap when batched 50 per call, and the linking is now fully cached, so re-runs cost $0.
- **Don't publish.** Build and preview locally; the GitHub Pages workflow stays unused.

**Immediate goal:** make the game-card candidates good enough to ship. `python -m pipeline outcomes --deck` is the live answer:

| gate | finds | cards | successful |
|---|---|---|---|
| a binary verdict and a linked original | 1,442 | 1,322 | 63% |
| link in a band read at 90% or better | 113 | 110 | 62% |
| + outcome confidence 0.8 or higher | 110 | **107** | **62%** |
| + the original's abstract held | 85 | 83 | 64% |

1. **The claim text is the last blocker.** 9-word labels like "Physical warmth promotes interpersonal warmth" are not a card, and the owner has said so. The original's abstract is the raw material. Over the 83 audited cards that hold one, a DeepSeek pass costs about **$0.03** — the ~$3.50 figure was for the whole site. That is a decision to put to the owner, not to take.
2. **The link gate is what costs, not the verdict gate** — 1,442 finds down to 113. The two bands nearest the line are `cited by this paper` (72/84 = 86%, 307 rows) and `reference_scan` high (32/40 = 80%, 299 rows). More reading on either could bring hundreds of cards back: `python -m pipeline originals --sample 40 --band 'cited by this paper/unscored'`.
3. **Both audits accumulate and cost nothing but reading.** `outcomes --score` (224 labels) and `originals --score` (384) recompute from `data/curated/*_audit.csv`. The page gate is computed from that file on every build — 20+ links read, 90%+ right — so a band moves in or out as the reading grows. That is the mechanism, not churn.

**How this project works, and it matters:** every accuracy number here was produced by reading cases one by one, not asserted. Several times a figure computed over the wrong population said "stop" and was wrong — reference containment measured 23% (really 84%); a fallback's ceiling measured 0 (really 478). And several times a figure computed over too *few* rows said "go": on 2026-09-21 `cited by this paper` was promoted to a page band on 34 of 36 and reverted the same day at 72 of 84, and `reference_scan` high had sat on pages since September on a quoted 32/36 that turned out to be 80% over 40 fresh reads. Check which rows an intermediate was built from, and how many. When a measurement says a route is dead, verify the measurement before closing the route — and when it says a route is open, read more before acting on it.

Also: don't use `pkill -f` with a pattern matching `pipeline` — it kills the shell running it.
