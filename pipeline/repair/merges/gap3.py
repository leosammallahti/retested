"""For the empty effects: shared attempts, and what FORRT's R&R file names as each famous effect's original paper. Read-only."""
import sys, json, collections, re
import pandas as pd
sys.path.insert(0, '/root/retested-wiki')
from pipeline import load
from pipeline.ids import norm_doi, norm_name
B = '/root/retested-wiki/data/build/'
effs = json.load(open(B + 'effects.json', encoding='utf-8'))
F = json.load(open(B + 'findings.json', encoding='utf-8'))
P = json.load(open(B + 'papers.json', encoding='utf-8'))
empty = [e for e in effs if not e['attempts']]
print('empty with shared attempts:', sum(1 for e in empty if e['shared_attempts']), '| with originals that are findings:', sum(1 for e in empty if e['originals']))
W = pd.read_excel('/root/retested/data/raw/forrt/osf/sub-datasets/231026_forrt_with_journals.xlsx', dtype=str)
def nd(*vals):
    for v in vals:
        if v is not None and str(v).lower() not in ('nan', 'none', ''):
            m = re.search(r'10\.\d{4,9}/[^\s<>"]+', str(v))
            if m:
                d = norm_doi(m.group(0).rstrip('.,;>)'))
                if d: return d
    return None
w_orig = collections.defaultdict(set)
for r in W.to_dict('records'):
    if isinstance(r.get('Effect'), str):
        o = nd(r.get('Original_doi'), r.get('Original_doi_cr'), r.get('Original_doi_url'), r.get('Original_Link'))
        if o: w_orig[norm_name(r['Effect'])].add(o)
leg = load.load_legacy()
for r in leg['rr']:
    if r.get('effect') and norm_doi(r.get('doi_original')):
        w_orig[norm_name(r['effect'])].add(norm_doi(r['doi_original']))
fam_only = [e for e in empty if not e['originals'] and e.get('famous') and not any(k in w_orig for k in [e['key']])]
fam_named = [e for e in empty if not e['originals'] and e.get('famous') and e['key'] in w_orig]
print('famous-only empty effects:', len(fam_only) + len(fam_named), '| FORRT R&R names an original DOI:', len(fam_named))
hit = [e for e in fam_named if any(d in F for d in w_orig[e['key']])]
print('  ... and that original already has replications:', len(hit), [e['name'] for e in hit[:6]])
nonfam = [e for e in empty if not e.get('famous')]
print('non-famous empty:', len(nonfam), '| whose FORRT original DOI has replications:', sum(1 for e in nonfam if any(d in F for d in w_orig.get(e['key'], ()))))
