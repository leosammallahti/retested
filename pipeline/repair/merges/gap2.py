"""What FORRT's Replications & Reversals files (the editable sheet in FReD 2.4.1 and 231026_forrt_with_journals.xlsx)
would link to the effects that have no replication attempt. Read-only."""
import sys, json, collections, re
import pandas as pd
sys.path.insert(0, '/root/retested-wiki')
from pipeline import load
from pipeline.ids import norm_doi, norm_name
B = '/root/retested-wiki/data/build/'
E = json.load(open(B + 'effects.json', encoding='utf-8'))
A = json.load(open(B + 'attempts.json', encoding='utf-8'))
effs = E if isinstance(E, list) else list(E.values())
pairs = {(a['doi_o'], a['doi_r']) for a in A.values()}
leg = load.load_legacy()
W = pd.read_excel('/root/retested/data/raw/forrt/osf/sub-datasets/231026_forrt_with_journals.xlsx', dtype=str)
def nd(*vals):
    for v in vals:
        if v is not None and str(v).lower() not in ('nan', 'none', ''):
            m = re.search(r'10\.\d{4,9}/\S+', str(v))
            if m:
                d = norm_doi(m.group(0).rstrip('.,;>)'))
                if d: return d
    return None
link = collections.defaultdict(set)  # effect key -> {(doi_o, doi_r, origin)}
excl = collections.Counter()
for r in leg['rr']:
    n = r.get('effect')
    if not n or str(n).strip() in ('#', '?'): continue
    o, rp = norm_doi(r.get('doi_original')), norm_doi(r.get('doi_replication'))
    ex = str(r.get('exclusion') or '')
    if ex and ex != 'None':
        excl[ex[:40]] += 1
        if 'not a replication' in ex.lower() or 'meta-analysis' in ex.lower():
            continue
    if o and rp: link[norm_name(n)].add((o, rp, 'rr'))
w_ok = 0
for r in W.to_dict('records'):
    n = r.get('Effect')
    if not isinstance(n, str): continue
    o = nd(r.get('Original_doi'), r.get('Original_doi_cr'), r.get('Original_doi_url'), r.get('Original_Link'))
    rp = nd(r.get('Critique_doi'), r.get('Critique_doi_parsed'), r.get('Critique_Link'), r.get('Critique_ref_apa'))
    if o and rp: link[norm_name(n)].add((o, rp, 'w')); w_ok += 1
print('231026 rows with both DOIs:', w_ok, 'of', len(W))
print('rr exclusions:', dict(excl))
allp = {(o, rp) for s in link.values() for o, rp, _ in s}
print('distinct R&R pairs:', len(allp), '| not yet attempts:', len(allp - pairs))
fam_names = {}
for f in load.load_famous():
    if f.get('name'): fam_names[norm_name(f['name'])] = f
empty = [e for e in effs if not e['attempts']]
fixed = collections.Counter(); left = []
for e in empty:
    ks = {e['key']} | {norm_name(a) for a in e.get('aliases') or []}
    got = set().union(*(link.get(k, set()) for k in ks))
    if got:
        fixed['rr' if any(x[2] == 'rr' for x in got) else 'w only'] += 1
    else:
        left.append(e)
print('empty effects that R&R pairs fill:', dict(fixed), '| still empty:', len(left))
print('still empty and famous-only:', sum(1 for e in left if e.get('famous') and e['name_sources'] == ['forrt'] and not e['originals']))
# do 231026 Effect names cover the docx famous names?
wnames = {norm_name(n) for n in W['Effect'].dropna()}
print('famous docx names found in 231026 Effect column:', sum(1 for k in fam_names if k in wnames), 'of', len(fam_names))
json.dump([{'name': e['name'], 'key': e['key'], 'famous': bool(e.get('famous'))} for e in left],
          open('/root/wiki-scratch/link_fix_20261028/still_empty.json', 'w'), ensure_ascii=False, indent=1)

new = allp - pairs
rep_known = collections.defaultdict(list)
for a in A.values():
    if a['doi_r']: rep_known[a['doi_r']].append(a)
print('new pairs whose replication paper is already an attempt for another original:', sum(1 for o, rp in new if rp in rep_known))
abs_w = {}
for r in W.to_dict('records'):
    rp = nd(r.get('Critique_doi'), r.get('Critique_doi_parsed'), r.get('Critique_Link'), r.get('Critique_ref_apa'))
    if rp and isinstance(r.get('Critique_Abstract'), str) and len(r['Critique_Abstract']) > 80:
        abs_w[rp] = r['Critique_Abstract']
print('new pairs with a replication abstract in FORRT file:', sum(1 for o, rp in new if rp in abs_w))
P = json.load(open(B + 'papers.json', encoding='utf-8'))
print('new pairs whose replication paper is in papers.json:', sum(1 for o, rp in new if rp in P))
print('new pairs whose original is already a finding:', sum(1 for o, rp in new if any(a['doi_o'] == o for a in A.values())))

import random
random.seed(7)
refs = {}
for r in leg['rr']:
    o, rp = norm_doi(r.get('doi_original')), norm_doi(r.get('doi_replication'))
    if o and rp: refs[(o, rp)] = (r.get('effect'), str(r.get('ref_replication'))[:160])
for r in W.to_dict('records'):
    o = nd(r.get('Original_doi'), r.get('Original_doi_cr'), r.get('Original_doi_url'), r.get('Original_Link'))
    rp = nd(r.get('Critique_doi'), r.get('Critique_doi_parsed'), r.get('Critique_Link'), r.get('Critique_ref_apa'))
    if o and rp: refs.setdefault((o, rp), (r.get('Effect'), str(r.get('Critique_ref_apa'))[:160]))
print('\n--- 25 random new pairs')
for p in random.sample(sorted(new), 25):
    print(refs.get(p, ('?', '?'))[0], '|', refs.get(p, ('?', '?'))[1].replace('\n', ' '))
