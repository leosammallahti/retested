"""Reading items for the queue (28 Oct 2026, afternoon; paid reading approved by Leo: "Yes, run it (cap $4)"): one per
machine-found (original, later paper) pair in the review queue whose original is identified, plus this morning's items
that had no abstract and now have one (fetch_abstracts.py). Same blocks as the morning's build_items.py. Free."""
import json, glob, hashlib, re, sys, collections, html
import pandas as pd
sys.path.insert(0, '/root/retested-wiki')
from pipeline.ids import norm_doi
from pipeline import load, rr_list
B = '/root/retested-wiki/data/build/'
A = json.load(open(B + 'attempts.json', encoding='utf-8')); P = json.load(open(B + 'papers.json', encoding='utf-8'))
E = json.load(open(B + 'effects.json', encoding='utf-8'))
W = json.load(open('/root/retested-wiki/data/raw/local/openalex_paper_metadata.json', encoding='utf-8'))['works']
LINES = json.load(open(B + 'wiki.json', encoding='utf-8')).get('effect_lines', {})
sh = lambda t, n=None: re.sub(r'\s+', ' ', html.unescape(str(t or ''))).strip()[:n]
# abstracts: stored replication and original abstracts, OpenAlex, FORRT's list file, FLoRA feeds
ab = {}
def clean_abs(t):
    t = re.sub(r'<[^>]+>', ' ', str(t or ''))
    t = re.sub(r'^\s*(xml:space="preserve">|Abstract[:.]?\s)', '', t.strip(), flags=re.I)
    return sh(t, 3000)
def put(d, t):
    d = norm_doi(d)
    t = clean_abs(t) if t else t
    if d and t and len(str(t)) > 80 and d not in ab: ab[d] = t
for k, v in json.load(open('/root/retested-wiki/data/discovery/replication_abstracts.json', encoding='utf-8'))['abstracts'].items(): put(k, v.get('abstract') if isinstance(v, dict) else v)
for k, v in json.load(open('/root/retested-wiki/data/discovery/original_abstracts.json', encoding='utf-8'))['abstracts'].items(): put(k, v.get('abstract') if isinstance(v, dict) else v)
def inv(ii):
    pos = {}
    for w, ps in (ii or {}).items():
        for p in ps: pos[p] = w
    return ' '.join(pos[i] for i in sorted(pos))
for f in glob.glob('/root/wiki-scratch/audit_20261028/abstracts/*.json'):
    for r in json.load(open(f)).get('result', []): put(r.get('doi'), inv(r.get('abstract_inverted_index')))
for r in rr_list.rows(load.load_legacy()['rr']):
    if r.get('abstract_r') and r.get('doi_r'): put(r['doi_r'], r['abstract_r'])
for f in glob.glob('/root/wiki-scratch/reading_20261028/openalex_missing/*.json'):
    for r in json.load(open(f)).get('result', []):
        d = norm_doi(r.get('doi'))
        if d and r.get('title'):
            W.setdefault(d, {'title': r['title'], 'year': r.get('publication_year'),
                             'authors': [((x.get('author') or {}).get('display_name') or '') for x in r.get('authorships') or []][:6]})
        put(r.get('doi'), inv(r.get('abstract_inverted_index')))
for name in ('flora-extractor_extracted.csv', 'flora-validation_flora_entry_sheets.csv'):
    for r in pd.read_csv('/root/retested/data/raw/forrt/feeds/' + name, dtype=str, keep_default_na=False).to_dict('records'):
        put(r.get('doi_r'), r.get('abstract_r'))
eff_by_orig = collections.defaultdict(list)
for e in E:
    for d in e['originals']: eff_by_orig[d].append(e)
def paper_line(d, fallback=None):
    p = P.get(d) or {}; w = W.get(d) or {}
    t = p.get('title') or w.get('title'); a = p.get('authors') or (', '.join(w.get('authors', [])[:3]) if w.get('authors') else None)
    y = p.get('year') or w.get('year')
    return f"{a or 'unknown authors'} ({int(y) if y else 'year unknown'}). {t or fallback or 'title unknown'}"
def original_block(doi_o, effects, rr_rows=()):
    lines = [f"Paper: {paper_line(doi_o)}" if doi_o else "Paper: not identified"]
    seen = set()
    for e in effects[:3]:
        claim = LINES.get(e['slug']) or (e.get('famous') or {}).get('description') or e.get('description')
        lines.append(f"Finding: {e['name']}" + (f" — {sh(claim, 400)}" if claim else ''))
        seen.add(' '.join(e['name'].lower().split()))
    for r in rr_rows:
        if r.get('effect') and ' '.join(r['effect'].lower().split()) not in seen:
            lines.append(f"Finding: {sh(r['effect'])}" + (f" — {sh(r.get('description'), 400)}" if r.get('description') else '')); seen.add(' '.join(r['effect'].lower().split()))
    if doi_o and ab.get(doi_o): lines.append(f"Abstract of the original: {sh(ab[doi_o], 1200)}")
    return '\n'.join(lines)
def later_block(doi_r, title=None, authors=None, year=None):
    w = W.get(doi_r) or {}; p = P.get(doi_r) or {}
    t = title or p.get('title') or w.get('title'); a = authors or p.get('authors') or (', '.join(w.get('authors', [])[:3]) if w.get('authors') else None)
    y = year or p.get('year') or w.get('year')
    return f"Title: {sh(t) or 'unknown'}\nAuthors: {a or 'unknown'} ({int(float(y)) if y else 'year unknown'})\nAbstract: {ab.get(doi_r) or 'not available'}"

F = json.load(open('/root/wiki-scratch/queue_20261028/fetched.json', encoding='utf-8'))
for d, w in F['works'].items():
    W.setdefault(d, w)
for d, v in F['abstracts'].items():
    put(d, v['abstract'])
for d, v in json.load(open('/root/wiki-scratch/queue_20261028/cache/openalex.json', encoding='utf-8')).items():
    if v and v.get('abstract'): put(d, v['abstract'])      # originals' abstracts too, so the finding is described
C = json.load(open(B + 'candidates.json', encoding='utf-8'))
GROUP = {'forrt_flora_extractor': 'FORRT machine search', 'retested_discovery': 'Retested machine search'}
items, seen = [], set()
for c in C:
    if c['group'] not in ('replication', 'other_behavioural') or not c.get('doi_o'):
        continue
    rk = c.get('doi_r') or c.get('landing_page')
    if not rk or (c['doi_o'], rk) in seen:
        continue
    seen.add((c['doi_o'], rk))
    if c.get('abstract'):
        put(c.get('doi_r'), c['abstract']) if c.get('doi_r') else None
    if c.get('abstract_o'):
        put(c['doi_o'], c['abstract_o'])
    effs = eff_by_orig.get(c['doi_o'], [])
    orig = original_block(c['doi_o'], effs)
    if 'title unknown' in orig.splitlines()[0] and c.get('title_o'):
        orig = orig.replace('title unknown', sh(c['title_o']), 1)
    later = later_block(c['doi_r'], c.get('title_r'), c.get('authors_r'), c.get('year_r')) if c.get('doi_r') else \
        f"Title: {sh(c.get('title_r')) or 'unknown'}\nAuthors: {c.get('authors_r') or 'unknown'} ({c.get('year_r') or 'year unknown'})\nAbstract: {clean_abs(c.get('abstract')) or 'not available'}"
    items.append({'item': 'q|' + c['doi_o'] + '|' + rk, 'group': GROUP[c['origin']], 'candidate': c['id'], 'doi_o': c['doi_o'],
                  'doi_r': rk, 'original': orig, 'later': later})
# this morning's items that had no abstract: read again where one has now been found
for l in open('/root/wiki-scratch/reading_20261028/items.jsonl', encoding='utf-8'):
    it = json.loads(l)
    if it['has_abstract'] or not it.get('doi_r') or not ab.get(it['doi_r']):
        continue
    it['later'] = it['later'].replace('Abstract: not available', 'Abstract: ' + ab[it['doi_r']])
    it['reread'] = True
    items.append(it)
for it in items:
    it['sha256'] = hashlib.sha256((it['original'] + '\n' + it['later'] + (it.get('cited_ref') or '')).encode()).hexdigest()
    it['has_abstract'] = 'Abstract: not available' not in it['later']
with open('/root/wiki-scratch/queue_20261028/items.jsonl', 'w', encoding='utf-8') as fh:
    for it in items: fh.write(json.dumps(it, ensure_ascii=False) + '\n')
c = collections.Counter((it['group'], it['has_abstract']) for it in items)
print(len(items), 'items'); [print(' ', v, k) for k, v in sorted(c.items())]
