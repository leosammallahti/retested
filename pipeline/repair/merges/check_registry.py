"""Build the registry in memory (nothing written) and report: merge and reviewed-link log lines, and how the effects
changed against the saved build (audit_20261028/build_before)."""
import sys, json, collections
sys.path.insert(0, '/root/retested-wiki')
from pipeline import load, registry, curated_links
from pipeline.ids import EffectLedger
from pipeline.__main__ import LEDGER
src = {k: getattr(load, f"load_{k}")() for k in ("flora", "fred", "legacy", "famous", "openalex", "merges")}
src["promoted"] = load.load_promoted(); src["links"] = curated_links.load()
from pipeline import openalex_works, read_pairs; src["openalex_works"] = openalex_works.load(); src["read_pairs"] = read_pairs.load()
from pipeline import flora_validation; src["flora_validation"] = flora_validation.rows()
src["explanations"] = load.load_finding_explanations(src["promoted"])
g = registry.build(src, EffectLedger(LEDGER))
for l in g['log']:
    if 'merges.yaml: unknown' in l or 'reviewed link not applied' in l:
        print('PROBLEM', l)
print('merges applied:', sum(1 for l in g['log'] if l.startswith("merges.yaml: '")))
old = json.load(open('/root/wiki-scratch/audit_20261028/build_before/effects.json', encoding='utf-8'))
new = list(g['effects'].values())
o_by = {e['id']: e for e in old}; n_by = {e['id']: e for e in new}
print('effects before', len(old), 'with replications', sum(1 for e in old if e['attempts']))
print('effects after ', len(new), 'with replications', sum(1 for e in new if e['attempts']))
gone = [o_by[i] for i in o_by if i not in n_by]
print('ids gone (folded):', len(gone), '| of them had replications:', sum(1 for e in gone if e['attempts']))
gained = [e for e in new if e['attempts'] and e['id'] in o_by and not o_by[e['id']]['attempts']]
print('effects that had none and now have replications:', len(gained))
for e in gained: print('   ', e['name'], len(e['attempts']))
lost = [e for e in new if not e['attempts'] and e['id'] in o_by and o_by[e['id']]['attempts']]
print('effects that lost all replications:', len(lost), [e['name'] for e in lost])
# replications per merged survivor: union of the folded ones?
own_old = collections.defaultdict(set)
for e in old: own_old[e['id']] = set(e['attempts'])
atts_old = set().union(*own_old.values()); atts_new = set().union(*(set(e['attempts']) for e in new))
print('attempts owned by some effect: before', len(atts_old), 'after', len(atts_new), '| lost ownership:', len(atts_old - atts_new))
