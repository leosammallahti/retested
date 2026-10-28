"""The reading questions (version 1, 28 Oct 2026): what a later paper is, whether it tests the earlier finding, and
what it found, each answer backed by a word-for-word quote from the later paper's own title or abstract."""
VERSION = "v2"
SYSTEM = ("You read the title and abstract of a later research paper and say how it relates to an earlier study. "
          "Use only the text you are given. Reply with one JSON object and nothing else.")
BODY = """EARLIER STUDY (the original finding)
{original}

LATER PAPER
{later}
{cited}
Answer these questions about the LATER PAPER.

1. "kind" — what the later paper is:
- NEW_DATA_REPLICATION: it collects new data to test the earlier finding again (a direct, close or conceptual replication, a multi-lab project, or a replication with an extension).
- REANALYSIS: it re-analyses the earlier study's own data, or reproduces its analysis.
- META_ANALYSIS: it pools the results of many studies.
- REVIEW_OR_COMMENTARY: a review, commentary, reply, critique, theory or methods paper with no new test of the finding.
- OTHER_NEW_STUDY: a new study on a related question that does not test the earlier finding.
- CANNOT_TELL: the text is too thin to say.

2. "tests_this_finding": does the later paper test the finding described under EARLIER STUDY? YES, NO or CANNOT_TELL.

3. "result" — only if kind is NEW_DATA_REPLICATION or REANALYSIS, what the later paper reports about that finding:
- FOUND: the finding appeared again.
- NOT_FOUND: it did not appear, or no reliable effect was found.
- MIXED: it appeared in some tests, conditions or measures but not in others.
- NO_RESULT_STATED: the text does not state the result.
A test counts as finding the effect only where the paper reports the effect as present (for example significant, reliable or clearly shown); an estimate that merely points the expected way but is not significant does not count.
For any other kind, answer NOT_APPLICABLE.
{cited_q}
Quotes: for "kind" and for "result", copy up to 25 consecutive words exactly from the LATER PAPER text above (its title or abstract) that show your answer: one place, no changes, no ellipsis. A quote may be empty only when the answer is CANNOT_TELL, NO_RESULT_STATED or NOT_APPLICABLE.

Reply with JSON only, in this form:
{{"kind": "...", "kind_quote": "...", "tests_this_finding": "...", "result": "...", "result_quote": "..."{cited_key}}}"""
CITED = "\nFORRT'S REFERENCE FOR THE LATER PAPER: {ref}\n"
CITED_Q = '\n4. "is_cited_paper": is the LATER PAPER above the paper named in FORRT\'S REFERENCE? YES, NO or CANNOT_TELL.\n'
CITED_KEY = ', "is_cited_paper": "..."'
ANSWERS = {
    "kind": ["NEW_DATA_REPLICATION", "REANALYSIS", "META_ANALYSIS", "REVIEW_OR_COMMENTARY", "OTHER_NEW_STUDY", "CANNOT_TELL"],
    "tests_this_finding": ["YES", "NO", "CANNOT_TELL"],
    "result": ["FOUND", "NOT_FOUND", "MIXED", "NO_RESULT_STATED", "NOT_APPLICABLE"],
    "is_cited_paper": ["YES", "NO", "CANNOT_TELL"],
}
EMPTY_OK = {"kind": {"CANNOT_TELL"}, "result": {"NO_RESULT_STATED", "NOT_APPLICABLE"}}


def messages(item: dict) -> list:
    ref = item.get("cited_ref")
    body = BODY.format(original=item["original"], later=item["later"], cited=CITED.format(ref=ref) if ref else "",
                       cited_q=CITED_Q if ref else "", cited_key=CITED_KEY if ref else "")
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": body}]
