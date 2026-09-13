"""Frozen exact flexibility controls, discovery, then held-out confirmation."""
import json,time
from pathlib import Path
import numpy as np
from research.formation.path_following import make_lf_game
from research.formation.exact_v12 import terminal_payoff_matrix,backward_induction
from research.formation.sequence_v12 import solve_sequence_form

OUT=Path('research/final_v12/flexibility');OUT.mkdir(exist_ok=True)
CORE=Path('research/final_v12/exact_grid3')
KD=json.load(open('research/results/e01/kernel_fits.json'))['CA']

def cell(geo,er,ev,phase):
    f=OUT/f'{phase}_{geo}_{er:g}_{ev:g}.json'
    if f.exists():return json.load(open(f))
    start=time.time();cache=CORE/f'payoff_{geo}_{er:g}_{ev:g}_lf.npz'
    if cache.exists():A=np.load(cache)['A']
    else:
        A=terminal_payoff_matrix(make_lf_game(KD,geo,er,ev,6))
        np.savez_compressed(cache,A=A)
    values={}
    for s in ('FF','CC','FC','CF'):
        checkpoint=OUT/f'{phase}_{geo}_{er:g}_{ev:g}_{s}.json'
        if checkpoint.exists():v=json.load(open(checkpoint))
        else:
            t=time.time()
            v=backward_induction(A,3,6,1 if s=='FF' else 6) if s in ('FF','CC') else solve_sequence_form(A,3,6,s)
            v['seconds']=time.time()-t;checkpoint.write_text(json.dumps(v,indent=2))
        values[s]=v;print(phase,geo,er,ev,s,v['V'],v['seconds'],flush=True)
    ff,fc,cf,cc=[values[s]['V'] for s in ('FF','FC','CF','CC')]
    fb=fc-cc;fr=fc-ff;fb_alt=ff-cf;fr_alt=cc-cf;c=cc-ff
    sign=float(np.sign(er-1));lo=values['CC']['LB']-values['FF']['UB'];hi=values['CC']['UB']-values['FF']['LB']
    dlo,dhi=(lo,hi) if sign>0 else (-hi,-lo)
    if sign==0:dlo=dhi=0.
    monotonicity=min(fb,fr,fb_alt,fr_alt)>=-1e-6
    if not monotonicity:raise RuntimeError('flexibility monotonicity failed')
    r={'geometry':geo,'eta_r':er,'eta_v':ev,'T':6,'grid':3,'formation':'leader_follower','phase':phase,
       'values':values,'F_B':fb,'F_R':fr,'F_B_alt':fb_alt,'F_R_alt':fr_alt,'interaction':fc+cf-ff-cc,
       'C':c,'C_LB':lo,'C_UB':hi,'Delta_F':sign*c,'Delta_LB':dlo,'Delta_UB':dhi,
       'correct_resolved':bool(dlo>1e-8),'reverse_resolved':bool(dhi < -1e-8),
       'monotonicity_pass':monotonicity,'identity_error':abs(c-(fr-fb)),'seconds':time.time()-start}
    if phase=='control':
        r['exchange_pass']=max(abs(ff),abs(cc),abs(fc+cf))<1e-6
        if not r['exchange_pass']:raise RuntimeError('exact exchange control failed')
    f.write_text(json.dumps(r,indent=2));return r

def main():
    branch=json.load(open(CORE/'discovery_summary.json'))['branch']
    if branch!='D_E':raise RuntimeError('wrong branch')
    controls=[cell(g,1.,1.,'control') for g in ('head_on','parallel','crossing')]
    (OUT/'controls_summary.json').write_text(json.dumps(controls,indent=2))
    discovery=[cell(g,r,1.,'discovery') for g in ('head_on','parallel','crossing') for r in (.8,1.2)]
    (OUT/'discovery_summary.json').write_text(json.dumps(discovery,indent=2))
    heldout=[cell(g,r,v,'heldout') for g in ('head_on','parallel','crossing') for r in (.85,1.15) for v in (.9,1.1)]
    n=sum(r['correct_resolved'] for r in heldout)
    verdict='FAIL_REMOVE_CORE' if n<8 else 'CONDITIONAL_REQUIRES_ROBUSTNESS' if n<10 else 'PASS_REQUIRES_ROBUSTNESS'
    summary={'n':12,'n_correct_resolved':n,'n_reverse_resolved':sum(r['reverse_resolved'] for r in heldout),
             'verdict':verdict,'rows':heldout,'no_optional_stress_grid':True}
    (OUT/'heldout_summary.json').write_text(json.dumps(summary,indent=2));print(verdict,n,flush=True)

if __name__=='__main__':main()
