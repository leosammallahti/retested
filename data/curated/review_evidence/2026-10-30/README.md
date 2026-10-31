# Full-text readings of uncoded replications and unresolved checks (30 Oct 2026)

1,425 pairs whose replication paper had an extracted full text or abstract in `/root/wiki-scratch/fullpapers_20261029/`
were read following `docs/READING_RUBRIC.md`:
- `mine20.txt`, `helper1_sample20.out`, `helper2_sample20.out`: 20-case blind calibration sample read independently
  before scaling up (exact match on link, study kind, and outcome across all 20 cases after settling one replication
  with a significant result in the opposite direction as `NOT_FOUND`).
- `batch01a.out` .. `batch19b.out`: full-text reading outputs from Sonnet 5.5 helpers, verified for exact verbatim
  substring quotes against the extracted paper texts.
- `fulltext_readings.tsv`: consolidated table of all 1,425 decisions (`case_id`, `doi_o`, `rep_key`, `needs`, `link`,
  `kind`, `result`, `authors_r`, `year_r`, `quote`, `reason`, `decided_by`).

Full paper texts remain off the public repository in `/root/wiki-scratch/fullpapers_20261029/`.
