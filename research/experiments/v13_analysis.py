"""Frozen contrasts, descriptive mechanism analyses and gate prerequisites."""
import csv,json
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
from research.experiments.v13_exact import write

ROOT=Path('research/final_v13');GEO=('head_on','parallel','crossing')
def read(p):return json.loads(Path(p).read_text())
def rho(x,y):
    if len(x)<3 or len(set(x))<2 or len(set(y))<2:return None
    return float(spearmanr(x,y).statistic)
def csvout(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def interactions(phase):
    data=read(ROOT/phase/'all_results.json');mech=read(ROOT/'mechanism'/phase/'all_results.json')
    exact={(r['geometry'],r['focal_speed_ratio']):r for r in data}
    scores={(r['geometry'],r['focal_speed_ratio']):r for r in mech}
    pairs=[('outer',.75,1.25),('inner',.9,1.1)] if phase=='confirmatory' else [(f'adjacent{i+1}',a,b) for i,(a,b) in enumerate(zip([.7,.85,1,1.15],[.85,1,1.15,1.3]))]
    rows=[]
    for g in GEO:
        for name,lo,hi in pairs:
            L=exact[g,lo];H=exact[g,hi];msL=scores[g,lo]['summary'];msH=scores[g,hi]['summary']
            for k in ('F','C'):
                l=L['blue']['conditional_flexibility'][k];h=H['blue']['conditional_flexibility'][k]
                lb=h['LB']-l['UB'];ub=h['UB']-l['LB'];m=h['F']-l['F'];width=ub-lb
                mm=H['red_mirror']['conditional_flexibility'][k]['F']-L['red_mirror']['conditional_flexibility'][k]['F']
                err=abs(mm-m)
                if err>1e-6:raise RuntimeError('interaction mirror failed')
                r={'id':f'{g}_{name}_{k}','phase':phase,'geometry':g,'contrast':name,'opponent_policy':k,
                   'v_low':lo,'v_high':hi,'opponent_speed':1.,'F_low':l['F'],'F_high':h['F'],'M':m,'LB':lb,'UB':ub,
                   'interval_width':width,'positive':bool(lb>1e-5 and abs(m)>100*width),
                   'reversal':bool(ub < -1e-5 and abs(m)>100*width),
                   'strong_reversal':bool(ub<-.1 and abs(m)>100*width),'mirror_M_error':err}
                for j,alpha in enumerate((.9,.8)):
                    for metric in ('Theta','Theta_centroid','Theta_hausdorff','R_raw','directed_drift','centroid_drift','hausdorff','raw_ratio','nonnegative_ratio','opponent_heading_change'):
                        a=msL[j][metric];b=msH[j][metric]
                        r[f'delta_{metric}_{alpha:g}']=None if a is None or b is None else b-a
                r['Theta_low']=msL[0]['Theta'];r['Theta_high']=msH[0]['Theta'];rows.append(r)
    out=ROOT/'analysis';out.mkdir(exist_ok=True);write(out/f'{phase}_interactions.json',rows);csvout(out/f'{phase}_interactions.csv',rows)
    return rows,data,mech

def mechanism_analysis(rows,data,mech):
    valid=[r for r in rows if r['delta_Theta_0.9'] is not None]
    x=np.array([r['delta_Theta_0.9'] for r in valid]);y=np.array([r['M'] for r in valid])
    labels=['intercept','DeltaTheta','geometry_parallel','geometry_crossing','opponent_C','contrast_inner']
    X=np.column_stack((np.ones(len(valid)),x,[r['geometry']=='parallel' for r in valid],[r['geometry']=='crossing' for r in valid],
                      [r['opponent_policy']=='C' for r in valid],[r['contrast']=='inner' for r in valid])).astype(float)
    if not any(r['contrast']=='inner' for r in valid):X=X[:,:-1];labels=labels[:-1]
    beta,res,rank,sv=np.linalg.lstsq(X,y,rcond=None);pred=X@beta;rss=float(np.sum((y-pred)**2));tss=float(np.sum((y-y.mean())**2))
    correlations={}
    for alpha in (.9,.8):
        for metric in ('Theta','Theta_centroid','Theta_hausdorff','raw_ratio','nonnegative_ratio','R_raw','directed_drift','centroid_drift','hausdorff'):
            key=f'delta_{metric}_{alpha:g}';rs=[r for r in rows if r[key] is not None]
            correlations[key]=rho([r[key] for r in rs],[r['M'] for r in rs])
    per_class={k:rho([r['delta_Theta_0.9'] for r in valid if r['opponent_policy']==k],[r['M'] for r in valid if r['opponent_policy']==k]) for k in ('F','C')}
    # F-vs-Theta is also reported as requested, separately by fixed opponent class.
    lookup={(r['geometry'],r['focal_speed_ratio']):r['summary'][0]['Theta'] for r in mech}
    f_association={k:rho([lookup[r['geometry'],r['focal_speed_ratio']] for r in data],
                       [r['blue']['conditional_flexibility'][k]['F'] for r in data]) for k in ('F','C')}
    physical={(r['geometry'],r['contrast']):r['delta_Theta_0.9'] for r in valid}
    coverage=sum(r['summary'][0]['n_defined'] for r in mech)/sum(r['summary'][0]['n_epochs'] for r in mech)
    return {'primary_spearman':rho(x.tolist(),y.tolist()),'per_opponent_class_spearman':per_class,
            'F_vs_Theta_spearman':f_association,'robustness_correlations':correlations,
            'n_endpoints':len(rows),'n_unique_physical_contrasts':len(physical),'n_positive_DeltaTheta':sum(v>1e-9 for v in physical.values()),
            'defined_epoch_fraction':coverage,'regression':{'columns':labels,'coefficients':dict(zip(labels,beta.tolist())),
             'rank':int(rank),'n_columns':len(labels),'n_rows':len(valid),'condition_number':float(np.linalg.cond(X)),
             'R_squared':1-rss/tss if tss else None,'fitted':pred.tolist(),'residuals':(y-pred).tolist(),
             'scope':'descriptive fixed-design least squares; shared mechanism probes; no population p-values or causal mediation'},
            'scope':'standardized kinematic probes, not equilibrium-policy paths; no independent-count inflation from policy classes'}

def main():
    for phase in ('discovery','confirmatory'):
        if not (ROOT/phase/'all_results.json').exists():continue
        rows,data,mech=interactions(phase);ma=mechanism_analysis(rows,data,mech);write(ROOT/'analysis'/f'{phase}_mechanism.json',ma)
        if phase!='confirmatory':continue
        n=sum(r['positive'] for r in rows);nr=sum(r['reversal'] for r in rows);ns=sum(r['strong_reversal'] for r in rows)
        pooled=ma['primary_spearman'];pcs=ma['per_opponent_class_spearman']
        chain=ma['n_positive_DeltaTheta']>=5 and ma['defined_epoch_fraction']>=.95
        assoc=pooled is not None and pooled>0 and all(v is not None and v>=0 for v in pcs.values())
        strongmech=assoc and pooled>.6 and chain;conditionalmech=assoc and chain
        perclass={k:{'positive':sum(r['positive'] for r in rows if r['opponent_policy']==k),'reversal':sum(r['reversal'] for r in rows if r['opponent_policy']==k)} for k in ('F','C')}
        pergeo={g:sum(r['positive'] for r in rows if r['geometry']==g) for g in GEO}
        fail=[]
        if n<=7:fail.append('primary support <=7/12')
        if ns>=2:fail.append('multiple strong reversals')
        if not conditionalmech:fail.append('tracking mechanism or directional chain unsupported')
        if any(v['reversal']>=4 for v in perclass.values()):fail.append('systematic reversal in a fixed opponent class')
        verdict='FAIL' if fail else 'CANDIDATE_STRONG_REQUIRES_REFINEMENT' if n>=10 and strongmech and min(pergeo.values())>0 else 'CANDIDATE_CONDITIONAL_REQUIRES_REFINEMENT'
        gate={'n_primary':12,'n_positive':n,'n_reversal':nr,'n_strong_reversal':ns,'n_unresolved':12-n-nr,
          'per_opponent_class':perclass,'per_geometry_positive':pergeo,'mechanism':ma,'failure_reasons':fail,'pre_refinement_verdict':verdict,
          'max_mirror_interaction_error':max(r['mirror_M_error'] for r in rows),'max_interaction_interval_width':max(r['interval_width'] for r in rows),
          'min_abs_interaction':min(abs(r['M']) for r in rows),'manuscript_writing_in_current_scope':False,
          'refinement_allowed':not bool(fail),'note':'Project gate is not journal rank or acceptance certification.'}
        write(ROOT/'analysis'/'GATE_DATA.json',gate);print(json.dumps({k:gate[k] for k in ['n_positive','n_reversal','n_strong_reversal','failure_reasons','pre_refinement_verdict']},indent=2))

if __name__=='__main__':main()
