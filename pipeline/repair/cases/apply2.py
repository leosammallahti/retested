"""Second round (28 Oct evening). Turn decisions2.txt (Sonnet 5.5 reading helper, checked by Claude; contra8's NOT_REPLICATION overruled: the
student-projects paper reports its own replications, which FORRT coded one by one) into reviewed inputs. Free."""
import csv, json, io
B = '/root/retested-wiki/data/build/'; C = '/root/retested-wiki/data/curated/'
A = json.load(open(B + 'attempts.json')); P = json.load(open(B + 'papers.json'))
EV = "Read 28 Oct 2026 from the title and abstract by a reading helper (Sonnet 5.5), checked by Claude; data/curated/review_evidence/2026-10-28/case_decisions2.txt"
RELINK = {'note7': '10.1111/joes.12131', 'note12': '10.1162/rest_a_00052', 'note14': '10.1007/s13209-019-0201-0',
          'note19': '10.7551/mitpress/4117.003.0010', 'early7': '10.1007/s00221-012-3266-6'}
case_attempt = {}
for block in open('/root/wiki-scratch/cases_20261028/cases2.txt').read().split('=== CASE ')[1:]:
    head = block.split('\n', 1)[0]
    cid, rest = head.split(' | ', 1)
    if rest.startswith('attempt '): case_attempt[cid] = rest.split()[1]
QUESTION = {'note': 'a reading of the abstract differs from the record', 'early': 'the replication is dated before its original',
            'review': 'titled like a review, comment or reply', 'contra': "FORRT's list verdict and the linked replications disagree"}
excl, relinks, results, checked = [], [], [], []
for line in open('/root/wiki-scratch/cases_20261028/decisions2.txt'):
    cid, dec, why = [x.strip() for x in line.split(' | ', 2)]
    q = QUESTION[cid.rstrip('0123456789')]
    if cid == 'contra8' and dec.startswith('NOT_REPLICATION'):
        aid = dec.split()[1]; a = A[aid]
        checked.append([a['doi_o'], a['rep_key'], q, 'kept', "The paper reports its students' own replications of individual studies, which FORRT coded one by one; it is a replication report, not only a study of replicability.", EV])
        continue
    if cid.startswith('contra'):
        continue                      # effect-level: recorded in the evidence file, nothing to change in the data
    aid = case_attempt[cid]; a = A[aid]; o, rk = a['doi_o'], a['rep_key']
    if dec == 'KEEP':
        checked.append([o, rk, q, 'kept', why, EV])
    elif dec == 'FULL_TEXT':
        checked.append([o, rk, q, 'needs the full text', why, EV])
    elif dec.startswith('RESULT'):
        results.append([o, rk, dec.split()[1], why, EV])
    elif dec.startswith('NOT_REPLICATION'):
        kind = dec.split()[1].lower().replace('_', ' ').replace('or commentary', 'or commentary')
        excl.append([o, rk, f"Not a replication of this finding ({kind}): {why}", EV])
    elif dec == 'WRONG_ORIGINAL':
        excl.append([o, rk, f"Filed under the wrong original: {why}", EV])
        if cid in RELINK:
            relinks.append([o, rk, RELINK[cid], f"{why} Crossref match found by Claude, checked against the later paper's abstract (28 Oct 2026)"])
    elif dec == 'EARLIER_EVIDENCE':
        excl.append([o, rk, f"Published before the original, so not a replication of it: {why}", EV])
    else:
        raise SystemExit('unknown decision ' + line)
def append(name, rows, header=None):
    p = C + name
    new = not __import__('os').path.exists(p)
    with open(p, 'a', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh, lineterminator='\n')
        if new: w.writerow(header)
        w.writerows(rows)
append('attempt_exclusions.csv', excl)
append('attempt_relinks.csv', relinks)
append('attempt_results.csv', results, ['doi_o', 'rep_key', 'result', 'reason', 'evidence'])
append('attempts_checked.csv', checked, ['doi_o', 'rep_key', 'question', 'decision', 'reason', 'evidence'])
print(len(excl), 'exclusions', len(relinks), 'relinks', len(results), 'results', len(checked), 'checked')
