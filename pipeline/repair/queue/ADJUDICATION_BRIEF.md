# Reading the papers two models split on

Each case in the input file is one later paper: the earlier study it is linked to (the paper and the finding), the
later paper's title, authors and abstract, sometimes FORRT's reference for it, and the two models' answers.

Decide from that text alone, as the models were asked:

1. KIND, what the later paper is:
   - NEW_DATA_REPLICATION: it collects new data to test the earlier finding again (direct, close or conceptual, a
     multi-lab project, or a replication with an extension).
   - REANALYSIS: it re-analyses the earlier study's own data.
   - META_ANALYSIS: it pools many studies.
   - REVIEW_OR_COMMENTARY: a review, commentary, reply, critique, theory or methods paper.
   - OTHER_NEW_STUDY: a new study on a related question that does not test the earlier finding.
   - CANNOT_TELL: the text is too thin to say. Use this when there is no abstract and the title does not settle it.
2. TESTS, does it test the finding under EARLIER STUDY: YES, NO or CANNOT_TELL.
3. RESULT, only for NEW_DATA_REPLICATION or REANALYSIS:
   - FOUND, NOT_FOUND, MIXED or NO_RESULT_STATED. A test counts as finding the effect only where the paper reports it
     as present (significant, reliable, clearly shown); an estimate that merely points the expected way does not
     count.
   - Otherwise NOT_APPLICABLE.
   - RESULT is about the earlier FINDING. When the earlier finding was a null (no effect, no difference), a later
     null is FOUND (the finding held) and a later effect is NOT_FOUND. (Added 28 Oct 2026, afternoon.)
4. CITED, only when FORRT'S REFERENCE is given: is the later paper the one that reference names? YES, NO or
   CANNOT_TELL. Otherwise write -.

When unsure, choose CANNOT_TELL: an unsure case stays unread rather than being counted.

Output: one line per case, nothing else:
<item id> | <KIND> | <TESTS> | <RESULT> | <CITED or -> | <reason, at most 15 words>
