"""For each replication set aside as filed under the wrong original: Crossref candidates (free API) for the original
the reading note names. Decides nothing; writes candidates.json for a reader."""
import csv, json, re, time, urllib.request, urllib.parse, sys
sys.path.insert(0, '/root/retested-wiki')
A = json.load(open('/root/wiki-scratch/audit_20261028/build_before/attempts.json', encoding='utf-8'))
rows = [r for r in csv.DictReader(open('/root/retested-wiki/data/curated/attempt_exclusions.csv', encoding='utf-8')) if r['reason'].startswith('Filed under the wrong original')]
out = []
for r in rows:
    note = r['reason'].split(':', 1)[1].strip()
    m = re.search(r"(?:replicates|replicate|repeats|reproduces|re-?examines|revisits|tests|reanalyses|compares with|names)\s+(?:and extends\s+)?(.+?)(?:,? not\b|;|$)", note)
    target = (m.group(1) if m else note)
    target = re.sub(r'\bet al\.?', '', target)
    q = target[:200]
    rec = {'doi_o_wrong': r['doi_o'], 'rep_key': r['rep_key'], 'note': note, 'query': q, 'candidates': []}
    url = 'https://api.crossref.org/works?rows=4&select=DOI,title,author,issued,container-title&query.bibliographic=' + urllib.parse.quote(q)
    for k in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                for it in json.loads(resp.read())['message']['items']:
                    rec['candidates'].append({'doi': it['DOI'].lower(), 'title': (it.get('title') or [''])[0][:200],
                                              'year': ((it.get('issued') or {}).get('date-parts') or [[None]])[0][0],
                                              'authors': [a.get('family') for a in it.get('author', [])][:4],
                                              'journal': (it.get('container-title') or [''])[0][:80]})
            break
        except Exception as e:
            rec['error'] = str(e); time.sleep(2 ** k)
    out.append(rec); time.sleep(0.15)
json.dump(out, open('/root/wiki-scratch/relink_20261028/candidates.json', 'w'), ensure_ascii=False, indent=1)
print(len(out), 'looked up;', sum(1 for o in out if o['candidates']), 'with candidates')
