"""Pick out, for reading, queue replications whose TITLE names the study it replicates with authors or a year that
do not match the original it is linked to (the error the 40-pair check found twice). Selection only; a reader decides."""
import json, re, unicodedata
W = json.load(open('/root/retested-wiki/data/raw/local/openalex_paper_metadata.json'))['works']
P = json.load(open('/root/retested-wiki/data/build/papers.json'))
R = [r for r in json.load(open('/root/retested-wiki/data/curated/read_pairs.json'))['readings']
     if r['item'].startswith('q|') and r['kind'] in ('NEW_DATA_REPLICATION', 'REANALYSIS') and r['tests_this_finding'] == 'YES']
I = {json.loads(l)['item']: json.loads(l) for l in open('/root/wiki-scratch/queue_20261028/items.jsonl')}
def fold(s):
    s = s.replace('ß', 'ss').replace('ø', 'o').replace('æ', 'ae')
    return re.sub(r'[^a-z]', '', unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower())
CITE = re.compile(r"\b(?:of|from)\s+(?:the\s+)?([A-Z][\w'’\-]+(?:(?:,?\s+and\s+|,?\s*&\s*|,\s*)[A-Z][\w'’\-]+)*(?:\s+et\s+al\.?)?)(?:'s|’s)?\s*\(?((?:19|20)\d\d)\b")
CITE2 = re.compile(r"([A-Z][\w'’\-]+(?:(?:,?\s+and\s+|,?\s*&\s*|,\s*)[A-Z][\w'’\-]+)*(?:\s+et\s+al\.?)?)(?:'s|’s)?,?\s*\(((?:19|20)\d\d)\)")
flag = []
for r in R:
    later = I[r['item']]['later']
    title = next((l[7:] for l in later.splitlines() if l.startswith('Title: ')), '')
    abst = later.split('Abstract:', 1)[1] if 'Abstract:' in later else ''
    m = CITE.search(title)
    if not m:
        # in the abstract only where the citation follows the word replicate closely
        for a in re.finditer(r'replicat\w*', abst):
            m = CITE2.search(abst[a.end():a.end() + 90])
            if m: break
    if not m: continue
    cited = {fold(x) for x in re.findall(r"[A-Z][\w'’\-]+", m.group(1)) if x not in ('And', 'Et')} - {''}
    w = W.get(r['doi_o']) or {}; pa = P.get(r['doi_o']) or {}
    names = {fold(a.split()[-1]) for a in (w.get('authors') or []) if a.strip()}
    if pa.get('authors'): names |= {fold(x.split()[-1]) for x in re.split(r',|&| and ', pa['authors'].replace(' et al.', '')) if x.strip()}
    names -= {''}
    yo = w.get('year') or pa.get('year')
    match = any(c in n or n in c for c in cited for n in names if len(c) > 2 and len(n) > 2)
    year_ok = not yo or abs(int(m.group(2)) - int(yo)) <= 1
    # a list of three or more authors that shares only one name with the original's is another paper by that author
    coauthors_ok = len(cited) < 3 or len({c for c in cited for n in names if len(c) > 2 and (c in n or n in c)}) >= 2
    if not names or (match and year_ok and coauthors_ok): continue
    flag.append({'item': r['item'], 'cites': m.group(0), 'original_authors': sorted(names)[:6], 'original_year': yo})
json.dump(flag, open('/root/wiki-scratch/queue_20261028/author_mismatch.json', 'w'), ensure_ascii=False, indent=0)
print(len(R), 'queue replications;', len(flag), 'titles name another study')
for f in flag[:12]: print(f['cites'], '|', f['original_authors'][:3], f['original_year'])
