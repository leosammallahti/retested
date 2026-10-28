# Handover: what is in flight (updated 28 Oct 2026, 11:35 Finnish time)

Read `START_HERE.md` first. The full work diary up to 28 Oct is in `history/HANDOFF_diary_2026-09-26_to_2026-10-28.md`.

## State

- The data build, the site build (11,796 pages, sitemap and link checks) and the 135 tests pass.
- The FORRT ledger accounts for all 26,916 source rows; `python -m pipeline quality-audit` lists what is still open.
- 5,353 attempts, 4,641 original papers, 2,225 effects with a replication (273 more named without one).
- The 28 Oct repair and the paper reading are described in `SOURCES_AND_LEDGER.md`, with their numbers. The scripts are
  in `pipeline/repair/` and the evidence is in `data/curated/review_evidence/2026-10-28/`.
- Not published: the site is planned for GitHub Pages at leosammallahti.github.io/retested. Leo must first create
  the empty public repository `retested`.

## Next, in order

1. **Read the 144 readings listed for a person** (`data/build/read_notes.json`). Nine differ from a result FORRT coded;
   135 are unclear whether the paper tests this exact finding.
2. **The queue** (about 7,000 machine-found pairs) is a paid reading of about $3.30. Ask Leo first. The same scripts
   apply: `pipeline/repair/reading/`.
3. **Papers without an abstract** (530) need their full text to be read.
4. **Publish** once Leo has created the repository and says go.

## Working rules

- Work in `/root/retested-wiki` (branch `wiki-pages`). The main checkout `/root/retested` holds another session's old
  uncommitted edits (`pipeline/export.py`, `load.py`, `validate.py`, `site/src/components/Feed.tsx`, `posts.json`),
  and this branch also changes `export.py` and `validate.py`, so expect to merge those by hand.
- Before any paid call, tell Leo the model, the number of calls and the cost, and wait for his yes.
