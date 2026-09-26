"""Publish staged, source-reviewed Retested rows in one validated batch.

Usage: .venv/bin/python -m pipeline.batch_publish /tmp/batch1.json /tmp/batch2.json
Input files are reader-produced JSON lists or {"rows": ..., "fields": ...} objects.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

from . import load, queue, registry, score
from .ids import EffectLedger
from .promoted import FILE, load as load_rows, validate
from .__main__ import LEDGER

ROOT = Path(__file__).resolve().parent.parent
FIELDS = ROOT / "data/curated/replication_primary_fields_20260925.json"
CANDIDATES = ROOT / "data/build/candidates.json"

def read_packet(path: Path):
    data = json.loads(path.read_text())
    rows = data["rows"] if isinstance(data, dict) else data
    fields = data["fields"] if isinstance(data, dict) else json.loads(path.with_name(path.stem + "_fields.json").read_text())
    if isinstance(fields, list):
        fields = {x["doi"]: {"id": x["id"], "field": x["field"], "topic": x.get("topic")} for x in fields}
    elif isinstance(fields, dict) and "records" in fields:
        fields = fields["records"]
    return rows, fields

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", type=Path)
    args = ap.parse_args()
    t0 = time.monotonic()
    base = load_rows()
    existing = {(r["doi_o"], r["doi_r"]) for r in base}
    by_pair = defaultdict(list)
    packet_fields = {}
    for path in args.files:
        rows, fields = read_packet(path)
        packet_fields[path] = fields
        for row in rows:
            key = (row["doi_o"], row["doi_r"])
            if key not in existing:
                by_pair[key].append((path, row))
    selected = [max(versions, key=lambda x: x[0].stat().st_mtime) for versions in by_pair.values()]
    new = [row for _, row in selected]
    if not new:
        print("NO_NEW_PAIRS")
        return 0
    validate(base + new)
    primary = json.loads(FIELDS.read_text())
    for path, row in selected:
        key = (row["doi_o"], row["doi_r"])
        field = packet_fields[path].get(row["doi_r"])
        if not field:
            for alt_path, _ in by_pair[key]:
                field = packet_fields[alt_path].get(row["doi_r"])
                if field:
                    break
        if not field or field["field"] != "Psychology":
            raise ValueError(f"missing Psychology field: {row['doi_r']} in {path}")
        prior = primary["records"].get(row["doi_r"])
        if prior and prior["field"] != field["field"]:
            raise ValueError(f"field conflict: {row['doi_r']}")
        primary["records"].setdefault(row["doi_r"], field)
    before_rows = FILE.read_text()
    before_fields = FIELDS.read_text()
    old_queue = json.loads(CANDIDATES.read_text())
    try:
        FILE.write_text(json.dumps(base + new, ensure_ascii=False, indent=2) + "\n")
        FIELDS.write_text(json.dumps(primary, ensure_ascii=False, indent=2) + "\n")
        load_rows()
    except Exception:
        FILE.write_text(before_rows)
        FIELDS.write_text(before_fields)
        raise
    src = {
        "flora": load.load_flora(), "fred": load.load_fred(), "legacy": load.load_legacy(),
        "famous": load.load_famous(), "openalex": load.load_openalex(),
        "merges": load.load_merges(), "promoted": load.load_promoted(),
    }
    graph = registry.build(src, EffectLedger(LEDGER))
    score.score(graph)
    current = queue.dedupe(
        queue.build(load.load_extractor(), graph)
        + queue.build_retested(
            load.load_triaged(), load.merged_links(), graph, load.load_known_replication_dois(),
            load.load_known_osf_ids(), load.load_surname_frequency(), load.load_osf(),
            load.load_original_authors(),
        )
    )
    old_ids = {x["id"]: x for x in old_queue}
    current_ids = {x["id"]: x for x in current}
    lost = [x for k, x in old_ids.items() if k not in current_ids]
    added = [x for k, x in current_ids.items() if k not in old_ids]
    new_dois = {r["doi_r"] for r in new}
    unrelated = [x for x in lost if x["doi_r"] not in new_dois]
    print(f"QUEUE old={len(old_queue)} new={len(current)} lost={len(lost)} restored={len(added)}")
    if unrelated:
        raise ValueError(f"unrelated candidate loss: {[(x['id'], x['doi_r']) for x in unrelated[:10]]}")
    def run(*argv):
        subprocess.run(argv, cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    run(sys.executable, "-m", "pipeline", "build", "--accept-baseline")
    subprocess.run(["npm", "run", "build"], cwd=ROOT / "site", check=True, stdout=subprocess.DEVNULL)
    run(sys.executable, "-m", "pipeline.audit_promoted")
    run(sys.executable, "-m", "pipeline.forrt_provenance")
    run("git", "diff", "--check")
    counts = json.loads((ROOT / "data/build/stats.json").read_text())["counts"]
    audit = json.loads((ROOT / "data/curated/forrt_overlap_audit_20260926.json").read_text())["summary"]
    print(
        f"COMPLETE added={len(new)} reviewed={counts['retested_reviewed_pairs']} "
        f"new_to_site={counts['retested_new_pairs']} candidate_links="
        f"{audit['combined_local_and_live_classifications']['later_paper_recorded_pair_unconfirmed'] + audit['combined_local_and_live_classifications']['no_exact_doi_or_title_match']} "
        f"elapsed_s={time.monotonic()-t0:.1f}"
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

