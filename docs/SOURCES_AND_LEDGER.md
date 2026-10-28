# What FORRT has, what Retested has, and what Retested added

Written 28 Oct 2026. This is the plain account of where the site's data comes from, what is counted, and how the build
proves that nothing FORRT publishes has gone missing. The site page `sources/` shows the same numbers for readers.

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
| FLoRA extractor (`feeds/flora-extractor_*.csv`) | Pairs FORRT's machine search found, and ones it has not confirmed | Machine-found pairs wait in the review queue; unconfirmed ones are recorded as such |
| Retested reviewed pairs (`data/curated/promoted_pairs.json`) | 1,941 pairs Retested's readers checked against the papers | Attempts marked "Retested reviewed" (1,465 are new to FORRT) |
| OpenAlex (`data/raw/local/openalex_paper_metadata.json`, fetched 28 Oct) | Title, year and authors for each DOI | Replaces a title the site could only parse out of a reference string, and fills a missing year or author list |

## What is counted

- **An attempt** is one pair of an original paper and a later paper that tested it again.
- **A finding** is one original paper with all its attempts.
- **An effect** is a named phenomenon, such as "Dunning-Kruger effect". It may span several original papers.
- **An effect enters the database only when a replication of its own is linked.** The others are named in FORRT's
  records but have no replication here yet. They keep a page, marked as such and left out of search engines. They are
  listed with the reason on the page `not-linked/`, and no list, count, map or search includes them.

## The FORRT ledger: every row has an outcome

`pipeline/forrt_ledger.py` writes `data/build/forrt_ledger.json`, one line for each row of each FORRT file (26,917 on
28 Oct). Each line has exactly one outcome:

- **on the site:** its pair is an attempt (the line names the attempt and its effects);
- **on the site under another original:** the later paper is on the site, linked to a different original;
- **waiting to be read:** its pair is in the review queue (found by a machine, not yet read);
- **not yet read:** FORRT's Replications & Reversals list cites the later paper, but nobody has yet read it to
  establish whether it is a replication and what it found;
- **names an effect:** the row carries no pair but names an effect, and the line says whether that effect has a
  replication;
- **left out:** with the reason. The reason is FORRT's own (its filter logs, its "not a replication" marks, its
  unconfirmed links), a missing identifier, or a reviewed decision recorded in `data/curated/` (below).

**The build stops if any row has no outcome.** The summary is in `stats.json` (`forrt_ledger`) and on the page
`sources/`.

## Reviewed inputs: judgements people made, and where they live

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
| `data/curated/same_title_checked.csv` | Replications titled like their original that reading found are real later studies | same |
| `data/curated/read_pairs.json` | Later papers read from their abstracts (two models that agree, with checked quotes, or Claude where they split): what the paper is, whether it tests the finding, what it found | `pipeline/read_pairs.py` |
| `data/curated/effect_description_exclusions.csv` | A source description that belongs to another claim, or is not a claim | same |
| `data/curated/effect_lines.json`, `effect_typology.json` | One plain line per effect; the study typology. **Keyed by the stable effect id**, so a merge or rename cannot detach them; entries of folded effects are kept under `set_aside` | `pipeline/wiki.py` |

## What happened on 28 October 2026, in numbers

- **Before:** the build used the Replications & Reversals list only for names. 480 effects had no replication, and
  many of them were second copies of an effect that did have replications, under another name. Machine-found
  replications without a DOI were dropped from the queue without a note.
- **Duplicate effect names:** 206 names were folded into the effect they belong to (148 merges in `merges.yaml`).
  - 155 were read by Claude, 49 by a reading helper (Sonnet 5.5) and checked, and 2 cut-off names were joined to
    their full names.
  - No replication lost its effect, and 32 effects that showed nothing now show their replications.
- **One study counted twice:** 67 attempts were a second copy of a study under the same original (a preprint and its
  article, a thesis and its article, one report on two hosts). Each copy is merged into its record
  (`attempt_duplicates.csv`), so the study is counted once and its sources, numbers and result are kept. 58 of the
  copies had been counted twice in the result tallies.
- **Set aside after reading** (`attempt_exclusions.csv`), 66 attempts:
  - 56 filed under the wrong original paper (found in the 23 Oct reading). The reason names the paper they really
    replicate, so they can be re-linked.
  - 8 are not replications at all: the original paper listed as its own replication, or the preprint of the same
    study.
  - 2 are copies carrying another paper's DOI.
- **Re-linked:** 44 of the 56 replications filed under the wrong original now sit under the original they replicate
  (found by reading and Crossref, checked). One old reading note was itself wrong, and that replication was restored.
- **Wrong effect names:** 7 effect names attached to a paper about something else were removed. Examples: "Anchoring
  Effect" on a money-priming study, and "Heat Priming" on studies of loneliness and warm baths.
- **Added:** 38 FORRT-validated pairs that never reached FLoRA's export.
- **Paper records:** all 9,082 papers were checked against OpenAlex.
  - Titles damaged in the source ("https://doi", ": 328", "Bateson et al") now show the paper's real title, and a
    year read out of a reference string gives way to the year OpenAlex holds.
  - Author fields that were not names ("(Ed.)", raw citation data, "KÃ¶bach") show the authors.
  - 16 retracted papers are now marked retracted wherever they appear.
  - 2 genuine DOI conflicts were checked against Crossref and fixed.
- **The paper reading** (paid, $1.11; DeepSeek v4.1 flash and GLM 5.3 flash, approved by Leo) covered 2,297 later
  papers.
  - Two models agreed on 1,272. The two models split on 442, which Claude decided (Sonnet 5.5 reading helpers, samples
    checked). 530 have no abstract and a title that does not settle them, and are recorded as not readable. 53 got no
    valid answer.
  - 243 replications that FORRT's Replications & Reversals list cites are now on the site: 120 found the effect, 55 did
    not, 55 were mixed, and 13 state no result.
  - 577 attempts that had no result now have one, read from the abstract with a quote. No result FORRT coded was
    changed.
  - 174 old FReD records that FORRT never coded turned out not to be replications (88 other studies, 61
    meta-analyses, 25 reviews or commentaries) and are set aside with that reason.
  - 144 readings are listed for a person in `data/build/read_notes.json`: 9 differ from a result FORRT coded, and 135
    could not say whether the paper tests this exact finding.
- **Result:**
  - 5,353 attempts: 3,886 from FORRT (243 of them read from its list) and 1,467 added by Retested.
  - 4,641 original papers.
  - 2,225 effects with a replication; 273 more are named without one and listed on `not-linked/` (480 had nothing on
    the morning of 28 Oct).
  - The share of attempts with a result that found the effect moved from 47.9% (4,109 results) to 48.9% (4,732).

## Still open (each counted by `python -m pipeline quality-audit` or on `sources/`)

1. **Papers that could not be read from an abstract:** 530 papers, plus the 53 without a valid answer. Reading them needs
   the full text.
2. **Results still not coded:** 465 attempts, mostly papers with no abstract or no result stated in it.
3. **Readings for a person:** 144, listed in `data/build/read_notes.json`.
4. **The queue:** 2,814 FORRT machine-found pairs and about 4,160 Retested finds are unread. Reading them is a paid run
   of about $3.30 and needs Leo's yes.
5. **Misfiled replications:** 12 whose right original could not be identified stay set aside, with the reason.
6. **Effects without a plain line:** 13, where the record is too thin or contradicts itself.
7. **Contradictions:** 8 effects where FORRT's famous-list verdict and the linked replications disagree (listed in the
   evidence folder).
8. **Descriptions:** 128 FORRT descriptions carry damage from how the list was parsed. A reader sees almost none of them,
   because a plain line or FORRT's famous-list text is shown first.
9. **Missing details:** 24 replications have no authors and 22 no year; these are papers without a DOI.
10. **Meta-analyses and reviews:** the papers set aside as not replications are real evidence about an effect. Effect
    pages could list them separately; not done yet.

## How to check it yourself

- `python -m pipeline build`: the ledger step prints "N source rows, 0 without an outcome", or stops.
- The page `sources/` shows the ledger file by file, with the reasons.
- `python -m pipeline quality-audit` lists every item in the built site that still needs a decision (writes
  `data/build/quality_audit.json`); an answered question becomes a reviewed input and drops off the list.
- `pipeline/repair/audit/audit.py` is the one-off check of 28 Oct that found the problems above.
- `pipeline/repair/audit/compare.py` compares a build with the one before 28 Oct (its saved copy is in `/root/wiki-scratch/audit_20261028/build_before/`).
