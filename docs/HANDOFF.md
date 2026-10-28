# Handover: what is in flight (updated 29 Oct 2026, Finnish time)

Read `START_HERE.md` first. What each source is, what is counted, every reviewed file, the 28 Oct work in numbers
and what is open: `SOURCES_AND_LEDGER.md`. The full work diary up to 28 Oct is in `history/`.

## State

- The data build, the site build (with its sitemap and link checks) and the 137 tests pass.
- The FORRT ledger gives all 27,227 source rows an outcome; `python -m pipeline quality-audit` lists what is open.
- 9,720 attempts (6,486 from FORRT, 3,234 added by Retested), 7,494 original papers, 2,252 effects with a
  replication (245 named without one). 47.2% of the 7,689 attempts with a result found the effect.
- No reading waits for a person (`data/build/read_notes.json` is empty).
- Branches: `wiki-pages` holds everything; `main` has been brought up to it, and the feed work that sat uncommitted
  in the main checkout is kept as branch `feed-posts-2026-10-22` (merged). All three are backed up to the local
  remote `/root/retested.git`.
- Not published: the site is planned for GitHub Pages at leosammallahti.github.io/retested. Leo must first create
  the empty public repository `retested`.

## Next, in order

1. **Replications of another paper** (447 queue pairs): link each to the study it really replicates.
2. **Results only the full text can give** (2,018 attempts): most open copies refuse automated download; an OSF
   project's result often sits in an attached document (`pipeline fulltext` collects OSF wikis and Europe PMC text).
3. **The rest of the queue** (2,055 pairs), mostly finds that name no identifiable original.
4. **Publish** once Leo has created the repository and says go.

## Working rules

- Work in `/root/retested-wiki` (branch `wiki-pages`). Use `/root/retested/.venv/bin/python -X utf8`.
- Before any paid call, tell Leo the model, the number of calls and the cost, and wait for his yes.
- A reading never overrules a result FORRT coded; a correction is a reviewed row with its reason and evidence.
