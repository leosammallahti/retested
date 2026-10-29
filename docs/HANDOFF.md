# Handover: what is in flight (updated 29 Oct 2026, afternoon)

Read `START_HERE.md` first, then `SOURCES_AND_LEDGER.md` for what is counted, how papers are read and what is open.

## State

- The data build, the site build (15,837 pages, sitemap and link checks) and the 137 tests pass.
- 8,624 attempts, 6,662 original papers, 2,247 effects with a replication. The ledger gives all 27,113 lines an
  outcome. No reading waits for a person.
- Machine-found pairs count only with a checked link (`data/curated/link_checks.csv`); the check was measured on a
  blind sample before and after (`data/curated/review_evidence/2026-10-29/`).
- 11 'replicated' game cards are held for the deck's balance (`data/curated/card_holds.json`, reason given).
- Branches: `wiki-pages` holds everything; `main` follows it; all are backed up to `/root/retested.git`.
  Not published: Leo must first create the empty public GitHub repository `retested`.

## Next

1. **837 queue pairs** a reader could not confirm, and **1,701 replications without a result**: both need the full
   papers.
2. **6 replications dated before their original** and **538 later papers without authors** (`quality-audit`).
3. **Publish** once Leo has created the repository and says go.

## Working rules

- Work in `/root/retested-wiki` (branch `wiki-pages`). Use `/root/retested/.venv/bin/python -X utf8`.
- Before any paid call, tell Leo the model, the number of calls and the cost, and wait for his yes.
- Measure before adding at scale: read a blind sample yourself first; a reading never overrules a result FORRT coded.
