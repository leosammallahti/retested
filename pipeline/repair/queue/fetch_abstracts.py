"""Free lookups for the queue reading (28 Oct 2026): abstracts for papers that have none, and OpenAlex records (title,
year, authors, retraction) for every queue DOI the site does not hold yet. Sources: OpenAlex, Semantic Scholar,
Europe PMC, Crossref, all free and unauthenticated. Resumable: each source's answers are cached in cache/<source>.json.

    python fetch_abstracts.py
"""
import json, re, sys, time, html, urllib.request, urllib.parse
from pathlib import Path
sys.path.insert(0, '/root/retested-wiki')
from pipeline.ids import norm_doi
HERE = Path(__file__).resolve().parent
CACHE = HERE / 'cache'; CACHE.mkdir(exist_ok=True)
B = Path('/root/retested-wiki/data/build')
UA = {'User-Agent': 'Retested replication wiki (mailto:snasolid@gmail.com)'}

C = json.load(open(B / 'candidates.json', encoding='utf-8'))
W = json.load(open('/root/retested-wiki/data/raw/local/openalex_paper_metadata.json', encoding='utf-8'))['works']
OLD = [json.loads(l) for l in open('/root/wiki-scratch/reading_20261028/items.jsonl', encoding='utf-8')]

queue_dois = {norm_doi(c['doi_r']) for c in C if c.get('doi_r')} | {norm_doi(c['doi_o']) for c in C if c.get('doi_o')}
queue_dois.discard(None)
need_meta = sorted(d for d in queue_dois if d not in W)
need_abs = sorted({norm_doi(c['doi_r']) for c in C if c.get('doi_r') and not c.get('abstract')}
                  | {norm_doi(i['doi_r']) for i in OLD if i.get('doi_r') and not i['has_abstract']} - {None})
print(f'{len(need_meta)} DOIs without an OpenAlex record here; {len(need_abs)} later papers without an abstract')


def get(url, data=None, headers=None, tries=4):
    for t in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            time.sleep(3 * (t + 1) * (4 if e.code == 429 else 1))
        except Exception:
            time.sleep(3 * (t + 1))
    return None


def cached(name):
    p = CACHE / f'{name}.json'
    return p, (json.load(open(p)) if p.exists() else {})


def save(p, d):
    p.with_suffix('.tmp').write_text(json.dumps(d, ensure_ascii=False)); p.with_suffix('.tmp').replace(p)


def inv(ii):
    pos = {p: w for w, ps in (ii or {}).items() for p in ps}
    return ' '.join(pos[i] for i in sorted(pos))


# OpenAlex: metadata for everything not held, abstracts for everything without one (50 DOIs a request)
p, oa = cached('openalex')
todo = [d for d in sorted(set(need_meta) | set(need_abs)) if d not in oa]
for i in range(0, len(todo), 50):
    chunk = todo[i:i + 50]
    url = ('https://api.openalex.org/works?per-page=50&select=doi,title,publication_year,authorships,abstract_inverted_index,is_retracted,type'
           '&filter=doi:' + '|'.join(urllib.parse.quote(d, safe='/') for d in chunk) + '&mailto=snasolid@gmail.com')
    res = get(url)
    if res is None: continue
    got = {norm_doi(r.get('doi')): r for r in res.get('results', [])}
    for d in chunk:
        r = got.get(d)
        oa[d] = None if not r else {'title': r.get('title'), 'year': r.get('publication_year'), 'type': r.get('type'),
                                    'is_retracted': r.get('is_retracted'),
                                    'authors': [((x.get('author') or {}).get('display_name') or '') for x in r.get('authorships') or []][:8],
                                    'abstract': inv(r.get('abstract_inverted_index')) or None}
    if i % 1000 == 0: save(p, oa); print('openalex', i, len(todo), flush=True)
    time.sleep(0.15)
save(p, oa)
have = lambda d: any(((src.get(d) or {}).get('abstract') or '') for src in (oa,))

# Semantic Scholar batch (500 a request) for those still without an abstract
p2, s2 = cached('semanticscholar')
todo = [d for d in need_abs if not have(d) and d not in s2]
for i in range(0, len(todo), 400):
    chunk = todo[i:i + 400]
    res = get('https://api.semanticscholar.org/graph/v1/paper/batch?fields=abstract,title,year',
              data=json.dumps({'ids': ['DOI:' + d for d in chunk]}).encode(), headers={'Content-Type': 'application/json'})
    if res is None: continue
    for d, r in zip(chunk, res):
        s2[d] = {'abstract': (r or {}).get('abstract')} if r else None
    save(p2, s2); time.sleep(3)
print('semantic scholar done', flush=True)
have = lambda d: bool((oa.get(d) or {}).get('abstract') or (s2.get(d) or {}).get('abstract'))

# Europe PMC, then Crossref, one DOI at a time, for those still without
p3, ep = cached('europepmc')
for n, d in enumerate([d for d in need_abs if not have(d) and d not in ep]):
    res = get('https://www.ebi.ac.uk/europepmc/webservices/rest/search?resultType=core&format=json&query=DOI:' + urllib.parse.quote('"' + d + '"'))
    hits = ((res or {}).get('resultList') or {}).get('result') or []
    hit = next((h for h in hits if norm_doi(h.get('doi')) == d), None)
    ep[d] = {'abstract': (hit or {}).get('abstractText')} if res is not None else None
    if n % 100 == 0: save(p3, ep)
    time.sleep(0.12)
save(p3, ep)
have = lambda d: bool((oa.get(d) or {}).get('abstract') or (s2.get(d) or {}).get('abstract') or (ep.get(d) or {}).get('abstract'))
p4, cr = cached('crossref')
for n, d in enumerate([d for d in need_abs if not have(d) and d not in cr]):
    res = get('https://api.crossref.org/works/' + urllib.parse.quote(d, safe='/'))
    cr[d] = {'abstract': ((res or {}).get('message') or {}).get('abstract')} if res is not None else None
    if n % 100 == 0: save(p4, cr)
    time.sleep(0.05)
save(p4, cr)


def clean(t):
    t = re.sub(r'<[^>]+>', ' ', html.unescape(str(t or '')))
    t = re.sub(r'^\s*(Abstract[:.]?\s)', '', t.strip(), flags=re.I)
    t = re.sub(r'\s+', ' ', t).strip()
    return t if len(t) > 80 else None


out = {}
for d in need_abs:
    for name, src in (('OpenAlex', oa), ('Semantic Scholar', s2), ('Europe PMC', ep), ('Crossref', cr)):
        t = clean((src.get(d) or {}).get('abstract'))
        if t: out[d] = {'abstract': t[:3000], 'from': name}; break
json.dump({'abstracts': out, 'works': {d: {k: v for k, v in r.items() if k != 'abstract'} for d, r in oa.items() if r}},
          open(HERE / 'fetched.json', 'w'), ensure_ascii=False)
print(f'abstracts found for {len(out)} of {len(need_abs)}; OpenAlex records for {sum(1 for d in need_meta if oa.get(d))} of {len(need_meta)}')
