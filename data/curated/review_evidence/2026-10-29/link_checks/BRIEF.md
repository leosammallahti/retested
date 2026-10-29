# Does each later paper replicate the original it is listed under?

The file has blocks. Each block starts `=== O<n>` with an ORIGINAL paper (authors, year, title, its findings if known,
its abstract), followed by later papers (`-- L<n> title | authors (year)` and its abstract), each found by a machine
search and listed as a replication of that original.

For each later paper decide one thing: does it test the original's finding again, with new data or a re-analysis of
its data, as a replication of THIS original paper?

- `Y`: yes. It replicates this original (a direct, close or conceptual replication, a registered replication, a
  student replication project of this paper, or a re-analysis of its data), even if the result differed.
- `N`: no. It replicates a different study (another paper by the same author, an earlier or later study on the
  topic), or it is not a replication of anything (a review, a new study, a scale validation of something else).
- `?`: the text cannot settle it (for example no abstract and a title that does not say which study).

When unsure, answer `?`: a pair left unverified costs nothing, a wrong `Y` puts an error on a public site.

Two traps seen in testing:
- If the ORIGINAL is a book, a book chapter, a review or a theory paper, a later study can only replicate it if it
  names a specific study reported in it, or this book or review itself. "A replication of Piaget's studies" does not
  confirm a particular Piaget book; answer `?` or `N`.
- A citation by authors and year alone ("Replication of Diener et al. (2010)") confirms nothing if it does not fit:
  "et al." for a two-author original, a different topic, or another paper by the same author that year. Answer `?`
  unless the text shows it is this paper.

Judge only from the text given. A paper titled "replication" may replicate a different study than this one: check
who and what it says it replicates against the original's authors, year, title and abstract. A different year by one
or two for the same authors and title is the same paper (online and print versions).

Read the file once (in parts if needed) and write `/root/wiki-scratch/verify_20261029/OUTPUT` with one line per later
paper, in file order, nothing else:

    L<n>|Y
    L<n>|N|<what it replicates instead, in at most 10 words, or "not a replication">
    L<n>|?

Read and write only these two files; the host is shared. Reply with one line: counts of Y, N and ?.
