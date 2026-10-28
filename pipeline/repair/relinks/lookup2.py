"""Second Crossref pass (free) for the SEARCH queries a reader wrote; writes cases2.txt for a second reading."""
import json, re, time, urllib.request, urllib.parse
C = json.load(open('candidates.json', encoding='utf-8'))
cases = {int(l.split('|')[0].split()[1]): l for l in open('decisions.txt', encoding='utf-8') if '| SEARCH' in l}
old = {i: blk for i, blk in enumerate(open('cases.txt', encoding='utf-8').read().split('=== CASE ')[1:])}
out = []
for i, line in sorted(cases.items()):
    q = re.search(r'SEARCH "([^"]+)"', line).group(1)
    url = 'https://api.crossref.org/works?rows=5&select=DOI,title,author,issued,container-title&query.bibliographic=' + urllib.parse.quote(q)
    cands = []
    for k in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                for it in json.loads(r.read())['message']['items']:
                    cands.append(f"{it['DOI'].lower()} | {', '.join(a.get('family') or '' for a in it.get('author', [])[:4])} {((it.get('issued') or {}).get('date-parts') or [[None]])[0][0]} | \"{(it.get('title') or [''])[0][:180]}\" | {(it.get('container-title') or [''])[0][:70]}")
            break
        except Exception:
            time.sleep(2 ** k)
    head = '\n'.join(x for x in old[i].splitlines() if not x.strip().startswith('CANDIDATE'))
    out.append('=== CASE ' + head + f'\n  SEARCHED FOR: {q}\n' + '\n'.join(f'  CANDIDATE {j}: {c}' for j, c in enumerate(cands)))
    time.sleep(0.2)
open('cases2.txt', 'w', encoding='utf-8').write('\n'.join(out) + '\n')
print(len(out), 'cases searched again')
