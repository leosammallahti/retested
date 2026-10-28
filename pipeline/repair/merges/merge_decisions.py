"""Merges decided by reading each case (merge_layout.py output, 28 Oct 2026): the same effect, on the same original
paper, under two or more names. Keyed by slug so the exact names come from effects.json. Writes
/root/retested-wiki/data/curated/merges.yaml. Cases left apart are listed at the bottom with the reason."""
import json, os, yaml
# first batch: slugs of the build before 28 Oct (build_before); second batch: slugs after the first merges
E = {e['slug']: e for e in json.load(open('/root/wiki-scratch/audit_20261028/build_before/effects.json', encoding='utf-8'))}
E2 = {e['slug']: e for e in json.load(open('/root/wiki-scratch/audit_20261028/build_after_first_merges/effects.json', encoding='utf-8'))}
M = [
 ('2d-4d-ratio-of-the-fingers', ['2d-4d', '2d-4d-ratio-of-the-fingers-and-its-correlation-with-psychological-trai'], 'one effect (finger-length ratio and masculine traits, Wilson 1983); FORRT names split by the list parse'),
 ('5-htt-gene-by-environment-interaction-5-htt-g-x-e', ['5-httlpr', 'stress-and-5-httlpr-interact-in-depression'], 'Caspi et al. 2003 gene-by-stress interaction in depression under three names'),
 ('ability-emotional-intelligence-as-a-second-stratum-factor', ['ability-ei-as-a-factor-of-intelligence', 'ability-emotional-intelligence-as-a-second-stratum-factor-of-intellige'], 'MacCann et al. 2014 under three names'),
 ('better-than-average-effect', ['above-average-effect', 'above-average-effect-better-than-average-effect'], 'the better-than-average effect (Alicke 1985); FORRT gives both names'),
 ('trait-controllability-strengthens-self-favoring-desirability-ratings', ['better-than-average-effect-moderated-by-controlability'], 'Alicke 1985 controllability moderation under two names'),
 ('accuracy-of-information', ['accuracy-of-information-truth-discernment'], 'Pennycook et al. 2020 accuracy nudge under two names'),
 ('achievement-priming', ['achievement-priming-goal-priming-high-performance-goal-priming', 'achievement-goal-priming-improves-performance', 'achievement-word-priming-improves-cognitive-task-performance'], 'Bargh et al. 2001 achievement-goal priming under four names'),
 ('action-sentence-compatibility-effect', ['action-sentence-compatibility-effect-ace'], 'Glenberg & Kaschak 2002 under two names'),
 ('self-interest-is-overestimated', ['actual-and-assumed-power-of-self-interest', 'overestimated-financial-self-interest-in-blood-donation-willingness'], 'Miller & Ratner 1998 under three names'),
 ('affect-heuristic', ['affect-heuristic-in-judging-outcome', 'risk-information-inversely-shifts-benefit-judgments', 'risk-and-benefit-perceptions-affect-heuristic'], 'Finucane et al. 2000 risk-benefit affect heuristic under four names'),
 ('american-flag-priming-boosts-republican-support', ['flag-priming'], 'Carter et al. 2011 flag priming under two names'),
 ('anthropomorphism', ['anthropomorphism-for-inanimate-objects'], 'Epley et al. 2008 loneliness and anthropomorphism under two names'),
 ('avoidance-of-dissonance-arousing-situations', ['avoidance-of-dissonance-arousing-situations-ideological-asymmetry-in-d'], 'Nam et al. 2013 under two names'),
 ('bilingual-executive-control-effect-non-verbal-task-switching', ['bilingual-advantages-in-executive-control-non-verbal-task-switching'], 'the same bilingual task-switching claim under two names'),
 ('bottomless-soup-bowl', ['bottomless-bowls-effect', 'self-refilling-bowls-increase-soup-intake'], 'Wansink et al. 2005 under three names'),
 ('choosing-versus-rejecting', ['choosing-versus-rejecting-framing-effects-compatibility-principle'], 'Shafir 1993 under two names'),
 ('classical-anchoring-effect', ['classical-anchoring-effect-anchoring-and-adjustment'], 'Tversky & Kahneman 1974 anchoring under two names'),
 ('conjunction-bias', ['conjunction-bias-conjunction-fallacy', 'conjunction-effect-james', 'conjunction-effect-linda'], 'Mellers et al. 2001: the conjunction effect and its two problems (James, Linda) as tested together'),
 ('default-effect', ['default-bias', 'default-effect-no-default-opt-in', 'default-effect-opt-out-opt-in'], 'the default effect (Johnson et al. 2002; Johnson & Goldstein 2003) under four names'),
 ('depressive-realism-effect', ['depressive-realism', 'depressive-realism-in-judgments-of-control'], 'Alloy & Abramson 1979 under three names'),
 ('screen-time-and-well-being', ['digital-technology-use-and-adolescent-wellbeing'], 'Twenge et al. 2017 screen time and adolescent wellbeing under two names'),
 ('distinction-bias', ['disjunction-bias'], "Hsee & Zhang 2004 distinction bias; 'Disjunction Bias' is FORRT's misspelling"),
 ('disjunction-effect', ['disjunction-effect-choice-under-risk', 'disjunction-effect-pay-to-know'], 'Tversky & Shafir 1992: the disjunction effect and its two problems as tested together'),
 ('dr-fox-effect', ['dr', 'the-doctor-fox-lecture-produces-favorable-ratings-but-illusory-learnin'], "Naftulin et al. 1973; 'Dr' is the famous-list name cut at its full stop"),
 ('dunning-kruger-effect', ['low-performers-overestimate-their-own-performance', 'metacognitive-deficits-explain-low-performer-overconfidence'], 'Kruger & Dunning 1999 under three names'),
 ('easterlin-paradox', ['easterlin-paradox-national-income-associated-with-happiness'], 'Easterlin 1974 under two names'),
 ('embodiment-of-secrets', ['embodiment-of-secrets-secrets-as-burdens', 'embodiment-of-secrets-effect', 'important-secrets-steepen-perceived-hills'], 'Slepian et al. 2012 under four names'),
 ('exceptionality-effect', ['exceptionality-effect-emotional-amplification-normality-bias-exception', 'exceptionality-heightens-attributed-regret-after-negative-outcomes'], 'Kahneman & Miller 1986 exceptionality effect under three names'),
 ('facial-feedback', ['facial-feedback-changes-cartoon-humor-ratings'], 'Strack et al. 1988 under two names'),
 ('fertility-on-voting', ['fertility-on-voting-ovulation-effect'], 'Durante et al. 2013 under two names'),
 ('goal-priming-effect', ['goal-priming-effect-goal-contagion-goal-inspiration-behavioural-inspir'], 'Aarts et al. 2004 goal contagion under two names'),
 ('grammar-influences-perceived-intentionality-effect', ['grammar-influences-perceived-intentionality', 'verbal-framing', 'verbal-framing-temporal-tense'], 'Hart & Albarracin 2011 verb aspect and intentionality under four names'),
 ('experiential-purchases-reveal-more-about-the-self-than-material-purcha', ['happiness-experiential-vs-materialistic'], 'Carter & Gilovich 2012 under two names'),
 ('variety-reduces-perceived-quantity', ['heterogeneity-reduces-perceived-quantity'], 'Redden & Hoch 2009 under two names'),
 ('threat-freezing', ['human-freezing-behaviour-postural-sway', 'human-freezing-like-behaviour-postural-sway-in-threat-processing'], 'Roelofs et al. 2010 under three names'),
 ('female-hurricanes', ['hurricane-names', 'female-named-hurricanes-are-more-deadly-than-male-named-ones'], 'Jung et al. 2014 under three names'),
 ('implicit-bias', ['implicit-bias-testing-for-racism'], 'Greenwald et al. 1998 implicit association test under two names'),
 ('implicit-god-prime-increases-self-reported-risky-behaviour', ['god-prime-self-report'], 'Kupor et al. 2015 self-reported risk taking under two names (the behavioural-risk study stays apart)'),
 ('impostor-phenomenon', ['imposter-phenomenon'], 'Clance & Imes 1978 under two spellings'),
 ('temporal-action-inaction-effect', ['inaction-effect-action-inaction-vs-temporal-change', 'inaction-effect-long-term-regret', 'inaction-effect-short-term-regret', 'temporal-reversal-of-action-and-inaction-regret'], 'Gilovich & Medvec 1994 temporal pattern of regret: its short- and long-term parts under five names (general regret stays apart)'),
 ('inaction-inertia-effect', ['inaction-inertia-car', 'inaction-inertia-fitness-center', 'inaction-inertia-frequent-flyer', 'inaction-inertia-ski', 'missed-attractive-opportunities-reduce-later-action'], 'Tykocinski et al. 1995 inaction inertia: one effect shown in four scenarios, under six names'),
 ('increase-in-narcissism', ['increase-in-narcissism-leadership-vanity-entitlement-in-young-people-o', 'increased-narcissim'], 'the generational narcissism claim (Twenge 2013) under three names'),
 ('information-source-on-attitudes-effect', ['information-source-on-attitudes-effect-quote-attribution'], 'Lorge & Curtiss 1936 under two names'),
 ('intelligence-priming', ['intelligence-priming-contemplation-professor-priming', 'professor-priming', 'professor-priming-increases-general-knowledge-performance'], 'Dijksterhuis & van Knippenberg 1998 under four names'),
 ('isolation-effect', ['isolation-effect-von-restorff-effect'], 'the same isolation-effect entry twice'),
 ('magnitude-effect', ['magnitude-effect-magnitude-perception'], 'the same magnitude-effect entry twice'),
 ('lack-of-a-theory-of-mind-is-universal-in-autism', ['lack-of-a-theory-of-mind-in-autistic-people', 'theory-of-mind-austism'], 'Baron-Cohen et al. 1986 under three names'),
 ('less-is-better', ['a-cheaper-scarf-can-seem-more-generous-than-a-costlier-coat'], 'Hsee 1998 less-is-better under two names'),
 ('matilda-effect', ['matilda-effect-matthew-matilda-effect'], 'the Matilda effect under two names'),
 ('color-match-effect-in-sentence-picture-verification', ['mental-simulation-mismatch-advantage-object-colour'], 'Connell 2007 object colour in sentence comprehension under two names'),
 ('miles-per-gallon-illusion', ['miles-per-gallon-illusion-mpg-illusion-kilometres-per-litres-illusion'], 'Larrick & Soll 2008 under two names'),
 ('milgram-experiment', ['milgram-experiment-was-a-study-examining-the-influence-of-authority-on', 'milgram-shock'], 'Milgram 1963 under three names'),
 ('growth-mindset', ['mindsets', 'growth-mindset-predicts-improving-grades-across-a-school-transition'], 'Blackwell et al. 2007 growth mindset and grades under three names (the instruction study stays apart)'),
 ('magpie-mirror-mark-directed-behavior', ['mirror-self-recognition-in-magpies-pica-pica'], 'Prior et al. 2008 under two names'),
 ('money-goods-social-market', ['more-is-better-effect', 'money-market-versus-goods-social-market'], 'Heyman & Ariely 2004 payment type and effort under three names'),
 ('mortality-salience', ['mortality-salience-death-priming-terror-management-theory', 'mortality-reminders-increase-national-in-group-bias', 'mortality-reminders-increase-preference-for-a-patriotic-essay-author', 'mortality-salience-and-pro-american-author-preference'], 'Greenberg et al. 1994 mortality salience under five names'),
 ('motivated-numeracy', ['numeracy-amplifies-partisan-interpretation-of-policy-data'], 'Kahan et al. 2013 under two names'),
 ('omission-bias', ['omission-bias-alternative-terms-action-inaction-effect'], 'Spranca et al. 1991 under two names'),
 ('other-race-effect', ['other-race-effect-cross-race-effect-own-race-bias'], 'the other-race effect under two names'),
 ('outcome-bias', ['outcome-bias-in-evaluation-of-decision-quality'], 'Baron & Hershey 1988 under two names'),
 ('temporal-value-asymmetry', ['past-future-asymmetry', 'temporal-value-asymmetry-tva'], 'Caruso et al. 2008 under three names'),
 ('personal-cognitive-dissonance-induced-compliance-paradigm', ['induced-compliance'], 'the induced-compliance paradigm under two names'),
 ('preference-for-indirect-harm', ['direct-versus-indirect-harm'], 'Royzman & Baron 2002 under two names'),
 ('public-exposure-distinguishes-shame-from-guilt', ['public-exposure-influences-shame-and-guilt-differently'], 'Smith et al. 2002 under two names'),
 ('pygmalion-effect', ['pygmalion-effect-rosenthal-effect-self-fulfilling-prophecy', 'teacher-expectancy-and-pupil-iq-gain'], 'Rosenthal & Jacobson 1968 under three names'),
 ('red-impairs-cognitive-performance', ['red-impairs-cognition', 'red-cue-impairs-achievement-performance', 'red-impairs-cognitive-performance-effect'], 'Elliot et al. 2007 under four names'),
 ('reduced-prosociality-of-high-ses-effect', ['prosociality-ses'], 'Piff et al. 2010 under two names'),
 ('romeo-and-juliet-effect', ['parental-interference-intensifies-romantic-love'], 'Driscoll et al. 1972 under two names'),
 ('scarcity-resource-allocation', ['scarcity-effect-resource-allocation'], 'Durante et al. 2015 under two names'),
 ('sex-differences-in-implicit-math-attitudes', ['sex-differences-in-implicit-maths-attitudes'], 'Nosek et al. 2002 under two spellings'),
 ('signing-at-the-beginning-rather-than-end-makes-ethics-salient', ['signing-ethics', 'signing-at-the-top-and-dishonesty'], 'Shu et al. 2012 under three names'),
 ('asch-s-conformity', ['solomon-aschs-conformity', 'solomon-aschs-conformity-study', 'unanimous-majorities-shift-visual-line-judgments', 'unanimous-wrong-answers-induce-conformity'], 'Asch 1956 under five names'),
 ('status-quo-bias', ['status-quo-effect', 'status-quo'], 'Samuelson & Zeckhauser 1988 under three names'),
 ('stereotype-threat-bonus', ['stereotype-threat-on-asian-womens-mathematical-performance', 'asian-women-mathematics'], 'Shih et al. stereotype susceptibility in Asian-American women under three names'),
 ('subliminal-anchoring-effect', ['subliminal-anchoring-effect-subliminal-anchoring', 'judgment-and-decision-making'], "Mussweiler & Englich 2005; 'Judgment and Decision Making' is a discipline name used as an effect name"),
 ('unconscious-thought-advantage', ['superiority-of-unconscious-decision-making-effect-deliberation-without', 'superiority-of-unconscious-decision-making-effect'], 'Dijksterhuis et al. 2006 under three names'),
 ('temporal-differences-in-trait-self-ascription', ['temporal-distance-actor-observer-bias', 'temporal-and-social-distance-in-trait-attributions'], 'Pronin & Ross 2006 under three names'),
 ('theory-of-mind-in-below-4-year-olds-false-belief', ['theory-of-mind-below-4-year-olds', 'tom-under-four'], 'Wimmer & Perner 1983 false belief under four years, three names'),
 ('theory-of-mind-over-development-false-belief', ['theory-of-mind-over-development'], 'the same entry twice'),
 ('transposed-word-effect', ['transposed-word-effect-responses-to-transposed-word-sequences-e-g'], "Mirault et al. 2018; the longer name is the famous-list entry cut at 'e.g.'"),
 ('unethicality-darkens-perception-of-light', ['unethicality-darkens-perception-of-light-el-greco-fallacy'], 'Banerjee et al. 2012 under two names'),
 ('vicarious-cognitive-dissonance', ['vicarious-cognitive-dissonance-induced-compliance-paradigm'], 'Norton et al. 2003 under two names'),
 ('weapons-priming-effect', ['weapons-priming-effect-weapons-effect', 'weapons-priming'], 'Berkowitz & LePage 1967 under three names'),
 ('honesty-priming', ['honesty-priming-goal-priming-social-priming'], 'Rasinski et al. 2005 under two names'),
 ('brain-drain-effect', ['smartphone-proximity-drains-cognitive-capacity'], 'Ward et al. 2017 under two names'),
]
LEFT_APART = {
 'choice-overload': "the famous list cites the wrong original (a luxury-goods study); no link made",
 'congruency-sequence-effect-conflict-adaptation-or-gratton-effect': 'title match was to a different paper; no link made',
 'low-self-esteem-on-poor-mental-health-psychological-outcomes': 'the famous list cites the Pygmalion study for it; no link made',
 'analytical-thinking-and-belief-in-conspiracy-theories': "'Analytic priming' also covers Gervais & Norenzayan 2012, a different claim",
 'affect-heuristic-music-book-versus-cash': 'three studies of Hsee & Rottenstreich 2004; which ones the replication tested needs reading',
 'anthropomorphism-belief-in-supernatural-agents': 'sub-study of Epley et al. 2008; which study a replication tested needs reading',
 'endowment-effect': 'moderator studies on two originals; needs reading',
 'reference-framing': 'separate prospect-theory problems; which ones a replication tested needs reading',
 'semantic-priming': 'a different effect from associative priming',
}
seen, out, bad = set(), [], []
for into, frm, why in M:
    for s in [into, *frm]:
        if s not in E: bad.append(s)
        if s in seen: bad.append('twice: ' + s)
        seen.add(s)
    out.append({'into': E[into]['name'] if into in E else into, 'from': [E[s]['name'] if s in E else s for s in frm], 'reason': why})
# second batch: identical-replication sets decided by a reading helper (Sonnet 5.5) from helpers_20261028/dup_sets.txt,
# its decisions in helpers_20261028/dup_decisions.txt, spot-checked by Claude (28 Oct 2026)
for line in open('/root/wiki-scratch/helpers_20261028/dup_decisions.txt', encoding='utf-8'):
    parts = [x.strip() for x in line.split('|')]
    if len(parts) != 3 or not parts[1].startswith('MERGE'):
        continue
    into = parts[1].split('into=')[1].split()[0]; frm = parts[1].split('from=')[1].split(',')
    for x in [into, *frm]:
        if x not in E2: bad.append(x)
        if x in seen: bad.append('twice: ' + x)
        seen.add(x)
    out.append({'into': E2[into]['name'] if into in E2 else into, 'from': [E2[x]['name'] if x in E2 else x for x in frm],
                'reason': parts[2] + ' (same replications; read by a helper, spot-checked)'})
# third batch, by name (28 Oct 2026): the famous list's parse cut two names at '(vs.'; each joins the full name it was cut from
for into, frm in (('Stuttering and phonological awareness impairment (vs. neurotypicals)', 'Stuttering and phonological awareness impairment (vs'),
                  ('Stuttering and reading fluency impairment (vs. dyslexia)', 'Stuttering and reading fluency impairment (vs')):
    out.append({'into': into, 'from': [frm], 'reason': "the famous list's entry, its name cut at '(vs.' when the list was read in"})
# fourth batch, by name (28 Oct 2026, read by Claude): pairs that shared exactly the same replications once copies of one
# study were merged; each is one claim under two names
for into, frm in (
    ('BDSM practitioners report higher subjective well-being than non-practitioners', 'Higher subjective well-being among BDSM practitioners'),
    ('Processing the word red impairs intellectual performance', 'color priming'),
    ('Comfort food buffers loneliness after a belongingness threat', 'Comfort food buffers loneliness after belongingness threat'),
    ('Preferences for uniqueness and conformity', 'Cultural difference in choosing uncommon pens'),
    ('Early parent reports predict 11-year language outcome', 'Early language questions predict later language difficulty'),
    ('Fructose or glucose ingestion improves anagram performance', 'Glucose and fructose boosts to anagram solving'),
    ('Iconic words are recognized faster', 'Iconic words yield faster lexical decisions'),
    ('Mental fatigue reduces cycling time to exhaustion', 'mental fatigue'),
    ('People overlook subtractive improvements', 'Overlooking of subtractive change'),
    ('Tempting fate increases expected bad luck', 'Tempting-fate actions raise perceived chance of negative outcomes')):
    out.append({'into': into, 'from': [frm], 'reason': 'the same claim on the same original under two names (same replications; read 28 Oct 2026)'})
# fifth batch, by name (28 Oct 2026, read by Claude): pairs that shared exactly the same replications once the readings
# added FORRT-listed replications
for into, frm in (('Superstition boosts performance effect', 'A lucky golf ball improves putting performance'),
                  ('Automatic approach and avoidance from affective evaluation', 'Behavioural-consequences-of-automatic-evaluation'),
                  ('Self-control relies on glucose effect', 'Glucose ingestion counteracts subsequent self-control impairment')):
    out.append({'into': into, 'from': [frm], 'reason': 'the same claim on the same original under two names (same replications; read 28 Oct 2026)'})
if bad: raise SystemExit(f'unknown or repeated slugs: {bad}')
head = ('# Curated effect merges. Applied after the automatic near-duplicate merge in pipeline/registry.py.\n'
        '# Each entry folds the "from" names into the "into" name; the ledger keeps every old id, so no URL breaks.\n'
        '# Entries of 28 Oct 2026 were decided by reading each case: the same effect on the same original paper under\n'
        '# several names (FORRT\'s data sheet, its Replications & Reversals list, and Retested\'s reviewed pairs each named it).\n')
p = '/root/retested-wiki/data/curated/merges.yaml'
open(p + '.tmp', 'w', encoding='utf-8').write(head + yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=200))
os.replace(p + '.tmp', p)
print(len(out), 'merges,', sum(len(m['from']) for m in out), 'names folded')
