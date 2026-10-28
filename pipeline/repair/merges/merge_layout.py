"""Reading layout: every effect with no attempts of its own whose original paper (from FORRT's rows, or the famous
list's citation matched by title, year and author) has replications that sit under other effect names. Shows the empty
effect's own text and, per replication on that paper, which effect owns it. Decides nothing."""
import sys, json, re, collections
sys.path.insert(0, '/root/retested-wiki')
B = '/root/retested-wiki/data/build/'
effs = json.load(open(B + 'effects.json', encoding='utf-8'))
F = json.load(open(B + 'findings.json', encoding='utf-8'))
A = json.load(open(B + 'attempts.json', encoding='utf-8'))
P = json.load(open(B + 'papers.json', encoding='utf-8'))
by_id = {e['id']: e for e in effs}
owner = collections.defaultdict(list)
for e in effs:
    for aid in e['attempts']:
        owner[aid].append(e['name'])
fc = {o['slug']: o for o in json.load(open('/root/wiki-scratch/link_fix_20261028/famous_candidates.json', encoding='utf-8'))}
items = []
for e in effs:
    if e['attempts']: continue
    dois = list(e['originals'])
    for c in (fc.get(e['slug']) or {}).get('cands', []):
        if c[0] >= 90 and c[1] not in dois: dois.append(c[1])
    dois = [d for d in dois if d in F]
    if not dois: continue
    items.append((e, dois))
def short(t, n): return re.sub(r'\s+', ' ', str(t or ''))[:n]
lo, hi = int(sys.argv[1]), int(sys.argv[2])
for i, (e, dois) in enumerate(items[lo:hi], lo):
    fam = e.get('famous') or {}
    print(f"===== [{i}] {e['name']}   ({e['slug']})")
    print('  FORRT text:', short(e.get('description') or fam.get('description'), 400))
    if fam.get('original_paper'): print('  famous list cites:', short(fam['original_paper'], 200))
    for d in dois:
        p = P.get(d, {})
        print(f"  ORIGINAL {d}: {short(p.get('authors'), 40)} {p.get('year')} — {short(p.get('title'), 120)}")
        for aid in F[d]['attempts'][:4]:
            a = A[aid]
            print(f"     rep: {short(a.get('authors_r'), 30)} {a.get('year_r')} — {short(a.get('title_r'), 90)} [{a['outcome']}] -> owned by {owner.get(aid) or 'none'}")
    others = sorted({n for d in dois for aid in F[d]['attempts'] for n in owner.get(aid, [])})
    for n in others:
        x = next(y for y in effs if y['name'] == n)
        print(f"  OTHER EFFECT '{n}' ({x['slug']}): {short(x.get('description') or (x.get('famous') or {}).get('description'), 220)}")
    print()
print(len(items), 'empty effects with replications on their original paper under other names')
