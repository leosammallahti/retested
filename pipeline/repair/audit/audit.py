"""Whole-site audit, 28 Oct 2026: every kind of statement the built site makes, compared with the FORRT files it came
from. Read-only. Writes audit.json (every flagged item) and prints the counts. A flag here is a question to answer,
not a verdict: where a word in a title is used (e.g. 'meta-analysis'), it only selects items for reading."""
import sys, json, re, collections
import pandas as pd
sys.path.insert(0, '/root/retested-wiki')
from rapidfuzz import fuzz
from pipeline import load
from pipeline.ids import norm_doi, norm_name

B = '/root/retested-wiki/data/build/'
FR = '/root/retested-wiki/data/raw/forrt/'
A = json.load(open(B + 'attempts.json', encoding='utf-8'))
F = json.load(open(B + 'findings.json', encoding='utf-8'))
E = json.load(open(B + 'effects.json', encoding='utf-8'))
P = json.load(open(B + 'papers.json', encoding='utf-8'))
S = json.load(open(B + 'stats.json', encoding='utf-8'))
C = json.load(open(B + 'candidates.json', encoding='utf-8'))
out = collections.OrderedDict()
def flag(group, item):
    out.setdefault(group, []).append(item)
def short(t, n=110): return re.sub(r'\s+', ' ', str(t or ''))[:n]

# ---------------------------------------------------------------- 1. FORRT pairs: on the site, in the queue, or nowhere
site_pairs = {(a['doi_o'], a['rep_key']) for a in A.values()} | {(a['doi_o'], a['doi_r']) for a in A.values() if a['doi_r']}
site_reps = {a['doi_r'] for a in A.values() if a['doi_r']}
cand_pairs = {(norm_doi(c['doi_o']), norm_doi(c['doi_r'])) for c in C if c.get('doi_o') and c.get('doi_r')}
cand_reps = {norm_doi(c['doi_r']) for c in C if c.get('doi_r')}
def pairs(rows, o, r, alt=None, url=None):
    s = set()
    for x in rows:
        do = norm_doi(x.get(o)); dr = norm_doi(x.get(r)) or (norm_doi(x.get(alt)) if alt else None) or (x.get(alt) if alt else None) or (x.get(url) if url else None)
        if do and dr: s.add((do, dr if isinstance(dr, str) else str(dr)))
    return s
leg = load.load_legacy()
src = {
    'FLoRA': pairs(load.load_flora(), 'doi_o', 'doi_r', 'alt_identifier_r', 'url_r'),
    'FReD current': pairs(load.load_fred(), 'doi_o', 'doi_r', None, 'url_r'),
    'FReD 2.4.1 data sheet': pairs(leg['data'], 'doi_original', 'doi_replication'),
    'Replications & Reversals sheet': pairs(leg['rr'], 'doi_original', 'doi_replication'),
    'FLoRA validation sheets': pairs(pd.read_csv(FR + 'feeds/flora-validation_flora_entry_sheets.csv', dtype=str, keep_default_na=False).to_dict('records'), 'doi_o', 'doi_r', 'alt_identifier_r', 'url_r'),
    'FLoRA extractor (machine-found)': pairs(pd.read_csv(FR + 'feeds/flora-extractor_extracted.csv', dtype=str, keep_default_na=False).to_dict('records'), 'doi_o', 'doi_r', None, 'url_r'),
}
cov = {}
for name, ps in src.items():
    on = {p for p in ps if p in site_pairs}
    q = {p for p in ps - on if p in cand_pairs}
    rep_elsewhere = {p for p in ps - on - q if p[1] in site_reps}
    nowhere = ps - on - q - rep_elsewhere
    cov[name] = {'pairs': len(ps), 'on_site': len(on), 'in_unread_queue': len(q), 'replication_on_site_under_another_original': len(rep_elsewhere), 'nowhere': len(nowhere)}
    for p in sorted(nowhere): flag(f'pair not on the site: {name}', {'doi_o': p[0], 'doi_r': p[1]})
    for p in sorted(rep_elsewhere): flag(f'pair whose replication sits under another original: {name}', {'doi_o': p[0], 'doi_r': p[1]})
atlas = {norm_doi(m) for m in re.findall(r'/doi/(10\.[^<]+?)/?</loc>', open(FR + 'feeds/atlas_sitemap.xml').read())} - {None}
cand_orig = {norm_doi(c['doi_o']) for c in C if c.get('doi_o')}
cov['FORRT atlas original papers'] = {'papers': len(atlas), 'on_site_as_finding': len(atlas & set(F)), 'only_in_unread_queue': len((atlas - set(F)) & cand_orig), 'nowhere': len(atlas - set(F) - cand_orig)}
out['coverage'] = cov

# ---------------------------------------------------------------- 2. attempts
by_title = {}
for aid, a in A.items():
    po = P.get(a['doi_o'], {})
    t_r, t_o = a.get('title_r'), po.get('title')
    rec = {'id': aid, 'doi_o': a['doi_o'], 'doi_r': a['doi_r'], 'original': short(t_o), 'replication': short(t_r), 'year_r': a.get('year_r'), 'sources': a['sources'], 'outcome': a['outcome']}
    if a['doi_r'] and a['doi_r'] == a['doi_o']:
        flag('attempt: the original paper is listed as its own replication (same DOI)', rec)
    elif t_r and t_o and fuzz.ratio(str(t_r).lower(), str(t_o).lower()) >= 95:
        flag('attempt: replication title equals the original title (likely the same paper)', rec)
    yo = po.get('year')
    if a.get('year_r') and yo and float(a['year_r']) < float(yo):
        flag('attempt: replication dated before the original', {**rec, 'year_o': yo})
    if not t_r or str(t_r).strip().lower() in ('none', 'nan', '') or str(t_r).startswith('http'):
        flag('attempt: no replication title', rec)
    if not a.get('authors_r') or str(a.get('authors_r')).strip().lower() in ('none', 'nan', ''):
        flag('attempt: no replication authors', rec)
    if not a.get('year_r'):
        flag('attempt: no replication year', rec)
    if t_r and re.search(r'meta-?analy|systematic review|\breview\b|commentary|\breply\b|comment on|rejoinder|erratum|corrigendum', str(t_r), re.I):
        flag('attempt: title says review, meta-analysis, commentary or reply (needs reading)', rec)
    obs = {k: v for k, v in a['outcomes_by_source'].items() if v != 'not_coded'}
    if obs.get('flora') and a['outcome'] != obs['flora'] and not a.get('outcome_adjudication'):
        flag('attempt: site result differs from FLoRA without a recorded adjudication', {**rec, 'by_source': a['outcomes_by_source']})
    if a.get('sources_disagree'):
        flag('attempt: FORRT sources disagree on the result (shown as such)', {**rec, 'by_source': a['outcomes_by_source']})
    if a['outcome'] == 'not_coded':
        flag('attempt: no result coded', rec)

# ---------------------------------------------------------------- 3. effects
owners = collections.Counter(x for e in E for x in e['attempts'])
for e in E:
    rec = {'slug': e['slug'], 'name': e['name'], 'famous': bool(e.get('famous')), 'own': len(e['attempts']), 'shared': len(e['shared_attempts'])}
    if not e['attempts']:
        unowned = [x for x in e['shared_attempts'] if owners[x] == 0]
        why = ('its paper was retested but the replication is attached to no effect' if unowned else
               'replications of its paper are filed under other effect names' if e['shared_attempts'] else
               'no replication linked at all')
        flag(f'effect without a replication of its own: {why}', rec)
    n = e['name']
    if len(n) < 4 or n.count('(') != n.count(')') or '**' in n or re.search(r'\(e\.g$|\be\.g$', n) or n.endswith(('-', ',')):
        flag('effect name looks broken (cut off, stray marks)', rec)
    d = e.get('description') or ''
    if d and (d[0] in ').,;:' or d[:1].islower() or '**' in d or re.match(r'^[A-Z][a-z]+ Effect\)?\.', d)):
        flag('effect description starts mid-sentence or carries stray marks', {**rec, 'description': short(d, 160)})
    # description sharing no content word with the effect's name, its FORRT text or its original papers' titles
    words = lambda s: {w for w in re.findall(r'[a-z]{5,}', str(s).lower())} - {'effect', 'effects', 'people', 'participants', 'their', 'which', 'higher', 'lower', 'about', 'other', 'study', 'studies'}
    if d:
        ctx = words(n) | words((e.get('famous') or {}).get('description')) | set().union(*[words(P.get(x, {}).get('title')) for x in e['originals']] or [set()])
        if ctx and not (words(d) & ctx):
            flag('effect description shares no word with its name or its papers (may belong to another effect)', {**rec, 'description': short(d, 160), 'papers': [short(P.get(x, {}).get('title'), 80) for x in e['originals'][:2]]})
desc_users = collections.defaultdict(list)
for e in E:
    if e.get('description') and len(e['description']) > 40:
        desc_users[e['description'].strip().lower()].append(e['name'])
for d, ns in desc_users.items():
    if len(ns) > 1 and len({norm_name(x) for x in ns}) > 1:
        flag('one description used for several differently named effects', {'names': ns, 'description': short(d, 120)})
# same original + same own attempts under two names
by_set = collections.defaultdict(list)
for e in E:
    if e['attempts']: by_set[tuple(e['attempts'])].append(e['name'])
for k, ns in by_set.items():
    if len(ns) > 1: flag('two or more effects with exactly the same replications (likely one effect under two names)', {'names': ns, 'attempts': len(k)})

# ---------------------------------------------------------------- 4. lists and counts
for lst in ('graveyard', 'survivors', 'contested', 'most_tested'):
    for c in S['lists'][lst]:
        if c['record']['n_attempts'] == 0:
            flag(f'list "{lst}" shows an effect with no replication', {'slug': c['slug'], 'name': c['name'], 'famous_status': c.get('famous_status'), 'code': c['record']['code']})
        fs = c.get('famous_status')
        if lst == 'survivors' and c['record']['code'] in ('failed', 'largely_failed', 'single_failure', 'contested'):
            flag('list "survivors" shows an effect whose replications mostly failed', {'slug': c['slug'], 'name': c['name'], 'code': c['record']['code']})
out['counts_shown'] = {k: S['counts'][k] for k in ('effects', 'effects_with_attempts', 'findings', 'attempts')}

# ---------------------------------------------------------------- 5. the famous list (FORRT Replications & Reversals text)
fam = load.load_famous()
fam_keys = {norm_name(f['name']) for f in fam if f.get('name')}
eff_by_key = {e['key']: e for e in E}
matched = [eff_by_key.get(k) for k in fam_keys]
out['famous_list'] = {'entries': len(fam_keys), 'effect_with_replications': sum(1 for e in matched if e and e['attempts']), 'effect_without': sum(1 for e in matched if e and not e['attempts']), 'no_effect': sum(1 for e in matched if not e)}
for e in E:
    f = e.get('famous') or {}
    code = e['lenses']['record']['code']
    if f.get('status') == 'replicated' and code in ('failed', 'largely_failed', 'single_failure'):
        flag("FORRT's list says replicated, the linked replications say failed", {'slug': e['slug'], 'name': e['name'], 'code': code})
    if f.get('status') in ('not_replicated', 'reversed') and code in ('replicated', 'largely_replicated', 'single_success'):
        flag("FORRT's list says not replicated, the linked replications say found", {'slug': e['slug'], 'name': e['name'], 'code': code})

summary = {g: len(v) for g, v in out.items() if isinstance(v, list)}
json.dump({'summary': summary, 'coverage': out['coverage'], 'famous_list': out['famous_list'], 'counts_shown': out['counts_shown'],
           'items': {g: v for g, v in out.items() if isinstance(v, list)}}, open('/root/wiki-scratch/audit_20261028/audit.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps(out['coverage'], indent=1)); print(out['famous_list']); print(out['counts_shown'])
for g, n in summary.items(): print(f'{n:6d}  {g}')
