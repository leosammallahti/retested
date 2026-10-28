#!/bin/bash
# Reruns the queue reading after any stop except its dollar cap (resumes from the answer logs); stops when complete.
cd /root/wiki-scratch/queue_20261028
for i in $(seq 1 12); do
  /root/retested/.venv/bin/python -X utf8 run_reading.py run --items all --cap-usd 4.00 --approved "Yes, run it (cap \$4) (Leo, 28 Oct 2026)" --rate 0.6 --workers 6 >> run.log 2>&1
  if grep -q "^STOP: spent" run.log; then echo "cap reached $(date -u +%FT%TZ)" >> run.log; break; fi
  left=$(/root/retested/.venv/bin/python -X utf8 -c "
import json, glob
items={json.loads(l)['item'] for l in open('items.jsonl',encoding='utf-8')}
d=set()
for f in glob.glob('answers/*.jsonl'):
    for l in open(f,encoding='utf-8'):
        r=json.loads(l)
        if r.get('valid'): d.add((r['run'], r['item']))
print(sum(1 for r in ('deepseek-v4.1-flash#1','glm-5.3-flash#1') for it in items if (r,it) not in d))")
  echo "pass $i done $(date -u +%FT%TZ), calls without a valid answer: $left" >> run.log
  [ "$left" -lt 60 ] && break
  sleep 600
done
echo "WATCHER FINISHED $(date -u +%FT%TZ)" >> run.log
