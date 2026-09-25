# Handoff — state as of 2026-09-22


## Update: 2026-09-24 psychology search on the VM

The owner scoped this run to psychology in /root/retested. Social Sciences and Neuroscience were not screened; the site was not published.

- DeepSeek screened all 2,107 previously unscreened low-tier Psychology keyword finds with a 200-case pilot first. It marked 140 as psychology replications. Source review accepted 72 candidate records, rejected 34, and left 34 unclear. The accepted records yielded 58 net new review-queue entries after duplicate deposits were collapsed. The queue is 7,391 candidates; these remain review candidates, not FORRT-validated attempts.
- Cached API usage for the 2,107 calls was 2,043,639 cached input tokens, 538,057 uncached input tokens, and 177,735 output tokens. At DeepSeek's published off-peak V4.1 Flash rates this is about $0.1935. The pipeline's older conservative cap meter showed $1.37; the run stayed within the $0.20 pilot and $1.50 remainder caps.
- data/curated/low_tier_review.csv records all 140 decisions. The loader admits only accepted low-tier rows; future triage and link runs cannot promote unreviewed low-tier guesses automatically.
- data/curated/original_links.csv has 52 source-backed exact find-to-original citations, 51 of which survive queue deduplication. The 51 built pairs are labelled right with source and paper recorded in original_audit.csv. Several displace wrong machine-picked originals, including sight-over-sound and the cross-norm effect.
- Four replication articles retest multiple originals. data/curated/multi_original_links.csv records all 17 exact original papers and the queue shows them as a list instead of forcing one primary DOI. One additional two-study weight paper is among these.
- After the labels, the data build ran twice as required by the prior-build link gate. It settled at 1,068 game cards and 232 pending candidates on 137 finding pages; the Astro site built 1,790 pages. No publication or push occurred.
- The free pipeline osf-documents sweep covered all 159 currently unlinked OSF psychology finds. Public files existed for 91; 56 yielded extractable PDF/DOCX text, 27 had DOI mentions, and 13 rows had document errors. The source-located evidence index is cached at data/discovery/osf_document_evidence.json; it never auto-links a bibliography mention.

## 1. What exists and works

**Pipeline (`pipeline/`)** turns FORRT's data into a site bundle in ~2 s on the VM:
906 named effects · 3,424 findings (one per original paper) · 3,879 attempts (3,590 replications, 289 reproductions;
1,024 known only from the legacy FReD 2.4.1 file) · 1,060 game cards · 2,425 review-queue candidates from FORRT's own
flora-extractor. Validation fails the build on unreachable FLoRA pairs, ID collisions, game-answer leakage,
count drops > 1%, secrets, and stray root files. Output is identical on the laptop and the VM.

**Site (`site/`, Astro 7 + Preact)**: ~1,810 static pages, built in ~3 s on the VM.
Home ("the record" waffle chart + three findings) · effect pages (verdict stamp, attempt tally, three lenses:
replicators' verdicts / pooled effect sizes + FORRT's seven criteria / design; forest plot; citation curve; ledger;
curated-list box) · finding pages · effects index with filters · "Did it replicate?" game (daily ten, endless,
famous; probability slider; Brier points; calibration chart; answers fetched only after lock-in) · review queue
(two sources; accept/correct/reject, CSV export in FLoRA columns) · "not in the record yet" boxes on effect and
finding pages · the record (rates with intervals) · Graveyard / Survivors /
Contested · Methods (sources, rules, full FORRT citation). Not deployed yet.

Headline numbers from FORRT data (on the site): 42% of 2,609 replications with a verdict succeeded; originals with
p ≤ .005 replicated 64% vs 30% for .005 < p < .05; teams sharing an author with the original 70% vs independent 39%;
median replication found 42% of the original effect size.

## 2. Discovery: finding replications FORRT has not recorded (done 2026-09-19)

"Known to FORRT" = in FLoRA/FReD/legacy **or** in any flora-extractor candidate file **or** flora-validation exports.

- **Coverage check** (`data/build/coverage.json`): of FORRT's 1,850 known replication papers, 98% are in OpenAlex,
  66% have "replic…" in the title, only 52% are tagged Psychology → a "psychology + replication in title" search can
  see only **35%** of known replications. The untagged half sits in Social Sciences, Neuroscience, Medicine,
  Economics, Business, Decision Sciences.
- **Keyword search** (`discovered-keyword.json`): 11,226 psychology-tagged works with "replication" in the title;
  2,903 known to FORRT; **7,990 new** (3,075 high tier). Cost $0.05.
- **Citation search** (`discovered-cites.json`): works citing any of our 3,395 resolvable originals and mentioning
  replication: 31,570; it rediscovered **61%** of FORRT's known pairs (2,450 / 3,988) — a recall check; 28,588 new,
  889 high tier (523 not found by the keyword search). Cost $0.21.
- **DeepSeek triage** of the 3,598 high-tier candidates (`triaged.json`, cache `data/cache/triage/deepseek-v4-flash/t1/`),
  ~$1.58 worst-case: replication 2,472 (**psychology 2,003**, other behavioural 377, non-behavioural 92),
  reproduction 19, registration-only 201, psychometric 176, about-replication 331, not replication 397, error 2.
  Psychology outcomes: successful 446, failed 246, mixed 198, not reported 1,113.
  Pilot vs 70 hand labels: 53/70 agree; most disagreements are "registration_only" and field-scope calls; ~2–3
  genuine false positives per 70. **Estimate: ~1,900 psychology replications absent from FORRT** (FORRT's curated
  list has ~1,850 replication papers).
- Linkage of those 2,003 to their original: 123 linked to an original in our library (via citation), 1,061 have the
  original named by DeepSeek (authors + year) but not yet resolved to a DOI, 819 unknown. 833 have a verbatim verdict
  quote that was mechanically checked against the abstract. 1,419 have a DOI; 690 are preprints (many OSF/CREP
  student replications — real but unpublished; show as a separate evidence tier).

## 2b. Originals resolved and finds put on the site (done 2026-09-19)

**Linking** (`pipeline/link.py`, `python -m pipeline link`, results in `data/discovery/links.json`).
1,063 psychology replications named an original with no DOI. **751 are now resolved** — 327 free against the
originals already in the wiki, 424 by one cached OpenAlex lookup each (578 calls, **$0.578**). By confidence:
179 high, 154 medium, 418 low. 329 point at an original that already has a page. The remaining 312 stay unresolved
rather than guessed. Every link stores its method, the runner-up, author/year/description agreement and a band.

Accuracy was measured, not assumed: `python -m pipeline link --check` hides the DOI on the 107 psychology
replications the citation graph had already resolved and re-derives it from (author, year, description). The
library pass gets **92%** right (100% of its high-confidence links); on a 40-case paid probe the OpenAlex pass gets
**89%** (100% at high confidence). Getting there needed two fixes worth keeping: plain content-word overlap instead
of rapidfuzz's token_set_ratio (which sat near .5 for right and wrong alike), and a topical gate on the OpenAlex
pass, without which author+year alone proposed retinal-surgery and Raman-spectroscopy papers as psychology
originals (68% → 89%).

**Site.** The queue now carries both sources, labelled and filterable: FORRT's extractor 2,425 rows, Found by
Retested 2,588 (2,013 psychology replications, 383 other behavioural, 192 registered protocols; 923 preprints).
914 have an original, 492 of them one with a page here. CSV export is unchanged in FLoRA's columns and names the
source. **453 of our finds now appear on 285 finding pages and 119 effect pages** (270 built pages) in a dashed
"Not in the record yet · unverified, pending review" box that states the link method and confidence. Nothing there
touches a verdict, a tally, a figure or a rate: every headline count is unchanged. FORRT's own extractor candidates
stay queue-only — putting someone else's unreviewed list on a page is their editorial call.

Two things were fixed while doing this. Discovery output used to be written to `data/build/`, which every build
wipes first — that is how `discovered-*.json` and `triaged.json` were lost; they now live in `data/discovery/` and
were rebuilt from cache for $0. And `pipeline link` now writes its results when OpenAlex's daily budget runs out
instead of exiting with nothing.

## 2c. Medium tier screened, prompt rewritten, links audited (2026-09-19)

**The screening prompt was the bottleneck, not DeepSeek.** t1 was written for papers that announce themselves as
replications, and on the medium tier it called anything adjacent a replication: a study replicating its own Study 1,
a new moderator on an old effect, a bare theory test, a paper that merely cited one of the originals we fed it.
Naming those four traps and fixing what counts as a "registration" (t3) beat t1 on the owner's 70 hand labels —
86% precision at the same recall — and lifted the medium tier from 39% to 50%. `pipeline/triage.py` carries the
version-by-version table. A new prompt version costs a full pass; the cache is keyed by model and version.

**Full run, t3, 12,462 candidates: real spend $2.13** (the $8.51 printed is worst-case pricing; prompt caching makes
the real figure much lower). 5,120 replications + 48 reproductions, of which **4,199 are psychology** — against
2,004 from the high tier alone under t1. 6,284 were rejected as not replications.

**Linking.** 1,748 psychology replications named an original with no DOI; 1,002 resolved (452 free against the wiki,
550 via OpenAlex), high tier first. The run stopped at its $0.20 cap with 364 candidates not yet attempted — finish
them after the daily OpenAlex allowance resets; cached pages make the re-run nearly free.

**A 65-link hand audit changed what the site shows: [`LINK_AUDIT_20260919.md`](LINK_AUDIT_20260919.md).** 53% of the
links being shown on effect pages pointed at the wrong original — a replication of Carlson et al. (2020) on climate
attention linked to "Good deeds gone bad: lay theories of altruism", a Jones et al. (2002) pitch-perception
replication linked to a paper on treating stuttering in children. `link --check` had said 92% because it only
measures papers whose original the citation graph had already found: the easy half, where the true original is in
the library. On the real population it usually is not, and a surname-and-year match returns an impostor instead of
nothing. Accuracy by source, read one by one: library high/medium 24/25, OpenAlex high 10/11, citation-list picks
6/11, OpenAlex medium 2/4, library low 5/14. Pages now take only the first two; everything else waits in the queue.
**Treat any `--check` number as an upper bound and sample the shipped rows instead.**

**39 finds are confirmed real and confirmed missing**, not estimated: read by hand, then checked against every
FORRT file. The absence check behind the headline was too narrow — it missed FLoRA's `alt_identifier_r`/`url_r`
columns and flora-validation's dated extractor snapshots — and now sweeps all 9,967 replication identifiers FORRT
holds, which dropped 345 candidates. 974 psychology finds have no DOI and cannot be checked this way; their
absence rests on title matching and is weaker.

**Where that leaves the site.** Queue 7,224 candidates: FORRT's extractor 2,425, ours 4,799 (3,942 psychology
replications, 739 other behavioural, 188 registered protocols; 2,483 high tier, 2,661 medium; 1,288 preprints).
1,460 have an original, 912 of them one with a page here. 151 rows appear on 82 finding pages and their effect
pages, down from 453 before the audit, and the build now refuses to put an unaudited link on a page.

## 2d. 2026-09-21: linking, rigour signals, and what the finds are allowed to claim

**Linking, 1,002 → 3,037 of 3,607 psychology finds (84%).** Three routes, each measured before it was trusted:
the library and OpenAlex author+year passes, and `pipeline references`, which scores a find's description against
the ~35 papers it cites. Searching OpenAlex for a description finds the original 17% of the time; its own
reference list contains it 84% of the time. A title fallback covers finds OpenAlex holds as a bare title.
Total OpenAlex spend for all of it: about $0.45.

**Rigour signals FORRT codes for 4–10% of entries, derived here instead.** `pipeline osf` asks OSF outright
whether a find is a registration (220 are). 430 finds declare direct/close/conceptual in their own words.
Independence is computed from both author lists — 2,385 independent, 687 sharing an author — decided by OpenAlex
author id where possible, because the median surname in the corpus appears once and "chen" appears 832 times.

**`pipeline authors` now fetches the whole original record**, not just authorships. Originals had a title 15% of
the time; now 100%, with an abstract for 65%. Four finds replicate a RETRACTED paper, Gino's "Evil Genius" among
them.

**343 repeat deposits collapsed** — OSF version suffixes, preprint-plus-published, re-minted Zenodo. One study had
been deposited seven times, and the CSV export would have sent FORRT all seven. 31 groups had been matched to
different originals by different copies and carry a warning.

**The queue now says what accepting a row does**: 571 candidates would change a verdict on 432 findings. The CSV
export uses FLoRA's real column names (one was previously misnamed) plus our derived columns.

**New page, `/uncounted/`**, presenting the finds as evidence rather than a backlog, walled off from every counted
figure. FORRT's strongest pattern reproduces in it independently: 63.5% success when the team shares an author
against 39.2% when not, against their 70/38.

**Accuracy, all measured by reading, none asserted:**

| judgement | accuracy | n |
|---|---|---|
| is it a replication (high tier / medium tier) | 86% / 50% | 70 owner labels / 40 Claude labels |
| right original: library high·med / OpenAlex high / reference_scan high | 96% / 91% / 89% | 25 / 11 / 36 |
| right original: citation pick / OpenAlex med / library low | 55% / 50% / 36% | 11 / 4 / 14 |
| **outcome read correctly: successful / failed / mixed** | **93% / 92% / 82%** | 60 / 60 / 22 |

Superseded on 2026-09-21: an earlier n=20 read put outcome accuracy at ~90% and said the error runs one way,
towards success. It does not. See section 2e.

## 2e. 2026-09-21: the verdicts themselves, measured at n=144

Every accuracy figure before this one was about *linking*. Whether the model read the **outcome** correctly had
been measured once, on 20 cases, and that read said failures were right 9/9 and successes 9/11 — an error running
one way, towards success. 144 more cases say it does not.

**`python -m pipeline outcomes`** owns this measurement now. `--sample N` draws a deterministic stratified sample
and prints each case as the replication's own full abstract plus the quote the verdict rests on; `--record` takes
the labels back on stdin; `--score` reports per-verdict precision with Wilson intervals. Labels live in
`data/curated/outcome_audit.csv`, keyed by candidate id, so they survive rebuilds and the next session samples
what is unlabelled instead of starting again — which is what this session had to do, because the 20 earlier rows
were never written down.

| the model said | right | precision | 95% interval |
|---|---|---|---|
| successful | 94/100 | **94%** | 88–97% |
| failed | 93/100 | **93%** | 86–97% |
| mixed | 18/22 | 82% | 62–93% |

(Extended to n=224 later the same day by eleven parallel readers; the figures did not move.)

**One case in 200 was read as the opposite of what the paper reports, and twelve have no binary answer at all.**
The error is overwhelmingly a missing answer rather than a wrong one — an abstract that settles nothing, called
either way, and falling on both sides. For a scored card that is the difference between a card that cheats the
player and a card that should never have been dealt.

**And the model's own confidence separates the unusable ones.** Below `outcome_confidence` 0.8 a verdict is
sound 23 times in 29 (79%); at 0.8 and above, 164 in 171 (**96%**). Dropping the low band costs 16% of the card
pool — 233 of 1,442 rows. That is a free quality gate for the deck, and `outcomes --score` re-derives it from
the labels rather than hard-coding it.

Three things follow, and all three overturn something the handoff said yesterday:

- **`/uncounted/` was blaming the wrong thing.** Re-weighting every verdict on that page by these labels moves it
  from 47.7% to 49.3% — further from the curated record's 41.7%, not closer. The page no longer offers model
  error as the explanation, and it now prints the audit numbers straight from the label file through
  `stats.uncounted().audit`, so the prose cannot drift from the measurement again.
- **The card pool's base rate is real.** At the deck's own grain — one card per original, dropping originals whose
  finds disagree — 1,322 cards at 62.9% successful, 62.7% after correction, against the existing deck's 53%. The
  gap is not a reading artefact.
- **Outcome reading is no longer a blocker on shipping these as cards.** The link is, and then the claim text
  (see 2f and 2g).

`docs/LINK_AUDIT_20260919.md` has the case-by-case detail, the nine mistakes named, and why the n=20 pattern was
noise rather than a direction.

## 2f. 2026-09-21: every link band read, the page gate handed to the measurement, eleven phantom papers removed

**Link accuracy decides a card as much as the verdict does** — the reveal names the original, and any written
claim would come from its abstract. `python -m pipeline originals` is the same instrument as `outcomes`, pointed
at the link; labels live in `data/curated/original_audit.csv`. **384 links read** — 146 by one reader, then a
band each by eleven parallel readers, with two bands read twice by independent readers who could not see the
first labels.

| band | read | | rows in the linked pool | on a page? |
|---|---|---|---|---|
| `library_author_year` high | 29/30 | **97%** | 45 | yes |
| `openalex_author_year` high | 31/33 | **94%** | 117 | yes |
| `library_author_year` medium | 30/32 | **94%** | 93 | yes |
| `openalex_author_year` medium | 30/33 | **91%** | 122 | yes, newly |
| `cited by this paper` | 72/84 | 86% | 307 | no |
| `reference_scan` high | 32/40 | 80% | 299 | no, removed |
| `reference_scan` medium | 28/44 | 64% | 463 | no |
| `openalex_author_year` low | 14/40 | 35% | 723 | no |
| `reference_scan` low | 10/40 | 25% | 682 | no |
| `library_author_year` low | 1/8 | 12% | 186 | no |

**The weak bands are not weak, they are wrong** — Dean (1966) on marital adjustment matched to the absorption-edge
spectrum of gallium phosphide, Nolan (1968) on smoking to a paper on protein structures. A recurring near-miss
worth someone's time: the right paper is often the **runner-up**, so the scorer ranks better than its own top-1.

**Three things the reading caught that a list had been getting wrong.** `cited by this paper` was reopened this
morning on 34 of 36 — a route closed in September on output from the retired t1 prompt — and then **reverted**
when 84 reads put it at 86%, short of the 90% bar. `reference_scan` high had been on pages since September on a
quoted 32/36 that nobody re-read; forty fresh cases put it at 80%, so it came off. `openalex_author_year` medium
had been excluded on 2 of 4; thirty-three reads put it at 91%, so it went on.

**So the gate is no longer a list.** `queue.TRUSTED_LINKS` is computed on every build from the label file: a band
qualifies at 20+ links read and 90%+ right — the rule this project stated in September, applied uniformly. Rows
shown beside a verdict: **110 on 64 finding pages**. Expect bands to move as reading accumulates.

**Reader agreement, since the reading is now the instrument.** Two blind readers of the same 25 `cited by this
paper` cases agreed on every one including all six they called wrong (κ = 1.00). On `reference_scan` medium they
agreed 26/30 (κ = 0.73), and every disagreement was *wrong* against *unclear*, never right against wrong.

**Eleven malformed DOIs folded.** The backlog's "95 papers share a normalised title" recovers nothing — 0 finds
point at a page-less twin — but underneath it were DOIs cut short upstream (`10.1016/j`, `10.1126/science.745568`)
splitting one study's record across two pages. Tversky and Kahneman's framing paper held seven attempts on one
page and a stranded eighth on the other; it now holds eight. A fold needs a strict-prefix DOI **and** the same
normalised title, and all twelve pairs were read before the rule was written.

## 2g. 2026-09-21: what the deck actually is

`python -m pipeline outcomes --deck` applies both audits, gate by gate:

| gate | finds | cards | successful |
|---|---|---|---|
| a binary verdict and a linked original | 1,442 | 1,322 | 63% |
| link in a band read at 90% or better | 113 | 110 | 62% |
| + outcome confidence 0.8 or higher | 110 | **107** | **62%** |
| + the original's abstract held, so a claim could be written | 85 | 83 | 64% |

**The deck that clears both measured bars is about 107 cards, not 1,323**, and 98 of them are originals FORRT
records no replication for at all — genuinely new. **The link gate is what costs, not the verdict gate**: 1,442
finds to 113. And the base rate stays near 62% against the existing deck's 53%, so these still belong in a deck
of their own; that gap is not a reading artefact.

The bar is a judgement and it is expensive, so `--deck` prices the bands just beneath it: `cited by this paper`
at 88% on the card pool would add 217 finds, `reference_scan` high at 71% would add 158. Anyone moving the bar
should move it deliberately.

**On the claim pass.** The costing of ~$3.50 was for the whole site. Over the 83 audited cards that hold the
original's abstract it is about **$0.03**. The instruction was to postpone it until everything achievable
without a model was done; a great deal now has been, and what stands between this work and a playable deck costs
three cents. Worth asking rather than assuming either way.

## 2h. 2026-09-22: the deck has real claims, and the finds are playable

The owner topped up DeepSeek, which answered the open question in 2g. Total spend for everything below: **$0.31**
against the ~$3.50 this work had been costed at.

**Every card in the deck was rewritten.** The deck had been dealing FReD's `description` column — "Main effect of
condition on the applicability of the insanity defense", a 400-character methods paragraph about conjugate
reinforcement schedules, one claim that ends in a comma because the comma is in the data. **689 of 749 cards now
carry a written claim and 685 a method line.** `pipeline/claims.py`, following D3 §8;
[`docs/CLAIMS_20260922.md`](CLAIMS_20260922.md) has the detail.

Four prompt versions, because reading the pilot myself was not enough: four reviewers each took one lens and the
fidelity lens called 14 of 24 non-ok. They found the writer inventing directions when FReD's result sentence was
an omnibus F, writing manipulation checks up as findings, reversing absences ("goats do not follow a human's
gaze" came back as "goats follow"), and hedging unevenly — which is a leak channel of its own, since a writer
hedges more when it doubts. **The root fix was not a prompt**: nobody had ever fetched the originals' abstracts.
OpenAlex serves them free and we held the identifiers — 387 of 501 for $0.001 and nine calls, and most of the
invention went with it.

**68 of our own finds are now playable cards, in a deck of their own.** A card is dealt only when the find clears
both hand-read audits, when every find on that original agrees, and when a claim could be written from the
original's abstract. They are a fourth mode rather than mixed in: they succeed more often than the counted
record, so shuffling them in would move the base rate a player calibrates against, and nobody has reviewed one.
The stamp says "unreviewed" and the reveal carries the whole provenance with a link into the queue.

**Then the deck was reviewed at scale and fixed again.** Six readers over 80 shipped cards put the previous
version at 15–20% serious fidelity errors and 29% would-not-deal on playability. Prompt c5 turns each named
defect into a rule (a prediction is not a result, a null is not an equivalence, a definition is not a finding, a
mismatched source is a refusal…), five of them as mechanical checks. Two of the defects were bugs here, not in
the writing: the leak filter matched bare "fail" and was killing clean claims while leaving garbled database
sentences in their place, and the `written` flag recorded whether a claim existed rather than whether it was
used, so the daily set was dealing fallbacks. **827 cards, 757 written**, and a hand-read of 16 fresh cards finds
14 clean. Roughly one in eight still reads like the paper rather than the player.

**The fairness test, which is now settled.** D3 §7 asks whether a model can guess the answer from the card
alone. Four blind guessers on a balanced 22-card pilot: 75% where they did not recognise the study (95% CI
62–85%), against 50% chance. All four explained it the same way — failures cluster at small samples — and **that
explanation is false**: successful cards have the larger median N, 132 against 112 in the pilot and 94 against 79
across the deck. The leak is real and its stated cause is wrong. **The control settles what it means**: the same
80 cards worded as the deck worded them *before* the rewrite leak at 69% (CI 62–75%) against 75% after. Heavily
overlapping — the deck already leaked at this rate, so the leak is the cards' design and content cues, which is
what a player is meant to reason from, and not the writing.

## 2i. 2026-09-22 (later): the verifier read where it was least likely to hold, and a PDF route

**285 links read by hand, and the open risk of the per-row design is closed.** `pipeline verify` had taken the
shipped pool from 600 rows to 1,565 by judging rows rather than bands, on a calibration of 98% averaged over
every band. By this morning **1,858 of the 1,866 rows a page could show were admitted by the verifier rather
than by any band rule**, and the two bands with the worst priors had 3 shipped rows read between them. Read
now: `openalex_author_year` low **97%** (37/38), `library_author_year` low **95%** (38/40), `reference_scan`
high **95%** (37/39), `reference_scan` low 90% (36/40). The verifier holds in the bands this project called
"not weak, wrong".

**The gate moved twice in one evening, and the band that failed is not the one anyone would have bet on.**
`reference_scan` low first fell to 89.5% and was overruled; 40 more reads cleared it at **92% (89/97)** and its
282 rows came back. The same treatment condemned `reference_scan` **medium — 88% (78/89)** — so it is overruled
and **339 rows left the pages**. Both bands sat at "exactly 90%" in the previous session; eighty more reads
separated them. `reference_scan` high rose to 96% and is trusted again. Nobody edited a list to make any of
this happen.

**The runner-ups are settled and they do not ship.** 45 more read (32 right, 8 wrong, 5 unclear); with the
earlier 18 that is **46 of 58 — 79%, 95% CI 67–88%**. The top of the interval is under the bar, so the ~36
cards that turned on this are decided: `load.merged_links` should not merge second choices.

**Deck 1,132 → 1,060** (493 record, 370 found, 197 famous). The whole fall is `reference_scan` medium leaving
the pages on its own measurement. What a page shows: **1,550 rows, 461 read, 95% right**.

**A PDF route exists.** `pipeline fulltext --pdf` finds open-access PDFs from OpenAlex records already cached,
fetches them, and extracts the Results section with `pypdf`. 144 silent finds had a PDF; **83 yielded a Results
section (58%)**; reading them cost **$0.054** and produced **39 usable outcomes (47%)**, against Europe PMC's
61%. **The limit is publishers refusing the request — 30% HTTP errors — not scanning: one PDF in 144 had no
text layer.** 4 finds cleared every card gate.

**The PDF route's own failure mode, found by reading 25 of its outcomes (22 agreed).** A mid-century journal
printed several papers per sheet, so one PDF can hold the next article too, and the extractor returned a
fluent, quotable Results section belonging to a different study. **The verbatim-quote check cannot catch this**
— the quote really is in the text it was given — so a weak guard was added: one content word of the paper's own
title must appear in the extracted text. A stronger version was tried and rejected because it threw away two
correct papers. Separately the heading branch had no minimum length, so one PDF extracted to the eighteen
characters "Results Discussion". Both answers retracted.

**Five defects found and fixed, all of the same family.** A label was keyed by find id, so recording the 45
runner-up labels **deleted six band labels** — a find has two pairings worth judging and the file could hold
only one; the key is now `(find, paper)`. `outcomes.PAGE_GRADE` was a stale hand-copy of the page gate naming a
band renamed in September, so `outcomes --pool page` scored a population no page had shown. And **the link gate
is computed from the previous build's `candidates.json`**, so the first build after new labels disagrees with
the next one — that reported a deck of 1,151 which the following build put at 1,096. `audit.candidates()` now
warns on stderr; build twice after recording labels.

**Spend: $0.06** — $0.054 reading PDFs, $0.006 writing 4 new claims. Balance $8.19. All hand-reading was free.

## 2j. 2026-09-22 (later still): reading became the decision procedure, not the audit

**The central instrument was built for a constraint that no longer exists.** Every accuracy number in this
project comes from reading a sample of a band and letting the band's score decide all its rows. That is what
you do when reading is scarce, and it was when a person did it. Six readers now do 285 careful reads in half an
hour for no API spend. Gating `reference_scan/medium` by its 88% band score discarded roughly 298 good rows to
exclude roughly 40 bad ones — a trade nobody chose, inherited from the scarcer world.

**So a hand label now decides its own row.** `queue._link_trusted` asks in order: what did a reader say about
this exact pairing, then `pipeline verify`, then the band average. Previously the reading was used only to score
bands and the band score then overruled the reading on the very row it was made about — a row read as `right`
was dropped if its band was overruled, and one read as `wrong` stayed on the page if its band held up. 621 rows
carry such a label. **Deck 1,060 → 1,073, page rows 229 → 235**, and more importantly 532 shipped rows are now
decided individually rather than by their band's average.

**The reader was calibrated before being trusted with that**, the same way `verify` was: 90 links already
carrying labels from earlier sessions, drawn 45 known-right and 45 known-wrong, given blind to two fresh
readers. They call a good link right 98% of the time and a bad link right 9–18% of the time; their rejections
matched the prior reader 97%; and two readers on the same 90 cases agreed 94%, **κ = 0.89**.

**The 50/50 balance then had to be undone, and this is the part worth remembering.** On that sample a
confirmation looks 85–92% right. Re-derived at the base rate of the rows that actually need reading (~95%
right), **a confirmation is 99% right and a rejection about 70% right**. The uncorrected 85% would have closed
a route that works — the third time in this project that a measurement taken on the wrong population nearly
did. A rejection removing ~0.7 bad rows per 0.3 good ones is the same trade `verify`'s rejections already make.

**The scoreboard changed with it.** "Precision of the rows a page shows" is now a tautology — a read row ships
only if it was read `right`. `originals --score --pool page` prints instead how much of what ships has been
read and how wrong the remainder is likely to be: currently **792 of 1,572 read, ~18 expected wrong, ~99%
right**. That estimate must be conditioned on the band *and* the admission route; conditioning on band alone
mixes in verifier-rejected rows that never ship and inflates it from 3.3% to 8.4%.

**320 rows were then read worst-first, and the ordering was the result**: batches 1–5 found 46 wrong links,
batches 7–8 found none in 80 rows. Batch 1 was half wrong — and it was not a band that failed but a **route**.
Rows whose band is trusted but which `verify` had DECLINED to confirm were admitted by the band-rule fallback.
Read out: a verifier-`right` link is right 93% (n=814), a verifier-`unclear` one 41% (n=44), and inside
`reference_scan/high` — trusted at 96% — the declined rows read 6 right of 24. **The band rule is no longer an
admission route**; a link ships only if a reader or the verifier confirmed it. Removing it cost 2 rows, because
the reading had already found the rest.

**Where the pages stand: 1,866 rows at ~95% this morning, 1,572 rows at ~99% tonight**, 792 of them read one at
a time. 605 links read today, all free.

**Reading is now a command.** [`docs/READING_RUBRIC.md`](READING_RUBRIC.md) is the single copy of the rubric —
six readers had each been given a hand-written variant, which is a reliability problem once a label decides a
row — and `pipeline originals --batches N --size M` writes batch files with it at the top, **ordered by
expected error** rather than stratified evenly. Measuring a band evenly is what you do when the sample is the
product; it is not what you do when the reading is.

## 2k. 2026-09-24: source-reviewed Psychology effects became finished pages

The owner's current priority is **named effect plus replication(s) pages that finish the pipeline**,
rather than a larger pending-review queue. The reviewed overlay in
`data/curated/promoted_pairs.json` had **85 exact original–replication pairs and 85 named
effects** (69 added today; 16 from the preceding pass). Each row has an original claim quote,
the replication's target and result quotes, source URLs, a verdict, and scope caveats. The
overlay creates counted attempts; machine-screened discoveries never promote themselves.

After two data builds, the site build, four tests, and an audit of all 39 pages in the latest batch,
the local record has **991 named effects, 514 with a linked attempt (356 with a coded replication result), 3,490 original
findings, 3,954 attempts, 3,665 replications, and 7,365 pending candidates**. Two of today's
new effect pages have multiple replication verdicts. Two previously linked pending candidates
were marked `wrong` for the *exact proposed original DOI* in `original_audit.csv`: the
retroactive-avoidance 2020 paper targets Maier et al. 2014 Experiment 4, and the 2023
broken-windows experiments directly target Keuschnigg and Wolbring 2015 Study 2.

For the next Psychology source-review wave, run `/tmp/retested_review_top200.py` to
regenerate the free 200-case packets from the current discovery cache. It writes
`/tmp/retested-review-top200-20260924.jsonl` and `.md`; promotions change eligibility. They are **leads, not finished effects**.
Review exact target, dates, original direction, replication result, and any changed sample
or contrast before adding a row. No paid DeepSeek calls were needed today ($0); do not
start a paid run outside the owner's off-peak/pilot/cap rules. Nothing was pushed or
published.

## 2l. 2026-09-24 17:12 UTC: measured bulk promotion throughput

The current owner metric is completed, source-reviewed **named effect + exact replication result** pages. Retested now has **306 reviewed pairs / 306 new effect pages**, up from 85 at commit `be85440`. The first 196 additions in this pass came from 310 strict source packets plus 34 broader packets; model decisions were leads only. The reviewers rejected mismatched contrasts, copied original predictions, reanalyses of the same sample, unverified result claims, and duplicate DOI versions. Each accepted row has an original result quote, replication target quote, replication outcome quote, and source URLs.

The data build was run twice and the static site build passed after each promotion wave. The latest 27 pages had 0 missing or mismatched effect/attempt/outcome/page checks. Current build: **1,212 named effects**, **735 with a linked attempt**, **577 with a coded replication result**, **3,669 findings**, **4,175 attempts**, **3,886 replications**, and **7,155 pending candidates**. The earlier figure of 514 was a count of effects with a linked attempt at an earlier build, not effects with a coded verdict.

Measured wall time from 16:32 to 17:12 UTC: **196 finished additions in 28 minutes** with three source readers working in parallel; two data builds take about 13 seconds and the site build about 5–6 seconds. This rate applies to pairs with available source text and must not be projected onto candidates with missing papers. The next source packet contained 54 inspectable pairs. A timed free retrieval of 365 missing original abstracts recovered 129 in 49 seconds; a separate 90-pair packet with exact result text is under review. This is the measured path into the larger missing-source pool. No site publication or push was done.

## 2m. 2026-09-24 17:51 UTC: 458 checked effect/replication pairs

The Psychology-only source review now has **458 exact original–replication pairs**
across **450 named Retested effect pages** (449 newly created effects; one joins
an existing effect). This is **373 more reviewed pairs than the 85 at commit
`be85440`**. The built site has **1,355 named effects** overall, **878 with a
linked attempt**, **727 with a coded replication result**, **3,796 findings**,
**4,327 attempts**, **4,038 replications**, and **7,019 pending candidates**.
Pending candidates are leads; their count is not a promise of valid pages.

Measured built-pair checkpoints (Kyiv time): **187 at 19:52**, **298 at 20:07**,
**374 at 20:22**, **411 at 20:37**, and **458 at 20:51**. The 20:22–20:37
window added 37, nine below the requested 46; the following window added 47
and met the target one minute early. The last two data builds took **6.25 s**
and **6.36 s**; the site build took **5.73 s**. Reading and verifying the exact
original study is the pace-setting step, especially once easy abstracts run out.

Sources added after the 306-pair checkpoint: 59 of 90 original-abstract
recovery packets; 9 from a 100-pair replication-result benchmark; 7 from
publisher replication abstracts; 13 of 23 exact-DOI Springer/Psychonomic
original abstracts (retrieved in 7.31 s); 6 source-ready preprints; 8 second
replications of existing effects; 49 of 306 lower-confidence published links
after explicit original-identity checks; and one herd-immunity Registered
Report found through a publisher abstract. The remaining 40 Elsevier/APA DOI
landing-page sample yielded no usable abstract and was stopped. Source-only
packets and benchmark logs are in `/tmp/retested-*` on the VM.

The reviewed overlay was validated against exact primary-source quotes and
study identity. Both data builds and the site build passed; all 458 rows map
to one exact original/attempt/outcome and a built effect page with **zero
mismatches**. `site/src/lib/fmt.ts` now preserves internal closing quote
marks in excerpts. Three tentative low-confidence links and one Physics
Education row were withdrawn before their pages were built. No Social
Sciences or Neuroscience field slices were screened, and no site publication
or push was done.

Next source-rich packets: `/tmp/retested-review-remaining-original-text.jsonl`
has 131 untouched trusted published original pairs, 43 with a cached
replication abstract; a separate 30-case untrusted Psychology preprint batch
is under review. Keep demanding the exact original paper, directional claim,
later-study target, and result before appending to
`data/curated/promoted_pairs.json`. After a batch, run the data build twice
and then `cd site && npm run build`; check every new page and update the
baseline when the reviewed queue intentionally shrinks.

## 2n. 2026-09-24 18:14 UTC: 506 built Psychology pairs and source-recovery benchmark

The fully built site now has **506 source-reviewed original–replication pairs**
across **497 named Retested effect pages** (496 newly created effects, one
joined to an existing effect). That is **421 pairs added** beyond the 85-pair
checkpoint at `be85440`. Current baseline totals: **1,402 effects**, **924
with linked attempts**, **3,821 findings**, **4,375 attempts**, **4,086
replications**, and **6,975 pending candidates**. Pending candidates are
unverified leads. The exact DOI/effect/attempt/outcome/static-page audit passed
on all 506 rows with **zero issues** after two data builds and the site build.

Measured pace: **458 built at 20:51 Kyiv**, **480 at 21:02**, **495 by 21:08**,
**500 at 21:10**, **504 at 21:12**, and **506 at 21:13**. The requested next
15-minute target of 504 by 21:07 was missed by at least nine; it
was reached at 21:12. The site/data build itself takes about 18 seconds
combined; exact-source identification and review set the pace.

A direct publisher fetch recovered usable abstracts for **73 of 75**
Springer/Psychonomic replication DOIs in **13.08 seconds** for 60 new requests.
Reviewers accepted 16 new pairs from that 73-paper packet and one additional
already-curated duplicate was excluded. A separate cached-full-text packet of
71 candidates produced four new exact pairs; two more passed review but were
already curated. Reviewed remaining-original-text packets added 25 new pairs
and are still under review. A 40-DOI Semantic Scholar benchmark recovered six
exact replication abstracts and four open PDF URLs in **0.54 seconds**; those
sources are being screened. An applied-linguistics candidate was withdrawn
from the Psychology slice before merge. Source packets and reviewer batches
remain in `/tmp/retested-*` on the VM.

No site publication or push was done. Continue source retrieval in batches,
require the exact original study and its directional result, and audit every
promoted row after the two data builds and site build.

## 2o. 2026-09-24 18:32 UTC: 540 fully built pairs

The current Psychology site build has **540 exact, source-reviewed pairs** across
**531 named Retested effect pages**. This is **455 additions** since the
85-pair checkpoint. The site has **1,436 effects** overall and **4,409
attempts**. The exact DOI/effect/attempt/outcome/static-page audit passed on
all 540 rows with **zero issues** after two data builds and the site build.

Measured interval: **506 built at 21:13 Kyiv → 540 at 21:31**, or **34
additions in 18 minutes (~32 seconds each)**. The owner's target is 46 in 15
minutes (~20 seconds each), so this interval was below target. The site build
is not the bottleneck; source recovery, correct original identity, and outcome
review are. A free Semantic Scholar lookup of **349 missing-replication DOIs**
took **1.1 seconds**, found **322 exact DOI matches**, **37 usable abstracts**,
and **50 open PDF URLs**. A follow-up recovered **12 primary original
abstracts** for 22 missing-original cases in about **11 seconds**. A separate
source-complete packet contains **100 unseen published original DOI pairs**;
three reviewers are auditing it in nonoverlapping segments.

One otherwise source-supported row was withdrawn after the build exposed a
conflict: its reviewed outcome was `mixed`, but an older FORRT result for the
same exact DOI pair was `failed`, and the registry intentionally gives FORRT
precedence. The row was removed before this zero-issue checkpoint. A proposed
Decision Sciences original was also rejected by Psychology scope. When a
machine-linked original is wrong, reviewers now try the paper's explicitly
named correct original DOI instead of discarding an otherwise valid
replication. No site publication or push was done.

## 2p. 2026-09-24 18:46 UTC: 560 built pairs; corrected machine links

The Psychology build has **560 exact source-reviewed pairs** across **551 named
Retested effect pages**, **475 more pairs** than the initial 85. Overall site
totals are **1,456 effects** and **4,428 attempts**. Every curated row maps
to one exact DOI original/replication attempt, the chosen outcome, and a built
static effect page; the latest full audit found **zero issues**.

The last measured 15-minute interval (about 21:28–21:43 Kyiv) added **29
fully built pairs**, below the requested **46**. Most recent additions came
from correcting a machine-suggested original DOI to the actual study named or
cited by the replication paper. All corrected DOI/result quotes were checked
against the original and later paper, and competing FORRT verdicts were
excluded. One preprint-to-published candidate ID had to be changed to its
canonical published DOI before the build would load; that fix is included.

A timed Crossref sweep of **92** untouched high-confidence Psychology leads
made **180 DOI requests in 3.5 seconds** but produced **zero complete
original-plus-replication abstract pairs**; that route was stopped. A separate
batch of **50 open-PDF URLs** yielded 11 readable PDFs in 9.5 seconds; original
source recovery is under review. The highest-yield current route is relinking
wrong-original candidates using explicit citations in the later paper. No site
publication or push was done.

## 2q. Source-reviewed Psychology pairs: 24 September, 22:00 Kyiv checkpoint

At **22:00 Kyiv**, the two data builds and site build showed **594** exact
source-reviewed effect-plus-replication pairs on **585** distinct effect pages,
with **zero** exact-pair audit issues. This was **36 new finished pairs** in the
preceding 15 minutes (558 at 21:45), below the owner's target of 46. The
measured throughput was therefore **2.4 finished pairs per minute**; the target
requires about 3.1. At 22:05 Kyiv, the next two data builds and site build passed with **604**
exact pairs on **595** distinct effect pages and **zero** audit issues.

The productive route is correcting machine-linked original DOIs from explicit
citations in later studies, then checking the original claim and replication
outcome against primary abstracts or full text. A frozen 257-row wrong-link
queue is split into disjoint rank ranges among four reviewers. The 50 open-PDF
route yielded a few additional source-backed pairs but was too sparse to keep
as the main route. DeepSeek is used only to prioritize or draft; every accepted
DOI, target, and result is checked against the source text. No site publication
or push has occurred.

## 2r. 2026-09-24 20:02 UTC: timed Psychology throughput checkpoint

At the timed 15-minute checkpoint, the full data/site builds and exact-pair
source audit passed with **676** finished Psychology pairs, up from **654** at
19:46 UTC. That is **22 new finished pairs in 15 minutes** (1.47/minute),
**24 short of the owner's 46-pair target**. The next completed build reached
**683** pairs, **668** distinct curated effects, **1,573** site effects, and
**4,550** attempts, with **zero** audit issues. These are built pairs, not
pending candidates. The earlier 610-pair checkpoint included 12 later papers
whose OpenAlex *primary field* was outside Psychology; they were removed before
this interval. This interval's 654-to-676 delta therefore has no removals.

Measured source-recovery steps explain the shortfall. For a 50-candidate
missing-original tranche, exact DOI Crossref/Europe PMC retrieval took 5.2 s
and returned only 3 usable original abstracts; later-paper OpenAlex field
checks took 5.8 s. Ten strict pairs took the remaining reviewer work, mostly
finding older original result text and confirming the named original. Another
50-candidate tranche took 9m36 from frozen queue to its first four reviewed
pairs; its first field/abstract/cache checks were about 3m, then publisher
source review took 5m28. DeepSeek's existing bulk exact review drafted 310
two-abstract pairs in 98 s, but its leads need original-identity, field, and
result verification before promotion. Faster model drafting alone does not
make a pair source-reviewed.

Current tactic: prioritize published later studies whose original claim is
already source-reviewed; retrieve source-complete abstracts; verify the exact
later OpenAlex primary field and paper identity; merge small reviewed batches;
run both data builds, the site build, and the exact-pair audit. The owner has
explicitly restricted this work to later papers with primary field Psychology.
Do **not** execute historical item 4 below (Social Sciences/Neuroscience
screening). No push or site publication has occurred.

## 2s. 2026-09-24 22:39 UTC: built Psychology pair checkpoint

The two data builds, site build, and exact-pair audit pass at **744**
source-reviewed Psychology effect-plus-replication pairs on **729** distinct
curated effects. The built site has **1,633** effects and **4,611** attempts;
the exact-pair audit reports **zero** issues. This is **90** more finished pairs
than the 654-pair 19:46 UTC baseline. From the 704-pair 22:18 UTC checkpoint
to 22:39 UTC, **40** finished pairs were added in about **21 minutes**,
approximately **1.9 per minute**. The owner target of 46 in 15 minutes
requires approximately 3.1 per minute; the measured pace remains short.

The four build/audit steps take about **20 seconds** in total: the two data
builds about 6.5 seconds each, the site build about 6.6 seconds, and the
exact-pair audit about 0.2 seconds. A batch OpenAlex screen of 115 uncurated
abstract-rich later papers took **9.2 seconds** and found **40** with
Psychology as their primary field. Verifying exact original identity,
result wording, and the later result against original abstracts or paper
full text remains the limiting work. Three disjoint source pools are being
reviewed in parallel: ranked missing-original links 151-483, Psychology
papers in Psychological Reports, and a 257-case wrong-original queue.
The root reviewer also uses the previously abstract-rich 310-pair queue.
Small checked batches are merged, then both data builds, the site build,
and audit run. DeepSeek/model drafts never count until exact source checks
and the full build pass. No push or site publication has occurred.

## 2t. 2026-09-24 23:03 UTC: built Psychology pair checkpoint

Both data builds, the site build, and the exact-pair audit pass at **782**
source-reviewed Psychology effect-plus-replication pairs on **766** distinct
curated effects. The built site has **1,670** effects and **4,649** attempts;
the audit reports **zero** issues. This is **128** more finished pairs than
the 654-pair 19:46 UTC baseline. From the 744-pair 22:39 UTC checkpoint to
23:03 UTC, **38** finished pairs were added in about **24 minutes**, or
about **1.6 per minute**. The requested 46 pairs in 15 minutes would require
about **3.1 per minute**, so the current measured pace remains below target.

The four-stage build/audit took **19.3 seconds** at this checkpoint:
6.4 seconds for each data build, 6.2 seconds for the site build, and
0.3 seconds for the audit. New source-reviewed pairs came from the ranked
missing-original queue, the corrected-original queue, and the
Psychology-primary next-tier/recovered queue. One named typist-preference
effect now has two independently reviewed later tests with different
outcomes; these count as two pairs and one distinct effect. The
Psychological Reports and corrected-original bounded pools are exhausted
under the source rule; the missing-original and abstract-rich queues are
still being reviewed in parallel. A candidate counts only after checking
the original result, exact later target, later outcome, field, identity,
and a passing full build. No push or site publication has occurred.

## 2u. 2026-09-24 23:32 UTC: built Psychology pair checkpoint

Both data builds, the site build, and the exact-pair audit pass at **838**
source-reviewed Psychology effect-plus-replication pairs on **821** distinct
curated effects. The built site has **1,725** effects and **4,705** attempts;
the audit reports **zero** issues. This is **184** more finished pairs than
the 654-pair 19:46 UTC baseline. From the 808-pair 23:20:40 UTC build to
this 23:31:46 UTC build, **30** finished pairs were added in about **11.1
minutes**, or **2.7 per minute**. The 46-in-15-minute target requires **3.1
per minute** and is not yet sustained.

The four-stage build/audit took **19.5 seconds**: 6.4 seconds for each data
build, 6.5 seconds for the site build, and 0.3 seconds for the audit.
Curation used three disjoint Psychology-primary queues in parallel, with
the root reviewer checking and relinking additional source-complete rows.
Several machine-selected originals were replaced by the actual original
study named in the later paper. A conference abstract with pilot-only
results was held out of the finished-paper count; one original abstract
was held until a publisher-deposited record verified it. Pair outcome
labels reflect the targeted effect, including mixed and failed results.
No push or site publication has occurred.

## 2v. 2026-09-24 23:51 UTC: built Psychology pair checkpoint

Both data builds, the site build, and the exact-pair audit pass at **867**
source-reviewed Psychology effect-plus-replication pairs on **850** distinct
curated effects. The built site has **1,754** effects and **4,734** attempts;
the audit reports **zero** issues. This is **213** more finished pairs than
the 654-pair 19:46 UTC baseline.

The four-stage build/audit took **19.8 seconds**: 6.4 seconds for each data
build, 6.7 seconds for the site build, and 0.3 seconds for the audit.
From 838 built at 23:32 UTC to 867 built at 23:51 UTC, **29** pairs were
finished in about **19 minutes**, or about **1.5 per minute**. This is below
the requested 46 pairs per 15 minutes (3.1 per minute). Source verification
and finding independent, exact-match studies dominate the elapsed time;
the build itself remains fast. The team rejected same-cohort reanalyses,
unclear original links, and conference-only abstracts rather than count
them as new replications. The most recent batches included new empirical
Psychology articles from the ranked missing-original and unseen queues.
No push or site publication has occurred.

## 2w. 2026-09-25 00:10 UTC: built Psychology pair checkpoint

Both data builds, the site build, and the exact-pair audit pass at **896**
source-reviewed Psychology effect-plus-replication pairs on **879** distinct
curated effects. The built site has **1,783** effects and **4,762** attempts;
the audit reports **zero** issues. This is **242** more finished pairs than
the 654-pair 19:46 UTC baseline and **29** more than the 867-pair checkpoint
at 23:51 UTC.

The latest four-stage build/audit took **19.6 seconds**: 6.3 and 6.4 seconds
for the data builds, 6.6 seconds for the site build, and 0.3 seconds for the
audit. From 867 built at 23:51 UTC to 896 built at 00:10 UTC, **29** pairs
were finished in about **19 minutes**, or **1.5 per minute**. The requested
pace is 46 in 15 minutes (**3.1 per minute**). Source review and exact
original matching remain the rate limit; build time is about 20 seconds.
The newer batch includes published, independent-sample Psychology studies
from explicit replication papers and direct full-text source reviews.
DOI aliases, reanalyses of the same cohort, and results outside the
specified Psychology field were excluded. No push or site publication occurred.

## 2x. 2026-09-25 00:22 UTC: built Psychology pair checkpoint

Both data builds, the site build, and the exact-pair audit pass at **910**
source-reviewed Psychology effect-plus-replication pairs on **893** distinct
curated effects. The built site has **1,797** effects and **4,775** attempts;
the audit reports **zero** issues. This is **256** more finished pairs than
the 654-pair 19:46 UTC baseline and **14** more than the 896-pair checkpoint
at 00:10 UTC.

The latest four-stage build/audit took **20.3 seconds**: 6.4 and 6.3 seconds
for the data builds, 7.4 seconds for the site build, and 0.3 seconds for the
audit. The 14 new pairs took about 12 minutes of wall time since the
previous verified checkpoint, approximately **1.2 per minute**, below the
owner's requested **3.1 per minute**. Published source review, original
identification, and independent-sample confirmation remain the limiting
steps. This batch includes new Psychology papers from OA, Elsevier,
Springer, legacy-journal, and exact-original relink queues. DOI aliases,
same-cohort reanalyses, non-Psychology primary-field papers, and records
without outcome evidence were not counted. No push or site publication occurred.

## 2y. 2026-09-25 00:44 UTC: built Psychology pair checkpoint

Both data builds, the site build, and the exact-pair audit pass at **927**
source-reviewed Psychology effect-plus-replication pairs on **910** distinct
curated effects. The built site has **1,814** effects and **4,792** attempts;
the audit reports **zero** issues. This is **273** more finished pairs than
the 654-pair 19:46 UTC baseline and **17** more than the 910-pair checkpoint
at 00:22 UTC.

The latest four-stage build/audit took **21.1 seconds**: 6.7 and 6.3 seconds
for the data builds, 7.7 seconds for the site build, and 0.3 seconds for the
audit. The 17 new pairs took about 22 minutes of wall time since the
previous verified checkpoint, about **0.8 per minute**. The owner's requested
pace is 46 in 15 minutes, about **3.1 per minute**. Source review, exact
original identification, and independent-sample confirmation continue to
limit the rate. Newly built pairs include additional independent-sample
Psychology studies from source-reviewed ranked and unseen queues. The later
replication papers have Psychology as their OpenAlex primary field. No push
or site publication occurred.

## 2z. 2026-09-25 00:55 UTC: built Psychology pair checkpoint

Both data builds, the site build, and the exact-pair audit pass at **937**
source-reviewed Psychology effect-plus-replication pairs on **920** distinct
curated effects. The built site has **1,824** effects and **4,801** attempts;
the audit reports **zero** issues. This is **283** more finished pairs than
the 654-pair 19:46 UTC baseline and **10** more than the 927-pair checkpoint
at 00:44 UTC.

The latest four-stage build/audit took **18.8 seconds**: 6.2 and 6.0 seconds
for the data builds, 6.3 seconds for the site build, and 0.3 seconds for the
audit. Ten new pairs took about 11 minutes of wall time since the previous
verified checkpoint, about **0.9 per minute**. The owner's requested rate is
46 in 15 minutes, about **3.1 per minute**. This batch includes exact-original
corrections and narrow effect claims where a later paper reproduced only
part of the original findings. Source verification remains the rate limit.
No push or site publication occurred.

## 2aa. 2026-09-25 01:03 UTC: built Psychology pair checkpoint

Both data builds, the site build, and the exact-pair audit pass at **944**
source-reviewed Psychology effect-plus-replication pairs on **925** distinct
curated effects. The built site has **1,829** effects and **4,808** attempts;
the audit reports **zero** issues. This is **290** more finished pairs than
the 654-pair 19:46 UTC baseline and **7** more than the 937-pair checkpoint
at 00:55 UTC.

The latest four-stage build/audit took **19.5 seconds**: 6.1 and 6.3 seconds
for the data builds, 6.8 seconds for the site build, and 0.3 seconds for the
audit. Seven new pairs took about 8 minutes of wall time since the previous
verified checkpoint, about **0.9 per minute**. The owner's requested rate is
46 in 15 minutes, about **3.1 per minute**. Source checking and linking
remain the rate limit. No push or site publication occurred.

## 2ab. 2026-09-25 01:15 UTC: built Psychology pair checkpoint

Both data builds, the site build, and the exact-pair audit pass at **952**
source-reviewed Psychology effect-plus-replication pairs on **929** distinct
curated effects. The built site has **1,833** effects and **4,814** attempts;
the audit reports **zero** issues. This is **298** more finished pairs than
the 654-pair 19:46 UTC baseline and **8** more than the 944-pair checkpoint
at 01:03 UTC.

The latest four-stage build/audit took **19.8 seconds**: 6.4 and 6.4 seconds
for the data builds, 6.8 seconds for the site build, and 0.3 seconds for the
audit. Eight new pairs took about 12 minutes of wall time since the previous
verified checkpoint, about **0.7 per minute**. The owner's requested rate is
46 in 15 minutes, about **3.1 per minute**. Source checking and linking
remain the rate limit. No push or site publication occurred.

## 2ac. 2026-09-25 01:33 UTC: built Psychology pair checkpoint

Both data builds, the site build, and the exact-pair audit pass at **964**
source-reviewed Psychology effect-plus-replication pairs on **939** distinct
curated effects. The built site has **1,843** effects and **4,826** attempts;
the audit reports **zero** issues. This is **310** more finished pairs than
the 654-pair 19:46 UTC baseline and **12** more than the 952-pair checkpoint
at 01:15 UTC.

The latest four-stage build/audit took **19.9 seconds**: 6.4 and 6.5 seconds
for the data builds, 6.7 seconds for the site build, and 0.3 seconds for the
audit. Twelve new pairs took about 18 minutes of wall time since the previous
verified checkpoint, about **0.7 per minute**. The owner's requested rate is
46 in 15 minutes, about **3.1 per minute**. Source checking and linking
remain the rate limit. The new Gable and Harmon-Jones finding has both a
successful 2016 registered replication and a failed 2022 online replication,
each explicitly tied to the narrowed-global-attention result. No push or site
publication occurred.

## 2ad. 2026-09-25 01:43 UTC: built Psychology pair checkpoint

Both data builds, the site build, and the exact-pair audit pass at **977**
source-reviewed Psychology effect-plus-replication pairs on **952** distinct
curated effects. The built site has **1,856** effects and **4,839** attempts;
the audit reports **zero** issues. This is **323** more finished pairs than
the 654-pair 19:46 UTC baseline and **13** more than the 964-pair checkpoint
at 01:33 UTC.

The latest four-stage build/audit took **19.6 seconds**: 6.4 and 6.3 seconds
for the data builds, 6.6 seconds for the site build, and 0.3 seconds for the
audit. Thirteen new pairs took about 9 minutes of wall time since the previous
verified checkpoint, about **1.4 per minute**. The owner's requested rate is
46 in 15 minutes, about **3.1 per minute**. The new records include two
independent studies with differing results for the same Gable/Harmon-Jones
attention effect, an infant communication-intervention replication with a
corrected original paper, and a Japanese psychological-flexibility profile
replication. No push or site publication occurred.

## 2ae. 2026-09-25 02:06 UTC: 1,000 built Psychology pairs

Both data builds, the site build, and the exact-pair audit pass at **1,000**
source-reviewed Psychology effect-plus-replication pairs on **965** distinct
curated effects. The built site has **1,869** effects and **4,859** attempts;
the audit reports **zero** issues. This is **346** more finished pairs than
the 654-pair 19:46 UTC baseline, and **23** more than the saved 977-pair
checkpoint at 01:43 UTC.

The latest four-stage build/audit took **19.7 seconds**: data builds 6.4
and 6.4 seconds, site build 6.6 seconds, audit 0.3 seconds. The 23 new
pairs took about 23 minutes of wall time since the prior checkpoint,
approximately **1.0 pair per minute**, below the owner's requested
46 in 15 minutes (**3.1 per minute**). Searching, reading exact results,
checking original links, and resolving an existing outcome disagreement
account for most of the elapsed time. New pages include the original
Song infant communication effect with later cross-language and conceptual
replications; independent power-pose retests with scoped hormone, risk,
and felt-power outcomes; Deci's monetary-reward effect with a failed
direct test; and an independent PTSD treatment replication. Existing
legacy coding for Bailey 2017 was retained as **failed** for its
preregistered main test, with exploratory support noted. No push or site
publication occurred.

## 2af. 2026-09-25 02:15 UTC: 1,006 built Psychology pairs

Both data builds, the site build, and the exact-pair audit pass at **1,006**
source-reviewed Psychology effect-plus-replication pairs on **968** distinct
curated effects. The built site has **1,872** effects and **4,865** attempts;
the audit reports **zero** issues. This is **352** more finished pairs than
the 654-pair 19:46 UTC baseline and **6** more than the saved 1,000-pair
checkpoint at 02:06 UTC. The four-stage build/audit took **20.0 seconds**
(data builds 6.5 and 6.6 seconds, site build 6.7 seconds, audit 0.3 seconds).
New reviewed pairs include independent vertical-time concept tests, an
aggression follow-up, and three new tests from a citation-linked candidate
queue. The candidate queue is undergoing source screening; raw links do
not count as finished pairs. No push or site publication occurred.

## 2ag. 2026-09-25 02:31 UTC: 1,036 built Psychology pairs

Both data builds, the site build, and the exact-pair audit pass at **1,036**
source-reviewed Psychology effect-plus-replication pairs on **972** distinct
curated effects. The built site has **1,876** effects and **4,881** attempts;
the audit reports **zero** issues. This is **382** more finished pairs than
the 654-pair 19:46 UTC baseline, **36** more than the 1,000-pair checkpoint,
and **30** more than the 1,006-pair checkpoint at 02:15 UTC. Elapsed wall
time since that checkpoint is about 16 minutes, or **1.9 finished pairs per
minute** (about 28 per 15 minutes), below the owner's requested 46 per
15 minutes. The latest four-stage build/audit took **19.8 seconds**.

A citation-linked discovery queue produced new, source-checked retests
across the Stroop/posture, mortality-salience, multimedia modality,
infant-helper preference, Kruger-Dunning, framing, mere-exposure, and other
effects. Machine-suggested original links were independently checked and
corrected where needed. Two older FLoRA paper-level outcome labels conflicted
with narrower primary results: ManyBabies' preregistered helper preference
was null, and the suicide-IAT follow-up predicted future attempts although
its separate baseline result failed. Their curated records now carry explicit
adjudications; the built graph retains both the FLoRA and Retested labels and
shows the reviewed effect-level verdict. Focused unittest suite: 5 passed.
No push or site publication occurred.

## 2ah. 2026-09-25 02:45 UTC: 1,066 built Psychology pairs

Both data builds, the site build, and the exact-pair audit pass at **1,066**
source-reviewed Psychology effect-plus-replication pairs on **987** distinct
curated effects. The built site has **1,891** effects and **4,900** attempts;
the audit reports **zero** issues. This is **412** more finished pairs than
the 654-pair 19:46 UTC baseline and **30** more than the saved 1,036-pair
checkpoint at 02:31 UTC. Elapsed wall time is about 14 minutes, or roughly
**2.1 finished pairs/minute** (about **32 per 15 minutes**), below the
owner's requested **46 per 15 minutes**. The latest four-stage build/audit
took **19.5 seconds**.

The new pairs include independent infant rule-learning and bilingual-switch
multicenter retests, a corrected original for the infant box-opening helper
effect, multiple independent reward/motivation tests, and direct tests of
creative movements, facial feedback, emotion-regulation choice, and
false-belief anticipation. The 2026 box-opening article's two new 9-month
samples were null, while its broader meta-analysis was positive; that scope
is explicit in the reviewed record. Exact original-paper relinking and
published-versus-preprint deduplication prevented false additions. No push
or site publication occurred.

## 2ai. 2026-09-25 03:00 UTC: 1,090 built Psychology pairs

Both data builds, the site build, and exact-pair audit pass at **1,090**
source-reviewed Psychology effect-plus-replication pairs on **997** distinct
curated effects. The site build has **1,901** effects and **4,922** attempts;
the audit reports **zero** issues. This is **436** more finished pairs than
the 654-pair 19:46 UTC baseline, and **24** more than the 1,066-pair
checkpoint at 02:45 UTC. Elapsed wall time was about **15 minutes**,
approximately **24 finished pairs per 15 minutes**, still below the owner's
requested **46 per 15 minutes**. The latest four-stage build/audit took
**18.9 seconds**.

This batch adds independent retests of ego depletion, infant rule learning,
emotion and risk choice, exercise priming, ERN reliability, peer-group
personality effects, and in-session rumination. Several candidate links
required correction to the actual cited original; preprint/published
duplicates and a self-overlapping cohort were excluded. The peer-group
replication's apparent assimilation was explained by regression to the
mean. No push or site publication occurred.

## 2aj. 2026-09-25 03:25 UTC: 1,116 built Psychology pairs

Both data builds, the site build, and exact-pair audit pass at **1,116**
source-reviewed Psychology effect-plus-replication pairs on **1,016** distinct
curated effects. The site build has **1,920** effects and **4,932** attempts;
the audit reports **zero** issues. This is **462** more finished pairs than
the 654-pair 19:46 UTC baseline and **26** more than the 1,090-pair
03:00 UTC checkpoint. About **25 minutes** elapsed, approximately
**16 finished pairs per 15 minutes**, below the owner's requested **46 per
15 minutes**. The latest four-stage build/audit took **19.6 seconds**.

New independent-author records include two failed direct retests of Bem's
retroactive recall claim, achievement-word priming, subjective likelihood
and construal, facial feedback, commitment priming, bottomless soup bowls,
emotion-regulation fit, and future-self letters. Several successful or
mixed outcomes are also represented. Three overlapping-author candidate
pairs were removed before this checkpoint, as was a duplicate candidate;
a Bem precognition link conflicting with the existing FLoRA paper-level
label remained excluded pending effect-specific adjudication. The current
bottleneck is source and author verification, not the builds. No push or
site publication occurred.

## 2ak. 2026-09-25 03:59 UTC: 1,150 built Psychology pairs

Both data builds, the site build, and exact-pair audit pass at **1,150**
source-reviewed Psychology effect-plus-replication pairs on **1,049** distinct
curated effects. The site build has **1,953** effects and **4,945** attempts;
the audit reports **zero** issues. This is **496** more finished pairs than
the 654-pair 19:46 UTC baseline and **34** more than the 1,116-pair
03:25 UTC checkpoint. About **34 minutes** elapsed, approximately
**15 finished pairs per 15 minutes**, below the owner's requested **46 per
15 minutes**. The latest four-stage build/audit took **19.8 seconds**.

New independent-author records include later tests of cocktail-party own-name
capture, inaction inertia, cross-talker accented-speech adaptation, the
incremental validity of average personality states, oxytocin and trust,
depressive realism, mortality salience, mirror self-recognition in magpies,
KiVa bullying prevention, childhood verbal rehearsal, and wallet honesty.
Published later OpenAlex primary field Psychology and exact original DOI were
checked. A few packets were reconciled to existing FLoRA mixed outcomes and
author-overlap candidates were excluded. Source and author verification
remain the bottleneck; the full build itself takes about 20 seconds.
No push or site publication occurred.

## 2al. 2026-09-25 04:24 UTC: 1,172 built Psychology pairs

Both data builds, the site build, and exact-pair audit pass at **1,172**
source-reviewed Psychology effect-plus-replication pairs on **1,071**
distinct curated effects. The site has **1,975** effects and **4,957**
attempts; the audit reports **zero** issues. Of the curated material,
**1,088** pairs and **1,069** distinct effects are additions beyond the
preexisting collection. This is **22** more finished pairs than the 1,150-pair
03:59 UTC checkpoint, over **25 minutes**: approximately **13 pairs per
15 minutes**, below the owner's requested **46 per 15 minutes**. The latest
four-stage build and audit took **19.3 seconds**.

New independent-author pairs include two failed replications of physical
cleanliness and political attitudes; a failed direct altruism/mating-success
test; two failed infant helper-preference attempts; a successful registered
status-desire/overconfidence replication; birthday-number preference;
recognition bias for psychology pioneers; and tests of machine trust,
shame-coping, emotional intelligence, and child pretense learning. The later
published work's OpenAlex primary field is Psychology. Source quotes,
original DOI, later outcome, and author separation were checked. A
previously present malformed DOI created a duplicate of the Heider/Olivier
to Roberson color-memory pair; the duplicate was removed and the
source-complete canonical-DOI record retained. Existing FLoRA mixed
outcomes were reconciled before acceptance. Source review remains the
time bottleneck; building the site takes about 20 seconds.
No push or site publication occurred.

## 3. Next steps, in order

**Current owner priority (2026-09-24):** continue source-reviewed Psychology effect and replication pages through both builds. The older numbered list below records the prior backlog; its Social Sciences/Neuroscience screening item is superseded by the owner’s Psychology-only instruction.

1. **Read the remaining 1,102 unread rows on pages.** This is now the main line of work rather than an audit
   chore: every row read is a row decided, confirmations are ~99% right at this base rate, and the ~54 expected
   wrong rows come off as they are found. `pipeline originals --batches 8 --size 40 --pool page` writes the
   next wave worst-first; hand each batch to a reader with the rubric. Free, and about 28 batches to finish.
2. **Read the 29 band-rule-only rows first** — rows shipping because their band is trusted although the
   verifier did not confirm them. They read 4 right of 7 in two bands: 2% of what ships, a quarter of its
   expected error.
3. **Keep reading the PDF-derived outcomes.** 22 of 25 agreed, which establishes that the population is usable
   and is too small to be a rate. Free.
3. **Widen the PDF route.** Only `primary_location.pdf_url` was used; `best_oa_location` would add the
   repository copies (270 of these finds are open access but only 154 had a publisher PDF), and OpenAlex
   lookups are free and cached. Narrow `fulltext._silent()` first: a third of this run's fetches went to finds
   that already had a `mixed` verdict, which the queue will never let a reread override.
4. **Screen Social Sciences and Neuroscience** — already crawled and cached, ~$0.60 to screen.
   `pipeline triage --tier high --fields "Social Sciences,Neuroscience"`.
5. **Re-measure `pipeline choose` on finds that have abstracts.** Its 74% was measured where neither side had
   one, so it is a floor rather than a verdict. `pipeline choose --check`, ~$0.15 per 500.
6. **Publish**: NOT for now (owner decision 2026-09-19). Keep building and previewing on the VM.
7. **Contact FORRT** (Wallrich / Röseler) before reusing unlicensed code from flora-extractor /
   flora-validation; offer the finds and the recall harness back to them.

## 4. Owner decisions and open questions
- Decided 2026-09-19: keep the laptop copy (`C:\Users\OMISTAJA\PsychologyReplication`); do not delete it.
- Decided 2026-09-19: do not host the site yet.
- Open: 418 of the 751 resolved links are low confidence, and 312 named originals stayed unresolved. Both are
  reviewer work, not model work — is the review queue the right place for them, or should low-confidence links be
  held back from effect pages until a person confirms them?
- Should the old OpenRouter (`sk-or-v1-91e…`) and OpenAI (`sk-proj-vj-p…`) keys have been revoked? They were in 51
  archived scripts (now redacted in `archive/`, which is gitignored). Remind once.

## 5. Where the thinking is
`docs/planning/`: `BRIEF.md` (goals), `understanding/U1–U8` (what existed, FORRT's data dictionary, landscape,
discovery methods, FORRT's 50-repo ecosystem), `designs/D1–D6` (encyclopedist, meta-scientist, game, discovery,
architecture, 48 ideas), `MASTER_PLAN.md` sections 0–4 + `_mp_parts/04-entities.md` (decision log). The design
docs contain more ideas than are built (crowd forecasts, Rise & Fall citation stories, textbook overlay, API).
