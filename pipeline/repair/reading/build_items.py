"""Reading items for stage 1: one per (original, later paper), with the earlier finding described from what the
database holds and the later paper's title and abstract. Writes items.jsonl. Free."""
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
S = json.load(open('/root/wiki-scratch/audit_20261028/reading_set.json'))
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
rr_by_pair = collections.defaultdict(list); rr_by_ref = collections.defaultdict(list)
for r in rr_list.rows(load.load_legacy()['rr']):
    if r['doi_o'] and r['doi_r']: rr_by_pair[(r['doi_o'], r['doi_r'])].append(r)
    if r.get('ref_r'): rr_by_ref[r['ref_r'][:200]].append(r)
items = []
for o, r in S['rr_pairs']:
    items.append({'item': 'rr|' + o + '|' + r, 'group': 'Replications & Reversals citation', 'doi_o': o, 'doi_r': r,
                  'original': original_block(o, eff_by_orig.get(o, []), rr_by_pair.get((o, r), [])), 'later': later_block(r)})
for aid in S['attempts']:
    a = A[aid]
    owners = [e for e in E if aid in e['attempts']] or eff_by_orig.get(a['doi_o'], [])
    later = later_block(a['doi_r'], a.get('title_r'), a.get('authors_r'), a.get('year_r')) if a['doi_r'] else \
        f"Title: {sh(a.get('title_r')) or 'unknown'}\nAuthors: {a.get('authors_r') or 'unknown'} ({a.get('year_r') or 'year unknown'})\nAbstract: not available"
    items.append({'item': 'at|' + aid, 'group': 'attempt on the site', 'attempt': aid, 'doi_o': a['doi_o'], 'doi_r': a['doi_r'],
                  'original': original_block(a['doi_o'], owners), 'later': later})
# reference-only citations, with Crossref's top candidate when it found one
for f in sorted(glob.glob('/root/wiki-scratch/reading_20261028/crossref/*.json')):
    c = json.load(open(f))
    if not c.get('items'): continue
    top = c['items'][0]; d = norm_doi(top['doi'])
    rows = rr_by_ref.get(c['ref'], [])
    items.append({'item': 'ref|' + (c['doi_o'] or '') + '|' + d, 'group': 'Replications & Reversals citation by reference', 'doi_o': c['doi_o'], 'doi_r': d,
                  'cited_ref': sh(c['ref'], 400), 'original': original_block(c['doi_o'], eff_by_orig.get(c['doi_o'], []), rows),
                  'later': later_block(d, top.get('title'), ', '.join(a for a in top.get('authors') or [] if a), top.get('year'))})
for it in items:
    it['sha256'] = hashlib.sha256((it['original'] + '\n' + it['later'] + (it.get('cited_ref') or '')).encode()).hexdigest()
    it['has_abstract'] = 'Abstract: not available' not in it['later']
with open('/root/wiki-scratch/reading_20261028/items.jsonl', 'w', encoding='utf-8') as fh:
    for it in items: fh.write(json.dumps(it, ensure_ascii=False) + '\n')
c = collections.Counter((it['group'], it['has_abstract']) for it in items)
print(len(items), 'items'); [print(' ', v, k) for k, v in sorted(c.items())]
