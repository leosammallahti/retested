"""Every number the documents quote, from the built data and the readings (run after a build)."""
import json, collections, glob
B = '/root/retested-wiki/data/build/'
A = json.load(open(B + 'attempts.json')); E = json.load(open(B + 'effects.json')); S = json.load(open(B + 'stats.json'))
L = json.load(open(B + 'forrt_ledger.json')); Q = json.load(open(B + 'quality_audit.json'))
N = json.load(open(B + 'read_notes.json')); C = json.load(open(B + 'candidates.json'))
R = json.load(open('/root/retested-wiki/data/curated/read_pairs.json'))['readings']
sm = L['summary']['site']
print('attempts', len(A), 'from FORRT', sm['from_forrt'], 'added by Retested', sm['added_by_retested'], 'findings', sm['findings'])
print('effects with replication', sm['effects_with_replication'], 'named without', sm['effects_named_without_replication'])
print('ledger rows', len(L['lines']), 'missing', L['summary']['missing'])
fb = collections.Counter(a.get('found_by') for a in A.values() if a.get('found_by'))
print('attempts by found_by', dict(fb))
oc = collections.Counter(a['outcome'] for a in A.values())
res = sum(oc[k] for k in ('successful', 'failed', 'mixed'))
print('outcomes', dict(oc), 'success share of results', round(100 * oc['successful'] / res, 1), 'of', res)
print('with a result read for Retested', sum(1 for a in A.values() if a['outcomes_by_source'].get('read') not in (None, 'not_coded')))
new = [a for a in A.values() if a.get('found_by') in ('forrt_machine_search', 'retested_machine_search')]
print('queue additions', len(new), collections.Counter(a['outcome'] for a in new))
print('readings by group', collections.Counter(r['group'] for r in R))
q = [r for r in R if r['group'].endswith('machine search')]
print('queue readings', len(q), collections.Counter('REP' if r['kind'] in ('NEW_DATA_REPLICATION', 'REANALYSIS') and r['tests_this_finding'] == 'YES' else r['kind'] if r['kind'] == 'CANNOT_TELL' else 'not' for r in q))
print('decided by helpers (all readings)', sum(1 for r in R if 'decided by Claude' in r['decided_by']), 'full text', sum(1 for r in R if 'full text' in r['decided_by']))
print('queue left', len(C), collections.Counter(c['origin'] for c in C))
print('read notes', len(N)); print('audit', {k: len(v) for k, v in Q['items'].items()})
print('effects with related papers', sum(1 for e in E if e.get('related_papers')), sum(len(e.get('related_papers') or []) for e in E))
spent = 0
for d in ('queue_20261028', 'fulltext_20261028', 'reading_20261028'):
    s = sum(json.loads(l).get('cost_usd', 0) for f in glob.glob(f'/root/wiki-scratch/{d}/answers/*.jsonl') for l in open(f))
    print('spent', d, round(s, 3)); spent += s
print('spent total', round(spent, 2))
print('game items', S.get('game_items'))
