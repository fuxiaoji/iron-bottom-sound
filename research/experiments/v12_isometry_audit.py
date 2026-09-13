"""A3/R4: check the WHOLE policy mapping, beyond exchange at initial states."""
import json,copy
import numpy as np
from pathlib import Path
from research.formation.commitment_v12 import *
from research.formation.path_following import make_lf_game


def transform(s,Q,c):
    out=s.clone();out.stations=s.stations@Q.T+c
    return out


def run(tag='pre_spatial'):
    rng=np.random.default_rng(1707);kd=json.load(open('research/results/e01/kernel_fits.json'))['CA'];rows=[]
    Qs=[-np.eye(2),np.diag([1.,-1.])]
    for i in range(20):
        g=make_lf_game(kd,('head_on','parallel','crossing')[i%3],1.,1.,6);b,r=initial_states(g)
        b.extend_plan(rng.choice([-60.,0.,60.],3));r.extend_plan(rng.choice([-60.,0.,60.],3))
        s=RemainingHorizonGame(g,b,r,3,GRIDS['3']).solve()
        Q=Qs[i%2];c=np.array([7.,-12.]);bb=transform(b,Q,c);rr=transform(r,Q,c)
        u=RemainingHorizonGame(g,bb,rr,3,GRIDS['3']).solve()
        p=np.arange(len(s['x'])) if np.linalg.det(Q)>0 else np.arange(len(s['x'])-1,-1,-1)
        rows.append({'id':i,'value_error':abs(s['V']-u['V']),'max_policy_error':float(max(abs(s['x']-u['x'][p]).max(),abs(s['y']-u['y'][p]).max()))})
    Path(f'research/final_v12/audit/isometry_{tag}.json').write_text(json.dumps(rows,indent=2));print(rows,flush=True)

if __name__=='__main__':run()
