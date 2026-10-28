# Retested: start here

Retested is a public wiki of psychology's replication record. For each effect and each original paper, it shows
what later teams found when they tried again. It is built on FORRT's open data and adds replications Retested's own
readers checked. Owner: Leo Sammallahti.

## Where things live

| What | Where |
|---|---|
| The code that builds everything | `pipeline/` (`python -m pipeline build`) |
| FORRT's files, as downloaded (never edited) | `data/raw/forrt/`, listed with hashes in `MANIFEST.json` |
| Every decision a reader (Leo, Claude, or two agreeing models with checked quotes) made | `data/curated/` (each file says what it decides; see `SOURCES_AND_LEDGER.md`) |
| Evidence behind the 28 Oct 2026 decisions | `data/curated/review_evidence/2026-10-28/` |
| The scripts that produced those decisions | `pipeline/repair/` (README inside) |
| What the build produces (wiped on every build) | `data/build/` |
| The website | `site/` (Astro; reads `data/build/`) |
| Tests | `tests/` (`python -m unittest discover -s tests`) |
| Old notes and the full work diary | `docs/history/` |

## The four commands

```bash
python -m pipeline build                 # sources + reviewed decisions -> data/build; stops on any unaccounted FORRT row
python -m pipeline quality-audit         # every item in the build that still needs a decision -> data/build/quality_audit.json
cd site && npm run build && npm run verify   # the static site and its link and sitemap checks
python -m unittest discover -s tests
```

Use `/root/retested/.venv/bin/python -X utf8`. Work in the worktree `/root/retested-wiki` (branch `wiki-pages`),
never in the main checkout `/root/retested`, which holds another session's uncommitted edits.

## How to read the data

- **The FORRT ledger** (`data/build/forrt_ledger.json`, and the page `sources/` on the site) gives every row of every
  FORRT file one outcome: on the site, waiting to be read, not yet read, names an effect, or left out with a reason.
  A build with an unaccounted row stops.
- **An effect counts only once a replication of its own is linked.** The rest are listed on `not-linked/`.
- **Results come from four sources:** FORRT's coding (FLoRA, FReD, the old FReD file), Retested's reviewed pairs, and
  later papers read for Retested from their abstracts. A reading never overrules a result FORRT coded; the cases where
  they differ are in `data/build/read_notes.json`, for a person to read.

## Documents

- `SOURCES_AND_LEDGER.md` covers what each source is, what counts, the reviewed files, the 28 Oct repair in numbers,
  and what is open.
- `HANDOFF.md` covers what is in flight now, and the next steps.
- `REPLICATION_REGISTRY.md`, `FORRT_OVERLAP_AUDIT.md`, `LINK_AUDIT_20260919.md` and `READING_RUBRIC.md` are the
  earlier designs and audits that the code still refers to.
- `BACKLOG.md` lists ideas not yet scheduled.

## Rules that matter most

- Never edit `data/raw/` or `data/build/` by hand. Change a reviewed input in `data/curated/` or the code, then rebuild.
- Every reviewed row carries its reason and evidence. One that stops matching the data stops the build; it is never
  skipped.
- Before any paid model call, tell Leo the model, the number of calls and the cost, and wait for his yes.
- Commit only when Leo asks.
