# Handoff — state as of 2026-09-21

## 1. What exists and works

**Pipeline (`pipeline/`)** turns FORRT's data into a site bundle in ~2 s on the VM:
906 named effects · 3,424 findings (one per original paper) · 3,879 attempts (3,590 replications, 289 reproductions;
1,024 known only from the legacy FReD 2.4.1 file) · 749 game cards · 2,425 review-queue candidates from FORRT's own
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

| the model said | right | precision | where the rest went |
|---|---|---|---|
| failed | 55/60 | 92% | 3 not established, 2 mixed |
| successful | 56/60 | 93% | 4 not established |
| mixed | 18/22 | 82% | 3 not established, 1 successful |

**Nothing in 144 cases was read as the opposite of what the paper reports.** The error is a missing answer, not a
wrong one: an abstract that settles nothing, called either way, four times towards success and five towards
failure. For a scored card that is the difference between a card that cheats the player and a card that should
never have been dealt.

Three things follow, and all three overturn something the handoff said yesterday:

- **`/uncounted/` was blaming the wrong thing.** Re-weighting every verdict on that page by these labels moves it
  from 47.7% to 49.3% — further from the curated record's 41.7%, not closer. The page no longer offers model
  error as the explanation, and it now prints the audit numbers straight from the label file through
  `stats.uncounted().audit`, so the prose cannot drift from the measurement again.
- **The card pool's base rate is real.** At the deck's own grain — one card per original, dropping originals whose
  finds disagree — 1,323 cards at 62.9% successful, 63.3% after correction, against the existing deck's 53%. Keep
  them a separate deck because the pool differs, not because its verdicts are misread.
- **Outcome reading is no longer a blocker on shipping these as cards.** The claim text is.

`docs/LINK_AUDIT_20260919.md` has the case-by-case detail, the nine mistakes named, and why the n=20 pattern was
noise rather than a direction.

## 3. Next steps, in order

1. **Finish the linking**: 364 candidates never got their OpenAlex lookup when the cap hit, and 746 named originals
   stayed unresolved. `python -m pipeline link --openalex --max-usd 1.0` after the daily reset.
2. **Audit what the audit could not reach**: the OpenAlex-high stratum rests on 11 reads and library-high/medium on
   25. Both look good; neither is settled. Medium-tier screening rests on 40 labels made by Claude, not a person.
   Outcome reading is now the best-measured judgement here and the cheapest to extend:
   `python -m pipeline outcomes --sample 60` picks up where this session left off and costs nothing but reading.
3. **Widen the keyword search** beyond psychology-tagged works (Social Sciences, Neuroscience, Decision Sciences,
   Economics, Business: ~49k titles) — with rule scoring and t3 triage. The medium tier is now done.
4. **Publish**: NOT for now (owner decision 2026-09-19). Keep building and previewing on the VM
   (`npm run preview`); the GitHub Pages workflow stays in `.github/workflows/site.yml` for later.
5. **Contact FORRT** (Wallrich / Röseler) before reusing unlicensed code from flora-extractor / flora-validation;
   offer the finds and the recall harness back to them.

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
