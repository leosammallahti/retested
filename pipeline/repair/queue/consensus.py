"""Turn the two models' answers into data/curated/read_pairs.json, and write disagreements.txt for reading.

Queue reading (28 Oct 2026, afternoon): the morning's readings (morning_read_pairs.json, frozen) plus the readings of
the review queue's machine-found pairs; a morning paper that had no abstract and now has one is read again, and its new
reading replaces the morning's when it is settled (agreed or decided).

    python consensus.py            # agreed readings + adjudicated ones (adjudicated.txt) -> read_pairs.json

Agreement: both answers valid (allowed values; every needed quote found word for word); the same broad kind
(replication or re-analysis / not a replication); the same answer on whether it tests this finding; for a
replication, the same result; for a paper named only by reference, the same answer on whether it is that paper.
A split, a CANNOT_TELL, or a missing answer goes to disagreements.txt; decisions written there by a reader (Claude) go in
adjudicated.txt as  <item> | <KIND> | <TESTS> | <RESULT> | <CITED or -> | <reason>  and are taken over the models.
"""
import json, os, sys, collections
from pathlib import Path
HERE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/root/wiki-scratch/queue_20261028')
# the readings this one is layered on: the morning's for the queue; for a later layer (the full-text reading), the
# file as the layer before it left it (run the queue's consensus first, then this with the full-text folder)
BASE = HERE / 'morning_read_pairs.json' if (HERE / 'morning_read_pairs.json').exists() else Path('/root/retested-wiki/data/curated/read_pairs.json')
RUNS = ('deepseek-v4.1-flash#1', 'glm-5.3-flash#1')
REP = {'NEW_DATA_REPLICATION', 'REANALYSIS'}
items = {json.loads(l)['item']: json.loads(l) for l in (HERE / 'items.jsonl').read_text(encoding='utf-8').splitlines()}
best = {}
for run in RUNS:
    p = HERE / 'answers' / f'{run}.jsonl'
    if not p.exists(): continue
    for l in p.read_text(encoding='utf-8').splitlines():
        r = json.loads(l)
        if r.get('valid'): best[(run, r['item'])] = r
broad = lambda k: 'REP' if k in REP else ('UNSURE' if k == 'CANNOT_TELL' else 'NOT')
adj = {}
if (HERE / 'adjudicated.txt').exists():
    for l in (HERE / 'adjudicated.txt').read_text(encoding='utf-8').splitlines():
        p = [x.strip() for x in l.split(' | ')]      # item ids contain '|' themselves; fields are ' | '-separated
        if len(p) >= 6: adj[p[0]] = {'kind': p[1], 'tests_this_finding': p[2], 'result': p[3], 'is_cited_paper': None if p[4] == '-' else p[4], 'why': p[5]}
def title_line(it, key):
    for line in it['later'].splitlines():
        if line.startswith(key + ':'):
            v = line.split(':', 1)[1].strip()
            return None if v.lower() == 'unknown' else v
def authors_year(it):
    # the later paper's authors and year as the reading item gave them ("Authors: A, B (2021)"), for a paper the
    # catalogue does not hold (a page without a DOI)
    import re
    v = title_line(it, 'Authors') or ''
    m = re.match(r'^(.*?)\s*\((\d{4})(?:\.0)?\)\s*$', v)
    a, y = (m.group(1), int(m.group(2))) if m else (v, None)
    a = None if not a or a.lower().startswith('unknown') else a
    return {'authors_r': a, 'year_r': y}
out, split, c = [], [], collections.Counter()
for iid, it in items.items():
    a, b = best.get((RUNS[0], iid)), best.get((RUNS[1], iid))
    base = {'item': iid, 'group': it['group'], 'doi_o': it.get('doi_o'), 'rep_key': it.get('doi_r'),
            'title_r': title_line(it, 'Title'), 'cited_ref': it.get('cited_ref'), 'read_on': '2026-10-28',
            **({'candidate': it['candidate']} if it.get('candidate') else {}), **authors_year(it),
            'effects': [l.split(':', 1)[1].split(' — ')[0].strip() for l in it['original'].splitlines() if l.startswith('Finding:')]}
    if iid in adj:
        d = adj[iid]; out.append({**base, **{k: v for k, v in d.items() if k != 'why'}, 'kind_quote': '', 'result_quote': '',
                                  'decided_by': f"the two AI models disagreed; decided by Claude (Sonnet 5.5 reading helpers, samples checked): {d['why']}"}); c['adjudicated'] += 1; continue
    if not a or not b:
        c['waiting for an answer'] += 1; continue
    if 'UNSURE' in (broad(a['kind']), broad(b['kind'])) and not it['has_abstract']:
        # no abstract, and the title alone does not settle it for at least one model: recorded as not readable here
        out.append({**base, 'kind': 'CANNOT_TELL', 'tests_this_finding': 'CANNOT_TELL', 'result': 'NOT_APPLICABLE',
                    'is_cited_paper': None, 'kind_quote': '', 'result_quote': '',
                    'decided_by': 'not readable from the title alone and no abstract is available'})
        c['no abstract, title does not settle it'] += 1
        continue
    # both say it is not a replication: whether it tests the finding changes nothing the build does with it
    both_not = broad(a['kind']) == broad(b['kind']) == 'NOT'
    same = (broad(a['kind']) == broad(b['kind']) != 'UNSURE' and (a['tests_this_finding'] == b['tests_this_finding'] or both_not)
            and (broad(a['kind']) != 'REP' or a['result'] == b['result'])
            and a.get('is_cited_paper') == b.get('is_cited_paper'))
    if same:
        kind = a['kind'] if a['kind'] == b['kind'] else ('NEW_DATA_REPLICATION' if broad(a['kind']) == 'REP' else a['kind'])
        out.append({**base, 'kind': kind, 'tests_this_finding': a['tests_this_finding'] if a['tests_this_finding'] == b['tests_this_finding'] else 'CANNOT_TELL', 'result': a['result'] if broad(a['kind']) == 'REP' else 'NOT_APPLICABLE',
                    'is_cited_paper': a.get('is_cited_paper'), 'kind_quote': a['kind_quote'], 'result_quote': a.get('result_quote') or b.get('result_quote'),
                    'decided_by': 'two AI models agreed (DeepSeek v4.1 flash and GLM 5.3 flash), each quote checked against the abstract'
                                  if not it.get('fulltext_from') else
                                  f"two AI models agreed (DeepSeek v4.1 flash and GLM 5.3 flash) reading the paper's open full text ({it['fulltext_from']}), each quote checked against it"})
        c['agreed: ' + broad(a['kind'])] += 1
    else:
        split.append((iid, a, b)); c['split'] += 1
morning = json.loads(BASE.read_text(encoding='utf-8'))
replaced = {r['item'] for r in out if items[r['item']].get('reread') and r['kind'] != 'CANNOT_TELL'}
out = [r for r in morning['readings'] if r['item'] not in replaced] + [r for r in out if not items[r['item']].get('reread') or r['item'] in replaced]
c['morning readings replaced by a reading with an abstract'] = len(replaced)
doc = {'schema_version': 1, 'about': morning['about'], 'readings': out}
t = Path('/root/retested-wiki/data/curated/read_pairs.json')
t.with_suffix('.json.tmp').write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8'); os.replace(t.with_suffix('.json.tmp'), t)
with open(HERE / 'disagreements.txt', 'w', encoding='utf-8') as fh:
    for iid, a, b in split:
        it = items[iid]
        fh.write(f"=== ITEM {iid}\n{it['original'][:900]}\n--- LATER PAPER\n{it['later'][:1800]}\n")
        if it.get('cited_ref'): fh.write(f"FORRT'S REFERENCE: {it['cited_ref']}\n")
        for r in (a, b):
            fh.write(f"  {r['model']}: kind {r['kind']} | tests {r['tests_this_finding']} | result {r['result']} | cited {r.get('is_cited_paper', '-')} | quote: {(r.get('result_quote') or r.get('kind_quote') or '')[:200]}\n")
print(dict(c))
