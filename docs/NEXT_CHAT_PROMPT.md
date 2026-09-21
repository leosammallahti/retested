Work on **Retested** at `/root/retested` (NOT `/root/CoopContent` — different project). Read `CLAUDE.md`, then `docs/HANDOFF.md`, then `docs/BACKLOG.md`. `docs/LINK_AUDIT_20260919.md` holds every accuracy measurement the pipeline's decisions rest on — read it before trusting or changing any confidence band.

State: 3,607 psychology replications FORRT doesn't record, 3,037 linked to the original they re-test, 1,854 with an outcome. Clean tree, nothing running.

**Two standing owner constraints:**
- **No DeepSeek.** A summarisation pass is costed and ready (~$3.50 for the whole site, ~$0.0004/paper from measured token usage) but is postponed until everything achievable without a model is done. OpenAlex is fine — cheap when batched 50 per call.
- **Don't publish.** Build and preview locally; the GitHub Pages workflow stays unused.

**Immediate goal:** make the ~1,323 game-card candidates good enough to ship as playable cards. Where the three blockers stand after 2026-09-21:

1. **Card claims are still 9-word labels** like "Physical warmth promotes interpersonal warmth" — the owner has said that isn't good enough. We hold the original's abstract for 984 of the 1,442 card rows, which is the raw material. Writing real claims from it is the postponed model pass, and it is now the only thing between these finds and a playable deck.
2. **Outcome accuracy: done, and it overturned the earlier reading.** 144 cases read one by one: successful 56/60, failed 55/60, mixed 18/22, and **zero read as the opposite of what the paper says**. The "~90%, one-directional towards success" from the n=20 sample was noise at that size. The error is a missing answer, not a wrong one. `python -m pipeline outcomes --sample 60` extends it for free; labels accumulate in `data/curated/outcome_audit.csv`.
3. **Card pool base rate 0.63 vs the existing deck's 0.53: real, not a measurement artefact.** Correcting every verdict by the audit moves it to 0.633. Keep them a separate deck because the pool genuinely differs. A gate at `outcome_confidence` >= 0.8 drops 16% of the pool and takes the rest from 93% to 96% sound (Fisher p = .001) — free, and worth applying when the deck is built.

**How this project works, and it matters:** every accuracy number here was produced by reading cases one by one, not asserted. Several times a figure computed over the wrong population said "stop" and was wrong — reference containment measured 23% (really 84%) because it ran over bad links; a fallback's ceiling measured 0 (really 478) because it read a stale temp file; and the n=20 outcome read above pointed a direction it could not establish. Check which rows an intermediate was built from before believing what it says about a different set. When a measurement says a route is dead, verify the measurement before closing the route. And write the cases down: the 20 rows behind the superseded figure were never recorded, so the larger sample had to start over instead of extending it.

Also: don't use `pkill -f` with a pattern matching `pipeline` — it kills the shell running it.
