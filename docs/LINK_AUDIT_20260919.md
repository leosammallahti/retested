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


## Addendum, 2026-09-21 (later): 384 links read, and the page gate now follows the reading

The 146 reads above were extended to **384** by eleven readers working a band each, with two bands read twice by
independent readers who could not see the first labels. **Three of the figures above moved, including one this
same session had acted on.**

| band | read | | rows in the linked pool | on a page? |
|---|---|---|---|---|
| `library_author_year` high | 29/30 | **97%** | 45 | yes |
| `openalex_author_year` high | 31/33 | **94%** | 117 | yes |
| `library_author_year` medium | 30/32 | **94%** | 93 | yes |
| `openalex_author_year` medium | 30/33 | **91%** | 122 | yes, newly |
| `cited by this paper` | 72/84 | 86% | 307 | no, reverted |
| `reference_scan` high | 32/40 | 80% | 299 | no, removed |
| `reference_scan` medium | 28/44 | 64% | 463 | no |
| `openalex_author_year` low | 14/40 | 35% | 723 | no |
| `reference_scan` low | 10/40 | 25% | 682 | no |
| `library_author_year` low | 1/8 | 12% | 186 | no |

**The promotion of `cited by this paper` earlier today was made on too small a sample and is reverted.** 34 of 36
became 72 of 84 — 86%, short of the 90% the project set when it first gated pages. The reading was not sloppy so
much as shallower: the readers who took the band to 84 checked full texts where the record was ambiguous, and
found, for instance, a warmth study whose own text says *"Replicating previous work (Inagaki & Eisenberger,
2013)"* while the match was Williams & Bargh (2008), cited only as background. Two blind readers of the same 25
cases agreed on **every one, including all six they called wrong** (Cohen's κ = 1.00), so the lower figure is not
one reader being harsh.

**`reference_scan` high was also below the line and nobody had noticed**, because its 32/36 = 89% had been quoted
since September and never re-read. Forty fresh cases put it at 80%. It had been shown on pages the whole time.

**And `openalex_author_year` medium was excluded on 2 of 4.** Thirty-three reads put it at 91%, so it is in.

### The gate is no longer a list

`queue.TRUSTED_LINKS` was a hand-maintained set of pairs. It is now computed on every build from
`data/curated/original_audit.csv`: a band qualifies when at least 20 of its links have been read and at least 90%
were right. That rule is the one this file stated in September — "the strata measured above 90%" — finally
applied uniformly instead of case by case, and it went stale in both directions while it was a list.

Rows shown beside a verdict: 111 → 168 when the band was promoted this morning, and **110 on 64 finding pages**
now that the measurement is in charge. A point estimate near the line at n≈30 is not stable, so bands will move
as reading accumulates. That is the mechanism working.

`cited by this paper` also stops calling itself "high". It has no per-row score — the model writes its account of
the original after choosing it — so it is `unscored`, and how often it is right is a question for the audit
rather than a band label.

### Reader agreement, since the reading is now the instrument

| band | same cases | agreement | κ |
|---|---|---|---|
| `cited by this paper` | 23 | 23/23 = **100%** | 1.00 |
| `reference_scan` medium | 30 | 26/30 = 87% | 0.73 |

Every disagreement in the second band was *wrong* against *unclear* — never right against wrong. Two readers
looking at the same records reach the same verdict on which links are real; what they differ on is how much
benefit of the doubt an unconfirmable record gets.


## Addendum, 2026-09-21 (later): outcome reading at n=200

The outcome audit was extended from 144 to **224 labels** the same way. It did not move:

| the model said | right | precision | 95% interval |
|---|---|---|---|
| successful | 94/100 | **94%** | 88–97% |
| failed | 93/100 | **93%** | 86–97% |
| mixed | 18/22 | 82% | 62–93% |

Still symmetric, still no sign of the one-directional error the n=20 sample suggested. One correction to the
earlier claim that nothing had been read as the opposite of what the paper reports: at n=200 there is **one**
such case, a "successful" whose paper reports a failure. One card in two hundred would score a player backwards;
twelve in two hundred have no binary answer at all.

The confidence split holds and sharpens: below `outcome_confidence` 0.8 the verdict is sound 23 times in 29
(79%); at 0.8 and above, 164 in 171 (**96%**).


## Addendum, 2026-09-22: a worse method was blocking a better one

Of the finds this project has matched to an original, 759 sat in bands read at 12–35%. That looked like a hard
limit — the paper says "we replicated Smith et al. (1998)", surnames repeat, and there are 250 million papers.

It was not a limit. `pipeline references` — which finds the original in the replication's own reference list, and
is measured at 78–89% — contained the line

    if t.get("original_doi") or r["cid"] in links: continue

so it skipped any find that already had an answer. The author-and-year matcher runs first, produces a weak
answer, and the better method walks straight past it. The two sets never overlapped: 1,491 finds got the
reference scan, 1,416 got author-and-year, **and not one got both**.

`--relink` now reconsiders any find whose author-and-year match landed in the low band. 2,121 of them cite a
reference list already on disk; resolving the 16,665 new cited titles cost **$0.033**. It proposed an original
for 1,937 finds: 375 high, 601 medium, 961 low.

And `load.merged_links()` now decides between the two matchers by measured accuracy rather than by which
dictionary was merged second. A low-band author-and-year link yields to a reference-list link; everywhere else
the earlier behaviour stands.

`reference_scan` high grows from 299 rows to 363, at an unchanged 80% (32/40).

### Two ways the labels nearly lied about this

**A label describes the match that existed when it was read.** Re-running a matcher can replace that link with a
different paper, and then the label is about a match nobody is making any more. 22 of the 384 hand-read labels
are now in that position, and scoring them against their rows' new bands made `reference_scan` high look like it
had dropped from 80% to 73% — a band's accuracy computed over rows it was never measured on, which is the
mistake this file exists to record. `originals.stale()` now sets those aside and says how many.

**But a band RENAME is not a changed match.** The first version of that check also set aside 36 labels whose
band had merely been renamed from `cited by this paper/high` to `/unscored`, and that made the best-read band in
the project look like 79% instead of 86%. The labels were migrated with the rename. Before trusting a drop, check
whether the rows moved or only their label did.


## Addendum, 2026-09-22: the author is in the bibliography

Web search was tried first, on two finds whose match was obviously wrong, and it worked: it identified Kang et
al. (2011) and Thomson, Besner & Smilek (2016) correctly from the replication's own description. But ~900 finds
need this, and a search per find is an expensive way to buy an answer.

Checking whether the right paper was already on disk changed the plan. For the vigilance case it was: *"A
critical examination of the evidence for sensitivity loss in modern vigilance tasks"*, Thomson, Besner & Smilek,
sitting in the replication's own reference list. The reference scan had missed it because it matches the find's
DESCRIPTION against reference TITLES, and "online semantic vigilance task results replicated in laboratory
setting" shares almost no words with that title. **An author and a year find it immediately.**

The author names were the one thing never fetched — `resolve_titles` asked OpenAlex for `id, doi, title,
publication_year` and nothing else.

`pipeline references --by-author` matches the surnames a find's abstract names against its own bibliography,
within a **±2 year window**. The window is not slack: OpenAlex lists that Thomson paper as 2015 and the citing
paper calls it 2016, one being the print year and the other online-first. An exact match would have missed it.

1,583 finds name an author and had no strong link; 995 of them cite a reference list already held. **894
matched** — 586 high, 210 medium, 98 low — for **$0.080**.

**Read by hand, 30 of the high band: 28 right, 93%** (95% CI 79–98%), the second-best band in the project. The
two misses both put a different paper by the right author in the right window. It is now a trusted band, which
took the finds eligible to be a game card from **83 to 119**.

### The gate was counting labels it should have set aside

`originals.stale()` had been taught that a label describes the match in force when it was read, and that
re-matching a find invalidates it. `queue.trusted_links()` — the function that actually decides what a page and
a card may show — had not. It read `reference_author/high` as 31 right of 42 where the live labels say 28 of 30,
because 12 labels written about the weak match the row used to have were being counted against the band it moved
to. Same rule, applied in the scorer and not in the gate. Both now share it.

---

## 2026-09-22 · Asking about the row instead of the band

Every number above scores a link METHOD. Read forty cases from a band, and if the band comes out at 90% or
better, every row in it ships. That is the only instrument this project had, and it judges a row by the company
it keeps. 1,259 psychology finds were matched to an original and excluded — not because anyone looked at them and
disagreed, but because the method that found them averages 86% or 80%. Inside a band measured at 29% there are
links that are plainly right and links that are plainly wrong, and a band score cannot tell them apart.

`pipeline verify` asks about the row. One call per find: here is the replication, here is the paper we matched it
to, is this the paper it re-tested? `right` / `wrong` / `unclear`, with a reason.

**It was scored against the 401 hand-read links that survive `stale()`** — labels made before this module existed,
for a different purpose, which is what makes them a fair test.

| the model says | person: right | wrong | unclear |
|---|---|---|---|
| right | **260** | 4 | 3 |
| wrong | 13 | 52 | 5 |
| unclear | 39 | 15 | 10 |

- **Of the links it confirms, 260 of 264 a person had settled were right — 98% (95%: 96–99%).** Clears the 90%
  bar the pages already use, on the low end of the interval.
- Of the links it rejects outright, 52 of 65 the person also called wrong — 80%.
- Of the links it calls unclear, the person called 39 of 54 right — about the average of the pool.

So the verdict is used where it is strong and not where it is weak (`queue._link_trusted`): **right** admits the
row whatever band it came from; **wrong** excludes it whatever band it came from, costing 13 good rows per 65 and
removing 52 bad ones; **unclear** falls back to the band rule, because the absence of a judgement is not one. It
turns down 17% of rows a person called right — the price of the 98%.

**The whole pool, 3,047 links, cost $1.105.** 1,500 confirmed.

| band | judged | confirmed | rejected | unclear | band's own measured accuracy |
|---|---|---|---|---|---|
| cited by this paper/unscored | 307 | 241 | 35 | 31 | 86% |
| reference_scan/high | 363 | 230 | 68 | 65 | 80% |
| reference_scan/medium | 572 | 224 | 154 | 194 | 64% |
| reference_scan/low | 625 | 142 | 240 | 243 | **29%** |
| reference_author/high | 223 | 140 | 37 | 46 | 93% |
| openalex_author_year/high | 117 | 110 | 5 | 2 | 94% |
| openalex_author_year/low | 364 | 103 | 241 | 20 | **17%** |
| openalex_author_year/medium | 122 | 98 | 15 | 9 | 91% |
| library_author_year/medium | 93 | 83 | 2 | 8 | 94% |
| library_author_year/low | 135 | 58 | 65 | 12 | 33% |
| library_author_year/high | 45 | 44 | 1 | 0 | 97% |
| reference_author/medium | 81 | 27 | 21 | 33 | 73% |

The two bottom bands are the point. `reference_scan` low reads 29% over 34 hand-read cases, and in the calibration
the model confirmed 9 of its links and a person had called all 9 right. Three of the 133 newly confirmed rows in
that band, read by hand afterwards: a paper titled *"Disguise and the structured self-report assessment of
psychopathology: II. A clinical replication"* matched to *"…: I. An analogue investigation"*; a 2018 *"systematic
replication"* of a 2015 preference-assessment study; a 2018 *"partial replication of laboratory findings"* matched
to Nevin 1990. Obviously-right rows that a band average had buried.

### What it changed

Rows a page may show: **600 → 1,565**. Scored per band against the 285 hand labels that survive the new pool
definition, every band in the shipped set now reads 90% or better (277 right of 285, 97%). That is the same
evidence as the calibration seen band by band, not a second independent check — but it confirms the filter is not
leaving a weak band behind.

Game deck: **912 → 1,149 cards**, the found tier 155 → 397. Base rate 54% successful (found tier 58%, down from
the 63% skew that a smaller and more selected pool had).

### The measurement this invalidates

`originals.POOLS["page"]` and `["shown"]` were defined by band membership and are now defined per row. **They are
different sets of rows, so every page-pool figure above this addendum was measured on a population that no longer
exists.** `pipeline originals --score --pool page` recomputes it; the `linked` and `card` pools are unchanged and
their numbers still stand.

### One thing the judge is not shown

For links whose method is `cited by this paper`, the model wrote `original_named.description` AFTER choosing which
cited work it meant. Handing that description back to the judge would be asking it whether it agrees with its own
earlier answer. Those cases are judged from the replication's own abstract against the original's title and
abstract, and nothing else — the same warning `originals.py` has always printed to human readers.

### A second prompt for the cases the first could not settle

663 links came back `unclear`, and **80% of those are rows where nobody holds a summary of the earlier paper** —
the judge was handed a bare title and the instruction that a shared topic is not evidence. That instruction is
right for modern papers and wrong for these. Read by hand, the refusals include:

- *"The determinants of Rorschach card rejection: A replication"* (1966) → *"Rorschach card rejection in
  psychodiagnosis"* (1954)
- *"The effects of ward change on patients' psychopathology and behavior: A failure to replicate"* (1973) →
  *"Effects of environmental change upon behavior of hospitalized schizophrenic patients"* (1968)

Mid-century psychology puts the finding in the title, so a near-verbatim title match is not a coincidence of
topic. It also includes refusals that are correct and must stay refused: *"Introversion, extraversion and social
intelligence: A replication"* matched to *"the effects of MMPI social introversion on WAIS PA performance"* is
not the same measure, and *"The MacAndrew alcoholism scale: A replication"* names MacAndrew while the matched
record is Whisler & Cantor's cross-validation of that scale — a different paper.

`SECOND_SYSTEM` (`v2`) says what to do when both records are bare, and runs only over the rows `v1` left unclear.

Scored on the 64 hand-read links `v1` could not settle:

| the model says | person: right | wrong | unclear |
|---|---|---|---|
| right | **29** | 4 | 1 |
| wrong | 2 | 1 | 5 |
| unclear | 8 | 10 | 4 |

- On its own the second pass confirms at **88% (95%: 73–95%)** — under the bar, and it is recorded as under it.
- **Both passes together: 289 of 297 confirmed links the reader had settled were right — 97% (95%: 95–99%).**
  That is the pool that actually ships, and it clears.
- Its rejections are not usable: of the 3 rows it called wrong, the reader had called 2 of them right.

So the second pass **promotes only**. `right` is kept; anything else leaves the row unclear and falling back to
the band rule. Using a judgement only where it was measured to work is the point of the whole file.

Over all 663: **328 promoted, 335 left unclear, $0.305.** Confirmed links 1,500 → **1,828**.

One weak spot is visible and is deliberately not acted on: in `reference_scan/medium` the second pass confirmed
10 and the reader had called 6 of them right. n=10 is not a measurement, and promoting or demoting a band on a
sample that size is the mistake this project made with `cited by this paper` (34 of 36, reverted the same day).
It stays in, and more reading of that band is the thing that would settle it.

### The route that was checked and closed

1,721 psychology finds are recorded as not saying how the replication turned out, and they are the largest single
loss in the funnel. **Only 573 of them have a summary at all**, and of those 573 exactly **14 contain a sentence
that looks like a result** — all of which, read, report the ORIGINAL study's finding ("Previous research has
shown that pictures of cognates are more easily named…"), not the replication's. The rest are study plans written
before the data ("we expect perceivers to rate relatively quicker targets higher"), registered reports, teaching
projects and OSF folder descriptions. The screen was right. Reaching these needs the documents themselves, and no
prompt gets there.

Crossref holds an abstract for **0 of 20** of the missing earlier papers; Semantic Scholar for **3 of 50**. These
are mostly pre-1995 papers for which no abstract was ever deposited anywhere.

### The paper the matcher ranked second — built, measured, held back

Every matcher scores candidate originals and records the runner-up, and nobody had ever looked at it. When the
judge rejected a first choice the find was dropped with its second choice unread: **1,189 finds** were in that
state. Two read by hand looked decisive —

- *"Association of smoking and personality with a polymorphism of the dopamine transporter gene"* names Sabol
  et al. 1999; the matcher chose a 1992 gene-mapping paper and ranked *"A genetic association for cigarette
  smoking behavior"*, Health Psychology 18(1):7 — which **is** Sabol 1999 — second.
- *"Online Moral Conformity Revisited"* → first choice *"Moral conformity in online interactions"* (a different
  paper), second choice *"Online Moral Conformity: how powerful is a Group of Strangers"*.

`verify --runners` fetches what OpenAlex holds on each runner-up and judges it with the `v2` prompt. **180 of
1,189 confirmed, $0.617.** Of the 180, the first choice had been called wrong 130 times and unclear 50 times.

**Read by hand, 18 drawn at random: 14 right — 78%** (95%: 54–92%), against a 90% bar. Labels are in
`original_audit.csv`. The four failures have a shape the judge cannot see without an abstract:

| the replication | what was picked |
|---|---|
| approach-bias *retraining* in alcohol dependence | a paper measuring motivational tendencies |
| adjustment of homosexual and heterosexual *men* | the companion paper on *women* |
| assertiveness and the Bem Sex-Role Inventory | a theoretical and methodological *critique* of the BSRI |
| a replication of Pfattheicher et al. 2021 | *"Prosocial behavior and altruism: a review of concepts"* |

**So nothing ships, and the reason matters more than the result.** The judge is allowed past the band gate at all
because it measures **98% on first choices**. That number is about first choices. A second choice is a different
population by construction — a paper some matcher already ranked *below* one that turned out to be wrong — and
the same instrument reads 78% there. Carrying a calibration from the population it was measured on to a
different one is the error this whole file exists to prevent, and it nearly happened here because the promotion
looked free.

The work is kept and the measurement written down: `data/discovery/runner_up_links.json` holds the 180, and 18
of them are labelled. About **36 cards** turn on it. If more reading clears 90%, `load.merged_links` is where to
merge them.

### The reference scan was reading a third of each bibliography

A question worth asking of any matcher: what would the ceiling be if it were perfect? For the reference scan
that is "how often is the original actually cited by the replication, and where does the scorer rank it". FORRT's
own **2,802 known (replication, original) pairs where we hold the bibliography** answer it without anyone
labelling anything: hide the original, score the references, see where the truth lands.

The first answer was that the original was findable **23%** of the time, which would have closed the route.

It was an artifact. `reference_titles.json` held 68,598 titles and `references.pick` silently skips any reference
without one, so the scan was reading about a third of each bibliography and the *measurement* was reading the
same third. Fetching the rest cost **$0.14** and took the file to **131,794**:

| | before | after |
|---|---|---|
| true original visible in the bibliography at all | 23% | **82%** |
| our text-similarity scorer ranks it first | 10% | **31%** |
| ...somewhere in its top 3 | 15% | 44% |
| ...somewhere in its top 8 | 19% | **56%** |

This is the second time here that a route measured as dead was measured through a crippled intermediate. The
rule in the handoff — *check which rows an intermediate was built from before believing what it says* — was
written about exactly this and still nearly cost the route.

### Choosing among the citations, rather than judging one at a time (built, measured, not shipped)

The gap between "ranked first 31%" and "in the top 8 56%" is the case for asking a different question. `pipeline
choose` shows the model the eight cited papers closest by wording and asks **which one, if any** — one call per
find rather than one per pairing, and alternatives supply the context a lone yes/no lacks.

Scored on 500 known pairs with the answer hidden:

- it named a paper 368 times and was right 213 — **58%** (95%: 53–63%)
- it answered "not listed" 132 times, 115 of them correctly
- it finds **213 right originals per 500 finds against the text-similarity scorer's 140** — half again as many

Feeding its choices to the verifier, the pairing the two agree on is right **74%** (95%: 68–79%) — better than
either alone and still short of 90%, so it does not ship. One caveat is on the record rather than argued from:
in that test neither paper had an abstract, because FORRT's rows do not carry one and shortlisted candidates are
titles. Production verification usually has both. The 74% is a floor, not a verdict, and re-measuring it on
finds that do have abstracts is the next thing to do here.

`pipeline choose --check` is the harness; it costs about $0.15 per 500 and needs no labelling.

### A label has to say which paper it judged

Completing the reference titles moved many rows to a different paper **inside the same band**. `stale()` compares
the band recorded with the label against the band the row is in now, and a band is too coarse to catch that: 32
labels on `reference_scan/medium` went on being counted though they were read against papers that had since been
replaced. The tell was reading twenty fresh cases of that same band and getting a different answer.

| `reference_scan/medium` | read | right | |
|---|---|---|---|
| 32 labels from 2026-09-21, before the titles were completed | 32 | 26 | 81% |
| 20 read today, after | 19 | 18 | **95%** |
| together, which is what the scorer prints | 52 | 44 | 85% |

`original_audit.csv` now carries a `matched_to` column and `stale()` checks it. Labels written before today have
it empty and are taken at their word, because nothing better can be said about them — which is why that band
still prints 85% rather than the 95% the current matcher probably deserves. Re-reading those 32 is the cheapest
way to settle 343 rows.

This is the third instance today of one pattern: **a judgement about a pairing has to record the pairing.** The
model's verdicts had it (fixed by keying on `doi_o`), the verdict cache had it (fixed by keying the file on
(find, paper)), and the hand labels had it. In each case the failure was invisible while nothing moved and
appeared the moment re-matching moved something.

### One rule for what a reader's "can't tell" means

Re-reading the two weak bands raised a question the codebase had two answers to. `queue.trusted_links` computed
a band's accuracy as `right / everything read`, counting `unclear` as a miss. The verifier's calibration
computed `right / (right + wrong)`, setting `unclear` aside. **On the same labels the two differed by 146
cards**, entirely in how a handful of "can't tell" reads were treated.

`right` and `wrong` are findings. `unclear` is the reader declining to judge — a bare title on one side, a
plausible match nothing confirms — and it is not evidence that the match is wrong. The harm this bar exists to
prevent is a **wrong** original sitting under a card. So the rate is `right / (right + wrong)`, unclear rows are
set aside and counted in their own column, and `queue.rate` is the one place it is written.

### Both weak bands, read out

`reference_scan/medium` was at 26 of 32 (81%) on labels written before the reference titles were completed.
Twenty fresh reads came out 18 of 19. Re-reading all 35 of the old ones against the matches actually in force —
several of which had changed, including a Briggs 2018 resurgence paper that had been matched to a study of
machine translation in Korean students and now points at the right Briggs paper — gave 29 right, 4 wrong, 2
unclear.

| band | rows | right | wrong | unclear | precision |
|---|---|---|---|---|---|
| reference_scan/medium | 343 | 47 | 5 | 3 | **90%** (79–96) |
| reference_scan/low | 282 | 19 | 2 | 3 | **90%** (71–97) |

Both sit exactly on the line rather than under it, which is not what either was thought to be. `reference_scan`
low had been the project's worst band at 29%; completing the bibliographies and filtering per row is what moved
it, and it is the same 282 rows.

### What a page shows, all of it

| | |
|---|---|
| rows a page shows | **1,867** |
| read by hand | 304 |
| right | **290** |
| wrong | 14 |
| **precision** | **95%** (95%: 92–97) |

Every band in the shipped set is at or above 90%. The deck is **1,091 cards** — 493 from the record, 401 from
our own finds, 197 famous — and every one of them is written rather than lifted from a database field.

### A guard that can now fire in both directions

`queue._overruled` exists because the verifier is let past the band gate on a 98% average, and an average that
clears a bar does not license every part of it. A band is overruled once at least 20 of ITS OWN SHIPPED rows
have been read and fewer than 90% hold. It is computed from the labels, so it switches itself off when reading
clears a band and on when a shipping band starts failing. Under the settled rule it currently names nothing —
but it named `reference_scan/medium` for the twenty minutes when the convention was the other one, which is the
demonstration that it works.

## 2026-09-22 · Going to get the result where the abstract does not report it

2,448 psychology finds — nearly 60% — could not become a card because nothing we held said how the replication
turned out. It was the largest loss in the funnel by a wide margin and had been written off twice, correctly
both times: reading the abstract harder does not work, because the abstract describes what the study DID.

The result exists. It is somewhere else. `pipeline fulltext` goes and gets it and `pipeline reread` reads it.

| where | finds with text | usable yes/no outcome | rate |
|---|---|---|---|
| OSF wikis and descriptions | 867 | 49 | **6%** |
| Europe PMC Results sections and abstracts | 236 | 143 | **61%** |
| | **1,103** | **192** | 17% |

OSF was the source I expected to carry this and it barely does. 11 of 12 plain OSF projects have a wiki and 98%
of the deposits yielded some text, but the text is a materials list, an ethics statement, a folder description,
or a plan written before the data existed — 525 of these are project folders and 141 are registrations. Europe
PMC is a tenth the size and produced three times as many answers, because a Results section is a result.

Europe PMC also filled a second gap: 183 of the finds it covered had **no abstract anywhere else**, and an
abstract that states the outcome makes a find usable without any full text at all.

### The quote check, which is not optional here

Every answer must carry a verbatim sentence from the text it was read from, and the sentence is checked against
that text before the answer is kept. On this population "the text does not say" is the right answer **72%** of
the time, which is exactly the situation where a model produces something plausible instead. 3 answers of 1,103
were thrown away for a quote that was not in the source.

### Read by hand

Fifteen of the new outcomes drawn at random, each checked against its quote: **15 right**. Labels are in
`outcome_audit.csv`. Two are indirect and worth naming — a replication reporting the same NULL as the original
("as in the previous study, there were no significant differences") is recorded as a successful replication,
which is correct and is the kind of case a careless reader gets backwards.

| | |
|---|---|
| finds with a yes/no outcome | 1,746 → **1,923** |
| read from the abstract | 1,746 |
| read from an OSF wiki | 48 |
| read from Europe PMC | 129 |
| clearing every gate to be a card | 522 → **583** |
| deck | 1,091 → **1,132** cards |

### What is left in that pile

1,135 of the silent finds have a DOI and are not in Europe PMC. About 27% of those are open access somewhere
else, which is roughly 300 papers behind a PDF rather than an API. Given Europe PMC's 61% yield, that is worth
perhaps 180 more outcomes and needs a PDF parser, which this project does not have. The rest are paywalled and
are not reachable at all.

---

## 2026-09-22 (later) · Reading the rows the verifier admits, and what a second pairing did to the label file

`pipeline verify` took the shipped pool from 600 rows to 1,565 by judging rows instead of bands, and the price
of that was stated at the time: its 98% is an average over every band, and an average that clears a bar does
not license every part of it. **By this morning 1,858 of the 1,866 rows a page could show were admitted by the
verifier rather than by any band rule**, and in the two bands with the worst priors nobody had read a single
shipped row — `openalex_author_year` low, measured at 17–35% as a band, had 2 of its 136 shipped rows read, and
`library_author_year` low, measured at 12–33%, had 1 of 70. `queue._overruled` exists to catch exactly this and
could not fire, because it needs 20 reads of a band's own shipped rows and had nowhere near that.

205 links read, five batches in parallel, each reader given the band's known failure shapes and told that
`unclear` is an answer rather than a hedge:

| band, shipped rows only | right | wrong | unclear | precision |
|---|---|---|---|---|
| `openalex_author_year` low | 37 | 1 | 2 | **97%** |
| `library_author_year` low | 38 | 2 | 0 | **95%** |
| `reference_scan` high | 37 | 2 | 1 | **95%** |
| `reference_scan` low | 36 | 4 | 0 | 90% |

**The verifier holds where it was least likely to.** In the two bands this project has called "not weak, wrong"
— gallium phosphide matched to marital adjustment, protein structures to smoking — the rows it confirms read
97% and 95%. That is the open risk of the whole per-row design, and it is now measured rather than assumed.

**And the guard fired on its own — then fired the other way.** Pooled with earlier reads, `reference_scan`
low's shipped rows first stood at 51 right and 6 wrong: **89.5%**, a hair under the bar, so `_overruled` named
it and its 282 rows came off the pages. 89.5% against 90% at n=57 is not a real difference, so 40 more were
read rather than argued about, and **they cleared it: 89 right of 97, 92% (85–96)**, and the rows are back.

**The same 40-read treatment condemned the band next door.** `reference_scan` medium had been the safer of the
two all day, and it is not: **78 right of 89, 88% (79–93)**, so it is overruled and **339 rows left the
pages**. Both bands sat at "exactly 90%" in the previous session's reading, and the only thing that separated
them was reading eighty more. `reference_scan` high moved up too, to 65 right of 68.

Which is the argument for the whole mechanism rather than for any of these numbers: two bands that looked
identical at n≈50 are 92% and 88% at n≈95, the gate moved twice in one evening without anybody editing a list,
and the band a reader would have bet on was the one that failed.

### The paper the matcher ranked second, settled

The 180 confirmed runner-ups were left "held back, ~36 cards turn on it, read more of them". **45 more read: 32
right, 8 wrong, 5 unclear.** With the 18 from 2026-09-21 that is **46 right of 58 — 79% (95%: 67–88%)**. The
top of the interval is below the bar, so this is no longer an open question: the second choices do not ship,
and `load.merged_links` should not merge them. All four failure shapes named in September turned up again in
the new reads — the companion paper on women when the replication is of the one on men, a theoretical critique
of an instrument instead of the study that used it, a review of a concept instead of its source study, and the
wrong paper by the right author.

### A judgement about a pairing has to record the pairing — including in the KEY

This file has said three times that a label must record which paper it judged, and `matched_to` was added as a
column to say so. The column was not enough. `audit.add` still replaced labels **by find id**, and a find has
two pairings worth judging: the paper the matcher chose and the paper it ranked second. Recording the 45
runner-up labels therefore **deleted six band labels**, five of them `wrong` verdicts that were holding weak
bands down, and the gate moved with nothing in the file to say why. The key is now `(find, paper)`, the
displaced labels are restored, and `audit.index`/`audit.label_for` pick the label that judged the pairing in
force, falling back to an older label that never recorded one.

This is the same failure as the verdict cache keyed on the find alone, one layer up. It was invisible while
every find had exactly one pairing, and appeared the moment one had two.

### Two places the gate had quietly been copied instead of asked

- `outcomes.PAGE_GRADE` was a hand-maintained set of five bands with a comment saying it was "kept in step with
  `queue.TRUSTED_LINKS`". It was not: it still named `cited by this paper/high`, a band renamed in September; it
  never gained `openalex_author_year/medium`; and it predated `pipeline verify` entirely, so it judged by band
  while the build judged by row. `outcomes --pool page` was scoring a population no page had shown for a day.
  It now asks `queue._link_trusted`, as `originals._shows` already did.
- **The link gate is computed from the PREVIOUS build's `candidates.json`.** So the first build after new
  labels gates on the bands as they stood before them and the next build disagrees with it. That reported a
  deck of 1,151 which the following build, with nothing changed in between, put at 1,096. Worse, a build that
  fails the count-drop check writes nothing, so every measurement taken from `candidates.json` afterwards
  describes a state that predates the work. `audit.candidates()` now prints one line on stderr when the label
  files are newer than the build it is reading. Build twice after recording labels, or read the second number.

### What a page shows, all of it

| | |
|---|---|
| rows a page shows | **1,550** |
| read by hand | 461 |
| right | **427** |
| wrong | 21 |
| unclear (set aside) | 13 |
| **precision** | **95%** (95%: 93–97) |

The deck is **1,060 cards** — 493 from the record, 370 from our own finds, 197 famous. Down from 1,132 at the
start of the day, and the whole of that fall is `reference_scan` medium leaving the pages on its own
measurement. 285 links were read to get here and every one of them is in `original_audit.csv`.

## 2026-09-22 (later) · The PDF route, built and measured

1,135 silent finds had a DOI and no full text in Europe PMC, about 300 of them open access as PDFs, worth
"perhaps 180 more outcomes" against Europe PMC's 61% yield. That estimate was too generous, and the route is
still worth having.

Nothing new had to be fetched to find the candidates: discovery cached each work's whole OpenAlex record, and
`primary_location` carries `is_oa` and `pdf_url`, so `fulltext.oa_pdf_urls()` answers "which of these can we
read" from disk at no cost. 144 silent finds had a PDF and no text.

| | finds | |
|---|---|---|
| open-access PDF available | 144 | |
| a Results section extracted | **83** | 58% |
| publisher refused the request (HTTP error) | 43 | 30% |
| a landing page served instead of the file | 8 | |
| no Results section and too long to take whole | 6 | |
| no text layer at all | 1 | |

**The 30% refusal rate is the route's real limit, not the scanning.** Only one PDF in 144 had no text layer.

Reading the 83 cost **$0.054** and produced **39 usable yes/no outcomes — 47%**, against Europe PMC's 61% and
OSF's 6%. 37 reach a candidate, 25 reach the card pool, and 4 clear every gate a card has to clear.

Two design decisions were made by measurement rather than by taste, and both went against the obvious choice:

- **The garbled-scan guard was wrong and was deleted.** Counting common English words separates prose from OCR
  debris in principle; measured on the 1971 *Psychonomic Science* scan that motivated it, the guard scored it
  identically to a clean modern PDF — and that paper's Results section extracts perfectly readable prose
  reporting `F = 2.72, df = 5/110`. The check would have thrown away a usable result to protect against a
  header nobody reads. What actually protects the answer is the quote check that already exists: unreadable
  text yields no answer rather than a wrong one.
- **A short note has no headings, and the fallback has to be measured in pages.** "Effects of irrelevant colors
  on reading of color names: A controlled replication" never writes the word "Results" and yielded nothing
  until a whole-note fallback existed. A character budget generous enough to admit it — it extracts 17,600
  characters from three pages — would also admit half the theses in the pile, so the test is `pages <= 4`. Both
  papers that forced these decisions ended up producing usable outcomes.

A third of the PDF fetches were spent on finds that already carried a `mixed` verdict from their abstract:
`fulltext._silent()` takes anything without a binary outcome, but the queue never lets a reread override the
screen, so those reads could not be used. Cheap here, worth narrowing before the route is widened.

### Reading a Results section is not reading an abstract, and it fails differently

The 94% outcome figure was measured on abstracts and does not carry here, so 25 of the PDF-derived outcomes
were read. **22 of 25 agreed** — too few to quote as a rate, and the three disagreements are worth more than
the ratio:

- a replication reporting the **same null as the original** ("in accord with those reported by Pechacek et
  al.: the males studied were incapable of recognizing their mirrored images") was called `failed`. It is a
  successful replication. This is the one trap the project already knew about, and full text walks into it more
  readily than an abstract does, because the discussion dwells on the negative finding before drawing the
  comparison;
- an **editor's note explaining that the article is satirical** was read as a failed replication, with the
  paper's own title quoted as the evidence;
- and one Results section **belonged to a different paper altogether**.

That last one is a defect in the route, not in the reading. Mid-century journals printed several one-page
papers per sheet, so a publisher's PDF for one DOI can contain the next article too, and the extractor returned
a fluent, quotable Results section about alternating-case letters for a paper on reward magnitude and reaction
time. **The quote check cannot catch this**: the quote really is in the text it was given. The guard that does
is weak on purpose — at least one content word of the paper's own title must appear somewhere in the extracted
text. A stronger test was tried and rejected on the evidence: "The intermittent punishment effect: A
replication with improved controls" shares 20% of its title with a section reading "IP Ss showed a marked
increase in latency", and a maternal-rations paper 22% with one about "pups reared by Purina-fed dams". Both
are correct and both would have been thrown away.

A second defect fell out of the same reading: the heading branch had no minimum length, so one journal's PDF
extracted to the eighteen characters "Results Discussion" — its own table of contents — and that was carried
forward as text a model was asked to read. Both branches now take the same 500-character floor. The two
affected answers have been retracted along with their text.

---

## 2026-09-22 (later still) · Reading stopped being the audit and became the decision

Every number in this file above was produced the same way: read a sample of a band, and if the band clears 90%,
every row in it ships. That design assumes reading is scarce. It was, when a person did it. It is not now — six
readers did 285 careful reads in about half an hour for no API spend at all — and the project had not noticed
that its central constraint had gone.

The consequence was visible and unargued. `reference_scan/medium` is 88% right, so gating it by band threw away
roughly 298 good rows in order to exclude roughly 40 bad ones. Nobody chose that trade; it fell out of an
instrument built for a scarcer world.

**So a label now decides its own row.** `queue._link_trusted` asks, in order: what did a reader say about this
exact pairing, then what did `pipeline verify` say, then what does the band average say. Until now the reading
was used only to score bands, and the band score was then allowed to overrule the reading on the very row it
was made about — a row read as `right` was dropped whenever its band was overruled, and a row read as `wrong`
stayed on the page whenever its band held up. 621 rows carry such a label today.

### But first, is the reader an instrument?

Asserting that would be the exact mistake this file exists to record, so it was measured the way `pipeline
verify` was measured: against labels made earlier, by different readers, for a different purpose.

90 links that already carried a label from a previous session were drawn **45 known-right and 45 known-wrong**,
interleaved so the order leaked nothing, and given to two fresh readers who could see neither the prior labels
nor each other.

| | reader A | reader B |
|---|---|---|
| calls a **good** link right | 44/45 = 98% | 44/45 = 98% |
| calls a **bad** link right | 4/44 = 9% | 8/45 = 18% |
| of the links it **rejects**, the prior reader agreed | 38/39 = 97% | 36/37 = 97% |
| of the links it **confirms**, the prior reader agreed | 44/48 = 92% | 44/52 = 85% |

Two readers on the same 90 cases agreed on 84 — **94%, Cohen's κ = 0.89** — and every disagreement was one
reader being more permissive than the other, never right against wrong.

**And then the sample balance had to be undone, because it is not the population.** A 50/50 draw was chosen so
that the bad links would be numerous enough to measure; it also makes confirmation look far worse than it is,
because a confirmation on a balanced sample is competing against 45 bad links rather than the 5 it would meet
in the real pool. The per-class rates are the transferable quantities, and the unread rows on pages are about
95% right:

| base rate of the population read | a confirmation is right | a rejection is right |
|---|---|---|
| 50% (the calibration sample) | 85–92% | 98% |
| 82% (all linked finds) | 96–98% | 90–91% |
| **95% (the unread rows on pages)** | **99%** | **68–70%** |

So on the rows that actually need reading, a confirmation is right about 99 times in 100 — comfortably past the
90% bar the pages use — and a rejection is right about 7 times in 10, which means each rejection removes about
0.7 wrong rows and 0.3 right ones. That is the same trade `pipeline verify`'s rejections already make, and it
raises precision at a small cost in recall.

The number that would have been quoted without this correction is 85%, and it would have closed a route that
works. It is the third time in this file that a measurement taken on the wrong population nearly did that.

### The scoreboard had to change too

"Precision of the rows a page shows" is now a tautology: a read row ships only if it was read as `right`, so the
answer is 100% and means nothing. `originals --score --pool page` no longer prints it. What it prints instead is
the honest question — how much of what ships has actually been read, and how wrong the rest is likely to be:

```
792 of 1572 rows were read one at a time and are decided by that reading; 780 still rest on their band
expected wrong rows among them: about 18, so roughly 99% of this pool is right
```

That estimate has to be conditioned on **both** the band and the route that admitted the row. Estimating an
unread verifier-confirmed row from every read row in its band mixes in rows the verifier rejected — which never
ship and are disproportionately wrong — and puts the figure at 8.4% where the matched populations put it at
3.3%. Same error, one more time, in a number I had just written.

Conditioning that way also surfaced the weakest thing on the site: rows admitted by the **band rule alone**,
where the verifier did not confirm them, read 4 right of 7 in two separate bands. They are 2% of what ships and
about a quarter of its expected error.

### Reading is now a command, and the rubric is one file

Six readers on 2026-09-22 each got a hand-written variant of the rubric, which is a reliability problem the
moment a label decides a row rather than contributing to an average. [`docs/READING_RUBRIC.md`](READING_RUBRIC.md)
is now the one copy, and `pipeline originals --batches N --size M` writes batch files with it at the top.

The draw changed with the purpose. A stratified sample spreads effort evenly so every band gets measured;
batches are ordered by **expected error instead** — an unread row's chance of being wrong, estimated from the
read rows sharing its band *and* its admission route — so the worst rows are read first. Measuring a band
evenly is what you do when the sample is the product. It is not what you do when the reading is.

### 320 rows read worst-first, and what the ordering found

The first eight batches went out ordered by expected error. The ordering is the result: **batches 1–5 found 46
wrong links; batches 7 and 8 found none at all in 80 rows.** A stratified sample of the same 320 rows would
have found roughly a third as many.

| batch | mostly | right | wrong | unclear |
|---|---|---|---|---|
| page-01 | `reference_scan/high`, admitted by band trust alone | 19 | **20** | 1 |
| page-02 | `reference_scan/low` | 34 | 5 | 1 |
| page-03 | `reference_scan/low` | 32 | 7 | 1 |
| page-04 | `reference_scan/low` | 32 | 7 | 1 |
| page-05 | `reference_scan/low` | 30 | 7 | 3 |
| page-06 | `library_author_year/medium` | 38 | 2 | 0 |
| page-07 | `openalex_author_year/high` | 40 | 0 | 0 |
| page-08 | `openalex_author_year/high` | 40 | 0 | 0 |

### The worst thing on the site was a fallback nobody had measured

Batch 01 was half wrong, and it was not a band that failed. It was a **route**: rows whose band is trusted but
which `pipeline verify` had declined to confirm. `_link_trusted` fell back to the band rule for those, and the
band rule said yes.

Read out across the whole pool, that fallback is indefensible:

| what the verifier said | a reader agrees | n |
|---|---|---|
| `right` | **93%** | 814 |
| `unclear` | 41% | 44 |
| `wrong` | 29% | 69 |
| never judged | 0% | 3 |

And inside `reference_scan/high` — a band measured at 96% and trusted — the verifier-declined rows read **6
right of 24**. A band's 90% is an average dominated by the rows the verifier confirmed; the rows it declined
are a different population, and the band score was being carried across to them. That is the same error as
`link --check`, as the reference scan measured through a third of each bibliography, and as the runner-ups
judged by a calibration built on first choices. It keeps arriving in new clothes.

**So the band rule is no longer an admission route.** A link appears beside a verdict only if a reader
confirmed it or the verifier confirmed it. It cost 2 rows to remove, because the prioritised reading had
already found and dropped almost all of them. The band rule keeps the two jobs it is good at: ordering the
matchers in `load.merged_links`, and standing in for unread rows when the scorer estimates how much of the pool
is still a guess.

### Where the pages stand at the end of the day

| | morning | evening |
|---|---|---|
| rows a page shows | 1,866 | 1,572 |
| of those, read one at a time | 3 | **792** |
| expected wrong rows | ~93 (5%) | **~18 (1%)** |

The pool is smaller and four times cleaner. 605 links were read today, all of them free.
