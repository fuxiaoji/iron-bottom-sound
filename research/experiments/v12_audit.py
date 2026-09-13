"""Deterministic v12 defect and metamorphic audits; never overwrite v11 data."""
import json,time
from pathlib import Path
import numpy as np
from research.formation.path_following import make_lf_game
from research.formation import matched_horizon as old
from research.formation.commitment_v12 import *
OUT=Path('research/final_v12/audit');OUT.mkdir(parents=True,exist_ok=True)
KD=json.load(open('research/results/e01/kernel_fits.json'))['CA']


def main():
    rng=np.random.default_rng(120001);rows=[]
    for j in range(100):
        geom=('head_on','parallel','crossing')[j%3]
        er=(.8,1.,1.2)[(j//3)%3];ev=(.8,1.,1.2)[(j//9)%3]
        g=make_lf_game(KD,geom,er,ev,6);b,r=initial_states(g)
        t=int(rng.integers(1,6));hb=rng.choice([-60.,-30.,0.,30.,60.],t);hr=rng.choice([-60.,-30.,0.,30.,60.],t)
        b.extend_plan(hb);r.extend_plan(hr)
        R=6-t;p=rng.choice([-60.,0.,60.],R);q=rng.choice([-60.,0.,60.],R)
        scalar=scalar_interval_payoff(g,b,r,p,q);batch=float(batch_interval_payoff(g,b,r,p[None,:],q,True,R)[0])
        sw=scalar_interval_payoff(swap_game(g),r,b,q,p)
        oldscalar=old.scalar_interval_payoff(g,b,r,p,q,R)
        oldbatch=float(old.batch_interval_payoff(g,b,r,p[None,:],q,True,R)[0])
        # Causality: appending a future suffix cannot change any earlier endpoint.
        p2=np.r_[p,rng.choice([-60.,0.,60.])]
        x1=trajectory_batch(b,p[None,:],g);x2=trajectory_batch(b,p2[None,:],g)
        pref=max(float(np.max(abs(x1[k]-x2[k][:,:R+1]))) for k in (0,1))
        rows.append({'id':j,'geometry':geom,'eta_r':er,'eta_v':ev,'executed':t,
                     'scalar':scalar,'batch':batch,'scalar_batch_error':abs(scalar-batch),
                     'swap_error':abs(scalar+sw),'prefix_error':pref,
                     'old_scalar_batch_error':abs(oldscalar-oldbatch),'old_new_batch_difference':oldbatch-batch})
    summary={'n':len(rows),'max_scalar_batch_error':max(x['scalar_batch_error'] for x in rows),
             'max_swap_error':max(x['swap_error'] for x in rows),'max_prefix_error':max(x['prefix_error'] for x in rows),
             'old_max_scalar_batch_error':max(x['old_scalar_batch_error'] for x in rows),
             'old_failures_1e8':sum(x['old_scalar_batch_error']>1e-8 for x in rows)}
    summary['pass']=all(summary[k]<1e-8 for k in ('max_scalar_batch_error','max_swap_error','max_prefix_error'))
    (OUT/'history_tests.json').write_text(json.dumps({'summary':summary,'rows':rows},indent=2))
    print(summary,flush=True)
    # Exact legacy cache collision: all different first-turn orders have equal
    # old keys because stations[head] points inside the prehistory (missing M).
    g=make_lf_game(KD,'crossing',1.2,1.,6);b,r=initial_states(g)
    b1=b.clone();b2=b.clone();r1=r.clone();r1.extend_plan([0.]);b1.extend_plan([-60.]);b2.extend_plan([60.])
    q=np.zeros(5);P=np.array([np.zeros(5),np.full(5,60.)])
    diff=float(np.max(abs(batch_interval_payoff(g,b1,r1,P,q,True,5)-batch_interval_payoff(g,b2,r1,P,q,True,5))))
    collision={'old_key_equal':old.state_key(b1,r1)==old.state_key(b2,r1),
               'exact_key_equal':full_lf_state_fingerprint(g,b1,r1,5,GRIDS['3'])==full_lf_state_fingerprint(g,b2,r1,5,GRIDS['3']),
               'payoff_difference':diff,'old_key':old.state_key(b1,r1)}
    (OUT/'cache_collision.json').write_text(json.dumps(collision,indent=2));print(collision,flush=True)
    # Cold Grid-5 controls benchmark; each full finite best response certified.
    rows=[]
    for geom in ('head_on','parallel','crossing'):
        t0=time.perf_counter();g=make_lf_game(KD,geom,1.,1.,6);b,r=initial_states(g)
        sol=RemainingHorizonGame(g,b,r,6,GRIDS['5']).solve()
        row={k:v for k,v in sol.items() if k not in ('x','y')};row['geometry']=geom;row['seconds']=time.perf_counter()-t0
        rows.append(row);print({k:row[k] for k in ('geometry','V','gap','iteration','status','seconds')},flush=True)
        (OUT/'initial_grid5_controls.json').write_text(json.dumps(rows,indent=2))
    assert summary['pass']
    assert collision['old_key_equal'] and not collision['exact_key_equal'] and diff>1e-8
    assert all(r['converged'] for r in rows)

if __name__=='__main__':main()
