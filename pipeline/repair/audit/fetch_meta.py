"""Fetch OpenAlex records (free, public API) for replication papers missing a title, authors or year, and for the
papers on both sides of a replication dated before its original. Raw responses kept in openalex/; summary printed."""
import json, sys, time, urllib.request, urllib.parse, pathlib
sys.path.insert(0, '/root/retested-wiki')
au = json.load(open('/root/wiki-scratch/audit_20261028/audit.json', encoding='utf-8'))['items']
A = json.load(open('/root/retested-wiki/data/build/attempts.json', encoding='utf-8'))
OUT = pathlib.Path('/root/wiki-scratch/audit_20261028/openalex')
dois = set()
for g in ('attempt: no replication title', 'attempt: no replication authors', 'attempt: no replication year'):
    dois |= {A[x['id']]['doi_r'] for x in au[g] if A[x['id']]['doi_r']}
for x in au['attempt: replication dated before the original']:
    a = A[x['id']]
    dois |= {d for d in (a['doi_r'], a['doi_o']) if d}
got = 0
for d in sorted(dois):
    f = OUT / (urllib.parse.quote(d, safe='') + '.json')
    if f.exists():
        continue
    url = 'https://api.openalex.org/works/doi:' + urllib.parse.quote(d, safe='/():;') + '?select=id,doi,title,publication_year,authorships,type'
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            f.write_text(r.read().decode('utf-8'), encoding='utf-8'); got += 1
    except Exception as e:
        f.write_text(json.dumps({'error': str(e)}), encoding='utf-8')
    time.sleep(0.15)
print(len(dois), 'DOIs;', got, 'fetched now')
