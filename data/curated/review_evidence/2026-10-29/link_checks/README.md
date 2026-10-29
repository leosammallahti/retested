# Link checks of machine-found pairs (29 Oct 2026)

Each machine-found pair that two models had read as a replication of its linked original was checked by a Sonnet 5.5
reading helper against both full abstracts (`BRIEF.md`; cases built by `pipeline/repair/verify/build_cases.py`, one
block per original). `queueNN.out` holds the answers (`L<n>|Y`, `L<n>|N|<what it replicates instead>`, `L<n>|?`),
`queueNN.ids.json` maps each `L<n>` to its reading; `pipeline/repair/verify/collect.py` writes
`data/curated/link_checks.csv`. Where a helper flagged its own yes as resting on judgement, Claude set it to `?`.

Test first: `calibration.out` is a helper's answer on the 200 pairs read blind by Claude (`../mine.txt`): of the 10
links found wrong there, it caught 8; the brief then gained its two warnings. After the run, 60 accepted links drawn at
random were read by Claude with the same text: all 60 right.

Result: 4,349 pairs; 3,253 yes, 259 no, 837 can't tell. 22 helpers, about 4.2 million tokens in all.
