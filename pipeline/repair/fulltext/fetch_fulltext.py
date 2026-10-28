"""Open full text for the later papers still unsettled (28 Oct 2026, free): Europe PMC's XML where the paper is in PMC,
otherwise the open PDF OpenAlex points to, turned into text with pdftotext. Keeps the abstract and the results,
discussion and conclusion sections (where the result is stated) in text/<n>.txt; resumable. Writes fulltext.json."""
import json, re, sys, time, hashlib, subprocess, urllib.request, html
from pathlib import Path
HERE = Path(__file__).resolve().parent
FILES, TEXT = HERE / 'files', HERE / 'text'
FILES.mkdir(exist_ok=True); TEXT.mkdir(exist_ok=True)
AV = json.load(open(HERE / 'availability.json'))
UA = 'Mozilla/5.0 (X11; Linux x86_64) Retested replication wiki (mailto:snasolid@gmail.com)'

def get(url, timeout=60):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': '*/*'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(25_000_000), r.headers.get('Content-Type', ''), r.geturl()

SECTION = re.compile(r'^\s*(\d+(\.\d+)*\.?\s*)?(results?|findings|discussion|general discussion|conclusions?|summary|results and discussion)\s*$', re.I | re.M)

def keep_sections(text, abstract=''):
    """The abstract, then from the first Results/Discussion heading on, cut before the references."""
    text = re.sub(r'[ \t]+', ' ', text)
    ref = re.search(r'^\s*(references|bibliography|literature cited)\s*$', text, re.I | re.M)
    body = text[:ref.start()] if ref and ref.start() > len(text) * 0.4 else text
    m = SECTION.search(body)
    part = body[m.start():] if m else body[-14000:]
    head = abstract or body[:2500]
    return (head.strip() + '\n\n[...]\n\n' + part.strip())

def pmc(pmcid):
    raw, _, _ = get(f'https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML')
    x = raw.decode('utf-8', 'replace')
    ab = ' '.join(re.sub(r'<[^>]+>', ' ', a) for a in re.findall(r'<abstract[^>]*>(.*?)</abstract>', x, re.S))
    secs = []
    for title, body in re.findall(r'<sec[^>]*>\s*<title>(.*?)</title>(.*?)</sec>', x, re.S):
        if re.search(r'result|discussion|conclu|finding|summary', title, re.I):
            secs.append(re.sub(r'<[^>]+>', ' ', title) + '\n' + re.sub(r'<[^>]+>', ' ', body))
    t = html.unescape(re.sub(r'\s+', ' ', ab).strip() + '\n\n[...]\n\n' + '\n\n'.join(re.sub(r'[ \t]+', ' ', s) for s in secs))
    return t if len(t) > 800 else None

def pdf(urls):
    for u in urls:
        if not u: continue
        try:
            raw, ctype, final = get(u)
        except Exception:
            continue
        if not raw.startswith(b'%PDF'):
            m = re.search(rb'<meta[^>]+name="citation_pdf_url"[^>]+content="([^"]+)"', raw)
            if not m: continue
            try:
                raw, ctype, final = get(html.unescape(m.group(1).decode()))
            except Exception:
                continue
            if not raw.startswith(b'%PDF'): continue
        f = FILES / (hashlib.sha1(u.encode()).hexdigest()[:16] + '.pdf'); f.write_bytes(raw)
        try:
            t = subprocess.run(['pdftotext', '-q', '-enc', 'UTF-8', str(f), '-'], capture_output=True, timeout=120).stdout.decode('utf-8', 'replace')
        except Exception:
            t = ''
        f.unlink()                              # keep only the text
        if len(t) > 3000: return keep_sections(t), final
    return None, None

out = json.load(open(HERE / 'fulltext.json')) if (HERE / 'fulltext.json').exists() else {}
for n, (d, a) in enumerate(sorted(AV['papers'].items())):
    if d in out or not (a.get('pmcid') or a.get('oa_url') or a.get('pdf')): continue
    rec = {'doi': d}
    try:
        if a.get('pmcid'):
            t = pmc(a['pmcid']); rec['from'] = 'Europe PMC ' + a['pmcid'] if t else None
        else:
            t = None
        if not t:
            t, url = pdf([a.get('pdf'), a.get('oa_url')]); rec['from'] = url if t else None
    except Exception as e:
        t, rec['error'] = None, str(e)[:200]
    if t:
        p = TEXT / (re.sub(r'[^a-z0-9]+', '_', d.lower())[:120] + '.txt'); p.write_text(t, encoding='utf-8')
        rec['text'] = p.name; rec['chars'] = len(t)
    out[d] = rec
    if n % 20 == 0:
        json.dump(out, open(HERE / 'fulltext.json', 'w'), indent=0); print(n, sum(1 for r in out.values() if r.get('text')), flush=True)
    time.sleep(0.3)
json.dump(out, open(HERE / 'fulltext.json', 'w'), indent=0)
print('done', len(out), 'tried;', sum(1 for r in out.values() if r.get('text')), 'with text')
