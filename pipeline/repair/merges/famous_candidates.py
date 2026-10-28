"""For each famous-list effect with no attempts: the original paper it cites, and papers we hold (originals with
replications) whose title, year and first author fit that citation. Prints a table to read; decides nothing."""
import sys, json, re, collections
sys.path.insert(0, '/root/retested-wiki')
from rapidfuzz import fuzz
from pipeline.ids import norm_name
B = '/root/retested-wiki/data/build/'
effs = json.load(open(B + 'effects.json', encoding='utf-8'))
F = json.load(open(B + 'findings.json', encoding='utf-8'))
P = json.load(open(B + 'papers.json', encoding='utf-8'))
by_doi_eff = collections.defaultdict(list)
for e in effs:
    for d in e['originals']:
        by_doi_eff[d].append((e['name'], len(e['attempts'])))
held = [(d, P.get(d, {})) for d in F]
held = [(d, p) for d, p in held if p.get('title')]
def norm(t): return re.sub(r'[^a-z0-9 ]', ' ', str(t).lower())
out = []
for e in effs:
    if e['attempts'] or not e.get('famous'): continue
    op = e['famous'].get('original_paper') or ''
    titles = re.findall(r'[“"]([^”"]{12,})[”"]', op) or [op[:200]]
    yr = e['famous'].get('original_year')
    cands = []
    for d, p in held:
        s = max(fuzz.token_set_ratio(norm(t), norm(p['title'])) for t in titles)
        if s < 85: continue
        py = p.get('year')
        if yr and py and abs(int(py) - yr) > 1: continue
        cands.append((s, d, p['title'][:110], py, str(p.get('authors'))[:40], len(F[d]['attempts']), by_doi_eff.get(d, [])[:3]))
    cands.sort(reverse=True)
    out.append({'slug': e['slug'], 'name': e['name'], 'op': op[:300], 'cands': cands[:3]})
n = 0
for o in out:
    if not o['cands']: continue
    n += 1
    print(f"## {o['name']}  [{o['slug']}]\n   cites: {o['op']!r}")
    for c in o['cands']:
        print(f"   {c[0]:.0f} {c[1]} | {c[2]} | {c[3]} | {c[4]} | {c[5]} att | effects: {c[6]}")
print(n, 'of', len(out), 'empty famous effects have a candidate')
json.dump(out, open('/root/wiki-scratch/link_fix_20261028/famous_candidates.json', 'w'), ensure_ascii=False, indent=1)
