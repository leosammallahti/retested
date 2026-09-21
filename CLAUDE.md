# Retested — instructions for Claude sessions

**Read `docs/HANDOFF.md` first.** It has the current state, the numbers, and the next steps.

## What this is
An effect-level wiki of psychology's replication record, built on FORRT's open data (FReD + FLoRA), plus a
"Did it replicate?" calibration game and a discovery pipeline that finds replications FORRT has not recorded.
Owner: Leo Sammallahti. Messages are often voice-dictated: "FORTT" means FORRT. He wants brilliant, not bare minimum,
and he wants API spending kept lean.

## Where things live (coop-vm is the primary machine)
- Checkout: `/root/retested` · bare repo: `/root/retested.git` · Python: `/root/retested/.venv/bin/python`
- A laptop copy exists at `C:\Users\OMISTAJA\PsychologyReplication` (git remote `vm`); the VM is the source of truth now.
- Keys (never print, commit or copy them): OpenAlex `OPENALEX_API_KEY` in `/root/retested/.env`;
  DeepSeek `DEEPSEEK_API_KEY` read from `/root/CoopContent/.env` (shared with the owner's other projects).
- Long jobs: run with `setsid nohup … > data/cache/logs/<name>.log 2>&1 < /dev/null &` so they survive disconnects.

## Commands
```bash
.venv/bin/python -m pipeline fetch [--refresh]        # raw FORRT files, sha256-checked against data/raw/forrt/MANIFEST.json
.venv/bin/python -m pipeline build [--accept-baseline] # sources -> data/build + site/public/generated (validates; fails loudly)
.venv/bin/python -m pipeline discover --mode keyword|cites|coverage   # OpenAlex searches, cached in data/cache/openalex
.venv/bin/python -m pipeline triage --tier high|medium [--pilot] [--max-usd N]   # DeepSeek check, cached per paper
.venv/bin/python -m pipeline link [--openalex] [--max-usd N] [--check]  # resolve the original each find names
.venv/bin/python -m pipeline outcomes --sample N | --score | --deck   # hand-read audit of the verdicts (free)
.venv/bin/python -m pipeline originals --sample N | --score  # hand-read audit of the link to the original
cd site && npm run build && npm run preview           # static site -> site/dist (preview on :4321)
```

## Rules
- Never hand-edit anything under `data/raw/` or generated files (`data/build/`, `site/public/generated/`).
- Discovery, triage and linking results go in `data/discovery/`, never `data/build/`: every build wipes `data/build/`
  first, which is how a day of discovery output was lost on 2026-09-19. They are all rebuildable from `data/cache/`.
- Human decisions go in `data/curated/` (merges.yaml, the append-only effect-ID ledger `registry/effect_ids.csv`, baseline).
- No one-off scripts in the repo root: the build fails on unexpected root entries. Experiments go in a scratch dir.
- Count drops > 1% fail the build; accept deliberate changes with `--accept-baseline` and say why in the commit.
- API spend: default to `deepseek-v4-flash` (served as `deepseek-flash`) with thinking disabled; pilot on a small
  labelled sample before any large run; always pass `--max-usd`. OpenAlex queries are cached; re-runs are free.
- Commit messages end with a `Co-Authored-By:` line for the model used.
