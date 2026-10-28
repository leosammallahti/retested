"""Build registry + queue in memory and run the ledger; print the summary and every MISSING line. Writes nothing."""
import sys, json, collections
sys.path.insert(0, '/root/retested-wiki')
from pipeline import load, registry, curated_links, queue, score, forrt_ledger, rr_list
from pipeline.ids import EffectLedger
from pipeline.__main__ import LEDGER
src = {k: getattr(load, f"load_{k}")() for k in ("flora", "fred", "legacy", "famous", "openalex", "merges")}
src["promoted"] = load.load_promoted(); src["links"] = curated_links.load()
from pipeline import flora_validation; src["flora_validation"] = flora_validation.rows()
src["explanations"] = load.load_finding_explanations(src["promoted"])
g = registry.build(src, EffectLedger(LEDGER))
score.score(g)
ext = load.load_extractor()
cands = queue.build(ext, g) + queue.build_retested(load.load_triaged(), load.merged_links(), g, load.load_known_replication_dois(), load.load_known_osf_ids(), load.load_surname_frequency(), load.load_osf(), load.load_original_authors())
cands = queue.dedupe(cands)
L = forrt_ledger.build(g, cands, rr_list.rows(src["legacy"]["rr"]), src["famous"], ext)
print(json.dumps(L["summary"], indent=1, ensure_ascii=False))
miss = [l for l in L["lines"] if l["outcome"] == "MISSING"]
print('MISSING by file', collections.Counter(l["file"] for l in miss))
json.dump(L, open('/root/wiki-scratch/link_fix_20261028/ledger_trial.json', 'w'), ensure_ascii=False, indent=0)
