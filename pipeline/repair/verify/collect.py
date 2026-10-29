"""Collect the reading helpers' link checks (queueNN.out, with queueNN.ids.json) into data/curated/link_checks.csv.
A batch whose output does not have exactly one line per later paper is refused."""
import csv, json, glob, os, sys
H = '/root/wiki-scratch/verify_20261029/'
R = {r['item']: r for r in json.load(open('/root/retested-wiki/data/curated/read_pairs.json'))['readings']}
EV = "read against both abstracts by a Sonnet 5.5 reading helper (brief and outputs in data/curated/review_evidence/2026-10-29/link_checks/), 29 Oct 2026"
rows, bad = [], []
for ids_f in sorted(glob.glob(H + 'queue*.ids.json')):
    out_f = ids_f.replace('.ids.json', '.out')
    ids = json.load(open(ids_f))
    if not os.path.exists(out_f):
        bad.append(os.path.basename(out_f) + ' missing'); continue
    lines = [l.strip().split('|', 2) for l in open(out_f) if l.strip()]
    got = [l[0] for l in lines]
    if sorted(got) != sorted(ids) or any(l[1] not in ('Y', 'N', '?') for l in lines):
        bad.append(os.path.basename(out_f) + f' has {len(got)} lines for {len(ids)} papers or a bad answer'); continue
    for l in lines:
        r = R[ids[l[0]]]
        note = (l[2] if len(l) > 2 else '').strip() or {'Y': 'replicates this original', 'N': 'replicates another study or is no replication', '?': 'the text does not settle it'}[l[1]]
        rows.append([r['doi_o'], r['rep_key'], l[1], note, EV])
if bad:
    print('REFUSED:', *bad, sep='\n  ')
# one row per pair: where a pair was checked twice and the checks differ, the more cautious one stands (N, then ?, then Y)
rank = {'N': 0, '?': 1, 'Y': 2}
best = {}
for r in rows:
    sys.path.insert(0, '/root/retested-wiki'); from pipeline.ids import norm_doi
    r[0] = norm_doi(r[0]) or r[0]; r[1] = norm_doi(r[1]) or r[1]
    k = (r[0], r[1])
    if k not in best or rank[r[2]] < rank[best[k][2]]: best[k] = r
rows = [r for r in best.values() if r[0] != r[1]]     # a paper listed as its own replication is never one
p = '/root/retested-wiki/data/curated/link_checks.csv'
with open(p + '.tmp', 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh, lineterminator='\n'); w.writerow(['doi_o', 'rep_key', 'decision', 'note', 'evidence']); w.writerows(rows)
os.replace(p + '.tmp', p)
import collections
print(len(rows), 'checks', collections.Counter(r[2] for r in rows))
