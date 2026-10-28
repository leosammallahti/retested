# Brief: one plain line for 24 effects (Retested, 28 Oct 2026)

Read /root/wiki-scratch/lines_20261028/inputs.json once (24 effects, each an id and the facts the record holds).
For each effect, follow these instructions exactly, as if they were your system prompt:

You write one short sentence that tells a general reader what a named effect from psychology or social science says: what the original research claimed. It appears under the effect's name in a list and at the top of its page, on a site about whether such findings hold up when other teams try them again. The list already shows the name and the verdict, so the sentence only has to make the effect understandable.

Rules:
1. One sentence of 8 to 20 words, in plain everyday English that a curious 15-year-old can follow.
2. State what the original research claimed, directly, as the effect's own statement: what was said to affect what, and in whom or in what situation. Example of the style: "Using self-control drains a limited reserve, so the next task that needs it goes worse."
3. Do not begin with a stock phrase such as "The idea that", "The claim that", "This effect" or "Research shows". Do not repeat the effect's name, and do not say the same thing twice.
4. Explain any technical term in everyday words. No jargon such as DV, IV, paradigm, prime, moderator, construct or manipulation; if the name is a technical term (for example "priming"), say in plain words what was done (for example "seeing words about old age").
5. Never say or hint whether the claim held up, was replicated, confirmed, debunked or doubted. No numbers, statistics, author names or years.
6. Use only what the facts below say. The later papers that retested the effect often describe it; use them only for what the effect is, never for how it turned out. Keep the direction the sources give; never guess one. If the facts disagree about what the effect is, or are too thin to tell, reply with null.

Reply with JSON only: {"line": "..."} or {"line": null}.

Write /root/wiki-scratch/lines_20261028/lines.json: one JSON object mapping each id to its line (a string) or null.
Write nothing else and edit no other file. Reply with one line: how many lines and how many nulls.
