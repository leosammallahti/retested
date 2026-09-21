# How often is a discovered replication linked to the right original? (2026-09-19)

65 rows read one by one by Claude (Opus 5): for each, does the paper actually replicate the original it was
linked to? Judged from the replication's title and abstract, the model's own account of the study it says it
replicated, and the title of the paper it was linked to.

| link source | correct | accuracy |
|---|---|---|
| `library_author_year`, high or medium confidence | 24/25 | **96%** |
| `openalex_author_year`, high confidence | 10/11 | **91%** |
| `cited by this paper` (DeepSeek picked from the citation list) | 6/11, 2 unclear | **55%** |
| `openalex_author_year`, medium confidence | 2/4 | 50% |
| `library_author_year`, low confidence | 5/14 | 36% |

**The headline: 53% of the links that were being shown on effect and finding pages were wrong.** A replication of
Carlson et al. (2020) on attention to climate imagery was linked to "Good deeds gone bad: lay theories of altruism";
a replication of Jones et al. (2002) on pitch perception was linked to a paper on treating stuttering in young
children. Both matched on a surname and a year and nothing else.

## Why `link --check` said 92% and this says 53%

`--check` measures on the 107 replications whose original the citation graph had already resolved — papers that
cite an original already in this wiki. That is the easy half. On those, the true original is in the library, so a
surname-and-year match usually lands on it.

On the real population the original is usually **not** in the library, and the library pass has no way to answer
"none of these". It returns the best same-surname, same-year paper it can find, which is an impostor. The
confidence band catches this — the impostors land in "low" — but the band was not being used to decide what a
reader sees. It is now.

Any accuracy figure from `--check` is an upper bound. Sample the shipped rows instead.

## Two things this found that the bands do not catch

- **Circular validation.** DeepSeek writes `original.description` *after* choosing which cited paper it means, so
  comparing that description with the chosen paper's title tests nothing. The worst error in the sample — a
  self-esteem affirmation replication linked to Cohen's racial-achievement-gap intervention — scored 0.57 on that
  comparison, higher than several correct links. Description-versus-title only means something for the library and
  OpenAlex passes, where the description existed before the candidate was found.
- **Self-links.** "Attitude Dimensions of Leisure: A Replication Study" (Neulinger & Breit, 1971) was linked to
  itself: the record we found was an abstracting-service entry for that very paper.

## What changed as a result

Effect and finding pages now show only `library` high/medium and `openalex` high links — the two strata measured
above 90%. Everything else stays in the review queue, where a person is expected to check it, and citation-derived
links no longer claim a confidence band that was never measured.


## Addendum, 2026-09-21: 39 of the 65 are confirmed real *and* confirmed missing

Of the 65 links read, 47 were a real replication of the original they were matched to. Checking those against
**every** FORRT file rather than our own filter, 39 are absent from all of them. Those 39 are not estimates: each
was read by hand, and its absence from FORRT was verified against their raw data. They include CREP and class
replications of Cameron et al. (2019) at four universities, three of Williams & Bargh (2008) including a Serbian
and a Japanese one, two of Stellar et al. (2018), and published work going back to a 1985 replication of Gheorghiu
and Reyher and a 1994 replication of the Baltimore infant-crying study.

**The absence check was too narrow and has been fixed.** `known_to_forrt` consulted the curated tables plus two
feed files. It missed FLoRA's `alt_identifier_r`/`url_r` columns, where an OSF project id can stand in for a
replication, and the dated extractor snapshots under `repos/flora-validation/data/`, which carry papers as `doi_r`
before they reach the feed. `load_known_replication_dois()` now sweeps every column in every FORRT file that names
a replication, 9,967 identifiers in all, and the build refuses to ship a find FORRT already has. That removed 345
candidates, 275 of them psychology.

One caveat that cannot be closed this way: 974 of the psychology finds have no DOI, so they cannot be checked
against FORRT by identifier at all. Their absence rests on title matching alone and is weaker.


## Addendum, 2026-09-21: one absence check, applied once

Fixing the absence check left two of them behind. `discover.known_to_forrt` kept the original narrow version —
the curated tables, the flora-extractor feed glob, and two flora-validation exports — while the queue applied the
comprehensive one. The shipped product was right, because the queue filtered afterwards, but discovery went on
reporting the inflated figure, and that is the figure people quote: "8,323 new" was really 7,990, and "28,588 new"
was 28,236.

Counted directly rather than by subtracting those two summaries — which double-counts works both searches found —
**633** surfaced DOIs are newly excluded. Where they actually live matters, and an earlier draft of this note got
it wrong by calling them papers FORRT "already held":

| appears in | count |
|---|---|
| `repos/flora-validation/data/extracted_*.csv`, FORRT's unreviewed extractor output | ~572 |
| FORRT's curated FLoRA/FReD tables, via `alt_identifier_r` / `url_r` | 61 |

Only 61 were in their database. The rest were in their own machine-extracted candidate pool — surfaced by their
pipeline, reviewed by nobody, which is exactly the status our finds have. Excluding them is still correct, because
the point is to find what FORRT has not recorded and a candidate of theirs is not our find; but the gap that was
being overstated was mostly a gap against their unreviewed queue, not against their published record.

`known_to_forrt` now uses the same comprehensive sets as everything else, and matches OSF tokens as well as DOIs.
The downstream filter that used to drop 390 candidates now drops none, because nothing reaches it — which is the
check that the two agree. Final counts are unchanged: 7,177 queue candidates, 3,897 psychology finds, 128 rows on
pages.


## Addendum, 2026-09-21: the reference list is the haystack

1,176 finds described what was replicated but named no author, and I wrote them off as unrecoverable because the
authors themselves say only "a replication of a previous study". Searching OpenAlex for the description finds the
right paper 17% of the time (2/12), and 0 of 8 OSF project descriptions name the original. Both true, and the
conclusion drawn from them was wrong.

A replication cites what it replicates. On 61 finds whose link was independently verified, the original is in the
paper's reference list **84%** of the time — the first attempt at measuring this said 23%, because it was run over
low-confidence library links that were mostly wrong themselves, so it measured bad links rather than missing
references. Scoring ~35 references against the description picks the original out at the top 78% of the time,
against 17% for searching all of OpenAlex. A haystack of 35 instead of 250 million.

Banded on the same 61, with the 16% whose reference list lacks the original left in the denominator:

| | correct | |
|---|---|---|
| score ≥ .50, margin ≥ .15 | 32/36 = **89%** | high, eligible for a page |
| score ≥ .30, margin ≥ .05 | 34/46 = 74% | medium, queue |
| anything proposed | 40/61 = 66% | low, queue |

`pipeline references` resolves reference titles 50 per call and cost **$0.081** for 40,229 of them. It proposed an
original for 1,104 finds: linked psychology finds go from 1,314 to **2,846**, and the number of distinct originals
our finds name goes to 2,317.

Only 17 of those originals have a page here, which is the expected shape rather than a disappointment: the
reference scan reaches originals we do not hold, and naming the replicated paper is what a FLoRA submission
requires whether or not we have a page for it.


### Title fallback

693 finds had no description because OpenAlex holds them as a bare title: no abstract for the triage step to read.
But 478 of those still carry a reference list, and a replication's own title usually mirrors the original's —
"Replication of <original title>", or "<original title>: a conceptual replication of ...". Stripping the
replication clause leaves a query that ranks the original top 55% of the time, against 78% for a description, so
a title-derived link is capped one band below the same score from a description.

That added 387 links for $0.021. **83% of psychology finds (3,233 of 3,897) now name an original**, from 1,002
this morning, across 2,690 distinct original studies, and 1,971 carry both an original and a stated outcome.

Two measurement mistakes on the way to this, both the same shape — an intermediate result computed over the wrong
population:
- reference containment first measured 23%, because it was run over low-confidence library links that were
  themselves mostly wrong. Split by link quality it is 84%.
- the title fallback's ceiling first measured 0 finds, because the reference lists were read from a temporary file
  built earlier for a different set that never included them. It is 478.

Both would have closed off a route that worked. Check which rows an intermediate was built from before believing
what it says about a different set.


## Addendum, 2026-09-21: outcome accuracy, measured at last

Every accuracy figure above is about *linking* — whether a find was matched to the right original. Whether the
model read the outcome correctly had never been measured, and for a scored game card that is the error that
matters most.

20 finds read against their own quotes, stratified 11 successful / 9 failed:

| the model said | clearly right | note |
|---|---|---|
| failed | **9 / 9** | unambiguous every time: "we did not replicate", "a failure to replicate" |
| successful | **9 / 11** | two do not establish a replication at all |

So roughly **90% overall, and the error is one-directional**: "failed" is never wrong in this sample, "successful"
is sometimes a quote that describes a result without saying the original effect held. One reported "substantial
within-gender variation and recurring directional discrepancy patterns"; another's own title says "a disconfirmed
hypothesis".

**This bears directly on the 47.4% vs 41.7% gap** on the uncounted page. That page offers two explanations —
curation favouring famous failures, or a model finding success easier to read than a hedged failure — and says
both would produce the gap. The second now has evidence behind it: over-calling success is exactly the error this
sample found, and none of the reverse. The gap should not be read as "uncounted replications succeed more" until
somebody has reviewed enough of them to separate the two.

n = 20. Enough to establish the direction, not the size.


## Addendum, 2026-09-21: outcome accuracy again, at n=144, and the one-directional error does not survive

The n=20 read above found failures right 9/9 and successes right 9/11, concluded the error runs one way —
towards success — and that conclusion was put on `/uncounted/` as the likely explanation of its 47.7% vs 41.7%
gap. **144 more cases, read the same way, do not support it.**

`python -m pipeline outcomes` now owns this measurement. It draws a deterministic stratified sample, prints each
case as the replication's own **full** abstract (not the 700-character copy the queue carries for the browser,
which usually cuts before the results sentence) plus the quote the verdict rests on, and records the labels in
`data/curated/outcome_audit.csv` keyed by candidate id. They survive rebuilds and accumulate, which is the thing
the n=20 read did not do: its 20 rows were never written down, so this sample could not extend it and had to
start again. Scoring uses every label whose candidate is in the pool, and names the rows in a pool that no draw
has reached instead of quoting a figure over them.

120 cases from the game-card pool (psychology finds with a binary verdict and a linked original), 60 successful
and 60 failed, plus 24 drawn from the `mixed` verdict that only the `/uncounted/` population contains:

| the model said | right | precision | 95% interval | where the rest went |
|---|---|---|---|---|
| failed | 55/60 | **92%** | 82–96% | 3 not established, 2 mixed |
| successful | 56/60 | **93%** | 84–97% | 4 not established |
| mixed | 18/22 | 82% | 62–93% | 3 not established, 1 successful |

**The two binary classes are the same within noise, and nothing in 144 cases was read as the opposite of what the
paper reports.** Zero flips. That is the number that matters for a scored card: the failure mode is not a wrong
answer but a missing one — an abstract that settles nothing, called either way.

The nine mistakes in the card pool are all of one kind. A dissertation that replicates a study and then reports
only whether its own new refinement worked (`10.12794/metadc149614`). A null result whose own abstract says the
manipulation checks failed and calls it inconclusive (`10.58837/chula.the.2021.337`). A decade replication that
prints eight correlations from .09 to .51 and never says whether they match Dean (1966) (`10.2307/351897`). A
violation-of-expectation study that replaced the human agent with a toy crane, so the original condition was
never re-run (`10.1111/desc.12887`). An uncontrolled open trial whose own conclusion says efficacy cannot be
concluded from it (`10.1177/10870547261457678`). Four of the nine were called successful and five failed.

Why the earlier sample pointed the other way: it did not. 9/9 and 9/11 are exactly what ~92% in both classes
produces at that size — the chance of seeing 9/9 at 92% is .47, and of 9 or fewer out of 11 at 93% is .18. The
pattern was read as a direction when it was the width of the interval. n=20 could establish that some verdicts
are wrong; it could not establish which way.

**What this changes.**

- `/uncounted/` no longer says a model over-reading success explains its gap. Re-weighting every verdict on that
  page by these labels moves it from 47.7% to 49.3% — slightly *further* from the curated record's 41.7%, not
  closer. The page now prints these numbers straight from the label file through `stats.uncounted().audit`, so
  the claim cannot drift from the measurement again.
- The card pool's base rate is not a measurement artefact either. At the deck's own grain — one card per original
  study, dropping originals whose finds disagree — it is 1,323 cards at **62.9% successful**, and correcting
  every verdict by the table above gives **63.3%**. Against the existing deck's 53%, the difference survives. Keep
  them a separate deck because the pool really is different, not because its verdicts are misread.
- The 17 rows of this sample that fall in the page-grade link band were right 17/17. Too few to quote as a rate,
  and recorded only so the next draw does not re-read them.

Limits worth stating. One reader, one session, judging the same abstracts the model judged — this measures whether
the verdict is a defensible reading of the abstract, not whether the abstract is a defensible reading of the paper.
Both readers can be wrong together where an abstract oversells. And it says nothing about whether the find was
matched to the right original; that is the separate measurement above, and a card needs both.

### The model's own confidence separates the unusable ones

The nine mistakes are not spread evenly. Five of them sit below `outcome_confidence` 0.8, a band holding only 14
of the 120 rows read:

| `outcome_confidence` | read sound | 95% interval | rows in the card pool |
|---|---|---|---|
| below 0.8 | 9/14 = 64% | 39–84% | 233 |
| 0.8 and up | 102/106 = **96%** | 91–98% | 1,209 |

Fisher two-sided p = .001, so this is wider than the sample. Dropping the low band costs 16% of the card pool and
takes the rest from 93% sound to 96%. `pipeline outcomes --score` re-derives the split from the labels every run
rather than quoting these numbers, because it is only as good as the reading behind it.

This is not the pattern the earlier session looked for and failed to find. That search was for a signal that a
verdict had been *over-read towards success*, and there is no such error to detect — the 2026-09-21 reading found
none in 144 cases. This one separates verdicts with no binary answer from verdicts with one, in either direction,
which is a different and easier question. (The two failed attempts were said to be recorded in this file so they
would not be rebuilt. They are not in it; whatever was tried was not written down.)


## Addendum, 2026-09-21: every link band read, and a route reopened

The 65 cases at the top of this file read five bands. They left most of the pool unmeasured: of the 1,442 rows
that could become a game card, **694 sat in bands nobody had read a single case from**. A card needs the right
original twice over — the reveal names it, and any written claim would come from its abstract — so this is as
decisive for the deck as the verdict is.

`python -m pipeline originals` is the same instrument as `pipeline outcomes`, pointed at the link: a
deterministic stratified draw, one case at a time, labels accumulating in `data/curated/original_audit.csv`.
146 read, band by band:

| band | right | | rows in the card pool |
|---|---|---|---|
| `cited by this paper` | 34/36 | **94%** | 217 |
| `library_author_year` high | 10/10 | **100%** | 7 |
| `library_author_year` medium | 11/12 | **92%** | 2 |
| `openalex_author_year` high | 8/8 | **100%** | 44 |
| `openalex_author_year` medium | 7/8 | 88% | 60 |
| `reference_scan` high | 8/10 | 80% | 158 |
| `reference_scan` medium | 8/14 | 57% | 195 |
| `openalex_author_year` low | 8/20 | 40% | 358 |
| `reference_scan` low | 7/20 | 35% | 336 |
| `library_author_year` low | 1/8 | 12% | 65 |

**The two weakest bands are not weak, they are wrong.** Dean (1966) on marital adjustment matched to the
intrinsic absorption-edge spectrum of gallium phosphide. Nolan (1968) on smoking matched to Nolan & Margoliash
on protein structures. Briggs (2018) on resurgence of problem behaviour matched to a paper on machine
translation in Korean students' academic writing. Stone (1966) on prognostic judgements matched to Stone (1966)
on non-geostrophic baroclinic stability. A surname and a year with nothing behind them, exactly as the first
audit found for `library_author_year` low — and those two bands hold 694 of the card rows.

A second, quieter failure appears throughout: the right paper is often the **runner-up**. Ermisch and Gambetta's
"Do strong family ties inhibit trust?" sits second while the pick is someone else's review; Tversky's
"Intransitivity of preferences" sits second while the pick is a different Tversky 1969; Krosch and Amodio's
scarcity study sits second while the pick is a different scarcity paper. The scorer is ordering candidates
better than its own top-1 suggests, which is a lead for anyone who wants to improve the matcher rather than
gate it.

### A route that was closed on a measurement that had stopped describing the data

`cited by this paper` — the model picking the original out of the paper's own reference list — was filed as
`unchecked`, kept off every page, and described here as "right only 6 times in 11". **Read again, it is 34 right
out of 36.** That is better than any other band, and better than the 32/36 that admitted `reference_scan` high.

The two readings are not in conflict, because they are not of the same data. The 6/11 was of output from prompt
t1. t3 added the mere-citation trap — *"Citing a study is not replicating it. Use original_index only when this
paper actually re-tests that study's finding"* — and the two caches show exactly what that did. Of 239
candidates t1 named a cited original for, **t3 withholds the name on 101 and keeps 137 of the remaining 138
picks identical**. It did not pick better; it stopped picking when it should not have picked at all, and the
doubtful half is precisely what the 6/11 was measuring.

The band is now trusted. Rows shown beside a verdict on a finding page go from 111 on 65 pages to **168 on 115**.
The pipeline's own rule caught this one: *when a measurement says a route is dead, verify the measurement before
closing the route.*

### And the bands that were quoted but never written down

`library_author_year` high/medium has been quoted at 24/25 since 2026-09-19, and it carries more rows onto pages
than any other band. Those 25 reads were never recorded row by row, so nobody could check them, extend them, or
find out which cases they were — the same hole that made the outcome audit start over rather than build on n=20.
They are now 10/10 and 11/12 **in a file**. Every band a page shows has been read, and the queue explainer and
the "not in the record yet" box print these numbers straight from `data/curated/original_audit.csv` through
`stats`, so no page can state an accuracy the label file does not hold. Until today the queue page was still
quoting the superseded 6 in 11.
