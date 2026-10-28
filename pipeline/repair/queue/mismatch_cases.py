"""Cases for a reader: queue replications whose title or abstract names the study they replicate with authors or a
year that do not match the linked original (author_check.py). Writes mismatch_cases.txt and MISMATCH_BRIEF.md."""
import json
H = '/root/wiki-scratch/queue_20261028/'
F = json.load(open(H + 'author_mismatch.json'))
I = {json.loads(l)['item']: json.loads(l) for l in open(H + 'items.jsonl')}
done = {l.split(' | ')[0].strip() for l in open(H + 'mismatch_decisions.txt')} if __import__('os').path.exists(H + 'mismatch_decisions.txt') else set()
out = [f"=== CASE {f['item']}\nNAMED IN THE LATER PAPER: {f['cites']}\nLINKED ORIGINAL: authors {', '.join(f['original_authors'])}; year {f['original_year']}\n{I[f['item']]['original'][:700]}\nLATER PAPER:\n{I[f['item']]['later'][:1500]}\n" for f in F if f['item'] not in done]
open(H + 'mismatch_cases.txt', 'w').write('\n'.join(out))
open(H + 'MISMATCH_BRIEF.md', 'w').write("""# Brief: is this the original the later paper replicates? (Retested, 28 Oct 2026)

Each case in /root/wiki-scratch/queue_20261028/mismatch_cases.txt is a later paper two models read as a replication
of the LINKED ORIGINAL. The later paper's own text names the study it replicates (NAMED IN THE LATER PAPER), and those
names or that year do not plainly match the linked original. Decide from the text only:

- SAME: the named study is the linked original (for example the same paper in another year, a name spelled
  differently, or a working-paper version), so the link is right.
- OTHER: the later paper replicates a different study (another paper by the same author, another team's study).
- UNSURE: the text cannot settle it.

Write /root/wiki-scratch/queue_20261028/mismatch_decisions.txt, one line per case, nothing else:
<case id> | SAME|OTHER|UNSURE | <reason, at most 15 words>
Read and write only these files (the host is shared). Reply with one line of counts.
""")
print(len(out), 'cases', sum(len(x) for x in out) // 4, 'tokens')
