"""Write data/raw/local/openalex_paper_metadata.json: title, year and first authors that OpenAlex holds for each DOI on
the site (fetched 2026-10-28 from api.openalex.org, free). A source file, read by the registry only to replace a title
the site could only parse out of a reference string, or one that is missing."""
import json, glob, os, sys
sys.path.insert(0, '/root/retested-wiki')
from pipeline.ids import norm_doi
out = {}
for f in sorted(glob.glob('/root/wiki-scratch/audit_20261028/openalex_all/*.json')):
    for r in json.load(open(f)).get('result', []):
        d = norm_doi(r.get('doi'))
        if not d or not r.get('title'):
            continue
        names = [((a.get('author') or {}).get('display_name') or '') for a in (r.get('authorships') or [])]
        out[d] = {'title': r['title'], 'year': r.get('publication_year'), 'authors': [n for n in names if n][:12],
                  'type': r.get('type')}
doc = {'retrieved_on': '2026-10-28', 'source': 'https://api.openalex.org/works (filter doi:…, 50 per request)', 'works': dict(sorted(out.items()))}
p = '/root/retested-wiki/data/raw/local/openalex_paper_metadata.json'
open(p + '.tmp', 'w', encoding='utf-8').write(json.dumps(doc, ensure_ascii=False)); os.replace(p + '.tmp', p)
print(len(out), 'works', os.path.getsize(p) // 1024, 'KB')
