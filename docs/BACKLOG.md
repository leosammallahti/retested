# Backlog

Open work, with what is known about each item rather than a guess at its size. Numbers are from the build of
2026-09-21. `docs/HANDOFF.md` has the current state; `docs/LINK_AUDIT_20260919.md` has the accuracy measurements
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
remaining place the original is named. That means fetching and parsing documents, which is a different class of
work from anything in the pipeline today, and worth doing only if 165 links justify it.

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

## 3. Data quality

- **95 papers in the library share a normalised title with another DOI.** A find can link to a copy that has no
  page and vanish from view. Merging them is straightforward and would recover some page rows.
- **18 independence verdicts are stuck on a common surname** because one side has no OpenAlex author ids. Unlikely
  to move without reading the papers.
- **15 OSF lookups failed transiently.** Re-running `pipeline osf` retries them for free.

## 4. Deferred by owner decision

- **No publication.** The site is built and previewed locally; the GitHub Pages workflow stays unused.
- **No DeepSeek.** Rules out re-screening the 24,449 low-tier works and the wider keyword sweep, both of which
  need a model to triage. Everything in sections 1–3 is reachable without one.
- **Contact FORRT** (Wallrich / Röseler) before reusing flora-extractor or flora-validation code, and offer them
  the finds and the recall harness.
