# Backlog

Open work, with what is known about each item rather than a guess at its size. Numbers are from the build of
2026-09-21. `docs/history/HANDOFF_diary_2026-09-26_to_2026-10-28.md` has the current state; `docs/LINK_AUDIT_20260919.md` has the accuracy measurements
that most of these items depend on.

## 1. The 664 finds with no original (17% of psychology finds)

3,233 of 3,897 psychology finds name an original. The remaining 664 are not one problem, and most of them are not
reachable through OpenAlex at all:

| what OpenAlex holds for the paper | finds | route |
|---|---|---|
| no abstract, no reference list | 333 | needs the document itself |
| an abstract but no reference list | 214 | description search fails at 17%; needs the document |
| an abstract and a reference list | 67 | reference scan already declined these: no reference scored above the floor |
| a reference list but no abstract | 50 | title fallback already declined these |

So ~547 are bare records — a title, sometimes an abstract, and nothing to match against. **165 of the 664 are
OSF-hosted**, and the deposited file (the preprint PDF, the registration form, the analysis script) is the only
remaining place the original is named. Document parsing is no longer a different class of work — `pipeline
fulltext --pdf` does it, with `pypdf` — so what stands between here and those 165 is pointing the same machinery
at OSF file listings rather than at publisher PDFs. Note what the PDF route measured on the way: 30% of fetches
are refused by the publisher, and one PDF in 144 has no text layer, so the loss is access, not scanning.

The other 117 declined finds (67 + 50) are a cheaper question: the reference scan and title fallback both refused
them rather than guessing. Raising `FLOOR` would produce links at the measured 66% accuracy of the unbanded scan.
That is queue-grade, not page-grade, and it is a judgement about whether a wrong original is worse than none.

**Do not confuse this with the discovery ceiling.** 24,449 works were never screened at all because they scored
below the medium rule tier, and widening the keyword search beyond psychology-tagged works is a separate ~49k
titles (handoff step 3). Those are bigger numbers than 664.

## 2. Things measured but resting on small samples

Every link method that reaches a page was validated by reading links one by one, and the samples are small:

| method | measured | n |
|---|---|---|
| library, high/medium | 96% | 25 |
| openalex, high | 91% | 11 |
| reference_scan, high | 89% | 36 |
| reference_scan, medium | 74% | 46 |

The medium-tier screening accuracy (50%) rests on 40 papers labelled by Claude, not by a person. The high tier's
86% rests on the owner's 70 hand labels. More reading is the only thing that moves these.

**Both machine judgements are now the exception, and both accumulate.** The link between a find and its original
is measured band by band in `data/curated/original_audit.csv` — **384 read**, from 97% down to 12% — and the page
gate is computed from that file rather than kept as a list (`queue.trusted_links`, 20+ read and 90%+ right).
`pipeline originals --score` recomputes it; `--pool shown` scores the rows a reader actually sees rather than the
band they belong to.

Updated 2026-09-22 after 285 more reads. What a page shows is **1,550 rows, 461 read, 95% right**. The band
that still moves something:

| band | rows | read | precision | |
|---|---|---|---|---|
| `reference_scan` medium | 339 | 89 | **88%** (79–93) | overruled and off the pages; the biggest block in play |
| `reference_scan` low | 278 | 97 | 92% (85–96) | fell below the bar, then 40 more reads cleared it |
| `reference_scan` high | 300 | 68 | 96% (88–98) | back in after 40 fresh reads |

Both `reference_scan` low and medium read "exactly 90%" in the previous session and eighty more reads put them
at 92% and 88%. Any band quoted at n≈50 near the line should be assumed unsettled.

The two worst-prior bands were read for the first time since `pipeline verify` began admitting rows one at a
time, and the verifier holds in both: `openalex_author_year` low 97% (n=38), `library_author_year` low 95%
(n=40). That was the open risk of the per-row design.

**The runner-ups are settled: 46 right of 58 = 79% (67–88%), under the bar, so they do not ship.** That closes
the "~36 cards turn on this" item rather than leaving it open.

**Outcome reading is measured at n=224** (successful 94%, failed 93%, mixed 82%, one case in 200
read as the opposite of what the paper says — `docs/LINK_AUDIT_20260919.md`, addenda of 2026-09-21). That
measurement is the one piece of tooling here built to accumulate: `python -m pipeline outcomes --sample 60` draws
what is unlabelled, and the labels go in `data/curated/outcome_audit.csv`. Doing the same for the link strata
would mean a comparable sampler over link bands, which does not exist yet — `link --check` measures the easy half
and is an upper bound.

An earlier n=20 read of the same judgement concluded the error was one-directional, towards success, and that
conclusion was shipped onto `/uncounted/`. It was noise at that size. Anything in this file resting on a sample
of 20 to 40 should be read as establishing that an error exists, not which way it points.

## 3. Data quality

- ~~**95 papers share a normalised title with another DOI**, so a find can link to a page-less copy.~~ Checked
  2026-09-21: **0** finds point at a page-less twin, so there is nothing to recover that way. What the check did
  find was real — eleven DOIs cut short upstream, splitting one study's record across two pages — and that is
  fixed (`registry._fold_doi_variants`). The 39 remaining shared titles are genuine twins (preprint and
  published, Zenodo re-mints) or different papers that happen to share a title; neither is costing us anything
  measurable.
- **A label is keyed by `(find, paper)`**, not by the find. It used to be keyed by the find alone, and
  recording a judgement about a second pairing deleted the judgement about the first — six band labels went
  that way on 2026-09-22 before it was caught. Anything that reads `original_audit.csv` should go through
  `audit.index` / `audit.label_for`.
- **The link gate is computed from the previous build's `candidates.json`**, so the first build after
  recording labels disagrees with the next one. `audit.candidates()` warns on stderr; build twice.
- **18 independence verdicts are stuck on a common surname** because one side has no OpenAlex author ids. Unlikely
  to move without reading the papers.
- ~~**15 OSF lookups failed transiently.**~~ Re-run 2026-09-21: it recovered 2 (220 → 222 registrations) and the
  same 15 failed again, so they are persistent, not transient. Not worth another run.

## 4. Deferred by owner decision

- **No publication.** The site is built and previewed locally; the GitHub Pages workflow stays unused.
- **API spend is shared and lean.** Three sessions share one key. Price a run in dollars before starting it,
  pilot on `--limit`, pass `--max-usd`, and prefer hand-reading, which costs nothing and is what most of these
  numbers rest on.
- **Contact FORRT** (Wallrich / Röseler) before reusing flora-extractor or flora-validation code, and offer them
  the finds and the recall harness.
