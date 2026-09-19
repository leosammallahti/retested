import pandas as pd, numpy as np, re, json, sys, warnings
from scipy import stats
warnings.filterwarnings('ignore')
ROOT="C:/Users/OMISTAJA/PsychologyReplication/"
def P(*a):
    print(*a); sys.stdout.flush()
def norm_doi(s):
    if pd.isna(s): return np.nan
    s=str(s).strip().lower()
    s=re.sub(r'^(https?://)?(dx\.)?doi\.org/','',s); s=re.sub(r'^doi:\s*','',s)
    return s.strip().rstrip('.')

# ---------- legacy ----------
L=pd.read_excel(ROOT+"data/raw/forrt/osf/version-history/FReD_2.4.1_2025-06-25.xlsx", sheet_name='Data', skiprows=[1,2])
P("legacy",L.shape)
for c in ['es_original','es_replication','n_original','n_replication','power','ci.lower_original','ci.upper_original','ci.lower_replication','ci.upper_replication']:
    L[c]=pd.to_numeric(L[c],errors='coerce')
L['doi_o']=L.doi_original.map(norm_doi); L['doi_r']=L.doi_replication.map(norm_doi)
ok=L[['es_original','es_replication','n_original','n_replication']].notna().all(axis=1)&(L.n_original>3)&(L.n_replication>3)&(L.es_original.abs()<1)&(L.es_replication.abs()<1)
P("legacy rows with r+N both sides:",ok.sum(), " with effect name:",(ok&L.effect.notna()).sum())
# align
sg=np.sign(L.es_original); L['eo']=L.es_original.abs(); L['er']=L.es_replication*sg
# result normalisation
L['res']=L.result.astype(str).str.strip().str.lower().replace({'sucess':'success'})
P("legacy result:",L.res.value_counts().head(8).to_dict())
# by source project (success from result column)
def rate(g):
    g=g[g.isin(['success','informative failure to replicate','practical failure to replicate','inconclusive'])]
    n=len(g); return pd.Series({'n_coded':n,'success':round((g=='success').mean(),3) if n else np.nan})
bs=L.groupby('source').res.apply(rate).unstack().sort_values('n_coded',ascending=False); P(bs[bs.n_coded>=10].to_string())
# power distribution (legacy 'power' column = power of replication for original ES)
P("legacy power: n",L.power.notna().sum()," quantiles",L.power.quantile([.1,.25,.5,.75,.9]).round(3).to_dict()," share>=.8",round((L.power>=.8).mean()/ (L.power.notna().mean()),3))
pw=L[L.power.notna()&L.res.isin(['success','informative failure to replicate'])]
P("legacy success by power bin:", pw.groupby(pd.cut(pw.power,[-.01,.5,.8,.95,1.01])).res.apply(lambda s:(round((s=='success').mean(),3),len(s))).to_dict())
# closeness fingerprint
CL=[c for c in L.columns if c.startswith('closeness_')]
cl=L[CL].apply(pd.to_numeric,errors='coerce')
P("closeness rows with any:",cl.notna().any(axis=1).sum()," all 10:",cl.notna().all(axis=1).sum())
P("closeness value distributions:");
for c in CL: P("  ",c, cl[c].value_counts().sort_index().to_dict())
P("closeness by source:", L[cl.notna().any(axis=1)].source.value_counts().to_dict())
# does closeness relate to success? sum score (1=exact ... higher = further)
cs=cl.sum(axis=1,min_count=7); L['closeness_sum']=cs
x=L[L.closeness_sum.notna()&L.res.isin(['success','informative failure to replicate'])]
P("closeness_sum n",len(x)," success by tertile:", x.groupby(pd.qcut(x.closeness_sum,3,duplicates='drop')).res.apply(lambda s:(round((s=='success').mean(),3),len(s))).to_dict())
P("corr closeness_sum vs er/eo ratio:", round(x.assign(rt=x.er/x.eo).dropna(subset=['rt'])[['closeness_sum','rt']].corr().iloc[0,1],3))
# same_design/same_test/prereg/original_authors
for c in ['same_design','same_test','original_authors','published_rep']:
    v=L[c].astype(str).str.strip().str.lower().replace({'wahr':'1','falsch':'0','yes':'1','true':'1','false':'0'})
    y=L[v.isin(['0','1'])&L.res.isin(['success','informative failure to replicate'])]
    P(c, y.groupby(v[y.index]).res.apply(lambda s:(round((s=='success').mean(),3),len(s))).to_dict())
pr=L[L.res.isin(['success','informative failure to replicate'])]
P("preregistration present vs success:", pr.groupby(pr.preregistration.notna()).res.apply(lambda s:(round((s=='success').mean(),3),len(s))).to_dict())

# ---------- per-effect random-effects meta-analysis (legacy effect names) ----------
def re_meta(r,n):
    r=np.clip(np.asarray(r,float),-.9999,.9999); n=np.asarray(n,float)
    z=np.arctanh(r); v=1/(n-3); w=1/v
    k=len(z); zfe=(w*z).sum()/w.sum(); Q=(w*(z-zfe)**2).sum(); df=k-1
    C=w.sum()-(w**2).sum()/w.sum(); tau2=max(0,(Q-df)/C) if k>1 else 0
    wr=1/(v+tau2); zre=(wr*z).sum()/wr.sum(); se=np.sqrt(1/wr.sum())
    I2=max(0,(Q-df)/Q)*100 if Q>0 else 0
    Qp=stats.chi2.sf(Q,df) if df>0 else np.nan
    # prediction interval (Higgins) uses t with k-2 df
    if k>=3:
        tcrit=stats.t.ppf(.975,k-2); pil,piu=zre-tcrit*np.sqrt(tau2+se**2), zre+tcrit*np.sqrt(tau2+se**2)
    else: pil=piu=np.nan
    return dict(k=k,est=np.tanh(zre),lb=np.tanh(zre-1.96*se),ub=np.tanh(zre+1.96*se),tau=np.sqrt(tau2),I2=I2,Q=Q,Qp=Qp,pi_lo=np.tanh(pil),pi_hi=np.tanh(piu))
E=L[ok&L.effect.notna()].copy()
E['eff']=E.effect.astype(str).str.strip()
g=E.groupby('eff')
P("effects with r+N rows:",g.ngroups," with >=2 attempts:",(g.size()>=2).sum()," >=3:",(g.size()>=3).sum()," >=5:",(g.size()>=5).sum()," >=10:",(g.size()>=10).sum())
rows=[]
for eff,gg in g:
    if len(gg)<2: continue
    # replications only meta-analysis (originals excluded)
    m=re_meta(gg.er.values,gg.n_replication.values)
    m['eff']=eff; m['orig_r_median']=gg.eo.median(); m['n_sites']=len(gg); m['n_unique_doi_r']=gg.doi_r.nunique(); m['sources']=','.join(sorted(gg.source.dropna().astype(str).unique())[:4])
    rows.append(m)
M=pd.DataFrame(rows).sort_values('k',ascending=False)
P("\nTop 25 effects by k (RE meta of replications only, Fisher-z DL):")
P(M.head(25)[['eff','k','n_unique_doi_r','orig_r_median','est','lb','ub','tau','I2','pi_lo','pi_hi','sources']].round(3).to_string())
P("\nI2 distribution for effects with k>=5:", M[M.k>=5].I2.describe().round(1).to_dict())
P("share of effects (k>=3) whose RE CI excludes 0:", round((M[M.k>=3].lb>0).mean(),3), " n=",(M.k>=3).sum())
P("share (k>=3) where original median r is inside RE prediction interval:", round(((M.orig_r_median>=M.pi_lo)&(M.orig_r_median<=M.pi_hi))[M.k>=3].mean(),3))
P("share (k>=3) where RE est < half of original median:", round((M.est<0.5*M.orig_r_median)[M.k>=3].mean(),3))
M.to_csv(ROOT+"_planning/designs/_d2_effect_meta_legacy.csv",index=False)
# evidence status prototype
def status(m):
    if m.k<2: return 'single attempt'
    if m.lb>0 and (m.k<3 or (not np.isnan(m.pi_lo) and m.pi_lo>0)): return 'robust (pooled CI>0 and PI>0)'
    if m.lb>0: return 'supported but heterogeneous (pooled CI>0, PI includes 0)'
    if m.ub<0: return 'reversed'
    if m.ub<0.1 and m.lb>-0.1: return 'null-ish (pooled CI within |r|<.1)'
    return 'inconclusive (pooled CI includes 0)'
M['status']=M.apply(status,axis=1); P("\nevidence status (k>=2 effects):",M.status.value_counts().to_dict())

# ---------- current FReD effect identity ----------
A=pd.read_excel(ROOT+"data/raw/forrt/fred-data/archive/2025-11-30_COSdata_validated.xlsx")
A['doi_o']=A.doi_o.map(norm_doi); A['doi_r']=A.doi_r.map(norm_doi)
A['key1']=A.doi_o+'|'+A.study_o.astype(str)
A['key2']=A.doi_o+'|'+A.study_o.astype(str)+'|'+A.claim_text_o.astype(str).str.strip().str.lower().str[:80]
A['key3']=A.doi_o+'|'+A.description.astype(str).str.strip().str.lower().str[:80]
for k in ['doi_o','key1','key2','key3']:
    gs=A.groupby(k).doi_r.nunique()
    P(f"current FReD grouping by {k}: groups {gs.size}, with >=2 distinct replications {(gs>=2).sum()}, >=3 {(gs>=3).sum()}, max {gs.max()}")
# legacy -> current join coverage for effect names
Lk=L[['doi_o','doi_r','effect']].dropna(subset=['doi_o','doi_r']).drop_duplicates()
j=A.merge(Lk,on=['doi_o','doi_r'],how='left')
P("current rows gaining a legacy effect name via (doi_o,doi_r):", j.effect.notna().sum(), " distinct names:", j.effect.nunique())
Lo=L[['doi_o','effect']].dropna().drop_duplicates()
j2=A.merge(Lo,on='doi_o',how='left'); P("current rows gaining effect name via doi_o only:", j2.effect.notna().sum(), " ambiguous doi_o (several names):", (Lo.groupby('doi_o').effect.nunique()>1).sum())

# ---------- FLoRA ----------
F=pd.read_csv(ROOT+"data/raw/forrt/fred-data/output_flora.csv")
P("\nFLoRA",F.shape, F.type.value_counts().to_dict())
R=F[F.type=='replication']
P("FLoRA replication outcomes:",R.outcome.value_counts(dropna=False).to_dict())
P("FLoRA reproduction outcomes:",F[F.type=='reproduction'].outcome.value_counts(dropna=False).to_dict())
R=R.assign(y=pd.to_numeric(R.year_r,errors='coerce'))
def rt(g):
    n=len(g); return pd.Series({'n':n,'successful':round((g=='successful').mean(),3),'failed':round((g=='failed').mean(),3),'mixed':round((g=='mixed').mean(),3)})
t=R.groupby('y').outcome.apply(rt).unstack(); P(t[t.n>=30].to_string())
# per-original dedup (FLoRA): one original many replications
po=R.groupby('doi_o').outcome.agg(lambda s: 'successful' if (s=='successful').all() else ('failed' if (s=='failed').all() else 'mixed'))
P("FLoRA per doi_o (n=%d):"%len(po), po.value_counts(normalize=True).round(3).to_dict())
# journal_o-based discipline via wiki disciplines.json
try:
    dj=json.load(open(ROOT+"wiki/data/sources/disciplines.json",encoding='utf-8'))
    inv={j:d for d,js in dj.items() for j in js}
    R=R.assign(disc=R.journal_o.map(inv))
    P("FLoRA journal->discipline coverage:", R.disc.notna().mean().round(3))
    t=R.groupby('disc').outcome.apply(rt).unstack().sort_values('n',ascending=False); P(t.head(15).to_string())
except Exception as e: P("disciplines.json failed",e)
# FReD (archive) vs FLoRA agreement
A2=A.merge(R[['doi_o','doi_r','outcome']].drop_duplicates(['doi_o','doi_r']),on=['doi_o','doi_r'],how='inner')
m=A2.reported_success.isin(['successful','failed','mixed'])&A2.outcome.isin(['successful','failed','mixed'])
P("FReD effect rows joined to FLoRA:",len(A2)," agreement effect-level reported_success vs FLoRA paper outcome:",round((A2.reported_success==A2.outcome)[m].mean(),3))
P(pd.crosstab(A2.reported_success[m],A2.outcome[m]).to_string())
P("DONE2")
