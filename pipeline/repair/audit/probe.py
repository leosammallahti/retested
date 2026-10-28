import sys, json, re, collections
import pandas as pd
sys.path.insert(0, '/root/retested-wiki')
from pipeline.ids import norm_doi
B = '/root/retested-wiki/data/build/'; FR = '/root/retested-wiki/data/raw/forrt/'
A = json.load(open(B + 'attempts.json', encoding='utf-8')); F = json.load(open(B + 'findings.json', encoding='utf-8'))
C = json.load(open(B + 'candidates.json', encoding='utf-8'))
au = json.load(open('/root/wiki-scratch/audit_20261028/audit.json', encoding='utf-8'))
atlas = {norm_doi(m) for m in re.findall(r'/doi/(10\.[^<]+?)/?</loc>', open(FR + 'feeds/atlas_sitemap.xml').read())} - {None}
site_reps = {a['doi_r'] for a in A.values() if a['doi_r']}
ext = pd.read_csv(FR + 'feeds/flora-extractor_extracted.csv', dtype=str, keep_default_na=False)
ext_o = {norm_doi(x) for x in ext['doi_o']} - {None}; ext_r = {norm_doi(x) for x in ext['doi_r']} - {None}
pend = pd.read_csv(FR + 'feeds/flora-extractor_target_pending.csv', dtype=str, keep_default_na=False)
pend_r = {norm_doi(x) for x in pend['doi_r']} - {None}
rest = atlas - set(F)
print('atlas not a finding:', len(rest), '| are site replication papers:', len(rest & site_reps), '| extractor originals:', len(rest & ext_o), '| extractor replications:', len(rest & ext_r), '| pending replications:', len(rest & pend_r))
rest2 = rest - site_reps - ext_o - ext_r - pend_r
print('left:', len(rest2), sorted(rest2)[:8])
ex = json.load(open(FR + 'feeds/flora-explorer_originals.json', encoding='utf-8'))['studies']
exk = {norm_doi(k) for k in ex}
print('explorer originals', len(exk), '| not findings:', len(exk - set(F)), '| atlas∩explorer not findings', len(rest & exk))
# extractor pairs nowhere: what do their rows say
nw = {(x['doi_o'], x['doi_r']) for x in au['items'].get('pair not on the site: FLoRA extractor (machine-found)', [])}
ext['k'] = [(norm_doi(o), norm_doi(r)) for o, r in zip(ext['doi_o'], ext['doi_r'])]
sub = ext[ext['k'].isin(nw)]
for c in ('paper_type', 'outcome', 'screen_categories', 'link_confidence', 'doi_o_verification'):
    print(c, collections.Counter(sub[c]).most_common(6))
print('candidate keys', collections.Counter(c.get('review_state') for c in C).most_common(5))
nc = [a for a in A.values() if a['outcome'] == 'not_coded']
print('not coded by sources:', collections.Counter(tuple(a['sources']) for a in nc).most_common(6))
print('not coded legacy result_raw:', collections.Counter(str(r.get('result_raw'))[:30] for a in nc for r in a['legacy_rows']).most_common(8))
print('---')
keys = set(nw)
mask = [k in keys for k in ext['k']]
sub = ext[mask]
print('extractor nowhere rows', len(sub))
for c in ('paper_type', 'outcome', 'screen_categories', 'link_confidence', 'doi_o_verification', 'source'):
    print(c, collections.Counter(sub[c]).most_common(6))
print('flora not coded raw:', collections.Counter(str(a.get('outcome_raw')) for a in nc if a['sources'] == ['flora']).most_common(6))
print('legacy-only not coded, projects:', collections.Counter(p for a in nc if a['sources'] == ['legacy'] for p in a['projects'] or ['none']).most_common(10))
