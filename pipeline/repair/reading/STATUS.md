# Paper reading, 28 Oct 2026 (Leo approved: "Yeah"; "GLM is fine, $1.4 is fine"; cap $1.60)

- What runs: `keep_running.v5.sh` (detached) -> `run_reading.py run --items all`, DeepSeek v4.1 flash + GLM 5.3 flash
  through cheaperinference, paper by paper. Shared account limit about 25 requests/minute (another session's
  find_trials job uses the same key); the watcher reruns every 10 minutes until fewer than 30 calls lack a valid answer.
- Inputs: `items.jsonl` (2,297 papers: 583 Replications & Reversals citations with DOIs, 419 by reference via Crossref,
  1,295 attempts on the site: uncoded, titled like reviews, dated before their original, doubtful pairings).
  Built by `build_items.py`; questions in `questions.py` (v2).
- Logs: `answers/<model>#1.jsonl` (append-only; `answers_backup/` before the re-check of 08:03 UTC), `run.log`.
- Next, as answers arrive:
  1. `python consensus.py` -> `/root/retested-wiki/data/curated/read_pairs.json` (agreed answers) and
     `disagreements.txt` (splits); a reader writes decisions to `adjudicated.txt` (format in consensus.py) and reruns it.
  2. `python -m pipeline build` in /root/retested-wiki; then `python -m pipeline quality-audit`; compare with
     `/root/wiki-scratch/audit_20261028/compare.py`; site build and verify; tests.
  3. Report to Leo: per group, how many were replications, what they found, what was set aside, what a person must read
     (`g["read_notes"]`: readings that disagree with a result FORRT coded).
