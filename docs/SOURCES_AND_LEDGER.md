# What FORRT has, what Retested has, and what Retested added

Where the site's data comes from, what is counted, how a later paper is read, and how the build proves that nothing
FORRT publishes has gone missing. Current as of 29 Oct 2026; how it got here is in
`history/2026-10-28_repair.md`. The site page `sources/` shows the same numbers for readers.

## The sources

Retested is built from FORRT's open replication data, with Retested's own reviewed additions on top. Every FORRT file
is downloaded under `data/raw/forrt/` and listed with its hash in `data/raw/forrt/MANIFEST.json`.

| Source | What it holds | How the site uses it |
|---|---|---|
| FLoRA (`fred-data/output_flora.csv`) | FORRT's current coded replication pairs (original paper, later paper), each with a result and the authors' words | Every pair is an attempt |
| FReD (`feeds/fred-apps_explorer-data.json`, `fred-data/output_FReD.xlsx`) | Effect-size rows for about 850 pairs | Numbers and the seven success criteria on each attempt |
| FReD 2.4.1 "Data" sheet (`osf/version-history/FReD_2.4.1_2025-06-25.xlsx`) | The old database: effect names, closeness coding, project labels, 1,094 pairs no newer file has | Effect names; pairs not elsewhere become attempts marked "legacy" |
| Replications & Reversals sheet ("FORRT R&R (editable)" in the same workbook) | FORRT's famous-effects list coded into (original, later paper) pairs, almost without results | Effect names; pairs already coded elsewhere count; the rest wait to be read (see below) |
| Replications & Reversals list file (`osf/sub-datasets/231026_forrt_with_journals.xlsx`) | The same list, one row per effect and cited later paper, with DOIs and the later paper's abstract | As above |
| Replications & Reversals text (`data/raw/local/docx_parsed_entries.json`) | The list as FORRT publishes it: name, a verdict, a description and citations without DOIs | The famous-list verdict and description on effect pages |
| FLoRA validation files (`feeds/flora-validation_*.csv`) | Pairs FORRT has validated, some not yet in FLoRA's export | A validated pair no other file carries enters as FLoRA data (38 on 28 Oct) |
| FLoRA extractor (`feeds/flora-extractor_*.csv`) | Pairs FORRT's machine search found, and ones it has not confirmed | The review queue: each pair is read for Retested (below) and counted once a reader has confirmed its link; unconfirmed links are recorded as such |
| Retested reviewed pairs (`data/curated/promoted_pairs.json`) | 1,941 pairs Retested's readers checked against the papers | Attempts marked "Retested reviewed" (1,467 are new to FORRT) |
| OpenAlex (`data/raw/local/openalex_paper_metadata.json`, fetched 28 Oct) | Title, year and authors for each DOI | Replaces a title the site could only parse out of a reference string, and fills a missing year or author list |
| OSF and the DOI registry (`data/raw/local/later_paper_records.json`, fetched 28 Oct) | Title, year and authors of later papers OpenAlex does not hold (OSF projects, preprints) | Fills a missing title, year or author list |

## What is counted

- **An attempt** is one pair of an original paper and a later paper that tested it again.
- **A finding** is one original paper with all its attempts.
- **An effect** is a named phenomenon, such as "Dunning-Kruger effect". It may span several original papers.
- **An attempt is counted only when its link was made or checked by FORRT's editors or a reader:** FORRT's coded
  files, a later paper FORRT's famous-effects list cites, a pair Retested's readers checked, or a machine-found pair
  whose link a reading helper confirmed against both abstracts. The others wait in the review queue.
- **An effect enters the database only when a replication of its own is linked.** The others are named in FORRT's
  records but have no replication here yet. They keep a page, marked as such and left out of search engines. They are
  listed with the reason on the page `not-linked/`, and no list, count, map or search includes them.

## The FORRT ledger: every row has an outcome

`pipeline/forrt_ledger.py` writes `data/build/forrt_ledger.json`, one line for each row of each FORRT file and each of
Retested's own finds (26,972 lines). Each line has exactly one outcome:

- **on the site:** its pair is an attempt (the line names the attempt and its effects);
- **on the site under another original:** the later paper is on the site, linked to a different original;
- **waiting to be read:** its pair is in the review queue (found by a machine, not yet read);
- **read, waiting to be verified:** in the queue; two models read it as a replication of its original, and it is
  counted once its link is verified;
- **not yet read:** FORRT's Replications & Reversals list cites the later paper, but nobody has yet read it to
  establish whether it is a replication and what it found;
- **names an effect:** the row carries no pair but names an effect, and the line says whether that effect has a
  replication;
- **left out:** with the reason. The reason is FORRT's own (its filter logs, its "not a replication" marks, its
  unconfirmed links), a missing identifier, a reading that found it is not a replication of its original, or a
  reviewed decision recorded in `data/curated/` (below).

**The build stops if any row has no outcome.** The summary is in `stats.json` (`forrt_ledger`) and on the page
`sources/`.

## How a later paper is read, and what a reading may change

Later papers are read from their title and abstract (or open full text, where it could be downloaded) by two models,
DeepSeek v4.1 flash and GLM 5.3 flash, with the same questions (`pipeline/repair/reading/questions.py`): what the
paper is, whether it tests this original's finding, what it found. An answer stands when both models agree and each
quote is found word for word in the text; where they disagree, a Sonnet 5.5 reading helper decides from the same text.
The readings are in `data/curated/read_pairs.json` (`pipeline/read_pairs.py`).

What a reading may do:

- **Fill a missing result** on an attempt FORRT or a person linked. It never overrules a result FORRT coded; where they
  differ, `data/build/read_notes.json` lists it for a person (empty at present).
- **Add a pair FORRT's famous-effects list cites,** when the reading says it is a replication of that finding: FORRT's
  editors linked the pair.
- **Set aside an attempt FORRT never coded,** when the reading says it is a meta-analysis, review or other study. An
  effect page lists the meta-analyses and reviews of its own finding apart from its replications.
- **Not, on its own, add a machine-found pair.** A blind reading of 200 machine-found pairs that both models accepted
  found about 6% that replicate a different study than the one linked. So a machine-found pair counts only once a
  Sonnet 5.5 reading helper has checked its link against both full abstracts (`data/curated/link_checks.csv`): yes
  (it joins the record, labelled "its link to this original checked by a reader"), no (it leaves the queue, the
  ledger saying what it replicates instead) or can't tell (it stays in the queue). The helpers were tested first on
  the 200 pairs read blind, and 60 links they accepted were then read by Claude: all 60 were right.

The link checks of 29 Oct 2026: 4,349 pairs, 3,253 yes, 259 no, 837 can't tell (22 helpers, about 4.2 million
tokens). Their briefs and answers are in `data/curated/review_evidence/2026-10-29/link_checks/`.

Measured limits of the reading: the question counts "no reliable effect" as not found, which is backwards where the
original finding is itself a null; such readings are searched for and corrected (`attempt_results.csv`).

## Reviewed inputs: judgements people made, and where they live

Every file in `data/curated/`, including older ones, is listed in `data/curated/README.md`.

Each file records the decision, the reason and the evidence. If a row ever stops matching the data, the build stops
rather than skipping it.

| File | Decides | Read by |
|---|---|---|
| `data/curated/merges.yaml` | Names that are one effect: the same claim on the same original paper | `pipeline/registry.py` |
| `data/curated/effect_originals.csv` | An effect's original paper when FORRT names it only in prose | `pipeline/curated_links.py` |
| `data/curated/attempt_effects.csv` | Which named effect a replication tested, when its original carries several | same |
| `data/curated/attempt_duplicates.csv` | One study listed twice under one original: the copy is merged into its record and counted once | same |
| `data/curated/attempt_exclusions.csv` | An "attempt" that is not a replication (the original listed as its own replication, a preprint of the same study, a wrong DOI). It is set aside with the reason, and the ledger shows it | same |
| `data/curated/attempt_relinks.csv` | A replication FORRT filed under the wrong original, moved to the original reading showed it replicates. It never overrides coding the right pair already has | same |
| `data/curated/effect_original_exclusions.csv` | A source row that names an effect with another paper's DOI, or an effect name attached to a paper about something else | same |
| `data/curated/effects_kept_apart.csv` | Effects that share the same replications but are different claims (read and kept apart) | `pipeline/quality_audit.py` |
| `data/curated/attempts_checked.csv` | An attempt that looked wrong (dated before its original, titled like a review or like its original, a reading that differs) checked and kept, or found to need the full text | `pipeline/curated_links.py`, `pipeline/quality_audit.py` |
| `data/curated/attempt_results.csv` | A result corrected against the paper's own text; the earlier coding is shown beside it | `pipeline/curated_links.py` |
| `data/curated/paper_details.csv` | Title, authors and year of a later paper no catalogue supplies, looked up by hand | `pipeline/curated_links.py` |
| `data/curated/read_pairs.json` | Later papers read from their abstracts or open full text (two models that agree, with checked quotes, or Claude where they split): what the paper is, whether it tests the finding, what it found | `pipeline/read_pairs.py` |
| `data/curated/effect_description_exclusions.csv` | A source description that belongs to another claim, or is not a claim | same |
| `data/curated/effect_lines.json`, `effect_typology.json` | One plain line per effect; the study typology. **Keyed by the stable effect id**, so a merge or rename cannot detach them; entries of folded effects are kept under `set_aside` | `pipeline/wiki.py` |

## The record now (29 Oct 2026, afternoon)

- 8,624 attempts under 6,662 original papers: 6,027 from FORRT (its files; 294 later papers its list cites; 2,123
  pairs its machine search found, link checked) and 2,597 added by Retested (1,467 checked by its readers, 1,130
  found by its machine search, link checked).
- 2,247 effects with a replication; 250 named without one (listed on `not-linked/`).
- 27,113 ledger lines (every FORRT file and Retested's own finds), none without an outcome.
- 6,910 attempts have a result; 47.6% found the effect. 1,701 replications state no result where they could be read.
- The review queue: 2,860 machine-found pairs, of which 837 were read but could not be confirmed, and most of the rest
  name no identifiable original.

## Still open (each counted by `python -m pipeline quality-audit` or on `sources/`)

1. **837 queue pairs whose link could not be confirmed** from the text; the full papers would settle most.
2. **1,701 attempts without a result,** mostly papers whose abstract or title does not state one (student replication
   projects, registrations); only the full text can.
3. **8 attempts a reader checked that only the full text can settle** (`attempts_checked.csv`).
4. **12 misfiled replications** whose right original has no DOI or could not be identified stay set aside, with the
   reason.
5. **11 effects without a plain line,** recorded as too thin or contradictory.
6. **Missing details:** 538 later papers without authors (mostly OSF pages that list none), 18 without a year, 3
   without a title.
7. **6 replications dated before their original,** to be read (`python -m pipeline quality-audit`).

## How to check it yourself

- `python -m pipeline build`: the ledger step prints "N source rows, 0 without an outcome", or stops.
- The page `sources/` shows the ledger file by file, with the reasons.
- `python -m pipeline quality-audit` lists every item in the built site that still needs a decision (writes
  `data/build/quality_audit.json`); an answered question becomes a reviewed input and drops off the list.
- `pipeline/repair/audit/audit.py` is the one-off check of 28 Oct that found the problems above.
- `pipeline/repair/audit/compare.py` compares a build with the one before 28 Oct (its saved copy is in `/root/wiki-scratch/audit_20261028/build_before/`).
