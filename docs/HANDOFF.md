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

## 3. Next steps, in order

**Current owner priority (2026-09-24):** continue source-reviewed Psychology effect and replication pages through both builds. The older numbered list below records the prior backlog.

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
