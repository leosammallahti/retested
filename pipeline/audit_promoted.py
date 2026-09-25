"""Audit every source-reviewed pair against the built site. Exit nonzero on errors."""
import json
from pathlib import Path
from pipeline.ids import norm_name
def equivalent_doi(value):
    return str(value).replace("//", "/")
root=Path(__file__).resolve().parent.parent
rows=json.loads((root/'data/curated/promoted_pairs.json').read_text())
effects=json.loads((root/'data/build/effects.json').read_text())
attempts=json.loads((root/'data/build/attempts.json').read_text())
bykey={(norm_name(e['name']),equivalent_doi(d)):e for e in effects for d in e['originals']}
issues=[]
for row in rows:
    key=(norm_name(row['effect_name']),equivalent_doi(row['doi_o']))
    effect=bykey.get(key)
    if not effect:
        issues.append((row['candidate_id'],'missing effect'));continue
    matched=[attempts[a] for a in effect['attempts'] if a in attempts and equivalent_doi(attempts[a].get('doi_o'))==equivalent_doi(row['doi_o']) and equivalent_doi(attempts[a].get('doi_r'))==equivalent_doi(row['doi_r'])]
    if len(matched)!=1:
        issues.append((row['candidate_id'],f'attempt matches {len(matched)}'))
    elif matched[0].get('outcome')!=row['outcome']:
        issues.append((row['candidate_id'],f'outcome {matched[0].get("outcome")} vs {row["outcome"]}'))
    if not (root/'site/dist/effect'/effect['slug']/'index.html').exists():
        issues.append((row['candidate_id'],'missing static page'))
print('curated',len(rows),'distinct_effects',len({(norm_name(r['effect_name']),equivalent_doi(r['doi_o'])) for r in rows}),'effects_total',len(effects),'attempts_total',len(attempts),'issues',len(issues))
for issue in issues[:30]:print(*issue)

if issues:raise SystemExit(1)
