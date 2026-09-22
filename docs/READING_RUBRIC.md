# Reading a link: the rubric

This is the one copy. `pipeline originals --batches` puts it at the top of every batch file, so every reader
answers the same question the same way, and a label made in one session means the same thing as a label made in
another. Six readers on 2026-09-22 each got a hand-written variant of it, which is how it came to be here.

The judgement this asks for is the most reliable evidence this project has about a link. Since 2026-09-22 a
label decides its own row: a link read as `right` appears beside a verdict whatever band it came from, and one
read as `wrong` does not appear whatever band it came from. Band accuracy is now only a stand-in for rows
nobody has read.

## The question

**Does the replication paper actually re-test a finding from the paper it was matched to?** Judge it from the
replication's own title and abstract, its own account of what it replicated, and the matched paper's title and
abstract.

## The three labels

- `right` — the matched paper is the study this replication re-tested.
- `wrong` — it is not. A paper merely cited as background; a different paper, including a different one by the
  same author in the same years; the replication itself; a correction or erratum record instead of the article;
  a review or meta-analysis where the replication re-tests one specific source study; the companion paper (the
  replication is of the study on men and the match is the one on women); or something unrelated.
- `unclear` — the records genuinely do not settle it: a bare title on one side with nothing to confirm it, or a
  plausible match that nothing in the record confirms.

`unclear` is a real answer and not a polite `wrong`. It is scored in its own column and set aside from the
precision figure, so an honest "I can't tell" protects the measurement while a guess corrupts it. It also
decides nothing: an `unclear` row falls back to the band rule, exactly as if it had never been read.

## What counts as evidence, and what does not

- **A shared topic is not evidence. A surname and a year are not evidence.** Real failures caught here include a
  marital-adjustment paper matched to the absorption-edge spectrum of gallium phosphide, a 1968 smoking paper
  matched to one on protein structures, and a resurgence-of-problem-behaviour paper matched to a study of
  machine translation in Korean students' academic writing.
- **But a mid-century title often is evidence.** Psychology of that era put the finding in the title, so a
  near-verbatim match between a 1966 "…: A replication" and a 1954 paper on the same specific measure is not a
  coincidence of topic. "The determinants of Rorschach card rejection: A replication" (1966) really does
  replicate "Rorschach card rejection in psychodiagnosis" (1954).
- **A review or meta-analysis reports no original finding.** A replication of an empirical effect matched to the
  review that describes that effect is `wrong`. Name the source study if you can see it.
- **A repository duplicate is the same study.** A PsycEXTRA, Zenodo, OSF or institutional-repository record of
  the right paper is `right`.
- **Where the band is `cited by this paper`, the `says it replicated` description is not evidence.** A model
  wrote that description *after* choosing which cited work it meant, so its agreeing with the chosen paper's
  title is circular. Judge those cases from the replication's own abstract against the matched paper's title
  and abstract, and nothing else.
- **Ignore the `evidence` scores.** They are the thing being measured.
- **The runner-up is often the right answer.** When you call a match wrong, say which paper you think is right —
  that note is what a later session uses to repair the link rather than merely drop it.

Searching the web for a case that turns on one checkable fact is encouraged and has repeatedly changed a
verdict. Do not spend long on any single case.

## Output

One line per case, tab separated, no header:

    <cid><TAB><label><TAB><one clause saying why>

Use the cid exactly as printed — some are DOIs, some are OpenAlex `W…` ids. Notes under about 200 characters,
plain text, with no tab characters and no newlines inside a note. Every case in the batch must appear exactly
once.

Record them with:

    python -m pipeline originals --record --pool <the batch's pool> --by <who read it> < labels.tsv
