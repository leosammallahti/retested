"""OpenAlex records (free, public API) for every DOI on the site, 50 per request, for the paper identity check.
Resumable: batches already saved are skipped. Output: openalex_all/batch_NNNN.json."""
import json, time, urllib.request, urllib.parse, pathlib
P = json.load(open('/root/retested-wiki/data/build/papers.json', encoding='utf-8'))
OUT = pathlib.Path('/root/wiki-scratch/audit_20261028/openalex_all'); OUT.mkdir(exist_ok=True)
dois = sorted(d for d in P if d.startswith('10.') and '|' not in d and ',' not in d)
for i in range(0, len(dois), 50):
    f = OUT / f'batch_{i // 50:04d}.json'
    if f.exists():
        continue
    chunk = dois[i:i + 50]
    q = 'doi:' + '|'.join(chunk)
    url = 'https://api.openalex.org/works?per-page=50&select=doi,title,publication_year,authorships,type&filter=' + urllib.parse.quote(q, safe=':|/')
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=40) as r:
                f.write_text(json.dumps({'asked': chunk, 'result': json.loads(r.read())['results']}), encoding='utf-8')
            break
        except Exception as e:
            err = str(e); time.sleep(2 ** attempt)
    else:
        f.write_text(json.dumps({'asked': chunk, 'error': err}), encoding='utf-8')
    time.sleep(0.2)
print('done', len(dois), 'DOIs')
