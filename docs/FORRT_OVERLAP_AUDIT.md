# FORRT overlap audit — 2026-09-26

This audit corrects the meaning of “new” in Retested's progress counts. The build's `retested_new_pairs` metric counts pairs with only a `retested` source in the **built site**. It does **not** prove the pair, paper, or outcome is absent from all FORRT data. Likewise, `retested_new_effects` counts effects new to the built site, not first discoveries anywhere.

At the 2026-09-26 00:59:58 UTC build, 1,736 distinct pairs carried Retested review. Of those, 451 already overlapped the built FORRT layer and 1,285 were new to the built layer. A separate comparison of those 1,285 against all local FORRT CSV/XLSX replication-identifier columns found 309 later-paper DOI matches somewhere in FORRT raw files. A row-level scan found 243 exact original-plus-later DOI pairs. An additional exact normalized-title scan found seven later papers represented under different DOI versions, four of which also named the same original DOI. Thus at least 247 pairs have strong same-original and same-later-paper evidence in the broader raw corpus. These categories overlap; do not add them together.

At least 210 of the 243 exact-DOI pairs are in `feeds/flora-extractor_extracted.csv` with a nonempty FORRT outcome already recorded. Their outcomes were 112 successful, 62 failed, 31 mixed, four cannot-be-determined, and one uninformative. FORRT already held the core original/paper/result relationship for these 210. Retested source checking and page completion are additional work, not first discovery of those pairs.

The remainder cannot be declared absent from **all** FORRT material. Alternate identifiers, changed titles, unindexed files, and upstream changes after the local snapshot may still match. A “no match” in this audit means no match in the scanned local tables by exact normalized DOI or title, not proof of worldwide novelty. Before describing an individual pair as newly discovered, check the original DOI, later DOI, title/version, and FORRT raw outcome. Preserve valid FORRT overlaps as source-checked promotions and label them accordingly.

Sources: local `data/raw/forrt` snapshot and its `MANIFEST.json` (retrieved 2026-09-07), `data/build/attempts.json`, `/tmp/retested_forrt_overlap_audit.json`, and `/tmp/retested_forrt_title_matches.json`. FORRT upstream: https://github.com/forrtproject/FReD-data and https://github.com/forrtproject/flora-extractor. The `/tmp` match files are working audit artifacts, not committed source data.

## Completed-site checkpoint — 2026-09-26 01:19 UTC

The latest audited Retested build has **1,766 finished source-reviewed pairs**: 451 overlay pairs in the built FORRT layer, and 1,315 pairs new to Retested's built pages. The 1,315 break down as follows; these categories are mutually exclusive:

| Relation to the local FORRT raw snapshot | Pairs |
| --- | ---: |
| Same original and later paper already represented (267 exact DOI pairs, four matching titles under another DOI) | **271** |
| Later paper present, but the same original/later link not confirmed in the scanned row | **69** |
| No exact later DOI or title match in the scanned local tables | **975** |

FORRT's raw extractor already has an outcome for **234** of the 271 same-pair records. Retested's scoped outcome label differs in **29** of those 234; these are differences to inspect, not automatically FORRT errors. Among the 451 overlays on built FORRT pairs, 21 have a source-outcome disagreement flag. Retested's contribution is therefore 1,766 completed source-reviewed site pairs, including 1,044 pairs without a confirmed same-pair match in this local FORRT audit. **975** of those 1,044 also lack an exact later-paper DOI/title match. Neither number proves absence from every FORRT release or identifier variant.

The complete pair-by-pair classification and evidence row is saved in `data/curated/forrt_overlap_audit_20260926.json`. The snapshot covers local FORRT files retrieved on 2026-09-07. No changes have been sent to upstream FORRT, so Retested has not yet changed FORRT's own database.

## Current official FORRT files checked — 2026-09-26 01:27 UTC

The September 7 local snapshot missed records added to FORRT afterwards. We fetched the current official extractor, pending, validated, `flora.csv`, and `flora_filtered.csv` files and compared all 1,332 pairs again by exact normalized later DOI or title and original DOI. **Seventy-four** pairs that appeared absent from the local snapshot are present in those live files. This supersedes the local-only 279/69/984 split below for judging what FORRT already has.

| Relation to local history **or current official files** | Pairs |
| --- | ---: |
| Same original and later paper already recorded | **338** |
| Later paper recorded, same original–later link unconfirmed | **84** |
| No exact later DOI/title match in checked sources | **910** |

The last two groups total **994 candidate new pair links**. Of these, 910 appear to add a later paper absent by exact DOI/title from the checked files; 84 may add a new original-to-paper link. This is **not** a proof of absence from every FORRT source or identifier variant. FORRT's local or live raw extractor already has an outcome for **293** of the 338 same-pair records; Retested's scoped outcome label differs for **54**. Those differences require examination before calling either label wrong. The pair-by-pair JSON includes local and live evidence, file/row, matching basis, and outcome.

Live source files were fetched directly from the official FORRT GitHub repositories listed in the JSON audit. FORRT's public Replication Atlas is a search layer over FLoRA and itself warns that coverage is incomplete. No Retested changes have been contributed upstream to FORRT.

## Updated completed-site checkpoint — 2026-09-26 01:22 UTC

Seventeen further source-checked pairs passed the complete build and audit, giving **1,783 finished Retested-reviewed pairs**: 451 built FORRT overlays and **1,332 additions to Retested's built pages**. The updated pair-by-pair file classifies those 1,332 as **279 same-pair raw FORRT overlaps**, **69 later papers in FORRT with no confirmed same-pair link**, and **984 later papers with no exact DOI/title match in the scanned local tables**. The latter two categories total **1,053 candidate new pair links**, not proven first discoveries. The raw extractor already holds an outcome for 242 of the 279 same-pair overlaps; 33 scoped Retested outcome labels differ from the extractor label. The 17 newest pairs included eight raw extractor overlaps and nine without an exact DOI/title match.
