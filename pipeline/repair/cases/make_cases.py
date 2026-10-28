"""Cases for one reading helper (28 Oct 2026, afternoon): readings that conflict with FORRT's coding, replications
dated before their original, review-like titles the reading did not settle, and the eight effects whose FORRT verdict
and linked replications disagree. Writes cases.txt. Free."""
import json, collections, sys
sys.path.insert(0, '/root/retested-wiki')
from pipeline import load, rr_list
B = '/root/retested-wiki/data/build/'
A = json.load(open(B + 'attempts.json')); P = json.load(open(B + 'papers.json')); E = json.load(open(B + 'effects.json'))
N = json.load(open(B + 'read_notes.json')); Q = json.load(open(B + 'quality_audit.json'))['items']
I = {}
for l in open('/root/wiki-scratch/reading_20261028/items.jsonl', encoding='utf-8'):
    x = json.loads(l); I[x.get('attempt') or x['item']] = x
R = {(r['doi_o'], r['rep_key']): r for r in json.load(open('/root/retested-wiki/data/curated/read_pairs.json'))['readings']}
out = []
def coded(a): return ', '.join(f"{k}: {v}" for k, v in a['outcomes_by_source'].items())
def attempt_case(cid, aid, why):
    a = A[aid]; it = I.get(aid); r = R.get((a['doi_o'], a['rep_key'])) or {}
    o = P.get(a['doi_o']) or {}
    s = [f"=== CASE {cid} | attempt {aid}", f"WHY LISTED: {why}",
         f"ORIGINAL ({o.get('year')}): {o.get('title')}" if not it else it['original'][:1500],
         "LATER PAPER:", (it['later'][:2200] if it else f"Title: {a.get('title_r')} ({a.get('year_r')})\nAbstract: not available"),
         f"FORRT CODING: {coded(a)}; sources {a['sources']}; FORRT's quote: {(a.get('quote') or '')[:300]}",
         f"OUR READING: kind {r.get('kind')}, tests this finding {r.get('tests_this_finding')}, result {r.get('result')}; quote: {(r.get('result_quote') or r.get('kind_quote') or '')[:250]}"]
    out.append('\n'.join(s))
n = 0
for x in N:
    if x['kind'] in ('NEW_DATA_REPLICATION', 'REANALYSIS') and x['tests_this_finding'] == 'CANNOT_TELL' and x.get('result') == 'NO_RESULT_STATED':
        continue
    n += 1; attempt_case(f'note{n}', x['attempt'], 'our reading differs from FORRT\'s record' + (f" (FORRT coded {x['differs_from']})" if x.get('differs_from') else ' (reading says it is not a replication of this finding, but FORRT coded a result)'))
for i, x in enumerate(Q['attempt: replication dated before its original'], 1):
    a = A[x['attempt']]; attempt_case(f'early{i}', x['attempt'], f"later paper dated {a.get('year_r')}, original dated {(P.get(a['doi_o']) or {}).get('year')}")
for i, x in enumerate([x for x in Q['attempt: titled like a review, meta-analysis, commentary or reply (needs reading)'] if (R.get((x['doi_o'], x['rep_key'])) or {}).get('kind') in (None, 'CANNOT_TELL')], 1):
    attempt_case(f'review{i}', x['attempt'], 'titled like a review, meta-analysis, commentary or reply; not settled by reading')
# the eight effects whose FORRT verdict and linked replications disagree
rr = rr_list.rows(load.load_legacy()['rr'])
for i, s in enumerate(['5-htt-gene-by-environment-interaction-5-htt-g-x-e', 'bottomless-soup-bowl', 'men-s-preference-for-competition',
                       'moral-foundations-across-the-political-spectrum', 'last-place-aversion', 'personal-cognitive-dissonance-induced-compliance-paradigm',
                       'scarcity-effect-discounting', 'scarcity-effect-physical-pain'], 1):
    e = next(e for e in E if e['slug'] == s); f = e.get('famous') or {}
    lines = [f"=== CASE contra{i} | effect {s}", f"EFFECT: {e['name']}; FORRT's famous list says: {f.get('verdict') or f.get('status')}",
             f"LIST TEXT: {(f.get('description') or '')[:900]}", f"LIST CITATIONS: {(f.get('critiques') or f.get('citations') or '')}"[:1500],
             "LINKED ATTEMPTS:"]
    for aid in e['attempts']:
        a = A[aid]; lines.append(f"  {aid}: {a.get('title_r')} ({a.get('year_r')}) outcome {a.get('outcome')}, sources {a['sources']}")
    names = {e['name'].lower()}
    for r in rr:
        if (r.get('effect') or '').lower() in names:
            lines.append(f"  list row: later {r.get('doi_r') or '-'} | {(r.get('ref_r') or '')[:200]}")
    out.append('\n'.join(lines))
open('/root/wiki-scratch/cases_20261028/cases.txt', 'w').write('\n\n'.join(out) + '\n')
print(len(out), 'cases', sum(len(x) for x in out) // 4, 'tokens about')
