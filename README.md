# Retested

**Every psychology finding, tested again.** An effect-by-effect guide to psychology's replication record, built on the open data of the [FORRT Replication Hub](https://forrt.org/replication-hub/) (FReD and FLoRA).

For each named effect (ego depletion, power posing, the Macbeth effect…) the site shows the original claim and every attempt to repeat it, through three lenses that are never merged into one score:

1. **What the replicators said.** Their own verdicts and quotes, rolled up with explicit count rules.
2. **What the numbers say.** Replication effect sizes pooled against the original, plus FORRT's seven success criteria side by side.
3. **How the attempts were done.** Preregistration, team independence, closeness to the original.

It also includes:
- **Did it replicate?** A calibration game. You read a real finding, give a probability, and are scored with the Brier score.
- **A review queue** of machine-found replication candidates that no human has checked yet, from two labelled sources: FORRT's own extractor, and our search of OpenAlex screened by DeepSeek. Accepted ones export as CSV for submission back to FORRT. Where one of our finds points at an original that already has a page, that page shows it as *unverified, pending review* — beside the record, never counted in it.
- **The record:** base rates with denominators and intervals, and the Graveyard, Survivors and Contested lists.

Retested is independent and not an official FORRT product. It links every paper to FORRT's [Replication Atlas](https://forrt.org/flora-replication-atlas/) rather than duplicating it.

## Build it

Requirements: Python ≥ 3.12 and Node ≥ 22.

```bash
pip install -e .
python -m pipeline fetch          # download FORRT sources listed in data/raw/forrt/MANIFEST.json (sha256-checked)
python -m pipeline build          # sources -> data/build/*.json + site/public/generated/
cd site && npm ci && npm run build   # -> site/dist (static, ~1,800 pages)
npm run preview                   # http://localhost:4321
```

Finding replications FORRT has not recorded is a separate, optional chain whose results live in `data/discovery/`
(outside `data/build/`, which every build wipes). Each step is cached, so re-runs are free:

```bash
python -m pipeline discover --mode keyword    # psychology papers with "replication" in the title
python -m pipeline discover --mode cites      # papers citing an original already here
python -m pipeline triage --tier high --max-usd 1.5   # DeepSeek reads each abstract
python -m pipeline link --openalex --max-usd 1.0      # resolve the original each one names
python -m pipeline link --check               # how often that resolution is right (free)
python -m pipeline outcomes --sample 40       # print verdicts to read one by one (free)
python -m pipeline outcomes --score           # how often the verdict was read right, from the labels
```

`outcomes` is the audit of the verdicts themselves. It draws a stratified sample, a person or a session reads
each case against the paper's own abstract, and the labels go in `data/curated/outcome_audit.csv` keyed by
candidate id, so they survive rebuilds and accumulate. `--score` turns them into per-verdict precision with
intervals, and names the rows in a pool that no draw has reached rather than quoting a figure over them.

`python -m pipeline fetch --refresh` pulls FORRT's newest release (FLoRA updates several times a week) and records the new hashes. CI does this weekly and deploys to GitHub Pages (`.github/workflows/site.yml`).

## Layout

| Path | What lives there | Edited by hand? |
|---|---|---|
| `pipeline/` | Python build: `load` → `registry` → `score` → `game` / `queue` / `stats` → `validate` → `export` | yes |
| `site/` | Astro 7 static site; Preact islands for search, the game and the review queue | yes |
| `data/raw/forrt/` | Upstream FORRT files. Only `MANIFEST.json` is committed; everything else is fetched | **never** |
| `data/raw/local/` | Two inputs salvaged from earlier work: the parsed famous-effects list and an OpenAlex citation snapshot | never |
| `data/curated/` | Human decisions: `merges.yaml`, the append-only effect-ID ledger, the count baseline | yes, via PR |
| `data/build/`, `site/public/generated/` | Generated bundle | never (gitignored) |
| `data/discovery/` | Discovery, triage and linking results; survives a build, rebuildable from cache | never (gitignored) |
| `docs/planning/` | The research and design reports behind this build | reference |
| `archive/` | Earlier attempts (harvester, taxonomy experiments, old wiki). Local only, gitignored | no |

## Rules that keep it from rotting

The build (`python -m pipeline build`) fails instead of shipping when:
- any FLoRA replication pair is unreachable from a page;
- an effect ID or slug collides, or a reference points at nothing;
- a game card contains an answer-revealing word, ships its answer, or the deck's base rate leaves 35–65%;
- any headline count drops by more than 1% against `data/curated/baseline/SUMMARY.json` (accept on purpose with `--accept-baseline`);
- a string that looks like an API key appears in code, curated data or docs;
- an unexpected file or folder appears in the repository root;
- a review-queue row loses its `machine` state, repeats a pair FORRT already records, or is shown on a page without being one of our linked replications.

Effect IDs (`fx_…`) are issued once by `data/curated/registry/effect_ids.csv` and never reused, so renaming or merging an effect never breaks a link.

## Data and credit

All replication data: FORRT, CC BY 4.0. Cite as *Wallrich, Röseler, Hartmann et al. (2026). FORRT Library of Replication Attempts (FLoRA) [Data set]. OSF. https://doi.org/10.17605/OSF.IO/9R62X* (full author list in `site` → Methods). Corrections to the underlying data belong with FORRT: <https://forrt.org/replication-hub/submit/>.
