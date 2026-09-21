"""Say what each find tested, how it differs, and what it showed, in plain English.

Assembled from what is already known about a find rather than written by a model. Three parts, and they are not
equally well covered, so each is allowed to be absent rather than padded:

  tested  — the one-line description the triage step took from the paper (82% of linked finds), else the
            original's title (100%). This one is solid.
  differs — what the replication changed. Thin and honest about it: the authors declare direct/close/conceptual
            for 10%, a concrete difference (sample size, online, another country, a modified paradigm) can be
            read out of the abstract for 39%, and whether the team was independent is known for 54%. Anything
            more specific needs somebody to read the paper.
  shows   — the outcome and the replicating authors' own words (61% and 59%).

Nothing here is inferred beyond the text: if the abstract does not say the sample was larger, we do not say it.
"""
from __future__ import annotations

import re

_SENT = re.compile(r"\s+")
DIFFERENCES = (
    ("larger sample", re.compile(r"\b(larger sample|higher[- ]powered|high[- ]powered|well[- ]powered|"
                                 r"greater statistical power|\d+\s*times the (?:sample|size))\b", re.I)),
    ("run online", re.compile(r"\b(online|web[- ]based|mturk|prolific|amazon mechanical turk)\b", re.I)),
    ("a different population", re.compile(r"\b(cross[- ]cultural|different (?:population|culture|country)|non[- ]WEIRD|"
                                          r"in (?:a )?(?:german|turkish|dutch|chinese|japanese|indian|brazilian|polish|"
                                          r"spanish|french|italian|swedish|norwegian|serbian|hungarian|czech|iranian|korean))\b", re.I)),
    ("a modified procedure", re.compile(r"\b(modified|adapted|variant|different (?:paradigm|measure|stimuli|task)|"
                                        r"new (?:measure|paradigm))\b", re.I)),
    ("several labs", re.compile(r"\bmulti-?(?:site|lab)|many labs|\d+\s+(?:labs|sites|universities)\b", re.I)),
)
_N = re.compile(r"\b[Nn]\s*=\s*([\d,]{2,7})|\b([\d,]{2,7})\s+(?:participants|undergraduates|students|adults|subjects|respondents)\b")
SHOWS = {"successful": "found the effect again", "failed": "did not find the effect",
         "mixed": "found it only partly — some tests held, others did not"}


def _clean(s: str | None) -> str | None:
    if not s:
        return None
    t = _SENT.sub(" ", str(s)).strip(" .;:,")
    return t or None


def _sentence(s: str | None) -> str | None:
    t = _clean(s)
    return (t[0].upper() + t[1:] + ".") if t else None


def summary(c: dict, abstract: str | None) -> dict | None:
    """{tested, differs, shows, shows_quote} — any part may be None when we genuinely do not know it."""
    named = c.get("original_named") or {}
    text = f"{c.get('title_r') or ''}. {abstract or ''}"

    tested = _sentence(named.get("description"))
    tested_from = "the paper's own account of what it replicated"
    if not tested and c.get("title_o"):
        tested = _sentence(c["title_o"])
        tested_from = "the original paper's title, for want of anything better"

    bits: list[str] = []
    design = (c.get("declared_design") or {}).get("word")
    if design:
        bits.append(f"the authors call it a {design.lower()} replication")
    for label, rx in DIFFERENCES:
        if rx.search(text):
            bits.append(label)
    if (m := _N.search(text)):
        bits.append(f"N = {(m.group(1) or m.group(2))}")
    ind = (c.get("independence") or {}).get("verdict")
    if ind == "independent":
        bits.append("run by a team sharing no author with the original")
    elif ind == "shares_author":
        bits.append("run by a team that shares an author with the original")
    if (c.get("preregistered") or {}).get("is_registration"):
        bits.append("preregistered on OSF")
    differs = (bits[0][0].upper() + bits[0][1:] + (", " + ", ".join(bits[1:]) if len(bits) > 1 else "") + ".") if bits else None

    out = c.get("outcome")
    shows = f"The replication {SHOWS[out]}." if out in SHOWS else None
    return {"tested": tested, "tested_from": tested_from if tested else None,
            "differs": differs, "shows": shows, "shows_quote": _clean(c.get("outcome_quote")),
            "complete": bool(tested and differs and shows)}
