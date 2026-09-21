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
