"""Rekey data/curated/effect_lines.json and effect_typology.json from effect slug to the stable effect id (fx_...),
so a rename or a merge can never orphan them again. Entries of an effect folded into another move to the survivor
when it has none; when it has its own, the folded entry is kept under "set_aside" with the reason. Free; writes by
temporary file and rename."""
import json, os
B0 = '/root/wiki-scratch/audit_20261028/build_before/effects.json'   # slugs as the files were written against
B1 = '/root/retested-wiki/data/build/effects.json'                   # after the merges (has merged_keys)
CUR = '/root/retested-wiki/data/curated/'
old = json.load(open(B0, encoding='utf-8')); new = json.load(open(B1, encoding='utf-8'))
old_by_slug = {e['slug']: e for e in old}
new_by_key = {}
for e in new:
    for k in [e['key'], *e.get('merged_keys', [])]:
        new_by_key[k] = e
for fname, section in (('effect_lines.json', 'lines'), ('effect_typology.json', 'labels')):
    doc = json.load(open(CUR + fname, encoding='utf-8'))
    entries = doc[section]
    out, aside, moved, unknown = {}, {}, 0, []
    # entries of surviving effects first, so a folded entry never displaces the survivor's own
    order = sorted(entries, key=lambda s: (new_by_key.get(old_by_slug[s]['key'], {}).get('id') != old_by_slug[s]['id']) if s in old_by_slug else True)
    for slug in order:
        o = old_by_slug.get(slug)
        if not o:
            unknown.append(slug); aside[slug] = {**entries[slug], 'set_aside_because': 'no effect had this slug when the file was rekeyed (2026-10-28)'}; continue
        tgt = new_by_key.get(o['key'])
        if not tgt:
            unknown.append(slug); aside[o['id']] = {**entries[slug], 'slug_then': slug, 'set_aside_because': 'its effect no longer exists after the 2026-10-28 rebuild'}; continue
        entry = {**entries[slug], 'slug_then': slug}
        if tgt['id'] == o['id']:
            out[tgt['id']] = entry
        elif tgt['id'] not in out:
            out[tgt['id']] = {**entry, 'carried_from': f"'{o['name']}', folded into '{tgt['name']}' on 2026-10-28 (data/curated/merges.yaml)"}
            moved += 1
        else:
            aside[o['id']] = {**entry, 'set_aside_because': f"'{o['name']}' was folded into '{tgt['name']}', which has its own entry (2026-10-28)"}
    doc['schema_version'] = 2
    doc['key'] = 'effect id (the fx_ id in data/curated/registry/effect_ids.csv), never the slug: a merge or rename changes slugs'
    doc[section] = dict(sorted(out.items()))
    doc['set_aside'] = dict(sorted(aside.items()))
    tmp = CUR + fname + '.tmp'
    open(tmp, 'w', encoding='utf-8').write(json.dumps(doc, ensure_ascii=False, indent=1) + '\n'); os.replace(tmp, CUR + fname)
    print(fname, 'entries', len(entries), '-> by id', len(out), '| carried to a survivor', moved, '| set aside', len(aside), '| unknown', len(unknown))
