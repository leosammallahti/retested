"""OpenAlex records (title, year, authors, abstract; free API) for reading-set DOIs the site does not hold yet.
Asks only for DOIs no saved batch has asked for; batches are named by their content, so reruns never skip new DOIs."""
import glob, hashlib, json, time, urllib.request, urllib.parse, pathlib, sys
sys.path.insert(0, '/root/retested-wiki')
OUT = pathlib.Path('/root/wiki-scratch/reading_20261028/openalex_missing'); OUT.mkdir(exist_ok=True)
W = json.load(open('/root/retested-wiki/data/raw/local/openalex_paper_metadata.json', encoding='utf-8'))['works']
asked = set()
for f in glob.glob(str(OUT / '*.json')):
    asked |= set(json.load(open(f)).get('asked', []))
items = [json.loads(l) for l in open('/root/wiki-scratch/reading_20261028/items.jsonl', encoding='utf-8')]
need = sorted({d for it in items for d in (it.get('doi_o'), it.get('doi_r'))
               if d and d.startswith('10.') and d not in W and d not in asked})
for i in range(0, len(need), 50):
    chunk = need[i:i + 50]
    f = OUT / ('batch_' + hashlib.md5('|'.join(chunk).encode()).hexdigest()[:12] + '.json')
    url = ('https://api.openalex.org/works?per-page=50&select=doi,title,publication_year,authorships,abstract_inverted_index,is_retracted,type&filter='
           + urllib.parse.quote('doi:' + '|'.join(chunk), safe=':|/'))
    for k in range(4):
        try:
            with urllib.request.urlopen(url, timeout=40) as r:
                f.write_text(json.dumps({'asked': chunk, 'result': json.loads(r.read())['results']})); break
        except Exception as e:
            err = str(e); time.sleep(2 ** k)
    else:
        f.write_text(json.dumps({'asked': chunk, 'error': err}))
    time.sleep(0.2)
print('newly asked', len(need), '| asked before', len(asked))
