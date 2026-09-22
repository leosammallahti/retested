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
PROMPT_VERSION = "c1"
OUT = DISCOVERY / "claims.json"

# The same test game.py applies to a claim before it will deal it, kept here so a leak is caught when it is
# written rather than silently dropped at build time.
LEAK = re.compile(r"replicat|reproduc|fail|robust|did not hold|null effect|not significant|no effect|debunk|retract", re.I)

SYSTEM = """You write cards for a game in which players read one psychology finding and guess whether a later study
found the same thing again. You are writing the card, never the answer. Reply with one JSON object, nothing else.

You are given ONE original study: its title, the sentence in which it reported its result, its sample size, its
field, and its topic tags. Write two things about it for a curious adult who has no training in psychology.

"claim" — what this study found, stated as its own authors would state it, in the present tense, at most 30 words.
  It is a finding about people, not about an experiment: say what is true of whom, not which condition differed
  from which. A reader who knows nothing about the study must be able to agree or disagree with it.
    good: "Holding a warm drink makes people judge a stranger as friendlier."
    bad:  "Main effect of condition on the applicability of the insanity defense."
    bad:  "Belief that the communicator would support democratic policies was bigger in the favorable LIB condition."

"method" — how it was tested, in one or two sentences, including the number of participants written as a numeral
  and the key thing that was manipulated or measured. No statistics, no test names, no p-values.
    good: "Forty-one students held a cup of hot or iced coffee for a moment, then rated the personality of a
    person described to them."

"effect_label" — three to five words naming the phenomenon, for the reveal screen. Title case. No author names.

HARD RULES.
- NEVER mention replication, reproduction, whether anything held up, controversy, fame, or the passage of time.
  The words "replicate", "fail", "robust", "null" and their relatives must not appear anywhere in your output.
- NEVER mention authors, years, journals, or the study's reputation.
- Hedge identically whether the finding sounds obvious or absurd. Do not soften a surprising claim and do not
  sharpen a dull one; a player who could tell which is which from your wording is playing a different game.
- Write what the study claimed, not what is true. If the finding is now doubted, that is not yours to signal.
- Use the study's own numbers only for the sample size. No effect sizes, no test statistics.
- Do not invent. If the material you are given does not say what was found or how, leave "claim" or "method"
  null and set "insufficient" to true with a one-line reason. A guessed card is worse than a missing one.

Return exactly these keys:
{
 "claim": "<= 30 words, present tense, or null>",
 "method": "one or two sentences, or null>",
 "effect_label": "<3-5 words, Title Case>",
 "design": "main_effect" | "interaction" | "correlation" | "other",
 "iv_kind": "manipulation" | "measured" | "natural",
 "dv_kind": "behaviour" | "self_report" | "physiological" | "judgment" | "performance",
 "n_participants": <integer or null>,
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
        bits.append(f"HOW THE DATABASE SUMMARISES THE FINDING (often terse or garbled, treat as a hint):\n  {card['description']}")
    if card.get("claim_text_o"):
        bits.append(f"THE SENTENCE THE STUDY REPORTED ITS RESULT IN:\n  {card['claim_text_o']}")
    if card.get("abstract_o"):
        bits.append(f"ABSTRACT OF THE STUDY:\n  {card['abstract_o'][:2500]}")
    return "\n".join(bits)


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
           "usage": d.get("usage"), **out, **_flags(out)}
    f.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    return rec


def _flags(out: dict) -> dict:
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
        "unterminated": bool(claim) and claim[-1] not in ".!?",
        "has_stats": bool(re.search(r"\b[pF]\s*[<=>]|\bp\s*[<=>]\s*\.?\d|η|Cohen|\bCI\b|\bSD\b", text)),
        "ok": bool(claim) and bool(method) and not out.get("insufficient"),
    }


def cards(g: dict, items: list[dict]) -> list[dict]:
    """The input each card gets, gathered from the original study and nothing else.

    The replication's verdict quote is deliberately absent — see the module docstring. So is anything about how
    the replication turned out, including which attempt produced it.
    """
    A, P = g["attempts"], g["papers"]
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
    for it in items:
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
        })
    return out


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


def run(mode: str, max_usd: float, workers: int, limit: int | None) -> int:
    from . import game, load, registry, score
    from .ids import EffectLedger
    from .load import ROOT
    src = {"flora": load.load_flora(), "fred": load.load_fred(), "legacy": load.load_legacy(),
           "famous": load.load_famous(), "openalex": load.load_openalex(), "merges": load.load_merges()}
    g = registry.build(src, EffectLedger(ROOT / "data" / "curated" / "registry" / "effect_ids.csv"))
    score.score(g)
    items, _ = game.build(g)
    cs = cards(g, items)
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
        OUT.write_text(json.dumps(results, ensure_ascii=False), encoding="utf-8")
        print(f"  wrote {OUT}")
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
        for k in ("ok", "leaks", "too_long", "unterminated", "has_stats"):
            c[k] += bool(r.get(k))
        c["insufficient"] += bool(r.get("insufficient"))
    print(f"\n   {n} claims written")
    for k in ("ok", "insufficient", "leaks", "too_long", "unterminated", "has_stats"):
        print(f"     {k:<14} {c[k]:>4}  {c[k] / n:>4.0%}" if n else "")
    lens = [r["claim_words"] for r in results if r.get("claim_words")]
    if lens:
        lens.sort()
        print(f"     claim length: median {lens[len(lens) // 2]} words, range {lens[0]}–{lens[-1]}")
    return 0
