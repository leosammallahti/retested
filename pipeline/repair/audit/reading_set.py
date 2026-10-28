"""The exact set of papers stage 1 would read, deduplicated by (original, later paper), with what is already known."""
import json, re, collections, sys
sys.path.insert(0, '/root/retested-wiki')
from pipeline.ids import norm_doi
B = '/root/retested-wiki/data/build/'
A = json.load(open(B + 'attempts.json', encoding='utf-8'))
L = json.load(open(B + 'forrt_ledger.json', encoding='utf-8'))
au = json.load(open('/root/wiki-scratch/audit_20261028/audit.json', encoding='utf-8'))['items']
sys.path.insert(0, '/root/retested-wiki')
from pipeline import load, rr_list
rr = rr_list.rows(load.load_legacy()['rr'])
at = {(r['file'], r['row']): r for r in rr}
pairs, refonly = {}, {}
for l in L['lines']:
    if l['outcome'] != 'not yet read': continue
    r = at.get((l['file'], l['row']))
    if not r: continue
    if r['doi_o'] and r['doi_r']:
        pairs.setdefault((r['doi_o'], r['doi_r']), r)
    else:
        refonly.setdefault((r['doi_o'], (r['ref_r'] or '')[:200]), r)
flag = {x['id'] for x in au['attempt: title says review, meta-analysis, commentary or reply (needs reading)']}
uncoded = {a for a, x in A.items() if x['outcome'] == 'not_coded'}
before = {x['id'] for x in au['attempt: replication dated before the original']}
att_set = flag | uncoded | before
print('R&R pairs with both DOIs (distinct):', len(pairs), '| R&R later papers named only by reference (distinct):', len(refonly))
print('attempts to read: flagged', len(flag), '+ uncoded', len(uncoded), '+ dated before', len(before), '= distinct', len(att_set))
print('  uncoded by source:', collections.Counter(tuple(A[a]['sources']) for a in uncoded).most_common(5))
print('  with a DOI for the later paper:', sum(1 for a in att_set if A[a]['doi_r']))
print('TOTAL distinct papers to read:', len(pairs) + len(refonly) + len(att_set))
json.dump({'rr_pairs': [list(k) for k in pairs], 'rr_refonly': [[k[0], k[1]] for k in refonly], 'attempts': sorted(att_set)},
          open('/root/wiki-scratch/audit_20261028/reading_set.json', 'w'), ensure_ascii=False)
