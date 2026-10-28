"""Why each effect with no replication attempt has none, and what FORRT's own files would link to it. Read-only."""
import sys, json, collections
sys.path.insert(0, '/root/retested-wiki')
from pipeline import load
from pipeline.ids import norm_doi, norm_name
B = '/root/retested-wiki/data/build/'
E = json.load(open(B + 'effects.json', encoding='utf-8'))
F = json.load(open(B + 'findings.json', encoding='utf-8'))
A = json.load(open(B + 'attempts.json', encoding='utf-8'))
P = json.load(open(B + 'papers.json', encoding='utf-8'))
effs = E if isinstance(E, list) else list(E.values())
print('effects', len(effs), 'keys', sorted(effs[0].keys()))
f0 = next(iter(F.values())) if isinstance(F, dict) else F[0]
print('finding keys', sorted(f0.keys()))

leg = load.load_legacy()
pairs = {(a['doi_o'], a['doi_r']) for a in A.values()}
orig_with_att = {a['doi_o'] for a in A.values()}
empty = [e for e in effs if not e['attempts']]
print('effects with no attempts:', len(empty))
# rows naming each effect key, both sheets
rows_by_key = collections.defaultdict(list)
for sheet in ('data', 'rr'):
    for r in leg[sheet]:
        n = r.get('effect')
        if n and str(n).strip() not in ('#', '?') and str(n).lower() != 'nan':
            rows_by_key[norm_name(n)].append((sheet, r))
def keys_of(e):
    ks = {e['key']} | {norm_name(a) for a in (e.get('aliases') or [])}
    return ks
cls = collections.Counter(); examples = collections.defaultdict(list)
for e in empty:
    rows = [x for k in keys_of(e) for x in rows_by_key.get(k, [])]
    fam = bool(e.get('famous'))
    if not rows:
        c = 'famous list only, no FORRT sheet row' if fam else 'no FORRT sheet row'
    else:
        rr_pairs = [(norm_doi(r.get('doi_original')), norm_doi(r.get('doi_replication'))) for s, r in rows if s == 'rr']
        rr_both = [p for p in rr_pairs if p[0] and p[1]]
        data_o_only = [r for s, r in rows if s == 'data' and norm_doi(r.get('doi_original')) and not norm_doi(r.get('doi_replication'))]
        if rr_both:
            c = 'R&R sheet gives original+replication DOIs'
        elif any(p[0] and p[0] in orig_with_att for p in rr_pairs):
            c = 'R&R original DOI already has replications'
        elif any(norm_doi(r.get('ref_replication')) or (r.get('ref_replication') and str(r.get('ref_replication')) != 'None') for s, r in rows):
            c = 'replication cited by reference text only (no DOI)'
        elif data_o_only or any(p[0] for p in rr_pairs):
            c = 'original DOI only, no replication named'
        else:
            c = 'row with no DOIs or reference'
    cls[c] += 1; examples[c].append(e['name'])
for c, n in cls.most_common():
    print(f'{n:4d}  {c}   e.g. {examples[c][:4]}')
