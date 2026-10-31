# Handover: finished and published state (31 Oct 2026)

Read `START_HERE.md` first, then `SOURCES_AND_LEDGER.md` for what is counted and how papers were read.

## Finished state

- All four checks pass on the final commit:
  - `python -m pipeline build`: **8,840** attempts (**8,560** replications, **280** reproductions; **7,399** replications
    with a verdict) across **6,829** original papers and **2,125** effects with a replication (**177** named without
    one, listed on `not-linked/`). All **27,119** ledger rows have a recorded outcome (`0` missing).
  - `python -m pipeline quality-audit`: **0** open items across all categories (`data/build/quality_audit.json` is
    `{"counts": {}, "items": {}}`).
  - `cd site && SITE_URL=https://leosammallahti.github.io BASE_PATH=/retested/ npm run build && npm run verify`:
    **15,976** static HTML pages (**8,968** indexable pages, **274,307** local references, **0** missing targets,
    **0** missing fragments).
  - `python -m unittest discover -s tests`: **137** tests passing.
- All fetched open full texts (1,256 papers and 56 abstracts) have been read by calibrated Sonnet 5.5 helpers following
  `docs/READING_RUBRIC.md`, with quotes and provenance recorded in `data/curated/review_evidence/2026-10-30/`.
- Every attempt whose result is not stated in any freely available text is recorded in `data/curated/attempts_checked.csv`
  and states plainly on the site that its result is not stated in any freely available text.
- Every effect has a plain sentence in `data/curated/effect_lines.json` and a study typology in
  `data/curated/effect_typology.json`; near-duplicate effects are merged in `data/curated/merges.yaml` with every
  attempt preserved.
- Branches `wiki-pages` and `main` are identical, backed up to `/root/retested.git`, pushed to
  `https://github.com/leosammallahti/retested`, and live at `https://leosammallahti.github.io/retested/`.
