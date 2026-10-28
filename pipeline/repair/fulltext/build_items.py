"""Reading items from open full text (28 Oct 2026): the attempts on the site with no result, and the papers this
morning's reading could not settle without an abstract, where fetch_fulltext.py found an open copy. The later paper is
given as its abstract and its results, discussion and conclusion sections; the original as this morning's reading
described it. Same item ids as the morning's, so a settled reading replaces the morning's. Free."""
import json, sys, hashlib, collections
sys.path.insert(0, '/root/retested-wiki')
from pipeline.ids import norm_doi
H = '/root/wiki-scratch/fulltext_20261028/'
F = json.load(open(H + 'fulltext.json'))
A = json.load(open('/root/retested-wiki/data/build/attempts.json')); P = json.load(open('/root/retested-wiki/data/build/papers.json'))
E = json.load(open('/root/retested-wiki/data/build/effects.json'))
M = [json.loads(l) for l in open('/root/wiki-scratch/reading_20261028/items.jsonl', encoding='utf-8')]
READ = {r['item']: r for r in json.load(open('/root/wiki-scratch/queue_20261028/morning_read_pairs.json'))['readings']}
text = {d: open(H + 'text/' + r['text'], encoding='utf-8').read()[:16000] for d, r in F.items() if r.get('text')}
def later(title, authors, year, t):
    return f"Title: {title or 'unknown'}\nAuthors: {authors or 'unknown'} ({year or 'year unknown'})\nText of the paper (its abstract, then its results, discussion and conclusion sections): {t}"
items, seen = [], set()
for it in M:
    d = norm_doi(it.get('doi_r'))
    if d not in text: continue
    r = READ.get(it['item'])
    aid = it.get('attempt')
    unsettled = (r is None or r['kind'] == 'CANNOT_TELL' or r.get('result') == 'NO_RESULT_STATED'
                 or (aid and A.get(aid, {}).get('outcome') == 'not_coded'))
    if not unsettled: continue
    lines = it['later'].splitlines()
    t_ = next((l[7:] for l in lines if l.startswith('Title: ')), None); a_ = next((l[9:] for l in lines if l.startswith('Authors: ')), None)
    items.append({**{k: v for k, v in it.items() if k not in ('later', 'sha256', 'has_abstract')}, 'later': later(t_, a_, '', text[d]).replace(' ( year unknown)', ''), 'reread': True, 'fulltext_from': F[d]['from']})
    seen.add(aid or it['item'])
eff_of = collections.defaultdict(list)
for e in E:
    for x in e['attempts']: eff_of[x].append(e['name'])
for aid, a in A.items():
    if a['outcome'] != 'not_coded' or a['doi_r'] not in text or aid in seen: continue
    o = P.get(a['doi_o']) or {}
    orig = f"Paper: {o.get('authors') or 'unknown authors'} ({o.get('year') or 'year unknown'}). {o.get('title') or 'title unknown'}" + ''.join(f"\nFinding: {n}" for n in eff_of.get(aid, [])[:3])
    items.append({'item': 'at|' + aid, 'group': 'attempt on the site', 'attempt': aid, 'doi_o': a['doi_o'], 'doi_r': a['doi_r'],
                  'original': orig, 'later': later(a.get('title_r'), a.get('authors_r'), a.get('year_r'), text[a['doi_r']]),
                  'reread': True, 'fulltext_from': F[a['doi_r']]['from']})
for it in items:
    it['sha256'] = hashlib.sha256((it['original'] + '\n' + it['later'] + (it.get('cited_ref') or '')).encode()).hexdigest()
    it['has_abstract'] = True
with open(H + 'items.jsonl', 'w', encoding='utf-8') as fh:
    for it in items: fh.write(json.dumps(it, ensure_ascii=False) + '\n')
print(len(items), 'items', collections.Counter(i['group'] for i in items), sum(len(i['later']) for i in items) // 4, 'tokens of text')
