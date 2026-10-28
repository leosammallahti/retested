"""After a merge, move entries of folded effect ids in effect_lines.json / effect_typology.json to the survivor (when it
has none) or into set_aside (when it has its own), so no entry points at an effect that no longer exists."""
import json, os, sys
prev = json.load(open(sys.argv[1] if len(sys.argv) > 1 else '/root/wiki-scratch/audit_20261028/build_after_first_merges/effects.json', encoding='utf-8'))
now = json.load(open('/root/retested-wiki/data/build/effects.json', encoding='utf-8'))
key_of = {e['id']: e['key'] for e in prev}; name_of = {e['id']: e['name'] for e in prev}
surv = {}
for e in now:
    for k in [e['key'], *e.get('merged_keys', [])]: surv[k] = e
ids_now = {e['id'] for e in now}
for fname, section in (('effect_lines.json', 'lines'), ('effect_typology.json', 'labels')):
    p = '/root/retested-wiki/data/curated/' + fname
    doc = json.load(open(p, encoding='utf-8')); moved = aside = 0
    for i in [i for i in doc[section] if i not in ids_now]:
        entry = doc[section].pop(i); t = surv.get(key_of.get(i))
        if t and t['id'] not in doc[section]:
            doc[section][t['id']] = {**entry, 'carried_from': f"'{name_of.get(i)}', folded into '{t['name']}' on 2026-10-28 (data/curated/merges.yaml)"}; moved += 1
        else:
            doc['set_aside'][i] = {**entry, 'set_aside_because': f"'{name_of.get(i)}' was folded into '{t['name'] if t else '?'}', which has its own entry (2026-10-28)"}; aside += 1
    doc[section] = dict(sorted(doc[section].items())); doc['set_aside'] = dict(sorted(doc['set_aside'].items()))
    open(p + '.tmp', 'w', encoding='utf-8').write(json.dumps(doc, ensure_ascii=False, indent=1) + '\n'); os.replace(p + '.tmp', p)
    print(fname, 'carried', moved, 'set aside', aside, 'now', len(doc[section]))
