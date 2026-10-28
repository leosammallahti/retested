# Brief: replications of a null finding (Retested, 28 Oct 2026)

Each case in /root/wiki-scratch/cases_20261028/null_cases.txt is a later paper read as a replication of the earlier
study, with the result coded for it. The result scale is about the earlier FINDING: FOUND means the finding appeared
again, NOT_FOUND means it did not, MIXED means in some tests but not others. When the earlier finding is itself a null
(no effect, no difference, X does not affect Y), a later null is FOUND and a later effect is NOT_FOUND.

For each case decide, from the text only: is the earlier finding (the Finding line, else the paper's title) a null?
If it is not a null, write KEEP. If it is a null, give the result the later paper's text supports on that scale.

Write /root/wiki-scratch/cases_20261028/null_decisions.txt, one line per case, nothing else:
<case id> | KEEP | <reason, at most 15 words>
<case id> | NULL <FOUND|NOT_FOUND|MIXED|NO_RESULT_STATED> | <reason, at most 15 words>
Read and write only these files (the host is shared). Reply with one line of counts.
