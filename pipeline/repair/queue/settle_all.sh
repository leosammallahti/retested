#!/bin/bash
# The readings file is rebuilt in layers: the morning's readings, then the queue's, then the full-text reading's.
set -e
PY=/root/retested/.venv/bin/python
$PY -X utf8 /root/wiki-scratch/queue_20261028/consensus.py /root/wiki-scratch/queue_20261028
$PY -X utf8 /root/wiki-scratch/queue_20261028/consensus.py /root/wiki-scratch/fulltext_20261028
