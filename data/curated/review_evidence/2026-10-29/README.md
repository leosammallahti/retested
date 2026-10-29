# Blind check of machine-found replications (29 Oct 2026)

200 of the 4,349 machine-found pairs that two models had read as replications of their linked original, drawn at
random (seed 20261029), were read by Claude without the models' answers: the original as the reading item described
it, and the later paper's title and first part of its abstract (`blind_sample.txt.gz`).

`mine.txt`: one line per case, `n|link|result`. Link: Y (replicates this original), N (replicates a different study),
? (the text cannot confirm it). Result: F found, N not found, M mixed, X not stated in the shown text, ? unsure.
`key.json` maps each case to its attempt and the models' outcome.

Link: 175 Y, 12 N, 13 ?. Where the link was right and the shown text stated a result, the models' result matched in
98 of 105 cases (the rest differed between found and mixed). Most other differences come from the shown abstract
being cut short. Decision: machine-found pairs are not counted until their link is verified (`pipeline/read_pairs.py`).
