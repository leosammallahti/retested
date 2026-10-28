"""Title, year and authors for the later papers on the site that still lack them (28 Oct 2026): OpenAlex first, then
the DOI's own registry (Crossref or DataCite) through doi.org content negotiation. Free. Writes details.json."""
import json, sys, time, urllib.request, urllib.parse
sys.path.insert(0, '/root/retested-wiki')
from pipeline.ids import norm_doi
A = json.load(open('/root/retested-wiki/data/build/attempts.json'))
W = json.load(open('/root/retested-wiki/data/raw/local/openalex_paper_metadata.json'))['works']
need = sorted({a['doi_r'] for a in A.values() if a['doi_r'] and (not a.get('authors_r') or not a.get('year_r') or not a.get('title_r') or a.get('title_r') == 'unknown')})
print(len(need), 'DOIs')
out = {}
def get(url, accept=None):
    req = urllib.request.Request(url, headers={'User-Agent': 'Retested (mailto:snasolid@gmail.com)', **({'Accept': accept} if accept else {})})
    try:
        with urllib.request.urlopen(req, timeout=40) as r: return json.loads(r.read().decode('utf-8'))
    except Exception as e: return None
for d in need:
    w = get('https://api.openalex.org/works/doi:' + urllib.parse.quote(d, safe='/') + '?select=doi,title,publication_year,authorships,type,is_retracted&mailto=snasolid@gmail.com')
    if w and w.get('title'):
        out[d] = {'title': w['title'], 'year': w.get('publication_year'), 'authors': [((x.get('author') or {}).get('display_name') or '') for x in w.get('authorships') or []][:8],
                  'type': w.get('type'), 'from': 'OpenAlex', **({'is_retracted': True} if w.get('is_retracted') else {})}
        continue
    c = get('https://doi.org/' + d, 'application/vnd.citationstyles.csl+json')
    if c and c.get('title'):
        y = ((c.get('issued') or {}).get('date-parts') or [[None]])[0][0]
        out[d] = {'title': c['title'] if isinstance(c['title'], str) else c['title'][0], 'year': y,
                  'authors': [' '.join(x for x in (a.get('given'), a.get('family')) if x) or a.get('literal', '') for a in c.get('author') or []][:8],
                  'type': c.get('type'), 'from': 'the DOI registry (doi.org)'}
    time.sleep(0.2)
json.dump(out, open('details.json', 'w'), ensure_ascii=False, indent=1)
print(len(out), 'found'); [print(' ', d, out.get(d, {}).get('from'), (out.get(d, {}).get('title') or 'NOT FOUND')[:70], out.get(d, {}).get('year'), out.get(d, {}).get('authors', [])[:2]) for d in need]
