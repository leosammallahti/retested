"""How many unsettled later papers have open full text (28 Oct 2026, free): the attempts on the site with no result,
and the papers the reading could not settle without an abstract. Europe PMC (full text in PMC) and OpenAlex (an open
copy). Writes availability.json."""
import json, sys, time, urllib.request, urllib.parse
sys.path.insert(0, '/root/retested-wiki')
from pipeline.ids import norm_doi
A = json.load(open('/root/retested-wiki/data/build/attempts.json'))
R = json.load(open('/root/wiki-scratch/queue_20261028/morning_read_pairs.json'))['readings']
nores = sorted({a['doi_r'] for a in A.values() if a['outcome'] == 'not_coded' and a['doi_r']})
unread = sorted({norm_doi(r['rep_key']) for r in R if r['kind'] == 'CANNOT_TELL' and norm_doi(r['rep_key'])})
dois = sorted(set(nores) | set(unread))
print(len(nores), 'no result', len(unread), 'unreadable', len(dois), 'DOIs')
def get(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Retested (mailto:snasolid@gmail.com)'}), timeout=40) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception: return None
out = {}
for i in range(0, len(dois), 50):
    chunk = dois[i:i + 50]
    res = get('https://api.openalex.org/works?per-page=50&select=doi,open_access,best_oa_location&filter=doi:' + '|'.join(urllib.parse.quote(d, safe='/') for d in chunk) + '&mailto=snasolid@gmail.com') or {}
    for w in res.get('results', []):
        d = norm_doi(w.get('doi')); oa = w.get('open_access') or {}
        out.setdefault(d, {})['oa_url'] = oa.get('oa_url') if oa.get('is_oa') else None
        out[d]['pdf'] = ((w.get('best_oa_location') or {}).get('pdf_url'))
    time.sleep(0.2)
for n, d in enumerate(dois):
    res = get('https://www.ebi.ac.uk/europepmc/webservices/rest/search?format=json&resultType=lite&query=DOI:' + urllib.parse.quote('"' + d + '"')) or {}
    hit = next((h for h in ((res.get('resultList') or {}).get('result') or []) if norm_doi(h.get('doi')) == d), None)
    out.setdefault(d, {})['pmcid'] = (hit or {}).get('pmcid') if (hit or {}).get('inEPMC') == 'Y' else None
    time.sleep(0.12)
json.dump({'no_result': nores, 'unreadable': unread, 'papers': out}, open('availability.json', 'w'))
for name, ds in (('no result', nores), ('unreadable', unread)):
    print(name, len(ds), 'full text in Europe PMC', sum(1 for d in ds if (out.get(d) or {}).get('pmcid')),
          'an open copy', sum(1 for d in ds if (out.get(d) or {}).get('oa_url')), 'either', sum(1 for d in ds if (out.get(d) or {}).get('pmcid') or (out.get(d) or {}).get('oa_url')))
