import pandas as pd, numpy as np, re, json, sys, warnings
from scipy import stats
warnings.filterwarnings('ignore')
ROOT="C:/Users/OMISTAJA/PsychologyReplication/"
OUT={}
def P(*a):
    print(*a); sys.stdout.flush()

# ---------- load ----------
arc=pd.read_excel(ROOT+"data/raw/forrt/fred-data/archive/2025-11-30_COSdata_validated.xlsx")
cur=pd.read_excel(ROOT+"data/raw/forrt/fred-data/output_FReD.xlsx")
assert len(arc)==len(cur)
for c in ['year_o','year_r','journal_o','journal_r','title_o','title_r']:
    arc[c]=cur[c].values
P("archive+current cols", arc.shape)

# ---------- conversion to r (R package rules) ----------
CANNOT={"beta (std)","partial etasq","χ2","b (unstd)","b","etasq (partial)","cramer's v","dz","hazards ratio","beta","percentage",
        "squared seminpartial correlation (sr2)","regression coefficient","unstandardized coefficient","cohen's h","h"}
MAP={"or":"or","odds ratio":"or","d":"d","cohen's d":"d","hedges' g":"d","hedges'g":"d","hedge's g":"d","hedges g":"d","hedgesg":"d","smd":"d",
     "etasq":"eta2","etaq":"eta2","eta^2":"eta2","η²":"eta2","f":"f","cohen's f":"f","f2":"f2","f^2":"f2","f²":"f2","cohen's f^2":"f2",
     "r":"r","phi":"r","φ":"r","r2":"r2","r^2":"r2","r²":"r2","r-square":"r2","test statistic":"test-stat","test statistics":"test-stat","test":"test-stat"}
def d2r(d): return d/np.sqrt(d*d+4)
def parse_ts(x):
    x=str(x).strip()
    m=re.match(r"^t\((\d+)\)\s*=\s*(-?\d+\.?\d*)$",x,re.I)
    if m:
        df,t=float(m.group(1)),float(m.group(2)); return t/np.sqrt(t*t+df),'t'
    m=re.match(r"^f\((\d+)\s*,\s*(\d+)\)\s*=\s*(\d+\.?\d*)$",x,re.I)
    if m:
        df1,df2,F=float(m.group(1)),float(m.group(2)),float(m.group(3))
        if df1==1:
            t=np.sqrt(F); return t/np.sqrt(t*t+df2),'F1'
        return np.nan,'Fdf>1'
    m=re.match(r"^z\s*=\s*(-?\d+\.?\d*)\s*,\s*n\s*=\s*(\d+)$",x,re.I)
    if m:
        z,n=float(m.group(1)),float(m.group(2)); return z/np.sqrt(z*z+n),'z'
    xc=re.sub(r"^[χΧ]","x",x)
    m=re.match(r"^x2\(\s*1\s*,\s*n\s*=\s*(\d+)\s*\)\s*=\s*(\d+\.?\d*)$",xc,re.I)
    if m:
        n,chi=float(m.group(1)),float(m.group(2)); return np.sqrt(chi/n),'chi1'
    return np.nan,'unparsed'
def conv(val,typ):
    if pd.isna(typ) or pd.isna(val): return np.nan,'missing'
    t=str(typ).lower().strip().replace("\u2019","'")
    if t in CANNOT: return np.nan,'cannot:'+t
    k=MAP.get(t)
    if k is None: return np.nan,'unknown:'+t
    if k=='test-stat': return parse_ts(val)
    try: v=float(val)
    except: return np.nan,'nonnumeric'
    if k=='r': return v,'r'
    if k=='r2': return np.sqrt(v),'r2'
    if k=='d': return d2r(v),'d'
    if k=='or': return d2r(np.log(v)*np.sqrt(3)/np.pi),'or'
    if k=='eta2': return d2r(2*np.sqrt(v/(1-v))),'eta2'
    if k=='f': return d2r(2*v),'f'
    if k=='f2': return np.sqrt(v/(1+v)),'f2'
    return np.nan,'?'
for side in ['o','r']:
    res=[conv(v,t) for v,t in zip(arc['es_value_'+side],arc['es_type_'+side])]
    arc['rconv_'+side]=[r for r,_ in res]; arc['rconv_how_'+side]=[h for _,h in res]
P("conv how o:", arc.rconv_how_o.value_counts().head(20).to_dict())
P("conv how r:", arc.rconv_how_r.value_counts().head(20).to_dict())
# compare with archive r_o/r_r
for side in ['o','r']:
    both=arc[['rconv_'+side,'r_'+side]].dropna()
    diff=(both['rconv_'+side]-both['r_'+side]).abs()
    P(f"r_{side}: archive nonnull {arc['r_'+side].notna().sum()}, ours {arc['rconv_'+side].notna().sum()}, both {len(both)}, |diff|>0.01: {(diff>0.01).sum()}, max {diff.max():.3f}")
# coalesce: prefer our conversion, fall back to archive
arc['es_o']=arc['rconv_o'].fillna(arc['r_o']); arc['es_r']=arc['rconv_r'].fillna(arc['r_r'])
arc['n_o']=pd.to_numeric(arc['n_o'],errors='coerce'); arc['n_r']=pd.to_numeric(arc['n_r'],errors='coerce')
for c in ['es_o','es_r']:
    arc.loc[arc[c].abs()>1,c]=np.nan; arc.loc[arc[c]==1,c]=.9999; arc.loc[arc[c]==-1,c]=-.9999
# align direction
sgn=np.sign(arc['es_o']); arc['es_o_al']=arc['es_o'].abs(); arc['es_r_al']=arc['es_r']*sgn
ok=arc[['es_o','es_r']].notna().all(axis=1); okn=ok&arc[['n_o','n_r']].notna().all(axis=1)&(arc.n_o>3)&(arc.n_r>3)
P("rows with r both sides:",ok.sum()," with Ns>3:",okn.sum())
OUT['rows_r_both']=int(ok.sum()); OUT['rows_r_both_n']=int(okn.sum())

# ---------- helpers (R package) ----------
def p_from_r(r,N):
    t=r*np.sqrt((N-2)/(1-r*r)); return 2*stats.t.sf(np.abs(t),N-2)
def ci_r(r,n,cl=.95):
    z=np.arctanh(r); se=1/np.sqrt(n-3); zc=stats.norm.ppf(1-(1-cl)/2); return np.tanh(z-zc*se),np.tanh(z+zc*se)
def pi_r(r,n_o,n_r,cl=.95):
    z=np.arctanh(r); se=np.sqrt(1/(n_o-3)+1/(n_r-3)); zc=stats.norm.ppf(1-(1-cl)/2); return np.tanh(z-zc*se),np.tanh(z+zc*se)
def fe_cor(r1,n1,r2,n2):
    # metafor escalc COR: yi=r, vi=(1-r^2)^2/(n-1); FE
    y=np.array([r1,r2]); v=np.array([(1-r1**2)**2/(n1-1),(1-r2**2)**2/(n2-1)]); w=1/v
    est=(w*y).sum()/w.sum(); se=np.sqrt(1/w.sum()); Q=(w*(y-est)**2).sum(); QEp=stats.chi2.sf(Q,1)
    return est,est-1.96*se,est+1.96*se,QEp
def power_r(r,n,alpha=.05):
    ttt=stats.t.ppf(1-alpha,n-2); rc=np.sqrt(ttt**2/(ttt**2+n-2)); zr=np.arctanh(abs(r))+abs(r)/(2*(n-1)); zrc=np.arctanh(rc)
    return stats.norm.cdf((zr-zrc)*np.sqrt(n-3))
def r_for_power(pt,n,alpha=.05):
    tc=stats.t.ppf(1-alpha,n-2); rc=np.sqrt(tc**2/(tc**2+n-2)); zp=stats.norm.ppf(pt); zreq=zp/np.sqrt(n-3)+np.arctanh(rc)
    ri=np.tanh(zreq); rcorr=ri-ri/(2*(n-1)); return np.tanh(zreq-rcorr/(2*(n-1)))
CRIT=['significance_r','significance_agg','consistency_ci','consistency_pi','homogeneity','homogeneity_significance','small_telescopes']
def assess(eo,no,er,nr):
    out={}
    po=p_from_r(eo,no); pr=p_from_r(er,nr)
    # 1
    if po>=.05: out['significance_r']='OS n.s.'
    elif pr>=.05: out['significance_r']='failure'
    elif np.sign(eo)==np.sign(er): out['significance_r']='success'
    else: out['significance_r']='failure (reversal)'
    est,lb,ub,QEp=fe_cor(eo,no,er,nr)
    out['significance_agg']='success' if (lb>0 and est>0) else ('failure (reversal)' if (lb>0 and est<0) else 'failure')
    lo,hi=ci_r(er,nr); out['consistency_ci']='success' if (lo<eo<hi) else 'failure'
    lo,hi=pi_r(eo,no,nr); out['consistency_pi']='success' if (lo<er<hi) else 'failure'
    out['homogeneity']='success' if QEp>=.05 else 'failure'
    if po>=.05: out['homogeneity_significance']='OS n.s.'
    else: out['homogeneity_significance']='success' if (QEp>.05 and lb>0) else 'failure'
    r33=r_for_power(.33,no); out['small_telescopes']='success' if er>=r33 else 'failure'
    out['p_o']=po; out['p_r']=pr; out['agg_est']=est; out['agg_lb']=lb; out['agg_ub']=ub; out['QEp']=QEp; out['r33']=r33
    out['power_r']=power_r(eo,nr) if nr>=4 else 0
    out['pi_lo'],out['pi_hi']=pi_r(eo,no,nr); out['ci_r_lo'],out['ci_r_hi']=ci_r(er,nr); out['ci_o_lo'],out['ci_o_hi']=ci_r(eo,no)
    return out
rows=[]
for i,rw in arc[okn].iterrows():
    o=assess(rw.es_o_al,rw.n_o,rw.es_r_al,rw.n_r); o['idx']=i; rows.append(o)
A=pd.DataFrame(rows).set_index('idx')
D=arc.join(A)
Dn=D[okn].copy()
P("\n=== criterion success shares (n=%d rows with r+N both sides) ==="%len(Dn))
tab={}
for c in CRIT:
    vc=Dn[c].value_counts(); n=len(Dn); succ=vc.get('success',0)
    tab[c]={'success':int(succ),'failure':int(vc.get('failure',0)+vc.get('failure (reversal)',0)),'reversal':int(vc.get('failure (reversal)',0)),'OS_ns':int(vc.get('OS n.s.',0)),'success_share_all':round(succ/n,3),
            'success_share_excl_osns':round(succ/(n-vc.get('OS n.s.',0)),3)}
    P(c,tab[c])
OUT['criteria']=tab
# disagreement: rows where criteria (binary success vs not, excluding OS n.s.) disagree
B=Dn[CRIT].apply(lambda s: s.map(lambda v: 1 if v=='success' else (np.nan if v=='OS n.s.' else 0)))
valid=B.notna().all(axis=1)
nsucc=B[valid].sum(axis=1)
P("rows with all 7 defined:",valid.sum()," unanimous success:",(nsucc==7).sum()," unanimous failure:",(nsucc==0).sum()," disagreement:",((nsucc>0)&(nsucc<7)).sum(), "share disagree:",round(((nsucc>0)&(nsucc<7)).mean(),3))
OUT['disagreement']={'n':int(valid.sum()),'unanimous_success':int((nsucc==7).sum()),'unanimous_failure':int((nsucc==0).sum()),'disagree':int(((nsucc>0)&(nsucc<7)).sum()),'dist':nsucc.value_counts().sort_index().to_dict()}
P("distribution of #criteria satisfied:",nsucc.value_counts().sort_index().to_dict())
# pairwise agreement
pa=pd.DataFrame(index=CRIT,columns=CRIT,dtype=float)
for a in CRIT:
    for b in CRIT:
        m=B[a].notna()&B[b].notna(); pa.loc[a,b]=round((B.loc[m,a]==B.loc[m,b]).mean(),2)
P("pairwise agreement\n",pa.to_string())
OUT['pairwise']=pa.to_dict()
# reported vs computed
P("\n=== reported_success vs significance_r ===")
ct=pd.crosstab(Dn.reported_success,Dn.significance_r); P(ct.to_string()); OUT['reported_vs_sigr']=ct.to_dict()
m=Dn.reported_success.isin(['successful','failed'])&Dn.significance_r.isin(['success','failure','failure (reversal)'])
agree=((Dn.reported_success=='successful')==(Dn.significance_r=='success'))[m].mean()
P("agreement reported(succ/fail) vs significance_r:",round(agree,3),"n=",m.sum())
OUT['reported_vs_sigr_agree']=round(float(agree),3)
ct2=pd.crosstab(Dn.reported_success,Dn.consistency_pi); P(ct2.to_string())
m2=Dn.reported_success.isin(['successful','failed']);
agr={}
for c in CRIT:
    mm=m2&(Dn[c]!='OS n.s.')
    ag=((Dn.reported_success=='successful')==(Dn[c]=='success'))[mm].mean()
    P(f"agree reported vs {c}: {ag:.3f} (n={mm.sum()})"); agr[c]=[round(float(ag),3),int(mm.sum())]
OUT['reported_vs_crit_agree']=agr
# statistical_success archive vs our significance_r
mm=Dn.statistical_success.notna()&(Dn.significance_r!='OS n.s.')
P("archive statistical_success vs our significance_r agreement:",round(((Dn.statistical_success==1)==(Dn.significance_r=='success'))[mm].mean(),3),"n=",mm.sum())

# ---------- shrinkage ----------
P("\n=== shrinkage ===")
Dn['ratio']=Dn.es_r_al/Dn.es_o_al
Dn['dz']=np.arctanh(Dn.es_r_al.clip(-.9999,.9999))-np.arctanh(Dn.es_o_al.clip(-.9999,.9999))
q=Dn.ratio.quantile([.1,.25,.5,.75,.9]).round(3).to_dict()
P("ratio es_r/es_o quantiles:",q," mean:",round(Dn.ratio.mean(),3))
P("share ratio<0 (reversed sign):",round((Dn.ratio<0).mean(),3)," <0.5:",round((Dn.ratio<0.5).mean(),3)," >=1:",round((Dn.ratio>=1).mean(),3))
P("median es_o:",round(Dn.es_o_al.median(),3)," median es_r:",round(Dn.es_r_al.median(),3))
OUT['shrinkage']={'ratio_q':q,'mean_ratio':round(Dn.ratio.mean(),3),'share_neg':round((Dn.ratio<0).mean(),3),'share_lt_half':round((Dn.ratio<0.5).mean(),3),'share_ge1':round((Dn.ratio>=1).mean(),3),'median_es_o':round(Dn.es_o_al.median(),3),'median_es_r':round(Dn.es_r_al.median(),3),'n':len(Dn)}
# shrinkage by original ES bucket
Dn['es_o_bin']=pd.cut(Dn.es_o_al,[0,.1,.2,.3,.5,1])
t=Dn.groupby('es_o_bin').agg(n=('ratio','size'),med_ratio=('ratio','median'),med_es_r=('es_r_al','median'),succ=('significance_r',lambda s:(s=='success').mean())).round(3); P(t.to_string()); OUT['shrink_by_es_o']=t.astype(str).to_dict()
# by reported outcome
t=Dn.groupby('reported_success').ratio.describe()[['count','25%','50%','75%']].round(3); P(t.to_string()); OUT['shrink_by_reported']=t.to_dict()

# ---------- p<.005 predictor ----------
P("\n=== p-value of original predicts success? ===")
Dn['p_o_bin']=pd.cut(Dn.p_o,[-1,.005,.05,1.1],labels=['p<=.005','.005<p<.05','p>=.05'])
for crit in ['reported_success','significance_r','consistency_pi','small_telescopes']:
    if crit=='reported_success':
        g=Dn[Dn.reported_success.isin(['successful','failed'])].groupby('p_o_bin').reported_success.apply(lambda s:pd.Series({'n':len(s),'succ':round((s=='successful').mean(),3)}))
    else:
        g=Dn[Dn[crit]!='OS n.s.'].groupby('p_o_bin')[crit].apply(lambda s:pd.Series({'n':len(s),'succ':round((s=='success').mean(),3)}))
    P(crit); P(g.unstack().to_string())
    OUT['p005_'+crit]=g.unstack().to_dict()
# also with reported p-values (pval_value_o with type '<' or '=' )
pv=pd.to_numeric(Dn.pval_value_o,errors='coerce')
Dn['p_rep_bin']=pd.cut(pv,[-1,.005,.05,1.1],labels=['p<=.005','.005<p<.05','p>=.05'])
g=Dn[Dn.reported_success.isin(['successful','failed'])].groupby('p_rep_bin').reported_success.apply(lambda s:pd.Series({'n':len(s),'succ':round((s=='successful').mean(),3)})).unstack()
P("using REPORTED original p-values (pval_value_o):"); P(g.to_string()); OUT['p005_reportedp']=g.to_dict()
# whole FReD (not only r rows)
pv_all=pd.to_numeric(arc.pval_value_o,errors='coerce'); ab=pd.cut(pv_all,[-1,.005,.05,1.1],labels=['p<=.005','.005<p<.05','p>=.05'])
g=arc[arc.reported_success.isin(['successful','failed'])].groupby(ab).reported_success.apply(lambda s:pd.Series({'n':len(s),'succ':round((s=='successful').mean(),3)})).unstack()
P("ALL FReD rows, reported p_o vs reported_success:"); P(g.to_string()); OUT['p005_reportedp_all']=g.to_dict()
# logistic: success ~ log10 p_o
from statsmodels.formula.api import logit
dd=Dn[Dn.reported_success.isin(['successful','failed'])].copy(); dd['y']=(dd.reported_success=='successful').astype(int); dd['lp']=np.log10(dd.p_o.clip(1e-30,1)); dd['lnratio']=np.log(dd.n_r/dd.n_o); dd['z_o']=np.arctanh(dd.es_o_al)/ (1/np.sqrt(dd.n_o-3))
OUT['logit']={}
for f in ['y ~ lp','y ~ lnratio','y ~ lp + lnratio','y ~ z_o']:
    try:
        mfit=logit(f,dd).fit(disp=0); P(f, mfit.params.round(3).to_dict(), 'pseudoR2',round(mfit.prsquared,3),'n',int(mfit.nobs)); OUT['logit'][f]={'params':mfit.params.round(3).to_dict(),'pR2':round(mfit.prsquared,3),'n':int(mfit.nobs)}
    except Exception as e: P(f,e)

# ---------- N ratio ----------
P("\n=== N ratio predicts success? ===")
Dn['nratio']=Dn.n_r/Dn.n_o
Dn['nr_bin']=pd.cut(Dn.nratio,[0,.5,1,2,5,1e9],labels=['<0.5','0.5-1','1-2','2-5','>5'])
g=Dn[Dn.reported_success.isin(['successful','failed'])].groupby('nr_bin').reported_success.apply(lambda s:pd.Series({'n':len(s),'succ':round((s=='successful').mean(),3)})).unstack(); P("reported:"); P(g.to_string()); OUT['nratio_reported']=g.to_dict()
g=Dn[Dn.significance_r!='OS n.s.'].groupby('nr_bin').significance_r.apply(lambda s:pd.Series({'n':len(s),'succ':round((s=='success').mean(),3)})).unstack(); P("significance_r:"); P(g.to_string()); OUT['nratio_sigr']=g.to_dict()
g=Dn.groupby('nr_bin').consistency_ci.apply(lambda s:pd.Series({'n':len(s),'succ':round((s=='success').mean(),3)})).unstack(); P("consistency_ci (should FALL with N ratio):"); P(g.to_string()); OUT['nratio_ci']=g.to_dict()
P("median n_o:",Dn.n_o.median()," median n_r:",Dn.n_r.median()," median ratio:",round(Dn.nratio.median(),2))
OUT['n_medians']={'n_o':float(Dn.n_o.median()),'n_r':float(Dn.n_r.median()),'ratio':round(float(Dn.nratio.median()),2)}
# power
Dn['pw_bin']=pd.cut(Dn.power_r,[-.01,.5,.8,.95,1.01],labels=['<.5','.5-.8','.8-.95','>.95'])
g=Dn[Dn.reported_success.isin(['successful','failed'])].groupby('pw_bin').reported_success.apply(lambda s:pd.Series({'n':len(s),'succ':round((s=='successful').mean(),3)})).unstack(); P("replication power (for es_o) vs reported:"); P(g.to_string()); OUT['power_reported']=g.to_dict()
P("share of replications with power>=.8 for es_o:",round((Dn.power_r>=.8).mean(),3))

# ---------- base rates: discipline, decade, ALL FReD reported_success ----------
P("\n=== base rates (all FReD rows, reported_success) ===")
arc['disc']=arc.discipline.astype(str).str.strip().str.lower()
arc['year_o']=pd.to_numeric(arc.year_o,errors='coerce'); arc['year_r']=pd.to_numeric(arc.year_r,errors='coerce')
arc['decade_o']=(arc.year_o//10*10)
def rate(g):
    n=len(g); return pd.Series({'n':n,'successful':round((g=='successful').mean(),3),'failed':round((g=='failed').mean(),3),'mixed':round((g=='mixed').mean(),3)})
bd=arc.groupby('disc').reported_success.apply(rate).unstack().sort_values('n',ascending=False); P(bd.head(20).to_string()); OUT['by_discipline']=bd.head(20).to_dict()
bdec=arc.groupby('decade_o').reported_success.apply(rate).unstack(); P(bdec.to_string()); OUT['by_decade_o']=bdec.to_dict()
byr=arc.groupby('year_r').reported_success.apply(rate).unstack(); P(byr[byr.n>=20].to_string()); OUT['by_year_r']=byr[byr.n>=20].to_dict()
# effect-level rows per doi_r (multi-site / mega-paper)
vc=arc.doi_r.value_counts(); P("rows per doi_r: top10",vc.head(10).to_dict()," share of rows in doi_r with >=20 rows:",round(vc[vc>=20].sum()/arc.doi_r.notna().sum(),3))
OUT['mega_doi_r']={'top10':vc.head(10).to_dict(),'share_rows_in_ge20':round(float(vc[vc>=20].sum()/arc.doi_r.notna().sum()),3)}
# entry-level dedup: reported success by entry (unique paper pairs)
ent=arc.groupby('entry_id').reported_success.agg(lambda s: 'successful' if (s=='successful').all() else ('failed' if (s=='failed').all() else 'mixed'))
P("entry-level (n=%d) outcome:"%len(ent), ent.value_counts(normalize=True).round(3).to_dict())
OUT['entry_level']=ent.value_counts().to_dict()
# per unique doi_o
do=arc.groupby('doi_o').reported_success.agg(lambda s: 'successful' if (s=='successful').all() else ('failed' if (s=='failed').all() else 'mixed'))
P("per original DOI (n=%d):"%len(do), do.value_counts(normalize=True).round(3).to_dict())
OUT['per_doi_o']=do.value_counts().to_dict()
# nested
P("nested_o:",arc.nested_o.value_counts().to_dict()," nested_r:",arc.nested_r.value_counts().to_dict())
P("es types NOT convertible (o):", arc[arc.rconv_how_o.str.startswith('cannot')|arc.rconv_how_o.str.startswith('unknown')].rconv_how_o.value_counts().head(15).to_dict())
P("es types NOT convertible (r):", arc[arc.rconv_how_r.str.startswith('cannot')|arc.rconv_how_r.str.startswith('unknown')].rconv_how_r.value_counts().head(15).to_dict())
OUT['nonconv_o']=arc[arc.rconv_how_o.str.startswith('cannot')|arc.rconv_how_o.str.startswith('unknown')].rconv_how_o.value_counts().head(15).to_dict()
OUT['nonconv_r']=arc[arc.rconv_how_r.str.startswith('cannot')|arc.rconv_how_r.str.startswith('unknown')].rconv_how_r.value_counts().head(15).to_dict()
P("unparsed test stats sample:", arc[arc.rconv_how_o=='unparsed'].es_value_o.head(12).tolist(), (arc.rconv_how_o=='unparsed').sum(),(arc.rconv_how_o=='Fdf>1').sum())
OUT['unparsed_ts']={'o_unparsed':int((arc.rconv_how_o=='unparsed').sum()),'o_Fdf>1':int((arc.rconv_how_o=='Fdf>1').sum()),'r_unparsed':int((arc.rconv_how_r=='unparsed').sum()),'r_Fdf>1':int((arc.rconv_how_r=='Fdf>1').sum()),'sample':arc[arc.rconv_how_o=='unparsed'].es_value_o.head(12).tolist()}
# mixed rows: what do they look like
P("author_overlap mean by outcome:", arc.groupby('reported_success').author_overlap.mean().round(3).to_dict())
P("prereg_r present by outcome:", arc.groupby('reported_success').prereg_r.apply(lambda s:s.notna().mean()).round(3).to_dict())
OUT['author_overlap_by_outcome']=arc.groupby('reported_success').author_overlap.mean().round(3).to_dict()
OUT['prereg_by_outcome']=arc.groupby('reported_success').prereg_r.apply(lambda s:s.notna().mean()).round(3).to_dict()
# author overlap vs success (self-replication)
ao=arc[arc.reported_success.isin(['successful','failed'])]
P("success rate by author_overlap>0:", ao.groupby(ao.author_overlap>0).reported_success.apply(lambda s: (round((s=='successful').mean(),3), len(s))).to_dict())
OUT['author_overlap_success']=ao.groupby(ao.author_overlap>0).reported_success.apply(lambda s: (round((s=='successful').mean(),3), len(s))).to_dict()
# same-paper multi-effect: how many entries have mixed results across effects
me=arc.groupby('entry_id').reported_success.agg(lambda s: s.nunique()); P("entries with >1 effect:", (arc.groupby('entry_id').size()>1).sum(), " of those with heterogeneous outcomes:", ((arc.groupby('entry_id').size()>1)&(me>1)).sum())
OUT['entries_multi']={'multi':int((arc.groupby('entry_id').size()>1).sum()),'heterogeneous':int(((arc.groupby('entry_id').size()>1)&(me>1)).sum())}

Dn.to_pickle(ROOT+"_planning/designs/_d2_fred_computed.pkl")
json.dump(OUT,open(ROOT+"_planning/designs/_d2_results_fred.json","w"),indent=1,default=str)
P("DONE")
