# U6 — Landscape of replication trackers, wikis and tools

Status: COMPLETE (research pass 2026-09-07). Written by a research subagent for other agents; all facts come from pages fetched/searched today or from the local BRIEF/data_sources files. Where a site could not be reached today, that is stated. Nothing is invented; "n/a" means not found.

Related local file: `C:\Users\OMISTAJA\PsychologyReplication\data_sources_analysis.md` (47 data sources, older notes; still valid for OSF URLs of ML1-5, RRRs, SSRP, LOOPR, XPhi, Data Replicada, ManyBabies, Many Smiles, I4R).

---

## 1. Tool-by-tool inventory

Legend: STATUS = alive / stalled / dead as observed 2026-09-07. OPENNESS = can we bulk-download and reuse?

### 1.1 FORRT Replication Hub (FReD, FLoRA, Explorer, Annotator, Atlas, Zotero checker) — the incumbent
- URLs: hub https://forrt.org/replication-hub/ ; FLoRA https://forrt.org/replication-hub/flora/ ; FLoRA submit https://forrt.org/replication-hub/submit/ ; FLoRA Explorer https://forrt.org/flora-explorer/ ; FLoRA Annotator https://forrt.org/annotator ; FReD Explorer https://forrt.org/explorer/ (Shiny at https://forrt-replications.shinyapps.io/fred_explorer/) ; FReD R package http://forrt.org/FReD/ + https://github.com/forrtproject/FReD ; Replication Atlas https://forrt.org/flora-replication-atlas/ (per-DOI pages like https://forrt.org/flora-replication-atlas/doi/10.2307/3333827/) ; Zotero Replication Checker https://forrt.org/flora-zotero/ + https://github.com/forrtproject/flora-zotero (Zenodo record 18671300) ; OSF data https://osf.io/9r62x ; large-scale project list https://forrt.org/replication-hub/large-scale-replication-projects/ ; also ReplicateThis nomination portal (/replicatethis, demo), Journal Replicability Tracker (/journalranking), R2 journal (replicationresearch.org), Replication Handbook.
- What it offers: FReD = effect-level rows with statistics (es_original, es_replication, N, p, closeness, preregistration, power, 7 success criteria in R package). FLoRA = paper-pair level, no statistics, any field (2,815 rows today: 2,526 replications + 289 reproductions; outcome successful/failed/mixed with outcome_quote). Explorer = Shiny filters + replicability/effect-size plots. Annotator = paste a reference list, get replication findings back (teaching use). Atlas = static per-DOI pages: metadata, APA/BibTeX, list of attempts, the quoted passage the outcome label was read from, OA + PubPeer links; claims "4,700+ original findings paired with replication outcomes". Zotero plugin = local DOI hash-prefix match against FLoRA; adds tags Successful/Failed/Mixed, "Has Replication"/"Is Replication" and child notes.
- Data openness: fully open. CC-BY 4.0 (JOPD paper; OSF 9r62x); R package MIT; CSV/XLSX; hub page itself CC BY-NC-SA. Snapshot in JOPD paper (Oct 2023): 1,239 entries, 336 original studies, 468 replication findings; outcomes success 447 / informative failure 641 / inconclusive 15 / practical failure 3 / n.a. 133. Sources aggregated: OSC 2015 (167 ES), Many Labs 1+3 (497), RRRs (120), CORE (109), OSF Registries (95), individual submissions (247), CurateScience (recoded from web archive Jan 2022), journal special issues. Merged with Replications & Reversals late 2024. (Paper: Röseler et al. 2025, J Open Psych Data, doi 10.5334/jopd.101; https://openpsychologydata.metajnl.com/articles/10.5334/jopd.101)
- Status: alive and accelerating. FORRT newsletters Feb/Apr 2026 (https://forrt.org/post/2026-02-newsletter/, https://forrt.org/post/2026-04-newsletter/): new ARIADNE, FReD Explorer app, FLoRA Annotator; FReD >1,000 findings, FLoRA >2,000 study pairs, call for validators, Replication Hub Showcase 1 July 2026, SIPS 2026 hackathon.
- Users like: authoritative, open, R-native, Zotero integration, teaching-oriented Annotator.
- Users dislike / authors' own stated limitations (JOPD paper): outcome coding inconsistent between batch imports and individual submissions; closeness metrics "difficult to measure, hard to validate"; power estimates skewed for within-subject designs; limited QC because crowdsourced; hypotheses/variables collapsed into free-text description; no standardized effect names (hence the owner's 17 failed taxonomy attempts). Shiny apps are slow to load (Explorer showed only "Please Wait" spinner when fetched today) and are paper/row-centric; Atlas has no download/API and no narrative; no game, no forecasts, no history of an effect over time.
- What it lacks (opportunity for us): effect/finding-level identity that persists across papers; human-readable synthesis ("what do we now believe about X and why"); time-lines; citation-context evidence; retraction overlay; forecast/guessing layer; per-effect confidence scores; a discovery pipeline that is visible to users; links to textbooks and Wikipedia.

### 1.2 ReplicationWiki (economics/social science)
- URL: https://replication.uni-goettingen.de/wiki/index.php/Main_Page (MediaWiki). Main page and Current events returned HTTP 500 today; ZBW/AEA still list it. Google-index pages exist (In the literature, In the news, Category:Replication).
- Offers: MediaWiki database of empirical studies categorised by JEL code, method, data type, software, geography, keywords, authors; tracks data/code availability, replication type and result (obtained / partially / not), corrections, retractions; forum, working-paper series, "vote for studies needing replication". Counts: 2,600+ studies & 339 replications (D-Lib Mar 2017, https://www.dlib.org/dlib/march17/hoeffler/03hoeffler.html); 4,484 studies, 652 replications, 231 journals, 23 corrections, 14 retractions, 6.6M page views (RePEc blog Aug 2020, https://blog.repec.org/2020/08/04/a-replication-database-for-economics-and-social-sciences-the-replicationwiki/). Founder Jan H. Höffler; funded by INET; RePEc bidirectional links boosted traffic.
- Openness: wiki pages are readable; Semantic MediaWiki-style category queries; no documented bulk export/API found.
- Status: stalled/fragile (server errors today; latest dated content found = webinar series to Mar 2023).
- Lessons (from D-Lib paper): "contributions from outside of our team have been very limited"; voting feature "not widely used"; RePEc integration was the single biggest traffic driver. => Community wikis do not self-populate; integrations into where researchers already are (RePEc, Zotero, Google Scholar) matter more than an edit button.

### 1.3 Curate Science
- URL: https://curatescience.org/ ; old app https://curatescience.org/app/replications ; code https://github.com/ScienceCommons/curate_science ; launch post https://replicationnetwork.com/2015/10/21/lebel-introducing-curatescience-org/
- Offered (2015-2019): crowd-curated replication tracker with meta-analytic forest plots per effect, transparency labels, "Replication Tracker" alpha, transparency audits leaderboard.
- Today: homepage is a proposal site: Replication Tracker "alpha version" linking to archived beta code; "currently seeking new funding" (latest date Dec 2022; funding proposal PDF v1.9.8 Nov 2021); solely led by Etienne LeBel; earlier EU Horizon 2020 MSCA grant. Its replication data survives only as a web-archive snapshot (Jan 2022) recoded into FReD.
- Status: zombie. Lesson: single founder + grant dependence + scope creep (tracker + author pages + transparency audits + business model) => stall. Its good idea (effect-level forest plots + transparency labels) is worth resurrecting.

### 1.4 PsychFileDrawer.org
- URLs: http://psychfiledrawer.org/ (DNS timeout today; www. also timed out) ; blog http://www.psychfiledrawer.org/blog/ ; attempt pages like https://www.psychfiledrawer.org/replication.php?attempt=MTU%3D still in search indexes.
- Offered (2012-~2020): brief self-reports of replication attempts (esp. unpublished), "Top-20 studies people most want replicated" vote list, per-attempt pages with original vs. replication details, discussion forum. Founders Pashler, Spellman, Holcombe, Kang. Domain registration expiry noted 2020-09-26 by index sites.
- Status: dead (unreachable). Openness: never had bulk export; content only in Wayback. Lesson: the "file drawer" use-case (unpublished null replications) is still unserved; and "most wanted replications" voting is a good idea that both PsychFileDrawer and ReplicationWiki tried and failed to sustain without integration.

### 1.5 OpenMKT replication tracker (marketing)
- URLs: https://openmkt.org/research/replications-of-marketing-studies/ ; full dataset https://openmkt.org/blog/frm_display/replications-full/ ; context post https://openmkt.org/blog/2022/replications-in-marketing-myth-and-reality/
- Offers: table of high-powered preregistered direct replications: original citation, replication citation, success, year made public, original journal, per-entry notes. 45 replications, 5 successes (~11%); success = significant in same direction and free of obvious confounds. Latest entry 2024 (Lohre et al.). Also notes only one true replication ever published in a marketing journal.
- Openness: viewable/downloadable table (no license stated). Status: alive but tiny, single-curator. Value to us: one of the few sources with explicit, documented success criteria and notes on ambiguity; feed for FLoRA gaps in marketing/consumer psych.

### 1.6 Replicability-Index (Ulrich Schimmack)
- URLs: https://replicationindex.com/ ; about https://replicationindex.com/about/ ; Z-curve 2.0 https://replicationindex.com/2020/01/10/z-curve-2-0/ ; textbook audit series https://replicationindex.com/2018/12/15/can-students-trust-social-psychology-textbooks/, https://replicationindex.com/2018/12/21/social-psychology-textbooks/, https://replicationindex.com/2018/12/28/socpsytb-ego-depletion/, https://replicationindex.com/2019/04/07/social-psychology-textbook-audit-something-smells-fishy/ ; decade review https://replicationindex.com/2020/01/05/replication-crisis-review/
- Offers: blog since 2014; statistical tools (Incredibility Test 2012, TIVA 2014, z-curve 1.0/2.0/3.0 -> expected replication rate ERR and expected discovery rate EDR); annual replicability rankings of ~120 psychology journals; "personalized p-values"/z-curves for individual eminent researchers; critical audits of Bem, Kahneman's book, Bargh, ego depletion; textbook audits.
- Openness: blog posts + R code (zcurve package on CRAN); rankings as blog tables, not a dataset API. Status: alive (one-person). Users like: brutal quantitative honesty, ERR per journal/author. Dislike: polemical tone, single author, hard to navigate, no structured data.
- Idea to borrow: show a z-curve/ERR estimate for the literature around an effect as a "prior" before revealing replication outcome in the game; per-journal expected replication rates as base rates.

### 1.7 DARPA SCORE, Replication Markets, repliCATS
- URLs: https://www.cos.io/score ; OSF data https://osf.io/dtzx4/overview ; SCORE registry https://osf.io/registries/score ; Replication Markets https://replicationmarkets.com/ (HTTP 522 today) / https://replicationmarkets.org/ (empty shell) ; about https://replicationmarkets.com/index.php/about/ ; repliCATS PLOS ONE https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0274429 ; field-forecast paper https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7428244/ ; press https://phys.org/news/2026-03-replicate.html, https://www.science.org/content/article/across-social-sciences-half-research-doesn-t-replicate, https://www.cos.io/about/news/large-scale-collaboration-releases-new-findings-on-research-credibility ; participant memoir https://fantasticanachronism.com/2021/11/18/how-i-made-10k-predicting-which-papers-will-replicate/ ; Adam Green https://www.adamlgreen.com/replication-markets/
- What happened: 2019-2026; 3,900 claims evaluated, 865 collaborators; Replication Markets ran 10 rounds over 3,000 claims from 62 journals (psych, econ, education, management/marketing, poli sci, sociology/criminology); Nov 2021: 121 resolutions (79 regular + 30 COVID + 12 meta-claims), $142,623 prizes to 258 winners. repliCATS used IDEA protocol (Investigate-Discuss-Estimate-Aggregate) on 3,000 claims (validation: 84% accuracy, AUC 0.94 on 25 prior claims).
- Final results (Nature collection 2026: Tyner et al. replications doi 10.1038/s41586-025-10078-y; Aczel et al. robustness doi 10.1038/s41586-025-09844-9; Miske et al. reproducibility doi 10.1038/s41586-026-10203-5): replication 49% of 164 papers (significant, same direction); median effect-size shrinkage >50%, explained variance -80%; reproducibility 54% precise / 74% approximate of 143 papers; only 24% of 600 assessed papers had data available; with data+code shared 91% approx / 77% precise vs 38%/11% when data reconstructed; robustness (100 papers): 34% within +/-0.05 d, 74% same conclusion, 2% opposite. Predictors: repliCATS 76% and Replication Markets 78% accuracy on best metric; three ML approaches "none consistently effective"; the three repeatability measures only modestly correlate with each other and with expert predictions ("credibility is multidimensional"). Community expectation before results (PMC7428244): econ 58% vs psychology & education 42%.
- Openness: SCORE data/code on OSF (dtzx4); Replication Markets per-claim forecasts partly embargoed at the time (per memoir), check OSF now. Status: program finished; RM site effectively dead.
- Participant critique of RM design (useful for our game): flat points, no compounding across rounds, no feedback until the end, poor UI, only ~107 of ~250 targeted replications completed (survivorship bias). Market mean 54% matched the realized 54% in that subset.

### 1.8 Forecasting literature: what accuracy did humans/markets reach (verified numbers)
| Study | Sample | Forecaster | Accuracy | Notes |
|---|---|---|---|---|
| Dreber et al. 2015 PNAS (https://www.pnas.org/doi/10.1073/pnas.1516179112) | 41-44 RPP studies | PhD social scientists, markets + survey | 71% (markets); survey 58% per Hoogeveen summary | first demonstration |
| Camerer et al. 2016 Science (https://www.science.org/doi/10.1126/science.aaf0918) | 18 econ lab experiments | markets | ~majority correct; 11/18 replicated (61%) | econ replicates better |
| Forsell et al. 2019 J Econ Psych (https://www.sciencedirect.com/science/article/pii/S0167487018303283) | 24 ML2 effects | markets/survey | 67% (per Hoogeveen 2020 summary) | ML2 replication 50% |
| Camerer et al. 2018 NHB (SSRP) | 21 Nature/Science studies | markets | 86%; 13/21 (62%) replicated | market beliefs correlate with outcome |
| Gordon et al. 2021 PLOS ONE (https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0248780) | pooled 103 findings, >15,000 forecasts | markets vs surveys | markets 73% (75/103), surveys 66% (68/103), n.s.; r(market price, outcome)=0.58 | base rate 49% but forecasts 61-63% => optimism bias 12-14 pts; p<=0.005 originals replicated 74% vs 28% for p>0.005; 90% of error reduction in first 69 trades |
| Altmejd et al. 2019 PLOS ONE (https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0225826) | 4 projects, 131 studies | random forest | 70% CV (AUC .77); 71% preregistered OOS (AUC .73); Spearman .38 for effect sizes | features below |
| Hoogeveen, Sarafoglou & Wagenmakers 2020 AMPPS (https://journals.sagepub.com/doi/full/10.1177/2515245920919667; OSF https://osf.io/wg9s3) | 27 SSRP+ML2 findings, 233 laypeople (123 description-only, 110 description+Bayes factor) | laypeople | 59% description-only; 67% with BF evidence strength | binary + confidence; "bogus item" attention check; predictions correlated with replication effect size |
| repliCATS (PLOS ONE 2022) | 25 validation claims; 3,000 SCORE claims | structured expert groups | 84%, AUC .94 (validation); 76% on SCORE (COS 2026) | beginners 69% vs experienced 61% on COVID preprints (PubMed 39706868) |
| Replication Markets (SCORE) | ~107-121 resolved | crowd market | ~75-78% | see 1.7 |
| Youyou, Yang & Uzzi 2023 PNAS (https://www.pnas.org/doi/10.1073/pnas.2208863120) | text model trained on 388 replicated studies, applied to 14,000+ papers | ML on paper text | reported good in-sample; heavily critiqued (https://www.pnas.org/doi/full/10.1073/pnas.2307596120, https://www.pnas.org/doi/10.1073/pnas.2309496120): learns subfield language style | do not use as ground truth |
| Human-AI hybrid markets 2026 (https://arxiv.org/abs/2605.27394; earlier https://arxiv.org/pdf/2211.16590, https://arxiv.org/pdf/2303.00866) | hundreds of prior outcomes | LLM agents + humans trading | "match or outperform artificial prediction markets" (no numbers in abstract) | humans add contextual credibility cues |
| Transparent Replications (Clearer Thinking) | first 12 recent top-journal papers | psychologists' forecast 55% | realized 83% replicated | recent, preregistered-era papers replicate far better; "importance hacking" more common than p-hacking |

Cues that predict replication (with sources):
- Original p-value / z: strongest single cue. p<=0.005 -> 74% vs p>0.005 -> 28% (Gordon 2021). Altmejd: top 3 features are post-hoc power, p-value, effect size (interrelated).
- Original effect size and sample size (Altmejd 2019; also RPP: larger original ES and smaller p predicted success).
- Main effect vs interaction: interactions replicated 8/41 (20%) vs main effects 48/90 (53%) (Altmejd 2019).
- Surprisingness / prior plausibility: laypeople's plausibility intuitions alone give 59% (Hoogeveen 2020); "nonsurprising studies more replicable" and media attention negatively correlated with replication (r = -0.21 training, -0.13 prediction; Altmejd/Wikipedia Bayesian section); Bayesian argument: replication probability rises with power and prior probability of H1 (Wikipedia "Bayesian explanation").
- Field/subfield: cognitive 50% vs social 25% in RPP; econ lab 61%; RPP by journal JPSP 23%, JEP:LMC 48%, Psych Science 38% (Wikipedia "In psychology"). Altmejd: discipline dummy NOT predictive once stats are in. SCORE: no field consistently higher across all three measures; econ/poli sci more reproducible because data is available.
- Context sensitivity: higher rated context-sensitivity -> lower replication even controlling for ES/N/power (Van Bavel et al., cited in Wikipedia "Context sensitivity").
- Preregistration ("huge plus"), design type (RCT/RD/DiD > lab > observational), multiple outcomes / binned continuous variables / ad-hoc choices as red flags (Fantastic Anachronism heuristics). Longer papers, more authors, no participant compensation -> lower replication (Altmejd). Language/location/subject-pool differences NOT predictive (Altmejd; ML2).
- Era: post-2015 preregistered-era papers replicate ~83% in Transparent Replications' sample vs ~36-50% for 2008-2015 samples.
- Forecasters are over-optimistic by 12-14 points; markets converge in ~69 trades; feedback and compounding incentives matter (Gordon 2021; Fantastic Anachronism).

### 1.9 Wikipedia "Replication crisis"
- URL: https://en.wikipedia.org/wiki/Replication_crisis (wikitext 205,844 chars fetched via API today).
- Named psychology effects/studies mentioned: social priming (Bargh elderly-walking 1996; two direct replications failed), ego depletion (failed), Bem precognition/ESP (failed), power posing (non-replication under-reported by media), subliminal perception and dissonance reduction (historical precedents), brain-wide association studies (invalid at small N). Headline numbers: RPP 36% of 97 (ES halved; 25% contradicted, 49% inconclusive; JPSP 23%, JEP:LMC 48%, PS 38%; cognitive 50% vs social 25%; replication samples ~40% of original size... [as written in article]); SSRP 62% of 21; ML2 50% of 28 (failures fail everywhere -> context not the driver). Sections "Metadata and digital tools for tracking replications" and "Replication database" explicitly call for "a simple way to check how often studies have been repeated" — i.e., for what we are building; the article itself has NO comprehensive effect list. The effect list lives in scattered articles (Ego depletion, Power posing, Priming, Stereotype threat, Marshmallow test, Facial feedback, Implicit-association test, Growth mindset, Stanford prison experiment, Milgram) — each with a "Replication" section of varying quality.
- Opportunity: our wiki can be the canonical, structured "list of effects and their replication status" that Wikipedia lacks, and can feed Wikidata (property for "replicated by" does not exist; could propose).

### 1.10 Textbook audits
- Ferguson & Brown 2025, "Have introductory psychology textbooks gotten better at representing psychological science?", J Gen Psych 153(2):272-285, doi 10.1080/00221309.2025.2587151 (https://www.tandfonline.com/doi/full/10.1080/00221309.2025.2587151; PDF https://www.christopherjferguson.com/2025%20Study.pdf; press https://www.psypost.org/psychology-textbooks-still-misrepresent-famous-experiments-and-controversial-debates/): 16 textbooks (2018) vs 18 (2023); errors remain common; errors bias toward making findings look more consistent; SPE and Milgram misrepresented. Earlier: Ferguson, Brown & Torres 2018 (Current Psychology) and Ferguson 2016.
- Schimmack textbook audit series (see 1.6): Gilovich et al. Social Psychology 5th ed. omits social-psych 25% RPP rate and 4% for classic between-subject designs while citing 75-85% from econ/small samples.
- "Strategies for Teaching Critical Thinking about Replication Based on A Study of Introductory Psychology Textbooks", J Sci Exploration (https://journalofscientificexploration.org/index.php/jse/article/view/3485); APA Teaching of Psychology supplement listing 10 reviewed textbooks (https://supp.apa.org/psycarticles/supplemental/stl0000439/stl0000439_SupplementalMaterialA.pdf).
- Gap: no public, structured, per-effect "which textbooks still teach this" table exists. That is a cheap, high-impact differentiator (OpenStax Psychology 2e and Noba are open-licensed and machine-readable: https://open.umn.edu/opentextbooks/textbooks/207, https://nobaproject.com/).

### 1.11 Many Labs, RRRs, PSA, ManyBabies, Transparent Replications, I4R (project hubs)
- Many Labs 1 (osf.io/wx7ck; Klein et al. 2014): 13 effects, 36 samples, >6,000 pp; 10 replicated, imagined contact weak, flag priming and currency priming failed. ML2 (Klein et al. 2018 AMPPS): 28 findings, 50% replicated. ML3 (https://osf.io/ct89g/wiki/home/): time-of-semester, 10 effects, mostly failed. ML4 (local ml4_full_data.csv): mortality salience null. ML5: 10 RPP failures with expert protocols, little improvement. FORRT lists ML1-5 at osf.io/wx7ck .. osf.io/7a6rd.
- APS Registered Replication Reports (https://www.psychologicalscience.org/publications/ampps/rrr-guidelines; intro https://journals.sagepub.com/doi/full/10.1177/1745691614543974): verbal overshadowing (31 labs, small effect), facial feedback (null), ego depletion, etc.; FReD has 120 RRR effect sizes. No single machine-readable RRR list; data per RRR on OSF.
- Psychological Science Accelerator (https://psysciacc.org/projects.html): 15 projects; replications PSA001 face perception (11,570 pp / 41 countries: generalizes under original analysis), PSA002 object orientation (no effect), PSA004 Gettier (1.86x), PSA006 trolley (personal force universal), PSA008 minimal groups & PSA-JTF1 in progress; data on OSF/GitHub per project. Alive.
- ManyBabies (https://manybabies.org; local manybabies_mb1_data.csv), Many Smiles (facial feedback adversarial), CORE (osf.io/5z4a8), Soto 2019 personality (LOOPR), Data Replicada (https://datacolada.org/archives/category/replication), XPhi replicability project — see data_sources_analysis.md.
- Transparent Replications (Clearer Thinking) https://replications.clearerthinking.org/ (+ /replications/, /faq/, Metaculus project https://www.metaculus.com/project/1774/ — 403 today; EA forum post https://forum.effectivealtruism.org/posts/qdKsYriypQskMQFLN/...): replicates a study from every new psychology paper in Nature/Science (+ PNAS, JPSP, Psych Science random); 14 reports by 24 Mar 2026; 3 star-ratings (transparency, replicability, clarity, 0-5); first 12: 83% replicated vs 55% forecast; materials on ResearchBox. Alive. The only live "forecast then replicate" loop in psychology right now.
- Institute for Replication (https://www.i4replication.org/, reports https://i4replication.org/reports/): econ/poli-sci; 110 papers reproduced/replicated by 15 Jun 2026; 232+ discussion papers; Meta Database of robustness checks (two periodically updated datasets). Alive; not psychology but a model for structured robustness data.
- Sports Science Replication Centre (https://ssreplicationcentre.com), ReproSci (biology), RP:Cancer Biology — outside scope, listed on FORRT page.

### 1.12 PCI Registered Reports
- URL: https://rr.peercommunityin.org/ (blocked by Anubis anti-bot today); overview https://peercommunityin.org/, FORRT glossary https://forrt.org/glossary/english/pci_registered_reports/, Wikipedia https://en.wikipedia.org/wiki/Peer_Community_in.
- Offers: free two-stage RR review (launched 2021), 100+ PCI-RR-friendly journals accept recommended RRs without further review; PCI overall ~1,051 recommended preprints (Mar 2026), 21 thematic PCIs. Openness: recommendations are public pages with RSS; no replication flag in metadata.
- Value: Stage-1 in-principle-accepted replications are a "coming soon" feed for our pipeline (scrape PCI RR recommendations + OSF Registries "Registered Report" type + PROSPERO-like lists).

### 1.13 Existing "guess if it replicated" quizzes/games
- 80,000 Hours "Psychology Replication Quiz" https://80000hours.org/psychology-replication-quiz/ (discussed https://www.lesswrong.com/posts/KsyD6GmFN2EtirX74/psychology-replication-quiz, https://statmodeling.stat.columbia.edu/2018/09/02/hey-take-psychological-science-replication-quiz/): 10/15/21 items = the 21 SSRP Nature/Science studies; short description + method details; binary yes/no + "don't know"; feedback compares to expert psychologists; commenters scored ~71-93%; wished for probabilistic answers; "don't know" underused.
- ClearerThinking 2018 quiz https://www.clearerthinking.org/post/2018/10/05/can-you-guess-which-of-these-high-profile-psychology-experiments-were-legit : same 21 SSRP items; report compares you to social scientists, prediction-market odds and general population; includes "crash course" on evaluating methods.
- Justin Domke "The replication game" https://justindomke.wordpress.com/2021/10/04/the-replication-game/ : 13 effects from the 2014 Social Psychology registered-replication special issue, 0-4 scale, categories textbook / conflicted / hot; only 1 fully replicated, mean 0.8/4, all "hot" effects failed; notes selection bias.
- Jonatan Pallesen "Guess along..." (Medium, 403 today); BPS Digest coverage of Hoogeveen (https://www.bps.org.uk/research-digest/want-know-whether-psychology-study-will-replicate-just-ask-bunch-people); Hoogeveen 2020 itself is a game-shaped study (description -> yes/no + confidence -> reveal).
- Metaculus Transparent Replications tournament (live forecasting on new studies).
- No hits for "Replication Roulette". Nothing found that is: continuously updated from a database, effect-centric, with calibration scoring, leaderboards, spaced repetition, or that feeds forecasts back as data. Every quiz is a frozen 21-item SSRP set from 2018.

### 1.14 Retraction Watch database
- URLs: https://www.crossref.org/documentation/retrieve-metadata/retraction-watch/ ; CSV git https://gitlab.com/crossref/retraction-watch-data ; API https://api.crossref.org/works/{doi} (`update-to` / `updated-by`, `source` = publisher|retraction-watch) and https://api.crossref.org/v1/works?filter=update-type:retraction ; labs page (deprecated) https://www.crossref.org/labs/retraction-watch/ ; background https://www.crossref.org/blog/news-crossref-and-retraction-watch, https://blogs.lse.ac.uk/impactofsocialsciences/2023/09/27/...
- Offers: ~43k RW + 14k Crossref-only = ~50k retractions; 20 CSV columns (Record ID, Title, Subject, Institution, Journal, Publisher, Country, Author, URLs, ArticleType, RetractionDate, RetractionDOI, RetractionPubMedID, OriginalPaperDate, OriginalPaperDOI, OriginalPaperPubMedID, RetractionNature, Reason, Paywalled, Notes); updated every working day; CC-BY 4.0. Alive, fully open. Trivial to join on OriginalPaperDOI to doi_o/doi_r.

### 1.15 Scite.ai
- URLs: https://scite.ai/ ; per-DOI report pattern https://scite.ai/reports/{doi} (403 to bots today). Offers 1.2B citation statements from 180M+ papers classified supporting / contrasting / mentioning; ~USD 20/month individual; API by application only (sales@scite.ai). Status alive, closed data. Use: outbound link per DOI only; do not depend on it.

### 1.16 Semantic Scholar citation intents
- URLs: https://www.semanticscholar.org/faq/citation-intent ; API https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}/citations?fields=intents,contexts,isInfluential,title,externalIds ; overview https://arxiv.org/html/2301.10140v2. Intents = background / method / result (SciCite, Cohan et al. 2019); only for papers with full text. Verified today: for 10.1126/science.aac4716 (RPP) 20 citations returned with `contexts` populated but `intents` empty in all; for Bargh 1996 DOI also empty. So intents coverage is sparse; but `contexts` (citation sentences) are returned and are free — a regex/LLM pass over contexts for "replicat", "failed to replicate", "did not replicate", "conceptual replication", "reproduced" is a viable open alternative to Scite. Rate limits: 1 rps unauthenticated; free API key available. Alive, open.

### 1.17 Other adjacent things worth knowing
- The Replication Network blog (https://replicationnetwork.com) — news aggregator, guest posts; no data.
- OpenAlex (used by FLoRA "openalex" source, 184 rows) — open; title/abstract search for "replication of" is how the owner's earlier harvester worked.
- FORRT "Replications and Reversals" list (local forrt_replications_reversals.csv) — merged into FReD late 2024.
- Atticus Li "Replication Crisis Hub" (https://atticusli.com/replication-crisis/) and cj-robinson data-story (https://cj-robinson.github.io/replication-crisis/) — popular explainers with famous-effects lists; useful for the "famous effects" narrative tone benchmark, not data.
- Bloomberg 2025-11-21 "Which Social Psychology Theories Survived the Replication Crisis?" (paywalled) — signals mainstream appetite for exactly a "what survived" list.

---

## 2. Comparative matrix (condensed)

| Tool | Level | Fields | Stats? | Open bulk data | API | Effect pages | Narrative | Game/forecast | Status |
|---|---|---|---|---|---|---|---|---|---|
| FReD | effect | psych+ | yes | CSV/XLSX CC-BY | R pkg, DOI-hash API | no (rows) | no | no | alive |
| FLoRA / Atlas | paper pair | any | no | CSV | hash API | per-DOI static | quote only | no | alive |
| ReplicationWiki | paper | econ/soc | partial | no | no | no | wiki text | vote list | stalled |
| Curate Science | effect | psych | yes (forest plots) | archived | no | yes (was) | labels | no | zombie |
| PsychFileDrawer | attempt | exp psych | self-report | no | no | per-attempt | forum | top-20 vote | dead |
| OpenMKT | paper pair | marketing | outcome only | table | no | no | notes | no | alive-small |
| R-Index | journal/author | psych | z-curve | blog | no | no | polemic | no | alive-solo |
| SCORE/RM/repliCATS | claim | soc sci | yes | OSF | no | no | no | markets (ended) | finished |
| Transparent Replications | study | recent top-journal | yes | ResearchBox | no | per-report | yes, ratings | Metaculus | alive |
| Retraction Watch | paper | all | n/a | CSV CC-BY | Crossref | n/a | n/a | n/a | alive |
| Scite | citation | all | n/a | closed | paid | no | n/a | n/a | alive |
| Semantic Scholar | citation | all | n/a | open | free | no | n/a | n/a | alive |
| Quizzes (80k/CT/Domke) | 21 studies | SSRP 2018 | shown | n/a | no | no | short blurbs | yes, frozen | frozen |

---

## 3. Ten differentiators that would make OUR wiki clearly distinct and better

1. Effect-centric identity with lineage. One stable page per finding/effect ("ego depletion", "elderly priming") aggregating every original, every replication, every RRR/Many Labs/PSA sample, retraction status, and a versioned verdict — nobody has this (FReD/FLoRA are row/paper-centric; Wikipedia is unstructured; Curate Science tried and died). Include the 362 hand-curated famous effects (docx_parsed_entries.json) as seed pages.
2. Evidence timeline + "what we believe now" synthesis. For each effect: original (year, N, p, d) -> each replication with N, outcome, closeness -> meta-analytic forest plot (the resurrected Curate Science idea, computed with FReD's 7 criteria from the R package) -> plain-language verdict with confidence and date. Show effect-size shrinkage (SCORE: median >50%), not just binary success.
3. The "Did it replicate?" game as a living, data-driven system: items generated from FReD/FLoRA every build, not a frozen 21-item SSRP list; two modes (description-only vs. description+evidence, mirroring Hoogeveen's 59% -> 67%); probabilistic answers + Brier/calibration scoring (the top user complaint about the 80k quiz); compare against base rates, prediction-market prices (Dreber/Camerer/Gordon data are on OSF), laypeople (Hoogeveen), and repliCATS; leaderboards; spaced-repetition "learn the cues" mode; player forecasts stored as a dataset for unreplicated effects (a citizen prediction market feeding differentiator 6).
4. Open, joinable, documented data with a real API. Reproducible one-command build; JSON/CSV/Parquet exports; per-effect JSON endpoints; DOI-hash lookup compatible with FORRT's Zotero API so their plugin could point at us; clear CC-BY provenance per row (source = FReD / FLoRA / our overlay / Retraction Watch / OpenAlex). ReplicationWiki and PsychFileDrawer died partly because their data could not leave the site.
5. Discovery pipeline in the open. Candidate-replication finder over OpenAlex + Crossref + Semantic Scholar citation contexts (regex/LLM on "replicat*" sentences of papers citing the original) + PCI RR / OSF Registries "coming soon" feed + Retraction Watch overlay; a public human-review queue with status; monthly diff; one-click "submit to FLoRA" export. Nobody shows users the pipeline or the queue.
6. Forecast layer for unreplicated effects. Every effect page carries a predicted replication probability from transparent cues (p-value bucket, N, interaction vs main, field base rate, era, preregistration; Altmejd/Gordon features) plus crowd forecasts from the game; displayed as a calibrated prior, and settled when a replication arrives (Transparent Replications/Metaculus loop, generalised).
7. Textbook/Wikipedia/media overlays. Per effect: which open textbooks (OpenStax, Noba) still teach it, whether Wikipedia's article has a replication section, media attention (a negative predictor) — turning the Ferguson & Brown and Schimmack audits into a structured, maintained table.
8. Multiple entry points and cross-cutting views: effect / paper / attempt / project (Many Labs 1-5, RRRs, PSA, SSRP, SCORE, Transparent Replications) / author / journal / topic / decade; journal-level and subfield-level replication rates with denominators (like R-Index rankings but from actual replications, with explicit selection caveats).
9. Honest uncertainty design. Show selection bias ("people replicate what they doubt" — Domke), context-sensitivity ratings, closeness-of-replication, mixed outcomes, and multiple success criteria side by side (significance, small telescopes, CI overlap) instead of one binary. Every verdict has a rationale and a "dispute this" link (PubPeer-style) and a changelog.
10. Sustainability by integration rather than community editing. Lessons from ReplicationWiki (outside contributions "very limited"), PsychFileDrawer (dead), Curate Science (grant-dependent): generate everything from upstream open data + small curated overlays in git, contribute back to FORRT, expose Zotero/RSS/JSON feeds and Wikidata-ready identifiers, so the site stays useful with zero editors.

---

## 4. Guessing-game design implications from the forecasting literature

Base rates to show/teach:
- Overall ~50% (SCORE 49%; Gordon pooled 49%; ML2 50%); RPP 36% (JPSP 23%, JEP:LMC 48%, Psych Sci 38%; cognitive 50% vs social 25%); SSRP 62%; econ lab 61%; ML1 85%; marketing preregistered direct replications 11% (OpenMKT); recent Nature/Science/PS papers 83% (Transparent Replications first 12); FLoRA snapshot: 1,036 successful / 890 failed / 557 mixed (BRIEF). Show the user the relevant base rate before they guess, then score against it.
- Forecasters (experts and markets) are over-optimistic by 12-14 points; a "calibration" feedback screen is more educational than a raw score.

Cues to expose progressively (each is a documented predictor):
1. Original p-value (best single cue: p<=.005 -> 74% vs 28%). Show as z or p bucket.
2. Original N and effect size; post-hoc power (Altmejd's top-3).
3. Main effect vs interaction (20% vs 53%).
4. Field/subfield and journal base rates (social vs cognitive; JPSP vs JEP:LMC).
5. Era and preregistration (pre-2015 vs preregistered era; RRR/Many Labs vs single-lab).
6. Surprisingness / prior plausibility (laypeople 59% from this alone); media attention negatively predicts.
7. Context sensitivity rating; design type (lab vs field vs observational); number of outcome measures; binned continuous variables.
8. Evidence strength as Bayes factor (raising lay accuracy from 59% to 67%).

Mechanics suggested by the evidence:
- Elicit probability (0-100) with a slider, score with Brier + log score; show calibration curve after 10+ items (users explicitly asked for this on the 80k quiz).
- Two difficulty modes: "description only" and "description + stats" (replicates Hoogeveen's design and lets us measure the cue value ourselves).
- Compare each guess to: market price (Dreber/Camerer/Forsell/Gordon data on OSF), lay average (Hoogeveen OSF wg9s3), model prediction (Altmejd features), and other players.
- Reveal effect-size shrinkage and closeness, not just yes/no; include "mixed" outcomes as a third answer with partial credit.
- Compounding/streak scoring rather than flat points; immediate feedback (both were the key RM design complaints).
- Item selection: stratify by outcome to keep base rate ~50% within a session (avoid "all hot effects fail" degeneracy noted by Domke), and by field; exclude items with ambiguous outcome coding.
- Store anonymised forecasts on effects that have not yet been replicated -> crowd prior (Transparent Replications/Metaculus loop).

---

## 5. Things to discard / not depend on
- Scite (closed, paid, API by application). Use Semantic Scholar `contexts` instead.
- Youyou/Yang/Uzzi text-ML replicability scores (learn style, contested) — never present as evidence.
- Curate Science and PsychFileDrawer as live sources (dead; their content already absorbed into FReD or lost to Wayback).
- Replication Markets website (down); use SCORE OSF (osf.io/dtzx4) instead.
- Owner's old 17 taxonomy iterations — the landscape confirms nobody has solved effect naming; solve it by adopting stable effect IDs + aliases seeded from the 362 docx entries and FReD "effect" strings, not by a grand taxonomy.
