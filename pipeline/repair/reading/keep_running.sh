#!/bin/bash
# Reruns the reading after any stop except its dollar cap (resumes from the answer logs); stops when complete.
cd /root/wiki-scratch/reading_20261028
for i in $(seq 1 12); do
  /root/retested/.venv/bin/python -X utf8 run_reading.py run --items all --cap-usd 1.60 --approved "Yeah; GLM is fine, \$1.4 is fine (Leo, 28 Oct 2026)" --rate 2.5 --workers 10 >> run.log 2>&1
  if grep -q "^STOP: spent" run.log; then echo "cap reached $(date -u +%FT%TZ)" >> run.log; break; fi
  left=$(/root/retested/.venv/bin/python -X utf8 -c "
import json
items={json.loads(l)['item'] for l in open('items.jsonl',encoding='utf-8')}
d=set()
import glob
for f in glob.glob('answers/*.jsonl'):
    for l in open(f,encoding='utf-8'):
        r=json.loads(l)
        if r.get('valid'): d.add((r['run'], r['item']))
print(sum(1 for r in ('deepseek-v4.1-flash#1','glm-5.3-flash#1') for it in items if (r,it) not in d))")
  echo "pass $i done $(date -u +%FT%TZ), calls without a valid answer: $left" >> run.log
  [ "$left" -lt 30 ] && break
  sleep 600
done
echo "WATCHER FINISHED $(date -u +%FT%TZ)" >> run.log
