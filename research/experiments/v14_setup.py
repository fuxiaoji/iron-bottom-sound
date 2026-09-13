"""Freeze approved design before any v14 physical experiment."""
import hashlib,json,platform,subprocess,sys
from pathlib import Path
from datetime import datetime,timezone

ROOT=Path('research/final_v14')
GEO=('head_on','parallel','crossing')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,data):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    temp=p.with_suffix(p.suffix+'.tmp');temp.write_text(json.dumps(data,indent=2,ensure_ascii=False));temp.replace(p)
def designs():
    cells={}
    def add(phase,g,s,d,T,grid=3,ablation='none'):
        key=f'{g}_v{s:g}_d{d:g}_T{T}_G{grid}_{ablation}'
        c=cells.setdefault(key,{'id':key,'geometry':g,'speed':s,'distance':d,'T':T,
                              'grid':grid,'ablation':ablation,'phases':[]})
        c['phases'].append(phase)
    for g in GEO:
        for s in [.85,1.,1.15]:add('development',g,s,16.,6)
        for s,d in zip([.8,.95,1.05,1.2],[13.5,15.,17.,18.5]):add('test',g,s,d,6)
        for T in [4,5,6,7]:add('robustness',g,1.,16.,T)
        for grid in [5,7]:add('robustness',g,1.,16.,4,grid)
        for ablation in ['isotropic','terminal','rigid']:add('ablation',g,1.,16.,4,3,ablation)
    for c in cells.values():
        c['mirror_solve_all']=((c['speed']==1 and c['distance']==16 and c['T']==6 and c['grid']==3)
                               or ('test' in c['phases'] and c['speed']==.8))
        c['opponents']=['F','C']
    return list(cells.values())

def main():
    ROOT.mkdir(exist_ok=True)
    design={'created_utc':datetime.now(timezone.utc).isoformat(),'cells':designs(),
            'main_plan_sha256':sha(ROOT/'MASTER_PLAN.md'),'main_opponents':['F','C'],
            'value_tolerance_scale':1e-6,'numeric_padding_scale':1e-8,
            'ordinary_wall_seconds':1200,'instance_wall_seconds':21600,
            'process_tree_memory_bytes':8*1024**3,'heavy_workers':1,
            'default_model':{'opponent_speed':6,'range_B':1,'range_R':1,'gamma':1,
            'formation':'leader_follower','ships':3,'spacing':2,'n_sub':6,'turn_bound_deg':60,
            'payoff':'causal endpoint trapezoid; frozen v13 boundary completion',
            'kernel_target_speed':'fixed input 6 clipped by wrapper to 5'},
            'ablation_scope':'T4 Grid3; one factor at a time',
            'test_interpretation':'fixed computational benchmark, not speed causal identification'}
    p=ROOT/'DESIGN.json'
    if p.exists():raise RuntimeError('design already frozen; do not overwrite')
    save(p,design)
    protected={}
    old=json.loads(Path('research/final_v13/FINAL_MANIFEST.json').read_text())
    # Keep a direct read-only hash inventory rather than altering old manifests.
    for root in ['research/final_v12','research/final_v13','manuscript_q2_frozen','paper_v11','paper_v12']:
        for f in sorted(Path(root).rglob('*')):
            if f.is_file():protected[str(f)]=sha(f)
    save(ROOT/'HISTORICAL_FREEZE.json',{'files':protected,'baseline':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()})
    core=['research/formation/schedule_v14.py','research/formation/pricing_v14.py','research/formation/physical_v14.py',
          'research/formation/commitment_v12.py','research/formation/payoff_v13.py','research/formation/path_following.py',
          'research/formation/matched_horizon.py','research/formation/exact_v12.py','research/formation/sequence_v12.py',
          'research/results/e01/kernel_fits.json']
    save(ROOT/'PILOT_FREEZE.json',{'files':{s:sha(s) for s in core},'design_sha256':sha(p)})
    import numpy,scipy,matplotlib,pytest
    save(ROOT/'ENVIRONMENT.json',{'python':sys.version,'executable':sys.executable,'platform':platform.platform(),
          'numpy':numpy.__version__,'scipy':scipy.__version__,'matplotlib':matplotlib.__version__,'pytest':pytest.__version__})
    src=Path('research/final_v12/skills/PROVENANCE.json')
    save(ROOT/'SKILLS_PROVENANCE.json',json.loads(src.read_text()))
    print('Frozen',len(design['cells']),'physical configurations;',len(protected),'historical files')

if __name__=='__main__':main()
