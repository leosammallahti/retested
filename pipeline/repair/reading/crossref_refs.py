"""Look up the later papers FORRT's Replications & Reversals list names only by reference text, on Crossref (free,
public API, one query per reference). Keeps the top three candidates per reference with their scores; decides nothing
(the reading models are asked whether the paper they read is the one the reference names). Resumable."""
import json, time, urllib.request, urllib.parse, pathlib, re, html
S = json.load(open('/root/wiki-scratch/audit_20261028/reading_set.json'))
OUT = pathlib.Path('/root/wiki-scratch/reading_20261028/crossref'); OUT.mkdir(exist_ok=True)
done = 0
for i, (doi_o, ref) in enumerate(S['rr_refonly']):
    f = OUT / f'{i:04d}.json'
    if f.exists(): continue
    q = re.sub(r'<[^>]+>|https?://\S+|doi:\S+', ' ', html.unescape(ref or ''))
    q = re.sub(r'\s+', ' ', q).strip()[:300]
    rec = {'doi_o': doi_o, 'ref': ref, 'query': q, 'items': []}
    if len(q) > 15:
        url = 'https://api.crossref.org/works?rows=3&select=DOI,title,author,issued,score&query.bibliographic=' + urllib.parse.quote(q)
        for k in range(3):
            try:
                with urllib.request.urlopen(url, timeout=30) as r:
                    for it in json.loads(r.read())['message']['items']:
                        rec['items'].append({'doi': it['DOI'].lower(), 'title': (it.get('title') or [''])[0], 'score': it.get('score'),
                                             'year': ((it.get('issued') or {}).get('date-parts') or [[None]])[0][0],
                                             'authors': [a.get('family') for a in it.get('author', [])][:4]})
                break
            except Exception as e:
                rec['error'] = str(e); time.sleep(2 ** k)
    f.write_text(json.dumps(rec, ensure_ascii=False)); done += 1
    time.sleep(0.12)
print('looked up', done)
