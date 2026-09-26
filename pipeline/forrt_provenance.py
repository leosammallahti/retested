"""Update Retested pair provenance against local history and current official FORRT CSVs.

Run: .venv/bin/python -m pipeline.forrt_provenance
The command updates only data/curated/forrt_overlap_audit_20260926.json.
"""
import concurrent.futures
import urllib.request

import csv
import datetime
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from pipeline.ids import norm_doi
from pipeline.load import load_known_replication_dois

AUDIT=Path("data/curated/forrt_overlap_audit_20260926.json")
ATTEMPTS=Path("data/build/attempts.json")
LOCAL=Path("data/raw/forrt/feeds/flora-extractor_extracted.csv")
LIVE=[("extractor",Path("/tmp/retested_live_forrt_extractor.csv")),("pending",Path("/tmp/retested_live_forrt_pending.csv")),("validated",Path("/tmp/retested_live_forrt_validated.csv")),("flora",Path("/tmp/retested_live_forrt_flora.csv")),("flora_filtered",Path("/tmp/retested_live_forrt_flora_filtered.csv"))]
VALID={"successful","failed","mixed","cannot_be_determined","uninformative"}
STRONG={"same_pair_exact_dois","same_pair_title_alternate_doi"}

def canon(value):
    d=norm_doi(value)
    return re.sub(r"^(10\.\d{4,9})/+",r"\1/",d) if d else None

def title(value):
    s=unicodedata.normalize("NFKD",str(value or "")).encode("ascii","ignore").decode().lower()
    return " ".join(re.findall(r"[a-z0-9]+",s))

LIVE_URLS={
    "extractor":"https://raw.githubusercontent.com/forrtproject/flora-extractor/HEAD/data/extracted.csv",
    "pending":"https://raw.githubusercontent.com/forrtproject/flora-extractor/HEAD/data/target_pending.csv",
    "validated":"https://raw.githubusercontent.com/forrtproject/flora-validation/HEAD/data/validated_export.csv",
    "flora":"https://raw.githubusercontent.com/forrtproject/fred-data/main/output/flora.csv",
    "flora_filtered":"https://raw.githubusercontent.com/forrtproject/fred-data/main/output/flora_filtered.csv",
}
def fetch(item):
    name,url=item
    with urllib.request.urlopen(url,timeout=45) as response:
        data=response.read()
    dict(LIVE)[name].write_bytes(data)
    return name,len(data)
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
    for name,size in pool.map(fetch,LIVE_URLS.items()):
        print("FETCHED",name,size,flush=True)

old=json.loads(AUDIT.read_text())
prior={(canon(r["doi_o"]),canon(r["doi_r"])):r for r in old["records"]}
assert len(prior)==len(old["records"]),"audit identity collision"
attempts=json.loads(ATTEMPTS.read_text())
pairs={(canon(a["doi_o"]),canon(a["doi_r"])):a for a in attempts.values() if set(a["sources"])=={"retested"}}
assert len(pairs)==len([a for a in attempts.values() if set(a["sources"])=={"retested"}])
new=set(pairs)-set(prior)
known=load_known_replication_dois()
local={}
with LOCAL.open(newline="",encoding="utf-8") as f:
    for rowno,x in enumerate(csv.DictReader(f),2):
        key=(canon(x.get("doi_o")),canon(x.get("doi_r")))
        if key in new:
            local[key]={"row":rowno,"outcome":x.get("outcome") or None}
records=[]
for key,a in sorted(pairs.items()):
    if key in prior:
        r=prior[key].copy()
        r["doi_o"],r["doi_r"]=key
        r["retested_outcome"]=a["outcome"]
    else:
        hit=local.get(key)
        cls="same_pair_exact_dois" if hit else "later_paper_doi_only" if key[1] in known else "no_exact_doi_or_title_match_in_local_forrt_tables"
        r={"doi_o":key[0],"doi_r":key[1],"classification":cls,"evidence":{"path":"feeds/flora-extractor_extracted.csv","row":hit["row"],"exact_pair":True} if hit else None,"forrt_extractor_outcome":hit["outcome"] if hit else None,"retested_outcome":a["outcome"]}
    records.append(r)
bydoi=defaultdict(list)
bytitle=defaultdict(list)
for key,a in pairs.items():
    bydoi[key[1]].append(key)
    t=title(a.get("title_r"))
    if len(t)>=30: bytitle[t].append(key)
live=defaultdict(list)
for source,path in LIVE:
    with path.open(newline="",encoding="utf-8-sig") as f:
        for rowno,x in enumerate(csv.DictReader(f),2):
            ds={canon(x.get(v)) for v in ("doi_r","doi_r_published","alt_identifier_r","url_r","replication_doi")}
            ds.discard(None)
            t=title(x.get("title_r") or x.get("title_replication") or x.get("replication_title"))
            keys=set()
            for d in ds: keys.update(bydoi.get(d,()))
            if len(t)>=30: keys.update(bytitle.get(t,()))
            if not keys: continue
            originals={canon(x.get(v)) for v in ("doi_o","alt_identifier_o","original_doi","doi_original")}
            originals.discard(None)
            for key in keys:
                live[key].append({"source":source,"row":rowno,"match_basis":"doi" if key[1] in ds else "title","same_original":key[0] in originals,"outcome":x.get("outcome") or None,"source_later_dois":sorted(ds)[:3]})
for r in records:
    key=(r["doi_o"],r["doi_r"])
    hits=live.get(key,[])
    best=next((x for x in hits if x["same_original"] and x["source"]=="extractor"),None) or next((x for x in hits if x["same_original"]),None) or next((x for x in hits if x["source"]=="extractor"),None) or (hits[0] if hits else None)
    r["live_match"]=best
    if r["classification"] in STRONG or any(x["same_original"] for x in hits):
        r["combined_classification"]="same_pair_recorded"
    elif r["classification"]!="no_exact_doi_or_title_match_in_local_forrt_tables" or hits:
        r["combined_classification"]="later_paper_recorded_pair_unconfirmed"
    else:
        r["combined_classification"]="no_exact_doi_or_title_match"
    raw=next((x["outcome"] for x in hits if x["source"]=="extractor" and x["same_original"] and x["outcome"] in VALID),None)
    r["forrt_extractor_outcome_latest"]=raw or (r.get("forrt_extractor_outcome") if r.get("forrt_extractor_outcome") in VALID else None)
counts=Counter(r["classification"] for r in records)
combined=Counter(r["combined_classification"] for r in records)
s=old["summary"]
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
s.update({
    "audited_at_utc":now,
    "live_checked_at_utc":now,
    "retested_new_to_built_site":len(records),
    "classifications":dict(counts),
    "same_pair_raw":counts["same_pair_exact_dois"]+counts["same_pair_title_alternate_doi"],
    "later_paper_present_but_same_pair_unconfirmed":counts["later_paper_doi_only"]+counts["later_paper_title_alternate_doi_only"],
    "later_paper_no_exact_doi_or_title_match":counts["no_exact_doi_or_title_match_in_local_forrt_tables"],
    "extractor_same_pair_with_outcome":sum(bool(r.get("forrt_extractor_outcome")) for r in records),
    "extractor_outcome_differs_from_retested":sum(bool(r.get("forrt_extractor_outcome") and r["forrt_extractor_outcome"]!=r["retested_outcome"]) for r in records),
    "combined_local_and_live_classifications":dict(combined),
    "live_new_matches_not_in_local_snapshot":sum(bool(r["classification"]=="no_exact_doi_or_title_match_in_local_forrt_tables" and r["live_match"]) for r in records),
    "same_pair_with_extractor_outcome_local_or_live":sum(bool(r["combined_classification"]=="same_pair_recorded" and r["forrt_extractor_outcome_latest"]) for r in records),
    "extractor_outcome_differs_from_retested_local_or_live":sum(bool(r["forrt_extractor_outcome_latest"] and r["forrt_extractor_outcome_latest"]!=r["retested_outcome"]) for r in records),
})
assert len(records)==len(pairs)==json.loads(Path("data/build/stats.json").read_text())["counts"]["retested_new_pairs"]
AUDIT.write_text(json.dumps({"summary":s,"records":records},ensure_ascii=False,indent=2)+"\n")
print("NEW_RECORDS",len(new))
print("NEW_COMBINED",dict(Counter(r["combined_classification"] for r in records if (r["doi_o"],r["doi_r"]) in new)))
print("SUMMARY",json.dumps({k:s[k] for k in ("retested_new_to_built_site","combined_local_and_live_classifications","same_pair_with_extractor_outcome_local_or_live","extractor_outcome_differs_from_retested_local_or_live")}))

