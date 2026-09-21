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
was 28,236. 685 papers FORRT already held were being counted as gaps in their database.

`known_to_forrt` now uses the same comprehensive sets as everything else, and matches OSF tokens as well as DOIs.
The downstream filter that used to drop 390 candidates now drops none, because nothing reaches it — which is the
check that the two agree. Final counts are unchanged: 7,177 queue candidates, 3,897 psychology finds, 128 rows on
pages.
