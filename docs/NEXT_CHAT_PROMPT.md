Work on **Retested** at `/root/retested` (NOT `/root/CoopContent` — different project). Read `CLAUDE.md`, then `docs/HANDOFF.md`, then `docs/BACKLOG.md`. `docs/LINK_AUDIT_20260919.md` holds every accuracy measurement the pipeline's decisions rest on — read it before trusting or changing any confidence band.

State: 3,607 psychology replications FORRT doesn't record, 3,037 linked to the original they re-test, 1,854 with an outcome. Clean tree, nothing running.

**Two standing owner constraints:**
- **No DeepSeek.** A summarisation pass is costed and ready (~$3.50 for the whole site, ~$0.0004/paper from measured token usage) but is postponed until everything achievable without a model is done. OpenAlex is fine — cheap when batched 50 per call.
- **Don't publish.** Build and preview locally; the GitHub Pages workflow stays unused.

**Immediate goal:** make the ~1,316 game-card candidates good enough to ship as playable cards. Blockers in order:
1. Card claims are still 9-word labels like "Physical warmth promotes interpersonal warmth" — the owner has said that isn't good enough. We now hold the original's abstract for 65% of linked finds, which is the raw material. Writing real claims from it is the postponed model pass.
2. Outcome accuracy is ~90% and biased *towards success*; n=20. More reading tightens it and costs nothing.
3. Card pool base rate is 0.63 vs the existing deck's 0.53 — partly that measurement bias. Keep them a separate deck rather than mixing.

**How this project works, and it matters:** every accuracy number here was produced by reading cases one by one, not asserted. Several times a figure computed over the wrong population said "stop" and was wrong — reference containment measured 23% (really 84%) because it ran over bad links; a fallback's ceiling measured 0 (really 478) because it read a stale temp file. Check which rows an intermediate was built from before believing what it says about a different set. When a measurement says a route is dead, verify the measurement before closing the route.

Also: don't use `pkill -f` with a pattern matching `pipeline` — it kills the shell running it.
