"""Second try for the papers whose first open copy refused an automated download: every open location OpenAlex lists
(repositories, preprint servers), then Semantic Scholar's open PDF. Free. Updates fulltext.json."""
import json, re, time, urllib.parse
import fetch_fulltext as F      # its loop runs on import only for papers not yet in fulltext.json: none are left
out = json.load(open(F.HERE / 'fulltext.json'))
fail = [d for d, r in out.items() if not r.get('text')]
print(len(fail), 'to retry', flush=True)
for n, d in enumerate(fail):
    urls = []
    w = None
    try:
        w = json.loads(F.get('https://api.openalex.org/works/doi:' + urllib.parse.quote(d, safe='/') + '?select=locations&mailto=snasolid@gmail.com')[0])
    except Exception:
        pass
    for loc in (w or {}).get('locations') or []:
        if loc.get('is_oa'):
            urls += [loc.get('pdf_url'), loc.get('landing_page_url')]
    try:
        s = json.loads(F.get('https://api.semanticscholar.org/graph/v1/paper/DOI:' + d + '?fields=openAccessPdf')[0])
        urls.append(((s or {}).get('openAccessPdf') or {}).get('url') or None)
    except Exception:
        pass
    urls = [u for u in dict.fromkeys(urls) if u and 'doi.org' not in u]
    t, url = F.pdf(urls) if urls else (None, None)
    if t:
        p = F.TEXT / (re.sub(r'[^a-z0-9]+', '_', d.lower())[:120] + '.txt'); p.write_text(t, encoding='utf-8')
        out[d].update(text=p.name, chars=len(t), **{'from': url})
    if n % 20 == 0:
        json.dump(out, open(F.HERE / 'fulltext.json', 'w'), indent=0); print(n, sum(1 for r in out.values() if r.get('text')), flush=True)
    time.sleep(1.2)
json.dump(out, open(F.HERE / 'fulltext.json', 'w'), indent=0)
print('done;', sum(1 for r in out.values() if r.get('text')), 'with text')
