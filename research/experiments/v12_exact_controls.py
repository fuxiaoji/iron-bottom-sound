"""Independent full finite-game controls before asymmetric discovery."""
import json,time
from pathlib import Path
from research.formation.path_following import make_lf_game
from research.formation.exact_v12 import terminal_payoff_matrix,backward_induction
OUT=Path('research/final_v12/exact_grid3');OUT.mkdir(exist_ok=True,parents=True)
KD=json.load(open('research/results/e01/kernel_fits.json'))['CA']
rows=[]
for geo in ('head_on','parallel','crossing'):
    g=make_lf_game(KD,geo,1.,1.,6);start=time.time();A=terminal_payoff_matrix(g)
    print(geo,'enumerated',A.shape,time.time()-start,flush=True)
    for h in (1,2,3,6):
        r=backward_induction(A,3,6,h);r['geometry']=geo;r['eta_r']=1.;r['eta_v']=1.;rows.append(r)
        print(geo,h,r['V'],r['numeric_error_budget'],time.time()-start,flush=True)
        (OUT/'symmetric_controls.json').write_text(json.dumps(rows,indent=2))
        if abs(r['V'])>1e-6:raise RuntimeError('EXACT_SYMMETRY_CONTROL_FAILED')
