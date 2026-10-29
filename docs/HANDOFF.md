# Handover: what is in flight (updated 29 Oct 2026)

Read `START_HERE.md` first, then `SOURCES_AND_LEDGER.md` for what is counted, how papers are read and what is open.

## State

- The data build, the site build (with its sitemap and link checks) and the 137 tests pass.
- 5,371 attempts, 4,629 original papers, 2,235 effects with a replication. The ledger gives all 26,972 lines an
  outcome. No reading waits for a person.
- Branches: `wiki-pages` holds everything; `main` follows it; all are backed up to the local remote
  `/root/retested.git`. Not published: Leo must first create the empty public GitHub repository `retested`.

## Next

1. **Verify the review queue's 4,347 read pairs.** Two cheap models agreeing was measured wrong 6% of the time on the
   link (200 read blind on 29 Oct, `data/curated/review_evidence/2026-10-29/`), so each link needs checking before
   it is counted. Options: a stronger paid reader (ask Leo first: model, calls, cost) or reading helpers; measure on a
   fresh blind sample before trusting either.
2. **Results only the full text gives** (331 attempts).
3. **Publish** once Leo has created the repository and says go.

## Working rules

- Work in `/root/retested-wiki` (branch `wiki-pages`). Use `/root/retested/.venv/bin/python -X utf8`.
- Before any paid call, tell Leo the model, the number of calls and the cost, and wait for his yes.
- Measure before adding at scale: read a blind sample yourself first; a reading never overrules a result FORRT coded.
