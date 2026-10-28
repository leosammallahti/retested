# Brief: decide 46 replication-record cases (Retested, 28 Oct 2026)

Retested is a public wiki of psychology replications. Each "attempt" pairs an ORIGINAL paper with a LATER paper that
tried to repeat its finding. Read `/root/wiki-scratch/cases_20261028/cases.txt` once, decide every case, and write
`/root/wiki-scratch/cases_20261028/decisions.txt`: one line per case, nothing else, in case order.

Use only the text in the case, plus free lookups where a case needs one (see below). Never guess: if the text does
not settle it, say FULL_TEXT. Reasons are short (under 30 words) and plain English. A quote is copied word for word
from the LATER PAPER text in the case, at most 25 words.

## Attempt cases (`note…`, `early…`, `review…`)

Write `<case id> | <DECISION> | <reason>`, where DECISION is one of:

- `KEEP`: the record is right as it stands (it is a replication of this finding and FORRT's result fits the text).
- `RESULT FOUND`, `RESULT NOT_FOUND` or `RESULT MIXED`: it is a replication of this finding, but the abstract plainly
  states a different result from FORRT's coding. Put the supporting quote in the reason, in double quotes.
- `NOT_REPLICATION <KIND>`, KIND one of META_ANALYSIS, REVIEW_OR_COMMENTARY, OTHER_NEW_STUDY, ORIGINAL_ITSELF: the
  later paper does not test this finding with new data or a re-analysis.
- `WRONG_ORIGINAL`: the later paper replicates a different original study; name it in the reason as the text names it
  (authors, year, title words).
- `EARLIER_EVIDENCE`: the later paper was published before the original and is not a version of a study that
  followed it, so it cannot be a replication of this paper, even if it tests the same idea.
- `FULL_TEXT`: the title and abstract cannot settle it.

Notes:
- A paper titled "reply", "comment" or "review" can still report new data; judge by the abstract.
- A multi-study audit or many-lab project that reports its own new replications of this finding is a replication.
- `early…` cases: a preprint, working paper or conference version of the original can precede the journal year, and a
  later paper may say it replicates a study that appeared earlier in another form. If the later paper's text says it
  replicates or extends this original, it is `KEEP`.
- FORRT's result stands unless the abstract plainly says otherwise; a pattern you merely infer is not enough.

## Effect cases (`contra…`)

FORRT's famous-effects list gives the effect a verdict, and the replications linked on our site point the other way.
Decide whether the site is missing something or holds something wrong. Write one or more lines per case:

- `<case id> | FINE | <reason>`: both are honest evidence (for example, the linked study is newer than the list, or the
  list relies on meta-analyses). The page shows both.
- `<case id> | ADD <doi> <FOUND|NOT_FOUND|MIXED> | <reason with quote>`: a replication the list cites is not linked.
  Find its DOI with one free Crossref query, for example
  `curl -s "https://api.crossref.org/works?rows=3&query.bibliographic=Price+2020+women+shy+away+competition+replication" | python3 -c "import json,sys;[print(i['DOI'],i.get('title'),i.get('issued')) for i in json.load(sys.stdin)['message']['items']]"`
  and read its abstract with one OpenAlex query (`curl -s "https://api.openalex.org/works/doi:<doi>?select=title,abstract_inverted_index,publication_year"`; the abstract is stored as word -> positions). Add only when the
  abstract shows it is a replication of this effect and states the result.
- `<case id> | NOT_REPLICATION <attempt id> <KIND> | <reason>`: a linked attempt does not test this effect.

## Limits

The host is shared. Run only the lookups above (at most 3 per contra case), nothing heavy, write only `decisions.txt`.
Do not edit any other file. When done, reply with one line: the number of decisions of each kind.
