"""Standardized seeded probes; discovery/confirmatory field diagnostics only."""
import argparse,hashlib,json,time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
from research.experiments.v13_exact import game,write,digest
from research.formation.commitment_v12 import initial_states
from research.formation.tracking_v13 import domain,epoch_metrics

ROOT=Path('research/final_v13');GEO=('head_on','parallel','crossing')
METRICS=('Theta','Theta_centroid','Theta_hausdorff','R_raw','directed_drift','centroid_drift','hausdorff','raw_ratio','nonnegative_ratio','opponent_heading_change')

def job(args):
    phase,geo,speed=args;out=ROOT/'mechanism'/phase;out.mkdir(parents=True,exist_ok=True);p=out/f'{geo}_{speed:g}.json'
    ph=digest(ROOT/'MECHANISM_PROTOCOL.md')
    implementation={s:digest(s) for s in ('research/formation/tracking_v13.py','research/formation/payoff_v13.py','research/experiments/v13_mechanism.py')}
    if p.exists():
        data=json.loads(p.read_text())
        if data['protocol_sha256']!=ph:raise RuntimeError('mechanism protocol changed')
        if data.get('implementation_hashes')!=implementation:raise RuntimeError('mechanism implementation changed')
        return data
    g=game(geo,speed);Z=domain();allrows=[];episodes=[];start=time.time()
    for probe in range(32):
        rng=np.random.default_rng(2026091300+probe);choices=rng.choice([-60.,0.,60.],size=(2,6))
        b,r=initial_states(g);rs=[]
        for t in range(6):
            rn=r.clone();rn.extend_plan([choices[1,t]])
            metrics,illustration=epoch_metrics(g,b,r,rn,Z)
            for m in metrics:m.update(probe=probe,t=t);rs.append(m)
            if probe==0 and t==0:
                np.savez_compressed(out/f'illustration_{geo}_{speed:g}.npz',**illustration)
            b.extend_plan([choices[0,t]]);r=rn
        allrows.extend(rs)
        for alpha in (.9,.8):
            defined=[r for r in rs if r['alpha']==alpha and r['defined']]
            episodes.append({'probe':probe,'alpha':alpha,'n_defined':len(defined),
                **{k:float(np.median([r[k] for r in defined])) if defined else None for k in METRICS}})
    summary=[]
    for alpha in (.9,.8):
        rs=[r for r in allrows if r['alpha']==alpha];ds=[r for r in rs if r['defined']];es=[e for e in episodes if e['alpha']==alpha and e['n_defined']]
        summary.append({'alpha':alpha,'n_epochs':len(rs),'n_defined':len(ds),'n_episodes_defined':len(es),
           'negative_correction_fraction':float(np.mean([r['negative_correction'] for r in ds])) if ds else None,
           'zero_drift_fraction':float(np.mean([r['zero_drift'] for r in ds])) if ds else None,
           'outside_domain_fraction':float(np.mean([r['outside_domain_before'] for r in rs])),
           **{k:float(np.median([e[k] for e in es])) if es else None for k in METRICS}})
    data={'phase':phase,'geometry':geo,'focal_speed_ratio':speed,'opponent_speed_ratio':1.,'protocol_sha256':ph,
          'implementation_hashes':implementation,'implementation_amendment_sha256':digest(ROOT/'IMPLEMENTATION_AMENDMENT_01.md'),
          'n_probes':32,'field_domain_points':len(Z),'summary':summary,'episodes':episodes,'epochs':allrows,'seconds':time.time()-start,
          'scope':'standardized kinematic probe; not equilibrium policy evaluation or causal mediation'}
    write(p,data);print('mechanism',phase,geo,speed,summary[0]['Theta'],round(data['seconds'],1),'s',flush=True);return data

def main():
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['discovery','confirmatory'],required=True);p.add_argument('--workers',type=int,default=3);a=p.parse_args()
    frozen=json.loads((ROOT/'MECHANISM_FREEZE.json').read_text())
    if digest(ROOT/'MECHANISM_PROTOCOL.md')!=frozen['protocol_sha256']:raise RuntimeError('mechanism protocol changed')
    if a.phase=='confirmatory' and not (ROOT/'confirmatory_design/FREEZE.json').exists():raise RuntimeError('confirmatory design not frozen')
    speeds=[.7,.85,1.,1.15,1.3] if a.phase=='discovery' else [.75,.9,1.1,1.25]
    with ProcessPoolExecutor(max_workers=a.workers) as pool:rows=list(pool.map(job,[(a.phase,g,s) for g in GEO for s in speeds]))
    write(ROOT/'mechanism'/a.phase/'all_results.json',rows)
if __name__=='__main__':main()
