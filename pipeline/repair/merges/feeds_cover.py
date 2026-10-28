"""How many of the new R&R pairs FORRT's FLoRA extractor or validation feeds already hold (with paper type and outcome)."""
import sys, json, collections, re
import pandas as pd
sys.path.insert(0, '/root/retested-wiki')
from pipeline import load
from pipeline.ids import norm_doi, norm_name
exec(open('/root/wiki-scratch/link_fix_20261028/rr_pairs.py').read())
FE = '/root/retested/data/raw/forrt/feeds/'
hold = collections.defaultdict(list)
for f in ('extracted', 'keyed_link_disputed', 'no_original_found', 'search_link_unconfirmed', 'target_pending', 'unidentified_original'):
    df = pd.read_csv(FE + f'flora-extractor_{f}.csv', dtype=str, keep_default_na=False)
    for r in df[['doi_r', 'doi_o', 'paper_type', 'outcome', 'outcome_phrase', 'abstract_r']].to_dict('records'):
        d = norm_doi(r['doi_r'])
        if d: hold[d].append((f, norm_doi(r['doi_o']), r['paper_type'], r['outcome'], bool(r['abstract_r'])))
for f in ('flora_entry_sheets', 'validated_export'):
    df = pd.read_csv(FE + f'flora-validation_{f}.csv', dtype=str, keep_default_na=False)
    for r in df[['doi_r', 'doi_o', 'type', 'outcome', 'abstract_r']].to_dict('records'):
        d = norm_doi(r['doi_r'])
        if d: hold[d].append((f, norm_doi(r['doi_o']), r['type'], r['outcome'], bool(r['abstract_r'])))
c = collections.Counter(); same_o = collections.Counter(); ptype = collections.Counter()
for o, rp in NEW:
    hs = hold.get(rp, [])
    if not hs: c['in no FLoRA feed'] += 1; continue
    c['in a FLoRA feed'] += 1
    if any(h[1] == o for h in hs): same_o['same original'] += 1
    for h in hs[:1]: ptype[(h[0], h[2], h[3])] += 1
print(dict(c), dict(same_o))
for k, n in ptype.most_common(15): print(n, k)
print('abstract present in a feed:', sum(1 for o, rp in NEW if any(h[4] for h in hold.get(rp, []))))
