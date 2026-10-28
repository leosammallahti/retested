# shared: the R&R pairs from both FORRT files (exclusion-marked non-replications skipped), and those not yet attempts
import json, re, collections
import pandas as pd
from pipeline import load
from pipeline.ids import norm_doi, norm_name
_A = json.load(open('/root/retested-wiki/data/build/attempts.json', encoding='utf-8'))
_PAIRS = {(a['doi_o'], a['doi_r']) for a in _A.values()}
_leg = load.load_legacy()
_W = pd.read_excel('/root/retested/data/raw/forrt/osf/sub-datasets/231026_forrt_with_journals.xlsx', dtype=str)
def nd(*vals):
    for v in vals:
        if v is not None and str(v).lower() not in ('nan', 'none', ''):
            m = re.search(r'10\.\d{4,9}/[^\s<>"]+', str(v))
            if m:
                d = norm_doi(m.group(0).rstrip('.,;>)'))
                if d: return d
    return None
RR = collections.defaultdict(list)   # (doi_o, doi_r) -> rows
for r in _leg['rr']:
    n = r.get('effect'); ex = str(r.get('exclusion') or '')
    if not n or str(n).strip() in ('#', '?'): continue
    if 'not a replication' in ex.lower() or 'meta-analysis' in ex.lower(): continue
    o, rp = norm_doi(r.get('doi_original')), norm_doi(r.get('doi_replication'))
    if o and rp: RR[(o, rp)].append({'file': 'rr', 'effect': str(n).strip(), 'ref_o': r.get('ref_original'), 'ref_r': r.get('ref_replication'), 'description': r.get('description')})
for r in _W.to_dict('records'):
    n = r.get('Effect')
    if not isinstance(n, str): continue
    o = nd(r.get('Original_doi'), r.get('Original_doi_cr'), r.get('Original_doi_url'), r.get('Original_Link'))
    rp = nd(r.get('Critique_doi'), r.get('Critique_doi_parsed'), r.get('Critique_Link'), r.get('Critique_ref_apa'))
    if o and rp: RR[(o, rp)].append({'file': '231026', 'effect': n.strip(), 'ref_o': r.get('Original_ref_apa') or r.get('Original_Paper_title'), 'ref_r': r.get('Critique_ref_apa'),
                                     'description': r.get('Description'), 'abstract_r': r.get('Critique_Abstract'), 'critique_text': r.get('Critique_text')})
NEW = sorted(set(RR) - _PAIRS)
