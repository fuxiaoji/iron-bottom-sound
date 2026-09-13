"""Fixed-opponent operating-speed x adaptation factorial; independent mirrors."""
from __future__ import annotations
import argparse,csv,hashlib,json,time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from research.formation.path_following import make_lf_game
from research.formation.exact_v12 import terminal_payoff_matrix,backward_induction
from research.formation.sequence_v12 import solve_sequence_form

ROOT=Path('research/final_v13');GEO=('head_on','parallel','crossing')
KD=json.loads(Path('research/results/e01/kernel_fits.json').read_text())['CA']
CORE=['research/formation/commitment_v12.py','research/formation/exact_v12.py',
      'research/formation/sequence_v12.py','research/formation/matched_horizon.py',
      'research/formation/path_following.py','research/results/e01/kernel_fits.json']

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,d):
    tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(d,indent=2));tmp.replace(p)

def game(geo,speed,mirror=False,T=6,formation='leader_follower'):
    g=make_lf_game(KD,geo,1.,1.,T,formation_mode=formation)
    g.vB=6. if mirror else 6.*speed;g.vR=6.*speed if mirror else 6.;g.gamma=1.
    return g

def differences(vals,mirror=False):
    pairs={'F':('FC','FF'),'C':('CC','CF')} if mirror else {'F':('FF','CF'),'C':('FC','CC')}
    out={}
    for k,(a,b) in pairs.items():
        out[k]={'F':vals[a]['V']-vals[b]['V'],'LB':vals[a]['LB']-vals[b]['UB'],'UB':vals[a]['UB']-vals[b]['LB']}
        if out[k]['F'] < -1e-6:raise RuntimeError('FLEXIBILITY_NONNEGATIVITY_FAILED')
    return out

def cell(phase,geo,speed,mirror):
    out=ROOT/phase;out.mkdir(exist_ok=True)
    name=f"{geo}_{speed:g}_{'red' if mirror else 'blue'}";p=out/f'{name}.json';cache=out/f'{name}_payoff.npz'
    config={'phase':phase,'geometry':geo,'focal_player':'Red' if mirror else 'Blue','focal_speed_ratio':speed,
            'opponent_speed_ratio':1.,'range_ratio':1.,'T':6,'grid':3,'turn_bound_deg':60.,
            'speed_semantics':'forced operating speed','formation':'leader_follower',
            'scientific_cache':'complete_configuration_terminal_matrix','source_hashes':{s:digest(s) for s in CORE},
            'discovery_protocol_sha256':digest(ROOT/'DISCOVERY_PROTOCOL.md')}
    if phase=='confirmatory':config['confirmatory_design_sha256']=digest(ROOT/'confirmatory_design/CONFIRMATORY_DESIGN.md')
    if p.exists():
        d=json.loads(p.read_text())
        if d['config']!=config:raise RuntimeError('frozen result configuration mismatch')
        if d.get('complete'):return d
    else:d={'config':config,'values':{},'complete':False}
    start=time.time()
    if cache.exists():A=np.load(cache)['A']
    else:
        A=terminal_payoff_matrix(game(geo,speed,mirror));np.savez_compressed(cache,A=A)
    d['payoff_sha256']=digest(cache)
    for structure in ('FF','CC','FC','CF'):
        if structure in d['values']:continue
        t=time.time()
        v=backward_induction(A,3,6,1 if structure=='FF' else 6) if structure in ('FF','CC') else solve_sequence_form(A,3,6,structure)
        v['seconds']=time.time()-t
        residual=v.get('gap',v.get('numeric_error_budget',0.))
        if residual>1e-6:raise RuntimeError(f'SCIENTIFIC_GAP_FAILED {residual}')
        d['values'][structure]=v;write(p,d)
        print(phase,name,structure,round(v['V'],8),round(v['seconds'],1),'s',flush=True)
    d['conditional_flexibility']=differences(d['values'],mirror)
    d['additional_seconds']=time.time()-start;d['complete']=True;write(p,d);return d

def geometry_job(args):
    phase,geo,speeds=args;rows=[]
    for speed in speeds:
        b=cell(phase,geo,speed,False);r=cell(phase,geo,speed,True)
        A=np.load(ROOT/phase/f'{geo}_{speed:g}_blue_payoff.npz')['A']
        B=np.load(ROOT/phase/f'{geo}_{speed:g}_red_payoff.npz')['A']
        expected=-A.T
        if geo=='parallel':expected=expected[::-1,::-1]
        pe=float(np.max(abs(B-expected)));ve=0.;fe=0.
        for xy in ('FF','FC','CF','CC'):
            vb=b['values'][xy];vr=r['values'][xy[::-1]]
            err=abs(vb['V']+vr['V']);ve=max(ve,err)
            budget=(vb['UB']-vb['LB'])+(vr['UB']-vr['LB'])+1e-7
            if err>budget:raise RuntimeError('MIRROR_VALUE_FAILED')
        for k in ('F','C'):fe=max(fe,abs(b['conditional_flexibility'][k]['F']-r['conditional_flexibility'][k]['F']))
        if pe>1e-8 or fe>2e-6:raise RuntimeError('MIRROR_PAYOFF_OR_FLEXIBILITY_FAILED')
        row={'geometry':geo,'focal_speed_ratio':speed,'blue':b,'red_mirror':r,
             'mirror_payoff_error':pe,'mirror_value_error':ve,'mirror_flexibility_error':fe}
        rows.append(row);write(ROOT/phase/f'{geo}_paired.json',rows)
    return rows

def main():
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['discovery','confirmatory'],required=True);p.add_argument('--workers',type=int,default=3);a=p.parse_args()
    if a.phase=='discovery':speeds=[.70,.85,1.,1.15,1.30]
    else:
        design=ROOT/'confirmatory_design/CONFIRMATORY_DESIGN.md'
        hashes=json.loads((ROOT/'confirmatory_design/FREEZE.json').read_text())
        if digest(design)!=hashes['design_sha256']:raise RuntimeError('confirmatory design changed')
        speeds=[.75,.90,1.10,1.25]
    (ROOT/a.phase).mkdir(exist_ok=True)
    with ProcessPoolExecutor(max_workers=a.workers) as pool:blocks=list(pool.map(geometry_job,[(a.phase,g,speeds) for g in GEO]))
    rows=[r for block in blocks for r in block];write(ROOT/a.phase/'all_results.json',rows)
    fields=['geometry','focal_speed_ratio','opponent_speed_ratio','V_FF','V_FC','V_CF','V_CC','F_blue_given_red_F','F_blue_given_red_C','mirror_value_error','exact']
    with (ROOT/a.phase/'four_values.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in rows:
            b=r['blue'];w.writerow({'geometry':r['geometry'],'focal_speed_ratio':r['focal_speed_ratio'],'opponent_speed_ratio':1.,
             **{f'V_{s}':b['values'][s]['V'] for s in ('FF','FC','CF','CC')},
             **{f'F_blue_given_red_{k}':b['conditional_flexibility'][k]['F'] for k in ('F','C')},
             'mirror_value_error':r['mirror_value_error'],'exact':'complete finite game to numerical LP precision'})
    print(a.phase,'complete',len(rows),'focal cells plus independent mirrors',flush=True)

if __name__=='__main__':main()
