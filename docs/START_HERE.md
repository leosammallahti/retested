# Retested: start here

Retested is a public wiki of psychology's replication record, published at https://leosammallahti.github.io/retested/.
For each effect and each original paper, it shows what later teams found when they tried again. It is built on FORRT's
open data and adds replications Retested's own readers checked. Owner: Leo Sammallahti.

## Finished state (31 Oct 2026)

- **8,840 replication and reproduction attempts** across **6,829 original papers** and **2,125 named effects** with a
  replication (**177** more named effects without a linked replication are listed on `not-linked/`).
- **27,119 FORRT and Retested ledger rows**, every one with a recorded outcome (`0` unaccounted rows).
- **0 open quality-audit items** (`python -m pipeline quality-audit` writes `{"counts": {}, "items": {}}`): every
  open full text has been read (`data/curated/review_evidence/2026-10-30/`), every effect has a plain sentence and
  study typology, and every attempt whose result is not stated in any freely available text is recorded plainly with its
  reason.
- **15,976 static HTML pages** built and verified (`0` broken links or fragments), and **137 unit tests** passing.

## Where things live

| What | Where |
|---|---|
| The code that builds everything | `pipeline/` (`python -m pipeline build`); every module and command in `pipeline/README.md` |
| FORRT's files, as downloaded (never edited) | `data/raw/forrt/`, listed with hashes in `MANIFEST.json` |
| Every decision a reader (Leo, Claude, or calibrated reading helpers with checked quotes) made | `data/curated/`, each file listed with what it decides in `data/curated/README.md` |
| Evidence behind the 28–30 Oct 2026 decisions | `data/curated/review_evidence/2026-10-28/`, `2026-10-29/`, and `2026-10-30/` |
| The scripts that produced the 28 Oct repair | `pipeline/repair/` (README inside) |
| What the build produces (wiped on every build) | `data/build/` |
| The website | `site/` (Astro; reads `data/build/`) |
| Tests | `tests/` (`python -m unittest discover -s tests`) |
| Historical notes, work diary, and earlier plans | `docs/history/` |

## The four checks

```bash
python -m pipeline build
python -m pipeline quality-audit
cd site && SITE_URL=https://leosammallahti.github.io BASE_PATH=/retested/ npm run build && npm run verify
python -m unittest discover -s tests
```

Use `/root/retested/.venv/bin/python -X utf8`. Work in `/root/retested-wiki` (branch `wiki-pages`, mirrored to `main`,
backed up to `/root/retested.git` and published to `leosammallahti/retested`), never in `/root/retested`.

## How to read the data

- **The FORRT ledger** (`data/build/forrt_ledger.json`, and the page `sources/` on the site) gives every row of every
  FORRT file one outcome: on the site, in the queue, names an effect, or left out with a reason. A build with an
  unaccounted row stops.
- **An effect counts only once a replication of its own is linked.** The rest are listed on `not-linked/`.
- **Results come from FORRT's coding** (FLoRA, FReD, the old FReD file), **Retested's reviewed pairs, papers read for
  Retested** (from their abstracts or open full text), and **results a reader corrected** against the paper's own
  text (`data/curated/attempt_results.csv`, shown with the earlier coding beside them). A reading never overrules a
  result FORRT coded.
- **An attempt is counted only when its link was made or checked by FORRT's editors or a reader.** Machine-found pairs
  count only once a reader has confirmed the link against the text (`SOURCES_AND_LEDGER.md`).

## Rules that matter most

- Never edit `data/raw/` or `data/build/` by hand. Change a reviewed input in `data/curated/` or the code, then rebuild.
- Every reviewed row carries its reason and evidence. One that stops matching the data stops the build; it is never
  skipped.
- Before any paid model call, tell Leo the model, the number of calls and the cost, and wait for his yes.
