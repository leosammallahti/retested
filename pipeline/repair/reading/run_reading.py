#!/usr/bin/env python3
"""Stage 1 reading (paid, approved by Leo 28 Oct 2026: "Yeah"): two cheap models read each later paper's title and
abstract and answer questions.py, with quotes checked word for word. Resumable from its own logs; stops before the cap.

    python run_reading.py plan  --items test3
    python run_reading.py run   --items test3 --cap-usd 0.02 --approved "Yeah"
    python run_reading.py run   --items all   --cap-usd 1.00 --approved "Yeah"
"""
import argparse, concurrent.futures, json, sys, threading, time, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path
HERE = Path('/root/wiki-scratch/reading_20261028')
sys.path.insert(0, str(HERE)); sys.path.insert(0, '/root/wiki-scratch/typology_test_20261026')
import questions as Q
from run_test import secret, prices, sha, quote_found, parse_json, Limiter, URL
RUNS = ['deepseek-v4.1-flash#1', 'glm-5.3-flash#1']
MAX_TOKENS, RETRY_MAX_TOKENS = 500, 1500
MODEL_MAX = {'glm-5.3-flash': (3000, 6000)}   # GLM reasons at length whatever reasoning_effort says
OUT = HERE / 'answers'


def later_text(item):
    return item['later']


def judge(parsed, item):
    rec = {}
    ok = True
    for k, allowed in Q.ANSWERS.items():
        if k == 'is_cited_paper' and not item.get('cited_ref'):
            continue
        v = str(parsed.get(k, '')).strip().upper().replace(' ', '_').replace('-', '_')
        rec[k] = v
        ok &= v in allowed
    # a result only applies to a replication or reanalysis; for any other kind it is set to NOT_APPLICABLE
    if rec.get('kind') in Q.ANSWERS['kind'] and rec['kind'] not in ('NEW_DATA_REPLICATION', 'REANALYSIS'):
        rec['result_given'] = rec.get('result')
        rec['result'] = 'NOT_APPLICABLE'
    for k in ('kind', 'result'):
        q = str(parsed.get(k + '_quote', '') or '')
        if rec.get(k) in Q.EMPTY_OK[k]:
            q = ''          # an answer that needs no quote is not failed by a stray one
        found = quote_found(q, later_text(item))
        rec[k + '_quote'], rec[k + '_quote_found'] = q, found
        ok &= found is True or (found is None and rec.get(k) in Q.EMPTY_OK[k])
    rec['valid'] = bool(ok)
    return rec


class Runner:
    def __init__(self, cap, rate):
        self.cap, self.key, self.prices = cap, secret(), prices()
        self.lock, self.limiter, self.stop = threading.RLock(), Limiter(rate), threading.Event()
        self.spent = sum(json.loads(l).get('cost_usd', 0.0) for p in OUT.glob('*.jsonl') for l in p.read_text(encoding='utf-8').splitlines())
        self.calls = self.failed = 0
        OUT.mkdir(exist_ok=True)
        self.handles = {}

    def done(self, run):
        p = OUT / f'{run}.jsonl'
        return {json.loads(l)['item'] for l in p.read_text(encoding='utf-8').splitlines() if json.loads(l).get('valid')} if p.exists() else set()

    def call(self, run, item):
        model = run.split('#')[0]
        messages = Q.messages(item)
        max_tokens, retry_max = MODEL_MAX.get(model, (MAX_TOKENS, RETRY_MAX_TOKENS))
        for attempt in (1, 2, 3):
            if self.stop.is_set():
                return
            p_in, p_out, _ = self.prices[model]
            ceiling = 2 * (p_in * sum(len(m['content']) for m in messages) / 3.0 + p_out * max_tokens)
            with self.lock:
                if self.spent + ceiling > self.cap:
                    self.stop.set(); print(f'STOP: spent ${self.spent:.4f} + next ${ceiling:.5f} would pass cap ${self.cap}', flush=True); return
            body = {'model': model, 'messages': messages, 'temperature': 0.0, 'max_tokens': max_tokens,
                    'reasoning_effort': 'none', 'prompt_cache_key': 'retested-read-' + item['item'][:60]}
            rec = {'utc': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'version': Q.VERSION, 'run': run, 'model': model,
                   'item': item['item'], 'attempt': attempt, 'item_sha256': item['sha256'], 'prompt_sha256': sha(Q.SYSTEM + Q.BODY)}
            self.limiter.wait(); t0 = time.monotonic()
            try:
                req = urllib.request.Request(URL, data=json.dumps(body, ensure_ascii=False).encode(),
                                             headers={'Authorization': 'Bearer ' + self.key, 'Content-Type': 'application/json',
                                                      'x-ci-prompt-cache-session': body['prompt_cache_key']})
                with urllib.request.urlopen(req, timeout=180) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                ch = data['choices'][0]
                rec['content'], rec['finish_reason'], rec['usage'] = ch['message'].get('content') or '', ch.get('finish_reason'), data.get('usage')
                rec.update(judge(parse_json(rec['content']), item))
            except urllib.error.HTTPError as e:
                rec['error'] = {'status': e.code, 'body': e.read().decode(errors='replace').replace(self.key, '[REDACTED]')[:500]}; rec['valid'] = False
                if e.code in (401, 402, 403): self.stop.set()
            except Exception as e:
                rec['error'] = {'type': type(e).__name__, 'message': str(e).replace(self.key, '[REDACTED]')[:500]}; rec['valid'] = False
            rec['seconds'] = round(time.monotonic() - t0, 2)
            u = rec.get('usage') or {}
            if u.get('cost') is not None: rec['cost_usd'], rec['cost_is_billed'] = float(u['cost']), True
            elif u: rec['cost_usd'], rec['cost_is_billed'] = 2 * (p_in * u.get('prompt_tokens', 0) + p_out * u.get('completion_tokens', 0)), False
            elif (rec.get('error') or {}).get('status'): rec['cost_usd'], rec['cost_is_billed'] = 0.0, False
            else: rec['cost_usd'], rec['cost_is_billed'] = ceiling, False
            with self.lock:
                self.spent += rec['cost_usd']; self.calls += 1
                h = self.handles.setdefault(run, (OUT / f'{run}.jsonl').open('a', encoding='utf-8'))
                h.write(json.dumps(rec, ensure_ascii=False) + '\n'); h.flush()
            if rec['valid']: return
            if rec.get('finish_reason') == 'length': max_tokens = retry_max
            st = (rec.get('error') or {}).get('status')
            if st and 400 <= st < 500 and st != 429: break
            time.sleep(5 * attempt if st == 429 else 2 * attempt if st else 0)
        with self.lock: self.failed += 1


def load_items(which):
    items = [json.loads(l) for l in (HERE / 'items.jsonl').read_text(encoding='utf-8').splitlines()]
    if which == 'all': return items
    ids = json.loads((HERE / f'{which}.json').read_text())
    by = {i['item']: i for i in items}
    return [by[i] for i in ids]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=['plan', 'run']); ap.add_argument('--items', default='test3')
    ap.add_argument('--cap-usd', type=float); ap.add_argument('--approved', default=''); ap.add_argument('--workers', type=int, default=16)
    ap.add_argument('--rate', type=float, default=6.0)
    a = ap.parse_args(); items = load_items(a.items); pr = prices()
    est = sum(2 * (pr[r.split('#')[0]][0] * sum(len(m['content']) for m in Q.messages(i)) / 3.6 + pr[r.split('#')[0]][1] * 120) / 2 for i in items for r in RUNS)
    print(f'{len(items)} items x {len(RUNS)} runs = {len(items) * len(RUNS)} calls; estimated ${est:.3f}')
    if a.mode == 'plan': return
    if not a.approved or a.cap_usd is None: raise SystemExit('run needs --approved and --cap-usd')
    R = Runner(a.cap_usd, a.rate)
    done = {run: R.done(run) for run in RUNS}
    # paper by paper, both models in turn, so each paper gets its pair of answers early; papers one model has
    # already answered come first, so their pairs complete first
    order = sorted(items, key=lambda it: -sum(it['item'] in done[r] for r in RUNS))
    with concurrent.futures.ThreadPoolExecutor(a.workers) as ex:
        for it in order:
            for run in RUNS:
                if it['item'] not in done[run]: ex.submit(R.call, run, it)
    for h in R.handles.values(): h.close()
    print(f'calls {R.calls}, failed {R.failed}, total spent on this reading ${R.spent:.4f}')


if __name__ == '__main__':
    main()
