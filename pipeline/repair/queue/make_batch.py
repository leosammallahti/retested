"""Write the next adjudication batch: splits in disagreements.txt not yet decided in adjudicated.txt or an open batch.
    python make_batch.py NAME [MAX]     -> adjudicate_NAME.txt (and .ids)"""
import sys, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
done = {l.split(' | ')[0] for l in (HERE / 'adjudicated.txt').read_text(encoding='utf-8').splitlines()} if (HERE / 'adjudicated.txt').exists() else set()
for f in HERE.glob('adjudicate_*.ids'):
    done |= set(f.read_text().split())
cases = [c for c in (HERE / 'disagreements.txt').read_text(encoding='utf-8').split('=== ITEM ')[1:]]
todo = [c for c in cases if c.split('\n', 1)[0].strip() not in done][:int(sys.argv[2]) if len(sys.argv) > 2 else 10**9]
(HERE / f'adjudicate_{sys.argv[1]}.txt').write_text(''.join('=== ITEM ' + c for c in todo), encoding='utf-8')
(HERE / f'adjudicate_{sys.argv[1]}.ids').write_text('\n'.join(c.split('\n', 1)[0].strip() for c in todo))
print(len(todo), 'cases in', f'adjudicate_{sys.argv[1]}.txt', sum(len(c) for c in todo) // 4, 'tokens about')
