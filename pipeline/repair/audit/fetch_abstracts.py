"""Abstracts (OpenAlex abstract_inverted_index, free API) for the later papers in the stage-1 reading set. Resumable."""
import json, time, urllib.request, urllib.parse, pathlib
S = json.load(open('/root/wiki-scratch/audit_20261028/reading_set.json'))
A = json.load(open('/root/retested-wiki/data/build/attempts.json', encoding='utf-8'))
dois = sorted({p[1] for p in S['rr_pairs']} | {A[a]['doi_r'] for a in S['attempts'] if A[a]['doi_r']})
OUT = pathlib.Path('/root/wiki-scratch/audit_20261028/abstracts'); OUT.mkdir(exist_ok=True)
for i in range(0, len(dois), 50):
    f = OUT / f'batch_{i // 50:04d}.json'
    if f.exists(): continue
    chunk = dois[i:i + 50]
    url = 'https://api.openalex.org/works?per-page=50&select=doi,title,abstract_inverted_index,type&filter=' + urllib.parse.quote('doi:' + '|'.join(chunk), safe=':|/')
    for k in range(4):
        try:
            with urllib.request.urlopen(url, timeout=40) as r:
                f.write_text(json.dumps({'asked': chunk, 'result': json.loads(r.read())['results']})); break
        except Exception as e:
            err = str(e); time.sleep(2 ** k)
    else:
        f.write_text(json.dumps({'asked': chunk, 'error': err}))
    time.sleep(0.2)
print('done', len(dois))
