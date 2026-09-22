"""Write the sentence a player actually reads.

A card shows one claim and asks "did it replicate?". The claims the deck has been dealing come straight out of
FReD's `description` column, and most of them cannot be played: "Main effect of condition on the applicability of
the insanity defense", "Participants judged the man as more likely to be the pilot than the woman," (the comma is
in the data), and a 400-character methods paragraph about conjugate reinforcement schedules. 16% are under 60
characters and 6% over 250. The owner's verdict on them was that they are not good enough, and that is the whole
deck, not just the finds this pipeline adds.

This asks a model for two sentences per card: what the original study claimed, and how it was tested. The design
is `docs/planning/designs/D3-game.md` §8, written before any of this existed; the rules below are its rules plus
what reading the bad examples taught.

    python -m pipeline claims --pilot            # 24 cards spread across disciplines and decades, ~$0.01
    python -m pipeline claims --all --max-usd 1  # the whole deck
    python -m pipeline claims --report           # what is written, what is flagged, what leaks

Results are cached per card in data/cache/claims/<model>/<version>/ so runs resume and never pay twice, and
consolidated into data/discovery/claims.json — NOT data/build/, which every build wipes first. A new prompt
version costs a full pass.

WHAT THE MODEL MUST NOT SEE. The replication's own verdict quote never enters the prompt. It is the answer, and a
model that has read it will shade the claim towards it however firmly it is told not to. Only the original study's
own material goes in: its title, the sentence it reported its result in, its sample size, its field and tags.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .load import CACHE, DISCOVERY
from .triage import URL, Meter, _key, balance

MODEL = "deepseek-v4-flash"
PROMPT_VERSION = "c5"
OUT = DISCOVERY / "claims.json"

# The same test game.py applies to a claim before it will deal it, kept here so a leak is caught when it is
# written rather than silently dropped at build time.
LEAK = re.compile(r"replicat|reproduc|debunk|retract|\\brobust\\b|did not hold|holds? up|"
                  r"fail(?:s|ed|ure)?\\s+to\\s+(?:replicat|reproduc)", re.I)  # see game.LEAK

SYSTEM = """You write cards for a game in which players read one psychology finding and guess whether a later
study found the same thing again. You are writing the card, never the answer. Reply with one JSON object, nothing
else.

You are given ONE original study. If an abstract is given, that is your source and the other fields are context.
If there is no abstract, the sentence the study reported its result in is your source.

BEFORE YOU WRITE ANYTHING, fill this sentence from the study's own words:

    "<who or what>, compared with <what else>, showed <more / less / none> <of what>."

If you cannot fill every slot from the source — because the only result given is an omnibus F, chi-square or
MANOVA with no direction in it, a table caption, a model-fit comparison, or a line saying results were
"generally supportive" — set "insufficient" to true and leave claim and method null. Do NOT take the direction
from the title, the topic tags, or a summary the input marks as terse or a hint.

ONE EXCEPTION, and the input will tell you when it applies: a summary marked CURATED AND HUMAN-WRITTEN was
written by a person who read the paper. It is an authoritative statement of the finding and you may fill the
slot sentence and the claim from it directly. When that is all you have, write the claim and leave "method"
null rather than refusing — a card with no method line is thinner, but it is still a card. A card asserting a direction the study never reported
is the worst thing you can produce, because the direction is exactly what the player is being asked about.

MORE REFUSALS. Each of these produced a card the reviewers would not deal.
- A CARD THAT ANSWERS ITSELF is not a card. If the claim you are about to write would be true by construction
  given the method you are about to write — a manipulation check ("participants rated the high-expertise source
  as more expert"), a definition restated, or the condition labels repeated back — set insufficient. The claim
  must be something a reader could have bet against.
- Do not add an outcome, a mechanism or a population the source never mentions. If the database summary
  speculates ("presumably because variety lowers perceived quantity") and the result does not show it, leave it
  out.
- IF THE SOURCE IS ABOUT A DIFFERENT STUDY than the summary, refuse. Sometimes the citation and the summary do
  not match — a summary about self-esteem beside a citation for a teacher-expectancy experiment, a summary about
  wolves beside a study of domestic dogs. You cannot write a card from two unrelated halves. Set insufficient.
- IF THERE IS NO STUDY, refuse. A trade book, a paper the curators could not locate, a sample size recorded as
  NA with no design anywhere in the material: there is nothing for a later study to have found again.
- A DEFINITION IS NOT A FINDING. "Poor self-esteem lowers self-appreciation", "reinforcing a behaviour that
  cannot occur at the same time as self-injury reduces self-injury" — the second follows from the first by
  meaning alone. If the claim is true by what the words mean, set insufficient.
- A CIRCULAR CLAIM IS NOT A FINDING. If the groups being compared were DEFINED by the measures the claim
  compares them on — profiles derived by clustering on delinquency, then said to differ in delinquency — set
  insufficient.
- A PREDICTION IS NOT A RESULT. If the sentence you are given says what the authors expected ("we predicted
  increased reaction times and/or reduced frequency") and never says what happened, set insufficient.
- A NULL IS NOT AN EQUIVALENCE. "No significant difference between front and back vowels" does NOT license
  "front and back vowels convey the same size". Write the absence as an absence, with the word "no" or "not" in
  it: "the vowels in a brand name make no difference to the size it conveys". Never write it as an equivalence
  ("the same", "equally", "as ... as"): a study that failed to find a difference did not find a sameness, and a
  player asked whether "X and Y are the same" replicated is being asked a different question.

AN ABSENCE IS A FINDING. If the study reports that something did not happen, that two groups did not differ, or
that an animal does not do a thing, say so plainly. The rule against revealing how a later study turned out is
NOT a rule against negative findings, and turning an absence into a positive claim misstates the original study.

Then write:

"claim" — what this study found, as its own authors would state it, present tense, at most 30 words. A finding
  about people (or animals), not about an experiment: say what is true of whom, not which condition differed
  from which. A reader who knows nothing about the study must be able to agree or disagree with it.
  THE TWO SIDES OF A COMPARISON MUST BE DIFFERENT THINGS. "People respond faster to words they later judge new
  than to words they correctly judge new" compares a set with a subset of itself. Read your own sentence back
  and check that the two groups cannot overlap.
  WRITE AT THE READER'S LEVEL, NOT THE PAPER'S. No construct name doing the work unexplained — not "executive
  control", "implied wage rates", "response set", "letters that call for the opposite response", not a brain
  region. Say what a person did or experienced. If the finding cannot be said without naming a construct,
  explain the construct inside the claim in ordinary words or set insufficient.
    good: "Holding a warm drink makes people judge a stranger as friendlier."
    bad:  "Main effect of condition on the applicability of the insanity defense."
    bad:  "Participants rated the high-expertise source as more expert."

"method" — how it was tested, one or two sentences, self-contained. Someone who cannot see the paper must be
  able to picture it: describe what was actually varied in plain words rather than naming a task or construct
  ("a scrambled-sentence task", "reference points", "bifactor structure") and leaving it unexplained.
  NEVER take a sample size from a test statistic. The 16 in "F(1, 16) = .71" is a degrees-of-freedom figure, not
  16 people. If the material gives you no sample size, write the method without one.
  Give the sample size in DIGITS, always, inside the sentence — "54 adults", "2,428 people" — never spelled out
  and never appended as a separate sentence. One card in the pilot spelled it, one wrote "There were 338
  participants." at the end, and a reader who notices which cards do which is reading the writer, not the study.
  The sample size given to you may count something other than people — networks, countries, dogs, sessions, or
  one experiment out of several. Say what it counts. If the number cannot plausibly support the design you are
  describing, leave it out rather than printing a figure that makes the study look impossible.
  Describe people as a paper written today would; do not carry forward outdated clinical or racial terms.
  No statistics, no test names, no p-values.
    good: "41 students held a cup of hot or iced coffee for a moment, then rated the personality of a person
    described to them."

"effect_label" — three to five words naming the phenomenon, for the reveal screen. Title case. No author names.

HARD RULES.
- NEVER mention replication, reproduction, whether anything held up, controversy, fame, or the passage of time.
  The words "replicate", "fail", "robust", "null" and their relatives must not appear in the claim or method.
- NEVER mention authors, years, journals, or how well known the study is.
- NO HEDGES, on any card. Not "tend to", "partly", "somewhat", "may", "often", "generally", "most", "can".
  State the finding flat. A writer hedges more when it doubts the finding, and a player who notices that is
  reading your confidence instead of the study — which is a different game, and an unfair one. If a finding is
  genuinely conditional, put the condition in the claim as a fact ("among children under four"), not as a hedge.
- Do not argue for the finding. State it and stop. No "even though", "even when", "surprisingly", and no clause
  whose only work is to tell the player the result is remarkable.
- Write what the study claimed, not what is true. If the finding is now doubted, that is not yours to signal.
- NO MODALS AND NO "ASSOCIATED WITH". Not "can increase", "is associated with", "is linked to", "predicts".
  Every claim asserts flatly: "X makes Y", "people who X are more Y". One card in the deck said "CAN increase"
  and one said "IS ASSOCIATED WITH", and both stood out from every other card.
- NEVER carry outdated clinical or racial wording from an old paper onto the card. "A profoundly retarded adult"
  must not reach a player. Describe the person as a paper written today would.
- IF THE ABSTRACT COVERS SEVERAL STUDIES and the sample size you are given belongs to one of them, do not write
  "across seven studies, 93 participants". Either give the number for the study you are describing, or leave the
  number out.
- Do not invent. A guessed card is worse than a missing one.

Return exactly these keys:
{
 "slot_sentence": "<the sentence above, filled in, or empty if you could not fill it>",
 "claim": "<= 30 words, present tense, or null>",
 "method": "<one or two sentences, or null>",
 "effect_label": "<3-5 words, Title Case>",
 "design": "main_effect" | "interaction" | "correlation" | "other",
 "iv_kind": "manipulation" | "measured" | "natural",
 "dv_kind": "behaviour" | "self_report" | "physiological" | "judgment" | "performance",
 "n_participants": <integer or null>,
 "n_counts": "<what that number counts: people, networks, countries, dogs, sessions...>",
 "finding_is_absence": <true|false>,
 "insufficient": <true|false>,
 "notes": "<= 15 words, or empty>"
}"""


def _user_msg(card: dict) -> str:
    bits = [f"TITLE OF THE STUDY: {card['title_o']}"]
    if card.get("year_o"):
        bits.append(f"YEAR: {card['year_o']}")
    if card.get("discipline"):
        bits.append(f"FIELD: {card['discipline']}")
    if card.get("tags"):
        bits.append(f"TOPIC TAGS: {card['tags']}")
    if card.get("n_o"):
        bits.append(f"SAMPLE SIZE: {card['n_o']}")
    if card.get("description"):
        label = ("A CURATED, HUMAN-WRITTEN STATEMENT OF THE FINDING (authoritative: it was written by a person "
                 "who read the paper, and you may take the direction from it)" if card.get("tier") == "famous"
                 else "HOW THE DATABASE SUMMARISES THE FINDING (a terse, often garbled field; treat as a hint only)")
        bits.append(f"{label}:\n  {card['description']}")
    if card.get("claim_text_o"):
        label = ("THE PAPER, ITS DESIGN AND ITS SAMPLE SIZES" if card.get("tier") == "famous"
                 else "THE SENTENCE THE STUDY REPORTED ITS RESULT IN")
        bits.append(f"{label}:\n  {_strip_fame(card['claim_text_o'])}")
    if card.get("abstract_o"):
        bits.append(f"THE STUDY'S OWN ABSTRACT (your best source; prefer it over everything above):\n"
                    f"  {card['abstract_o'][:3000]}")
    return "\n".join(bits)


_FAME = re.compile(r"\[?\s*citations?\s*=[^\]\n]*\]?", re.I)


def _strip_fame(s: str) -> str:
    """Citation counts out of the input. How famous a study is predicts whether it replicated, and the card is
    not allowed to carry that; the curated famous-effects notes have it inline."""
    return _FAME.sub("", s).strip()


def write_one(card: dict, key: str, meter: Meter, cache_dir: Path) -> dict | None:
    gid = re.sub(r"[^A-Za-z0-9._-]+", "_", card["id"])[:120]
    f = cache_dir / f"{gid}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    if meter.over:
        return None
    body = json.dumps({
        "model": MODEL, "temperature": 0, "max_tokens": 600, "thinking": {"type": "disabled"},
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": _user_msg(card)}],
    }).encode()
    d = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(URL, data=body, headers={"Authorization": f"Bearer {key}",
                                                                  "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.loads(r.read())
            break
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == 4:
                print(f"    give up {gid}: {e}")
                return None
            time.sleep(2 * 2 ** attempt)
    meter.add(d.get("usage") or {})
    try:
        out = json.loads(d["choices"][0]["message"]["content"])
    except (KeyError, json.JSONDecodeError):
        out = {"insufficient": True, "notes": "model returned no usable JSON"}
    rec = {"id": card["id"], "model": MODEL, "prompt_version": PROMPT_VERSION,
           "usage": d.get("usage"), **out, **_flags(out, card.get("description") or "")}
    f.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    return rec


# A finding stated as an absence — "goats do not follow a human's gaze" — is the one thing the writer reliably
# gets backwards, because a rule against signalling null results reads like a rule against negative sentences.
# One reversal in the first 48 claims. These are the markers strong enough to mean the finding itself is an
# absence, not a contrast inside a sentence ("people who do NOT expect a mug" is not an absence).
_ABSENCE = re.compile(r"\b(?:do|does|did|was|were|is|are)\s+not\b|\bno\s+(?:effect|difference|evidence|"
                      r"relationship|advantage|benefit|association|correlation)\b|\bfail(?:s|ed)?\s+to\b|"
                      r"\bunable\s+to\b|\bneither\b", re.I)


# Hedges are a leak channel of their own: a writer reaches for "tend to" when it doubts the finding, so a player
# who notices the pattern is reading the writer's confidence rather than the study. Causal verbs are NOT on this
# list — "makes", "increases" reveal that the study was an experiment, but so does the method line, which says
# what was manipulated. Hiding the design in the claim while printing it underneath buys nothing.
# Only the hedging senses. Bare "often" and "most" are ordinary words — "how often parents play", "the stimuli
# they most prefer" — and flagging them buried the real hedges in false positives.
_HEDGE = re.compile(r"\b(?:tend(?:s|ed)? to|partly|somewhat|may|might|generally|typically|mostly|"
                    r"can\s+be|appears?\s+to|seems?\s+to|suggest(?:s|ed)?)\b|\bmost\s+(?:people|participants|of)\b",
                    re.I)


# A claim that hedges its verb stands out from every card that asserts. Both of the deck's two instances were
# found by a reviewer reading all 80 side by side, which is not a check that scales; this one does.
_WEAK = re.compile(r"\bcan\s+(?:increase|reduce|make|cause|lead|improve|impair)|is\s+associated\s+with|"
                   r"is\s+linked\s+to|\bpredicts\b", re.I)
# Wording no card may carry to a player, however old the paper it came from.
_DATED = re.compile(r"\bretard(?:ed|ate|ation)\b|\bmongoloid\b|\bfeeble[- ]minded\b|\bcripple[ds]?\b|"
                    r"\bmidget\b|\bnegro(?:es)?\b|\boriental\b|\bhysteric(?:al|s)?\s+wom[ae]n\b", re.I)


def _flags(out: dict, source: str = "") -> dict:
    """Mechanical checks applied to every claim as it is written, so nothing rests on the model obeying.

    A leak is the one that matters: the card is the question, so a word like "failed" in it hands over the answer.
    The rest are shape — a claim that runs past 30 words or stops mid-sentence is the defect the current deck has.
    """
    claim, method = (out.get("claim") or "").strip(), (out.get("method") or "").strip()
    # Only what the player sees BEFORE answering can leak. The effect label is the reveal screen's heading, and
    # "Productive Failure Learning" is the actual name of the phenomenon — flagging it as a leak would force the
    # writer to rename real effects.
    text = f"{claim} {method}"
    return {
        "leaks": bool(LEAK.search(text)),
        "label_leaks": bool(LEAK.search(out.get("effect_label") or "")),
        "claim_words": len(claim.split()) if claim else 0,
        "too_long": len(claim.split()) > 34,
        # a closing quote or bracket after the stop is fine: 'the range they call "big."'
        "unterminated": bool(claim) and claim.rstrip('"\u201d\')]').rstrip()[-1:] not in ".!?",
        "has_stats": bool(re.search(r"\b[pF]\s*[<=>]|\bp\s*[<=>]\s*\.?\d|η|Cohen|\bCI\b|\bSD\b", text)),
        # a spelled-out sample size is a formatting tell, not a style choice: it has to be the same on every card
        "spelled_n": bool(re.search(r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
                                    r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|"
                                    r"thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand)[\s-]"
                                    r"(?:\w+\s+){0,3}?(?:participants|people|students|adults|children|"
                                    r"undergraduates|volunteers|subjects|dogs|men|women)\b", method, re.I)),
        # the source says the study found an absence and the claim does not say so: read it before dealing it
        "polarity_check": bool(source) and bool(_ABSENCE.search(source)) and not bool(_ABSENCE.search(claim)),
        # The writer itself says the finding is an absence, and then phrases the claim as an equivalence:
        # "no significant difference between front and back vowels" becomes "front and back vowels convey the
        # same size", which is a positive claim the study never made. Its own slot sentence gives it away.
        "absence_written_positive": bool(out.get("finding_is_absence")) and bool(claim)
                                    and not _ABSENCE.search(claim) and not re.search(r"\bno\b|\bnot\b|\bnone\b|"
                                                                                     r"\bneither\b", claim, re.I),
        "no_method": bool(claim) and not method,
        "hedged": bool(_HEDGE.search(claim)),
        "weak_verb": bool(_WEAK.search(claim)),
        "dated_language": bool(_DATED.search(text)),
        # a claim with no method line is thinner but still playable; a card with no claim is not a card
        # An absence written as an equivalence is not a card we can score somebody against, so it does not
        # reach the deck even though the sentence is otherwise fine.
        "ok": bool(claim) and not out.get("insufficient")
              and not (bool(out.get("finding_is_absence")) and not _ABSENCE.search(claim)
                       and not re.search(r"\bno\b|\bnot\b|\bnone\b|\bneither\b", claim, re.I)),
    }


def cards(g: dict, items: list[dict], abstracts: dict[str, dict] | None = None) -> list[dict]:
    """The input each card gets, gathered from the original study and nothing else.

    The replication's verdict quote is deliberately absent — see the module docstring. So is anything about how
    the replication turned out, including which attempt produced it.
    """
    A, P = g["attempts"], g["papers"]
    abstracts = abstracts or {}
    rows_by_group: dict[tuple, list[dict]] = defaultdict(list)
    for a in A.values():
        if a["type"] != "replication":
            continue
        for r in a["rows"]:
            study = str(r.get("study_o") or "").strip().lower() or "-"
            rows_by_group[(a["doi_o"], study)].append(r)
    by_gid = {"g" + hashlib.md5(f"{doi}|{s}".encode()).hexdigest()[:9]: (doi, rs)
              for (doi, s), rs in rows_by_group.items()}
    out = []
    # The famous tier's own material is thinner — a curated one-line description and a paragraph naming the
    # original paper — and two of its fields, `critiques` and `replication_es`, ARE the answer. They are not in
    # the record this reads from, and must never be added to it.
    fam_by_gid = {"f" + hashlib.md5(e["key"].encode()).hexdigest()[:9]: e for e in g["effects"].values()
                  if e.get("famous")}
    for it in items:
        if it["tier"] == "famous":
            e = fam_by_gid.get(it["id"])
            f = (e or {}).get("famous") or {}
            out.append({
                "id": it["id"], "tier": "famous", "doi_o": None,
                "title_o": e["name"] if e else it.get("effect_name"),
                "year_o": f.get("original_year"), "discipline": e.get("discipline") if e else None,
                "tags": None, "n_o": None,
                "description": f.get("description"),
                # names the study and gives its design and sample sizes; says nothing about how it turned out
                "claim_text_o": f.get("original_paper"),
                # famous entries carry no DOI, so their abstract is stored under the card's own id — and only
                # when the title matched closely enough to be the same paper (pipeline/authors.py)
                "abstract_o": (abstracts.get(it["id"]) or {}).get("abstract"),
            })
            continue
        if it["tier"] != "study":
            continue
        doi, rs = by_gid.get(it["id"], (None, []))
        p = P.get(doi, {})
        first = lambda k: next((r[k] for r in rs if r.get(k)), None)  # noqa: E731
        out.append({
            "id": it["id"], "tier": "study", "doi_o": doi,
            "title_o": p.get("title") or it.get("claim"), "year_o": p.get("year"),
            "discipline": first("discipline"), "tags": first("tags"), "n_o": first("n_o"),
            "description": first("description"), "claim_text_o": first("claim_text_o"),
            # the study's own abstract, where OpenAlex has one: the only source here that states a finding in
            # sentences rather than in a test statistic
            "abstract_o": (abstracts.get(doi) or {}).get("abstract"),
        })
    return out


def found_cards(candidates: list[dict]) -> list[dict]:
    """Cards from our own finds: one per original study, as the game deals them.

    Only finds that clear both hand-read audits — a link band read at 90% or better and an outcome the model was
    confident about — and only originals whose finds agree, because a card is one answer. The claim is written
    from the ORIGINAL's abstract, which is why this exists at all: the nine-word label we hold for these
    ("Physical warmth promotes interpersonal warmth") is what the owner rejected.
    """
    from .queue import TRUSTED_LINKS
    keep = [c for c in candidates
            if c.get("origin") == "retested_discovery" and c.get("group") == "replication"
            and c.get("field") == "psychology" and c.get("outcome") in ("successful", "failed")
            and c.get("doi_o") and c.get("abstract_o")
            and (c.get("link_method"), c.get("link_confidence")) in TRUSTED_LINKS
            and (c.get("outcome_confidence") or 0) >= 0.8]
    by_original: dict[str, list[dict]] = defaultdict(list)
    for c in keep:
        by_original[c["doi_o"]].append(c)
    out = []
    for doi, cs in sorted(by_original.items()):
        if len({c["outcome"] for c in cs}) != 1:
            continue                                   # finds disagree: no single answer to score against
        c0 = cs[0]
        out.append({
            "id": "d" + hashlib.md5(doi.encode()).hexdigest()[:9], "tier": "found", "doi_o": doi,
            "title_o": c0.get("title_o"), "year_o": c0.get("year_o"),
            "discipline": None, "tags": None, "n_o": None,
            "description": None, "claim_text_o": None,
            "abstract_o": c0.get("abstract_o"),
        })
    return out


def _queue_candidates(g: dict) -> list[dict]:
    """The review queue exactly as the build assembles it, so a card and its queue row cannot disagree."""
    from . import load, queue
    return queue.build_retested(load.load_triaged(),
                                load.merged_links(), g,
                                load.load_known_replication_dois(), load.load_known_osf_ids(),
                                load.load_surname_frequency(), load.load_osf(), load.load_original_authors())


def _pilot(cs: list[dict], n: int = 24) -> list[dict]:
    """A spread, not a random draw: the point of a pilot is to meet the awkward cases early.

    Two per discipline where there are two, and within a discipline the shortest and the longest existing
    description — those are the two ways the current claims fail, and a prompt that handles both handles the rest.
    """
    by_disc: dict[str, list[dict]] = defaultdict(list)
    for c in cs:
        by_disc[c.get("discipline") or "unknown"].append(c)
    picked = []
    for disc in sorted(by_disc):
        group = sorted(by_disc[disc], key=lambda c: len(c.get("description") or ""))
        picked += [group[0], group[-1]] if len(group) > 1 else group[:1]
    return picked[:n]


def run(mode: str, max_usd: float, workers: int, limit: int | None, tier: str | None = None) -> int:
    from . import game, load, registry, score
    from .ids import EffectLedger
    from .load import ROOT
    src = {"flora": load.load_flora(), "fred": load.load_fred(), "legacy": load.load_legacy(),
           "famous": load.load_famous(), "openalex": load.load_openalex(), "merges": load.load_merges()}
    g = registry.build(src, EffectLedger(ROOT / "data" / "curated" / "registry" / "effect_ids.csv"))
    score.score(g)
    items, _ = game.build(g)
    cs = cards(g, items, load.load_original_authors())
    if tier in (None, "found"):
        cs += found_cards(_queue_candidates(g))
    if tier:
        cs = [c for c in cs if c["tier"] == tier]
    if mode == "pilot":
        cs = _pilot(cs)
    if limit:
        cs = cs[:limit]
    key = _key()
    b0 = balance(key)
    cache_dir = CACHE / "claims" / MODEL / PROMPT_VERSION
    cache_dir.mkdir(parents=True, exist_ok=True)
    meter = Meter(max_usd)
    print(f"  {len(cs)} cards · model {MODEL} · prompt {PROMPT_VERSION} · cap ${max_usd:.2f} · balance ${b0}")
    results, t0 = [], time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(write_one, c, key, meter, cache_dir) for c in cs]
        for i, fu in enumerate(as_completed(futs), 1):
            r = fu.result()
            if r:
                results.append(r)
            if i % 100 == 0:
                print(f"    {i}/{len(cs)} · est ${meter.usd:.3f} · {time.time() - t0:.0f}s")
    b1 = balance(key)
    real = (b0 - b1) if (b0 is not None and b1 is not None) else float("nan")
    print(f"  done: {len(results)} written, {len(cs) - len(results)} not (cap or errors) · "
          f"est ${meter.usd:.3f} · real spend ${real:.3f}")
    if mode == "all":
        # merge, never replace: a run restricted to one tier would otherwise drop every other tier's claims out
        # of the file, and the build reads this file to decide what the deck says.
        existing = {r["id"]: r for r in json.loads(OUT.read_text(encoding="utf-8"))} if OUT.exists() else {}
        merged = {**existing, **{r["id"]: r for r in results}}
        OUT.write_text(json.dumps(sorted(merged.values(), key=lambda r: r["id"]), ensure_ascii=False),
                       encoding="utf-8")
        print(f"  wrote {OUT} · {len(merged)} claims in all ({len(results)} from this run)")
    report(results)
    return 0


def report(results: list[dict] | None = None) -> int:
    if results is None:
        if not OUT.exists():
            print("nothing written yet — run `python -m pipeline claims --pilot` first")
            return 0
        results = json.loads(OUT.read_text(encoding="utf-8"))
    n = len(results)
    c = Counter()
    for r in results:
        for k in ("ok", "leaks", "label_leaks", "polarity_check", "hedged", "no_method", "too_long",
                  "unterminated", "has_stats"):
            c[k] += bool(r.get(k))
        c["insufficient"] += bool(r.get("insufficient"))
    print(f"\n   {n} claims written")
    for k in ("ok", "insufficient", "leaks", "label_leaks", "polarity_check", "absence_written_positive",
              "hedged", "weak_verb", "dated_language", "spelled_n", "no_method", "too_long", "unterminated", "has_stats"):
        print(f"     {k:<15} {c[k]:>4}  {c[k] / n:>4.0%}" if n else "")
    lens = [r["claim_words"] for r in results if r.get("claim_words")]
    if lens:
        lens.sort()
        print(f"     claim length: median {lens[len(lens) // 2]} words, range {lens[0]}–{lens[-1]}")
    return 0


# ---------------------------------------------------------------- second pass: say it in ordinary words

PLAIN_VERSION = "p1"

# What "written at the paper's level rather than the player's" looks like from the outside. Not a definition of
# jargon — a net wide enough to catch the cards worth re-asking about, at 19% of the deck.
_LONG = re.compile(r"\b\w{13,}\b")
_JARGON = re.compile(r"\b(?:paradigm|stimuli|stimulus|valence|salien\w+|construct|dyad\w*|congruen\w+|priming|"
                     r"primed|latency|latencies|cortex|cortical|gyrus|amygdala|cerebell\w+|neural|stereotypy|"
                     r"prospective memory|response conflict|task[- ]switch\w*|n[- ]back|implicit association|"
                     r"factor structure|bifactor|latent|mediat\w+|moderat\w+|self[- ]construal|affordance|"
                     r"schema|heuristic|utilitarian|deontolog\w+|tact\w*|mand\w*|desensitiz\w+|"
                     r"cognitive reflection|oral motor)\b", re.I)

PLAIN_SYSTEM = """You are editing one card in a game. A player reads a psychology finding and guesses whether a
later study found the same thing again. The card below is accurate but reads like the paper it came from, and the
player has no training in psychology. Say the same thing in ordinary words.

RULES.
- Do NOT change what is claimed. Not the direction, not who it is about, not how strong it is. You are changing
  the words, nothing else.
- Explain a technical term inside the sentence or drop it for what it means: "vocal stereotypy" is repetitive
  noises a child makes; "tacts and mands" are naming things and asking for things; "cognitive reflection" is
  overriding a first instinct.
- Keep it under 30 words, present tense, flat and unhedged. No "tend to", "may", "can", "is associated with".
- Never mention replication, a later study, fame, controversy, authors or years.
- If the finding genuinely cannot be said in ordinary words without changing what it claims, return the claim
  UNCHANGED and set "changed" to false. An accurate hard card beats a readable wrong one.

Return one JSON object: {"claim": "<the plain version, or the original unchanged>",
                         "method": "<the method line in ordinary words, or unchanged, or null>",
                         "changed": <true|false>, "note": "<= 12 words"}"""


def _plain_user(card: dict, rec: dict) -> str:
    bits = [f"CLAIM AS IT STANDS: {rec.get('claim')}"]
    if rec.get("method"):
        bits.append(f"METHOD AS IT STANDS: {rec['method']}")
    if card.get("abstract_o"):
        bits.append(f"THE STUDY'S ABSTRACT, so you can tell what the terms mean:\n  {card['abstract_o'][:2000]}")
    elif card.get("claim_text_o"):
        bits.append(f"WHAT THE STUDY REPORTED:\n  {card['claim_text_o'][:1200]}")
    return "\n".join(bits)


def needs_plain(claim: str) -> bool:
    return bool(_JARGON.search(claim)) or bool(_LONG.search(claim)) or len(claim.split()) > 28


def _meaning_changed(old: str, new: str) -> str | None:
    """Did the rewrite change what is claimed, rather than how it is said?

    The first version of this guard rejected any content word the source did not already contain, which rejected
    every rewrite: replacing "vocal stereotypy" with "repetitive noises a child makes" introduces new words by
    definition, and that is the entire point of the pass. What must not change is the CLAIM — its polarity, the
    direction of its comparison, and its numbers. Those are checkable; vocabulary is not.
    """
    # Both tests are ASYMMETRIC on purpose. A paraphrase legitimately drops the word that carried the direction
    # — "reduces postoperative pain" becomes "lowers their pain", "reduces the false fame effect" becomes "stops
    # repeated names from feeling famous" — and an earlier symmetric version rejected every one of those. Only a
    # genuine reversal is a meaning change: an increase written as a decrease, or an absence written as a
    # presence. Gaining a negation ("no longer makes the noises" for "reduces the noises") is fine.
    neg = lambda t: bool(re.search(r"\bno\b|\bnot\b|\bnone\b|\bneither\b|\bnever\b|\bwithout\b", t, re.I))  # noqa: E731
    if neg(old) and not neg(new):
        return "polarity"
    up = r"\b(?:more|higher|greater|larger|better|faster|increase\w*|raises?|improves?)\b"
    dn = r"\b(?:less|fewer|lower|smaller|shorter|worse|slower|decrease\w*|reduces?|impairs?)\b"
    o_up, o_dn = bool(re.search(up, old, re.I)), bool(re.search(dn, old, re.I))
    n_up, n_dn = bool(re.search(up, new, re.I)), bool(re.search(dn, new, re.I))
    if (o_up and not o_dn and n_dn and not n_up) or (o_dn and not o_up and n_up and not n_dn):
        return "direction"
    nums = lambda t: set(re.findall(r"\d+(?:\.\d+)?", t))  # noqa: E731
    if nums(new) - nums(old):
        return "new numbers"
    return None


def plain_one(card: dict, rec: dict, key: str, meter: Meter, cache_dir: Path) -> dict | None:
    gid = re.sub(r"[^A-Za-z0-9._-]+", "_", rec["id"])[:120]
    f = cache_dir / f"{gid}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    if meter.over:
        return None
    body = json.dumps({
        "model": MODEL, "temperature": 0, "max_tokens": 500, "thinking": {"type": "disabled"},
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": PLAIN_SYSTEM},
                     {"role": "user", "content": _plain_user(card, rec)}],
    }).encode()
    d = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(URL, data=body, headers={"Authorization": f"Bearer {key}",
                                                                  "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.loads(r.read())
            break
        except (urllib.error.URLError, TimeoutError):
            if attempt == 4:
                return None
            time.sleep(2 * 2 ** attempt)
    meter.add(d.get("usage") or {})
    try:
        out = json.loads(d["choices"][0]["message"]["content"])
    except (KeyError, json.JSONDecodeError):
        out = {"changed": False}
    new = (out.get("claim") or "").strip()
    flags = _flags({**rec, "claim": new or rec.get("claim"), "method": out.get("method") or rec.get("method")},
                   card.get("description") or "")
    changed = _meaning_changed(rec.get("claim") or "", new) if new else None
    rec2 = {"id": rec["id"], "plain_version": PLAIN_VERSION, **out, "drifted": changed,
            "accepted": bool(new) and out.get("changed") and flags["ok"] and not flags["leaks"]
                        and not changed and len(new.split()) <= 34}
    f.write_text(json.dumps(rec2, ensure_ascii=False), encoding="utf-8")
    return rec2


def run_plain(max_usd: float, workers: int, limit: int | None) -> int:
    """Re-ask, in ordinary words, only the cards that read like the paper."""
    from . import game, load, registry, score
    from .ids import EffectLedger
    from .load import ROOT
    src = {k: getattr(load, f"load_{k}")() for k in ("flora", "fred", "legacy", "famous", "openalex", "merges")}
    g = registry.build(src, EffectLedger(ROOT / "data" / "curated" / "registry" / "effect_ids.csv"))
    score.score(g)
    items, _ = game.build(g, load.load_claims())
    cards_by_id = {c["id"]: c for c in cards(g, items, load.load_original_authors())}
    cards_by_id.update({c["id"]: c for c in found_cards(_queue_candidates(g))})
    written = {r["id"]: r for r in json.loads(OUT.read_text(encoding="utf-8"))} if OUT.exists() else {}
    todo = [r for gid, r in sorted(written.items())
            if r.get("ok") and r.get("claim") and needs_plain(r["claim"]) and gid in cards_by_id]
    if limit:
        todo = todo[:limit]
    key = _key()
    b0 = balance(key)
    cache_dir = CACHE / "claims" / MODEL / f"plain-{PLAIN_VERSION}"
    cache_dir.mkdir(parents=True, exist_ok=True)
    meter = Meter(max_usd)
    print(f"  {len(todo)} of {sum(1 for r in written.values() if r.get('ok'))} claims read like the paper · "
          f"cap ${max_usd:.2f} · balance ${b0}")
    done = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(plain_one, cards_by_id[r["id"]], r, key, meter, cache_dir) for r in todo]
        for fu in as_completed(futs):
            if (r := fu.result()):
                done.append(r)
    acc = [r for r in done if r.get("accepted")]
    for r in acc:
        w = written[r["id"]]
        w["claim_before_plain"], w["claim"] = w["claim"], r["claim"]
        if r.get("method"):
            w["method_before_plain"], w["method"] = w.get("method"), r["method"]
        w.update(_flags(w, (cards_by_id[r["id"]].get("description") or "")))
        w["plain"] = True
    OUT.write_text(json.dumps(sorted(written.values(), key=lambda r: r["id"]), ensure_ascii=False), encoding="utf-8")
    b1 = balance(key)
    real = (b0 - b1) if (b0 is not None and b1 is not None) else float("nan")
    print(f"  {len(acc)} rewrites accepted, {sum(1 for r in done if r.get('drifted'))} rejected for drifting from "
          f"the source, {sum(1 for r in done if not r.get('changed'))} left alone by the editor · "
          f"est ${meter.usd:.3f} · real ${real:.3f}")
    left = sum(1 for r in written.values() if r.get("ok") and needs_plain(r.get("claim") or ""))
    print(f"  claims still reading like the paper: {left}")
    return 0
