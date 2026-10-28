"""Before (build_before, 28 Oct 06:02) against after (data/build now): every class of difference, counted."""
import json, collections
B0, B1 = '/root/wiki-scratch/audit_20261028/build_before/', '/root/retested-wiki/data/build/'
ld = lambda b, f: json.load(open(b + f, encoding='utf-8'))
E0, E1 = ld(B0, 'effects.json'), ld(B1, 'effects.json')
A0, A1 = ld(B0, 'attempts.json'), ld(B1, 'attempts.json')
F0, F1 = ld(B0, 'findings.json'), ld(B1, 'findings.json')
S0, S1 = ld(B0, 'stats.json'), ld(B1, 'stats.json')
W0, W1 = ld(B0, 'wiki.json'), ld(B1, 'wiki.json')
e0, e1 = {e['id']: e for e in E0}, {e['id']: e for e in E1}
print('effects', len(E0), '->', len(E1), '| with a replication', sum(1 for e in E0 if e['attempts']), '->', sum(1 for e in E1 if e['attempts']))
gone = set(e0) - set(e1); new = set(e1) - set(e0)
print('effect ids gone', len(gone), '(all folded by merges.yaml?)', all(any(e0[i]['key'] in [x['key'], *x.get('merged_keys', [])] for x in E1) for i in gone), '| new ids', len(new))
renamed = [(e0[i]['name'], e1[i]['name']) for i in set(e0) & set(e1) if e0[i]['name'] != e1[i]['name']]
print('effects renamed by a merge', len(renamed), renamed[:6])
lost_att = [i for i in set(e0) & set(e1) if set(e0[i]['attempts']) - set(e1[i]['attempts'])]
print('surviving effects that lost an attempt they had', len(lost_att))
print('attempts', len(A0), '->', len(A1), '| gone', len(set(A0) - set(A1)), '| new', len(set(A1) - set(A0)), collections.Counter(A1[a].get('flora_source', '?')[:40] for a in set(A1) - set(A0)))
chg = [a for a in set(A0) & set(A1) if A0[a]['outcome'] != A1[a]['outcome']]
print('attempts whose result changed', len(chg))
print('findings', len(F0), '->', len(F1))
for k in ('graveyard', 'survivors', 'contested', 'most_tested'):
    a, b = {c['slug'] for c in S0['lists'][k]}, {c['slug'] for c in S1['lists'][k]}
    print(f'list {k}: {len(a)} -> {len(b)} | left {len(a - b)} | joined {len(b - a)}')
    if k == 'survivors': print('   left survivors (no replication):', sorted(a - b)[:12])
print('overall rate', S0['overall'], '->', S1['overall'])
print('wiki effect stories', len(W0['effects']), '->', len(W1['effects']), '| effect lines', len(W0.get('effect_lines', {})), '->', len(W1.get('effect_lines', {})), '| typology', len(W0.get('effect_typology', {})), '->', len(W1.get('effect_typology', {})))
lines_lost = [i for i in set(e0) & set(e1) if e0[i]['slug'] in W0.get('effect_lines', {}) and e1[i]['slug'] not in W1.get('effect_lines', {})]
typ_lost = [i for i in set(e0) & set(e1) if e0[i]['slug'] in W0.get('effect_typology', {}) and e1[i]['slug'] not in W1.get('effect_typology', {})]
print('surviving effects that lost their line', len(lines_lost), '| lost their typology', len(typ_lost))
acc0, acc1 = W0.get('accounts', {}), W1.get('accounts', {})
print('attempt accounts', len(acc0), '->', len(acc1), '| lost', len(set(acc0) - set(acc1)))
