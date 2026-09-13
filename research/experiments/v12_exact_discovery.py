"""Six frozen asymmetric anchors; complete finite block games and branch decision."""
import json,time
from pathlib import Path
import numpy as np
from research.formation.path_following import make_lf_game
from research.formation.exact_v12 import terminal_payoff_matrix,backward_induction
OUT=Path('research/final_v12/exact_grid3');KD=json.load(open('research/results/e01/kernel_fits.json'))['CA']

def main():
    gate=json.load(open('research/final_v12/audit/PHASE_A_GATE.json'))
    if not gate['amended_deterministic_gate_pass']:raise RuntimeError('Phase A deterministic gate not passed')
    rows=[]
    for geo in ('head_on','parallel','crossing'):
        for er in (.8,1.2):
            f=OUT/f'anchor_{geo}_{er:g}.json';cache=OUT/f'payoff_{geo}_{er:g}_1_lf.npz'
            if f.exists():rows.append(json.load(open(f)));continue
            g=make_lf_game(KD,geo,er,1.,6);start=time.time();A=terminal_payoff_matrix(g)
            np.savez_compressed(cache,A=A)
            results={str(h):backward_induction(A,3,6,h) for h in (1,2,3,6)}
            c=results['6']['V']-results['1']['V'];error=results['6']['numeric_error_budget']+results['1']['numeric_error_budget']
            r={'geometry':geo,'eta_r':er,'eta_v':1.,'T':6,'grid':3,'formation':'leader_follower','classification':'discovery',
               'values':results,'C6':c,'C6_LB':c-error,'C6_UB':c+error,'sign_matches':bool(np.sign(c)==np.sign(er-1)),
               'sign_resolved':bool(abs(c)>error+1e-8),'seconds':time.time()-start}
            f.write_text(json.dumps(r,indent=2));rows.append(r);print(geo,er,c,r['sign_matches'],r['seconds'],flush=True)
    n=sum(r['sign_matches'] and r['sign_resolved'] for r in rows)
    result={'n_correct_resolved':n,'n':6,'branch':'C' if n>=5 else 'D_E','rows':rows}
    (OUT/'discovery_summary.json').write_text(json.dumps(result,indent=2));print('branch',result['branch'],n,flush=True)

if __name__=='__main__':main()
