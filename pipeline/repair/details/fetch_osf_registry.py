"""Authors, title and year for later papers on the site that no catalogue record covers (28 Oct 2026, free): OSF's
public API for OSF pages and OSF DOIs, the DOI registry (doi.org, Crossref or DataCite) for other DOIs.
Writes /root/retested-wiki/data/raw/local/later_paper_records.json keyed by the attempt's rep_key. Resumable."""
import json, re, sys, time, urllib.request, urllib.parse
from pathlib import Path
OUT = Path('/root/retested-wiki/data/raw/local/later_paper_records.json')
A = json.load(open('/root/retested-wiki/data/build/attempts.json'))
need = sorted({a['rep_key'] for a in A.values() if not a.get('authors_r')})
rec = json.load(open(OUT))['records'] if OUT.exists() else {}
UA = {'User-Agent': 'Retested replication wiki (mailto:snasolid@gmail.com)'}
def get(url, accept=None):
    try:
        req = urllib.request.Request(url, headers={**UA, **({'Accept': accept} if accept else {})})
        with urllib.request.urlopen(req, timeout=40) as r: return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        if e.code == 429: time.sleep(30)
        return None
    except Exception: return None
def osf_id(k):
    m = re.search(r'osf\.io/(?:v2/(?:nodes|registrations|preprints)/)?([a-z0-9]{5})(?:[/_?]|$)', k, re.I)
    return m.group(1).lower() if m else None
def osf(gid):
    g = get(f'https://api.osf.io/v2/guids/{gid}/?resolve=false')
    kind = (((g or {}).get('data') or {}).get('type')) or 'nodes'
    kind = {'registrations': 'registrations', 'preprints': 'preprints'}.get(kind, 'nodes')
    d = get(f'https://api.osf.io/v2/{kind}/{gid}/?embed=contributors')
    if not d or 'data' not in d: return None
    at = d['data'].get('attributes') or {}
    names = []
    for c in (((d['data'].get('embeds') or {}).get('contributors') or {}).get('data') or []):
        u = ((c.get('embeds') or {}).get('users') or {}).get('data') or {}
        if c.get('attributes', {}).get('bibliographic', True) and u: names.append((u.get('attributes') or {}).get('full_name'))
    y = (at.get('date_published') or at.get('date_registered') or at.get('date_created') or '')[:4]
    return {'title': at.get('title'), 'authors': [n for n in names if n], 'year': int(y) if y.isdigit() else None, 'from': f'OSF ({kind} {gid})'}
def registry(doi):
    c = get('https://doi.org/' + urllib.parse.quote(doi, safe='/'), 'application/vnd.citationstyles.csl+json')
    if not c or not c.get('title'): return None
    y = (((c.get('issued') or {}).get('date-parts') or [[None]])[0] or [None])[0]
    names = [' '.join(x for x in (a.get('given'), a.get('family')) if x) or a.get('literal', '') for a in c.get('author') or []]
    return {'title': c['title'] if isinstance(c['title'], str) else c['title'][0], 'authors': [n for n in names if n], 'year': y, 'from': 'the DOI registry (doi.org)'}
for n, k in enumerate(need):
    if k in rec: continue
    gid = osf_id(k) if 'osf' in k.lower() else None
    r = osf(gid) if gid else (registry(k) if k.startswith('10.') else None)
    rec[k] = r
    if n % 25 == 0:
        OUT.with_suffix('.tmp').write_text(json.dumps({'about': __doc__.strip(), 'records': rec}, ensure_ascii=False)); OUT.with_suffix('.tmp').replace(OUT)
        print(n, len(need), sum(1 for v in rec.values() if v and v.get('authors')), flush=True)
    time.sleep(0.7)
OUT.with_suffix('.tmp').write_text(json.dumps({'about': __doc__.strip(), 'retrieved_on': '2026-10-28', 'records': rec}, ensure_ascii=False)); OUT.with_suffix('.tmp').replace(OUT)
print('done', len(need), 'tried;', sum(1 for v in rec.values() if v and v.get('authors')), 'with authors')
