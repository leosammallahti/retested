"""Compact reading files for the helpers (one per task). Read-only over the current build."""
import json, re, collections
B = '/root/retested-wiki/data/build/'
E = json.load(open(B + 'effects.json', encoding='utf-8')); A = json.load(open(B + 'attempts.json', encoding='utf-8'))
P = json.load(open(B + 'papers.json', encoding='utf-8'))
au = json.load(open('/root/wiki-scratch/audit_20261028/audit.json', encoding='utf-8'))['items']
by_name = {e['name']: e for e in E}; by_slug = {e['slug']: e for e in E}
sh = lambda t, n: re.sub(r'\s+', ' ', str(t or ''))[:n]
def paper(d):
    p = P.get(d, {}); return f"{sh(p.get('authors'), 30)} {int(p['year']) if p.get('year') else ''} \"{sh(p.get('title'), 100)}\" [{d}]"
def att(a):
    return f"{sh(a.get('authors_r'), 30)} {int(a['year_r']) if a.get('year_r') else ''} \"{sh(a.get('title_r'), 90)}\" [{a['outcome']}; {'/'.join(a['sources'])}]"
# 1. duplicate sets
out = []
for i, it in enumerate(au['two or more effects with exactly the same replications (likely one effect under two names)']):
    out.append(f"=== SET {i}")
    for n in it['names']:
        e = by_name[n]
        fam = (e.get('famous') or {}).get('description')
        out.append(f"  EFFECT slug={e['slug']} | named by: {'/'.join(e['name_sources'])} | name: {n}")
        out.append(f"     text: {sh(fam or e.get('description'), 220)}")
    e0 = by_name[it['names'][0]]
    for d in e0['originals'][:3]: out.append(f"  ORIGINAL {paper(d)}")
    for aid in e0['attempts'][:3]: out.append(f"  REPLICATION {att(A[aid])}")
    if len(e0['attempts']) > 3: out.append(f"  (+{len(e0['attempts']) - 3} more replications, same for every effect in the set)")
open('/root/wiki-scratch/helpers_20261028/dup_sets.txt', 'w', encoding='utf-8').write('\n'.join(out) + '\n')
# 2. self-replications, contradictions, unowned / shared-only effects
out = []
for g in ('attempt: the original paper is listed as its own replication (same DOI)', 'attempt: replication title equals the original title (likely the same paper)'):
    for it in au[g]:
        a = A[it['id']]
        owners = [e['slug'] for e in E if it['id'] in e['attempts']]
        out.append(f"=== ATTEMPT id={it['id']} | effects: {', '.join(owners) or 'none'}")
        out.append(f"  ORIGINAL    {paper(a['doi_o'])}")
        out.append(f"  REPLICATION {att(a)} [{a['rep_key']}]")
        if a.get('quote'): out.append(f"  FORRT quote: {sh(a['quote'], 200)}")
for g in ("FORRT's list says not replicated, the linked replications say found", "FORRT's list says replicated, the linked replications say failed"):
    for it in au[g]:
        e = by_slug[it['slug']]
        out.append(f"=== CONTRADICTION slug={e['slug']} | {e['name']} | FORRT's list says: {e['famous']['status_raw']!r} | site verdict: {it['code']}")
        out.append(f"  FORRT text: {sh(e['famous'].get('description'), 200)}")
        out.append(f"  FORRT critiques: {sh(e['famous'].get('critiques'), 300)}")
        for aid in e['attempts'][:6]: out.append(f"  REPLICATION {att(A[aid])}")
owned = collections.Counter(x for e in E for x in e['attempts'])
for e in E:
    if e['attempts'] or not e['shared_attempts']: continue
    out.append(f"=== UNLINKED slug={e['slug']} | {e['name']} | named by: {'/'.join(e['name_sources'])}")
    out.append(f"  text: {sh((e.get('famous') or {}).get('description') or e.get('description'), 220)}")
    for d in e['originals'][:2]: out.append(f"  ORIGINAL {paper(d)}")
    for aid in e['shared_attempts'][:5]:
        others = [x['slug'] for x in E if aid in x['attempts']]
        out.append(f"  REPLICATION OF THE SAME PAPER id={aid} {att(A[aid])} | filed under: {', '.join(others) or 'no effect'}")
open('/root/wiki-scratch/helpers_20261028/attempt_cases.txt', 'w', encoding='utf-8').write('\n'.join(out) + '\n')
print('done')
