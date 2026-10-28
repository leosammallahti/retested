"""Paper identity check: for every DOI on the site, does the title the site shows match the title OpenAlex holds for
that DOI? A mismatch means the source row paired a DOI with another paper's reference. Read-only; writes
identity_mismatch.json and prints counts by role (original / replication) and source."""
import json, glob, re, collections, sys
sys.path.insert(0, '/root/retested-wiki')
from rapidfuzz import fuzz
from pipeline.ids import norm_doi
B = '/root/retested-wiki/data/build/'
P = json.load(open(B + 'papers.json', encoding='utf-8')); A = json.load(open(B + 'attempts.json', encoding='utf-8'))
F = json.load(open(B + 'findings.json', encoding='utf-8'))
oa = {}
asked = set()
for f in glob.glob('/root/wiki-scratch/audit_20261028/openalex_all/*.json'):
    d = json.load(open(f)); asked |= set(d['asked'])
    for r in d.get('result', []):
        k = norm_doi(r.get('doi'))
        if k: oa[k] = r
norm = lambda t: re.sub(r'[^a-z0-9 ]', ' ', str(t or '').lower()).split()
role = collections.defaultdict(set)
for a in A.values():
    role[a['doi_o']].add('original')
    if a['doi_r']: role[a['doi_r']].add('replication')
srcs = collections.defaultdict(set)
for a in A.values():
    for s in a['sources']:
        srcs[a['doi_o']].add(s)
        if a['doi_r']: srcs[a['doi_r']].add(s)
out, c = [], collections.Counter()
for d, p in P.items():
    if d not in asked: continue
    r = oa.get(d)
    if not r:
        c['not in OpenAlex'] += 1; continue
    t1, t2 = p.get('title'), r.get('title')
    if not t1 or not t2:
        c['a title missing'] += 1; continue
    s = fuzz.token_set_ratio(' '.join(norm(t1)), ' '.join(norm(t2)))
    yr = p.get('year'); oy = r.get('publication_year')
    if s < 60:
        c['title disagrees'] += 1
        out.append({'doi': d, 'site_title': t1, 'openalex_title': t2, 'site_year': yr, 'openalex_year': oy, 'score': s,
                    'roles': sorted(role.get(d, [])), 'sources': sorted(srcs.get(d, [])), 'is_finding': d in F,
                    'attempts': [x for x in (F.get(d) or {}).get('attempts', [])][:20]})
    else:
        c['title agrees'] += 1
        if yr and oy and abs(float(yr) - oy) > 2: c['title agrees, year differs by more than 2'] += 1
print(dict(c))
print('mismatches by role and source:', collections.Counter((tuple(x['roles']), tuple(x['sources'])) for x in out).most_common(12))
json.dump(out, open('/root/wiki-scratch/audit_20261028/identity_mismatch.json', 'w'), ensure_ascii=False, indent=1)
