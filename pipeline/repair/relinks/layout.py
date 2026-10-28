import json, glob, re, sys
sys.path.insert(0, '/root/retested-wiki')
from pipeline.ids import norm_doi
C = json.load(open('/root/wiki-scratch/relink_20261028/candidates.json', encoding='utf-8'))
A = json.load(open('/root/wiki-scratch/audit_20261028/build_before/attempts.json', encoding='utf-8'))
P = json.load(open('/root/wiki-scratch/audit_20261028/build_before/papers.json', encoding='utf-8'))
ab = {}
for k, v in json.load(open('/root/retested-wiki/data/discovery/replication_abstracts.json', encoding='utf-8'))['abstracts'].items():
    ab[norm_doi(k)] = (v.get('abstract') if isinstance(v, dict) else v)
def inv(ii):
    pos = {}
    for w, ps in (ii or {}).items():
        for p in ps: pos[p] = w
    return ' '.join(pos[i] for i in sorted(pos))
for f in glob.glob('/root/wiki-scratch/audit_20261028/abstracts/*.json') + glob.glob('/root/wiki-scratch/reading_20261028/openalex_missing/*.json'):
    for r in json.load(open(f)).get('result', []):
        d = norm_doi(r.get('doi'))
        if d and d not in ab and r.get('abstract_inverted_index'): ab[d] = inv(r['abstract_inverted_index'])
sh = lambda t, n: re.sub(r'\s+', ' ', str(t or ''))[:n]
by_pair = {(a['doi_o'], a['rep_key']): a for a in A.values()}
out = []
for i, c in enumerate(C):
    a = by_pair.get((c['doi_o_wrong'], c['rep_key'])) or {}
    po = P.get(c['doi_o_wrong'], {})
    out.append(f"=== CASE {i} | replication {c['rep_key']}")
    out.append(f"  REPLICATION: {sh(a.get('authors_r'), 40)} {a.get('year_r')} \"{sh(a.get('title_r'), 200)}\"")
    out.append(f"  ABSTRACT: {sh(ab.get(norm_doi(c['rep_key'])), 1500) or 'not available'}")
    out.append(f"  WRONGLY FILED UNDER: {sh(po.get('authors'), 30)} {po.get('year')} \"{sh(po.get('title'), 120)}\"")
    out.append(f"  READER'S NOTE: {c['note']}")
    for j, k in enumerate(c['candidates']):
        out.append(f"  CANDIDATE {j}: {k['doi']} | {', '.join(x for x in k['authors'] if x)} {k['year']} | \"{k['title']}\" | {k['journal']}")
open('/root/wiki-scratch/relink_20261028/cases.txt', 'w', encoding='utf-8').write('\n'.join(out) + '\n')
print(len(C), 'cases;', sum(1 for c in C if ab.get(norm_doi(c['rep_key']))), 'with an abstract')
