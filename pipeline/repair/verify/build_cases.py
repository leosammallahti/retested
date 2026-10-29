"""Link verification cases for Sonnet 5.5 reading helpers (29 Oct 2026): one block per original paper (shown once,
with its full abstract), and under it every later paper to check (title, authors, year, full abstract), with short
ids. Only non-text noise is removed (OSF upload records, file hashes, markup). Code maps the ids back.

    python build_cases.py calibration      # the 200 pairs read blind on 29 Oct
    python build_cases.py queue N          # all read pairs waiting for verification, in files of about N pairs
"""
import json, re, sys, html, glob, collections
sys.path.insert(0, '/root/retested-wiki')
from pipeline.ids import norm_doi
from pathlib import Path
H = Path('/root/wiki-scratch/verify_20261029')
I = {json.loads(l)['item']: json.loads(l) for l in open('/root/wiki-scratch/queue_20261028/items.jsonl', encoding='utf-8')}
W = json.load(open('/root/retested-wiki/data/raw/local/openalex_paper_metadata.json'))['works']
P = json.load(open('/root/retested-wiki/data/build/papers.json'))
# full abstracts of originals (the reading items cut them at 1,200 characters)
AB = {}
for f in ('/root/retested-wiki/data/discovery/original_abstracts.json', '/root/retested-wiki/data/discovery/replication_abstracts.json'):
    for k, v in json.load(open(f, encoding='utf-8'))['abstracts'].items():
        t = v.get('abstract') if isinstance(v, dict) else v
        if t: AB.setdefault(norm_doi(k), t)
for k, v in json.load(open('/root/wiki-scratch/queue_20261028/cache/openalex.json')).items():
    if v and v.get('abstract'): AB.setdefault(norm_doi(k), v['abstract'])
def clean(t):
    t = html.unescape(str(t or ''))
    t = re.sub(r"uploader: \{.*?\}\}", ' ', t, flags=re.S)          # OSF upload record with file ids and hashes
    t = re.sub(r"'file_hashes': \{[^}]*\}", ' ', t)
    t = re.sub(r'<[^>]+>', ' ', t)
    t = re.sub(r'^\s*(Abstract[:.]?\s)', '', t, flags=re.I)
    return re.sub(r'\s+', ' ', t).strip()
def field(block, key):
    m = re.search(rf'^{key}: (.*)$', block, re.M)
    return m.group(1).strip() if m else ''
def original_text(doi_o, item):
    p = P.get(doi_o) or {}; w = W.get(doi_o) or {}
    head = item['original'].splitlines()[0].replace('Paper: ', '')
    findings = [l.replace('Finding: ', '') for l in item['original'].splitlines() if l.startswith('Finding:')]
    ab = clean(AB.get(doi_o)) or clean(item['original'].split('Abstract of the original: ', 1)[1]) if 'Abstract of the original: ' in item['original'] else clean(AB.get(doi_o))
    return head, findings, ab
def later_text(item):
    l = item['later']
    ab = l.split('\nAbstract: ', 1)[1] if '\nAbstract: ' in l else ''
    ab = '' if ab.strip() == 'not available' else clean(ab)
    return field(l, 'Title'), field(l, 'Authors'), ab
def write(name, items):
    by_o = collections.defaultdict(list)
    for it in items: by_o[it['doi_o']].append(it)
    out, ids, n = [], {}, 0
    for k, (o, its) in enumerate(sorted(by_o.items()), 1):
        head, findings, ab = original_text(o, its[0])
        out.append(f"=== O{k} {head}" + ''.join(f"\nFinding: {f}" for f in findings) + (f"\nAbstract: {ab}" if ab else "\nAbstract: none"))
        for it in its:
            n += 1; ids[f'L{n}'] = it['item']
            t, a, ab2 = later_text(it)
            out.append(f"-- L{n} {t} | {a}" + (f"\n{ab2}" if ab2 else "\n(no abstract)"))
    (H / f'{name}.txt').write_text('\n'.join(out) + '\n', encoding='utf-8')
    (H / f'{name}.ids.json').write_text(json.dumps(ids))
    txt = (H / f'{name}.txt').read_text()
    print(name, len(items), 'pairs,', len(by_o), 'originals,', len(txt), 'characters, about', len(txt) // 4, 'tokens')
if sys.argv[1] == 'calibration':
    key = json.load(open('/root/wiki-scratch/blind_20261029/key.json'))
    write('calibration', [I[v['item']] for v in key.values()])
if sys.argv[1] == 'queue':
    R = [r for r in json.load(open('/root/retested-wiki/data/curated/read_pairs.json'))['readings']
         if r['item'].startswith('q|') and r['kind'] in ('NEW_DATA_REPLICATION', 'REANALYSIS') and r['tests_this_finding'] == 'YES']
    its = sorted((I[r['item']] for r in R), key=lambda it: it['doi_o'])
    size = int(sys.argv[2]) if len(sys.argv) > 2 else 400
    # whole originals per file, about `size` pairs each
    by_o = collections.defaultdict(list)
    for it in its: by_o[it['doi_o']].append(it)
    batch, k = [], 0
    for o in sorted(by_o):
        batch += by_o[o]
        if len(batch) >= size:
            k += 1; write(f'queue{k:02d}', batch); batch = []
    if batch:
        k += 1; write(f'queue{k:02d}', batch)
