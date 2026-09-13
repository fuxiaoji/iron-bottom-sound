"""Read-only audits of complete experimental artifacts; no new scientific cells."""
import csv,hashlib,json
from pathlib import Path
import numpy as np
from research.experiments.v13_exact import CORE

R=Path('research/final_v13');OLD=R/'pre_boundary_amendment'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def csvout(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def source_tables():
    rows=[]
    for phase in ['discovery','confirmatory']:
        for d in read(R/'mechanism'/phase/'all_results.json'):
            for s in d['summary']:
                theta=[e['Theta'] for e in d['episodes'] if e['alpha']==s['alpha'] and e['n_defined']]
                rows.append({'phase':phase,'geometry':d['geometry'],'speed':d['focal_speed_ratio'],**s,
                  'Theta_probe_q25':float(np.quantile(theta,.25)),'Theta_probe_q75':float(np.quantile(theta,.75))})
    csvout(R/'analysis/mechanism_summary.csv',rows)
    data=read(R/'capability/all_results.json')
    csvout(R/'analysis/capability_interactions.csv',[r for d in data for r in d['interactions']])
    vals=[]
    for d in data:
        for level in ['low','high']:
            for side in ['blue','red']:
                c=d['four_values'][level][side]
                for k,v in c['values'].items():vals.append({'geometry':d['geometry'],'capability':level,'focal':side,'structure':k,'V':v['V'],'LB':v['LB'],'UB':v['UB']})
    csvout(R/'analysis/capability_four_values.csv',vals)

def audit():
    stats={};allvalues=[];allflex=[]
    for phase,n in [('discovery',15),('confirmatory',12)]:
        data=read(R/phase/'all_results.json');assert len(data)==n
        for r in data:
            for side in ['blue','red_mirror']:
                d=r[side];assert d['complete']
                assert d['config']['opponent_speed_ratio']==d['config']['range_ratio']==1.
                assert d['config']['source_hashes']=={s:sha(s) for s in CORE}
                allvalues.extend(d['values'].values());allflex.extend(f['F'] for f in d['conditional_flexibility'].values())
            assert r['mirror_payoff_error']<=1e-8
        stats[phase]={'physical_cells':n,'independent_mirror_cells':n,
          'max_payoff_mirror_error':max(r['mirror_payoff_error'] for r in data),
          'max_value_mirror_error':max(r['mirror_value_error'] for r in data),
          'max_flexibility_mirror_error':max(r['mirror_flexibility_error'] for r in data)}
    stats['all_main_values']={'count':len(allvalues),'max_interval_width':max(v['UB']-v['LB'] for v in allvalues),
       'max_flow_residual':max(max(v.get('flow_residual_B',0),v.get('flow_residual_R',0)) for v in allvalues),
       'max_inequality_violation':max(v.get('inequality_violation',0) for v in allvalues),'min_flexibility':min(allflex)}
    assert min(allflex)>=-1e-6
    stats['mechanism']={}
    for phase,n in [('discovery',15),('confirmatory',12)]:
        data=read(R/'mechanism'/phase/'all_results.json');assert len(data)==n
        rows=[s for d in data for s in d['summary']]
        assert all(d['implementation_hashes']['research/formation/payoff_v13.py']==sha('research/formation/payoff_v13.py') for d in data)
        stats['mechanism'][phase]={'cells':len(data),'probe_episodes':sum(d['n_probes'] for d in data),
          'epoch_alpha_rows':sum(s['n_epochs'] for s in rows),'defined_epoch_alpha_rows':sum(s['n_defined'] for s in rows),
          'min_negative_correction_fraction':min(s['negative_correction_fraction'] for s in rows),
          'max_negative_correction_fraction':max(s['negative_correction_fraction'] for s in rows),
          'min_outside_domain_fraction':min(s['outside_domain_fraction'] for s in rows),
          'max_outside_domain_fraction':max(s['outside_domain_fraction'] for s in rows),
          'min_zero_drift_fraction':min(s['zero_drift_fraction'] for s in rows),
          'max_zero_drift_fraction':max(s['zero_drift_fraction'] for s in rows)}
    caps=read(R/'capability/all_results.json');assert len(caps)==3
    cr=[r for d in caps for r in d['interactions']]
    stats['capability']={'n':6,'positive':sum(r['LB']>1e-5 for r in cr),'reversal':sum(r['UB'] < -1e-5 for r in cr),
      'max_nested_payoff_error':max(r['nested_payoff_error'] for r in cr),
      'max_mirror_payoff_error':max(d['four_values'][k]['mirror_payoff_error'] for d in caps for k in ['low','high']),
      'max_interval_width':max(r['UB']-r['LB'] for r in cr)}
    # All frozen copies and the old failed outputs must remain byte-for-byte intact.
    stats['freezes']={}
    for f,key in [(R/'v12_freeze/FREEZE_MANIFEST.json','frozen_files'),(OLD/'ARCHIVE_MANIFEST.json','files'),(R/'RERUN_FREEZE.json','source_hashes')]:
        hashes=read(f)[key];bad=[p for p,h in hashes.items() if not Path(p).exists() or sha(p)!=h]
        stats['freezes'][str(f)]={'n':len(hashes),'mismatches':bad}
        assert not bad,(str(f),bad)
    # Verify the frozen original design against its original immutable checksum.
    assert sha(R/'confirmatory_design/CONFIRMATORY_DESIGN.md')==read(R/'confirmatory_design/FREEZE.json')['design_sha256']
    protected=[]
    for p in (R/'v12_freeze/code').rglob('*'):
        if p.is_file():
            live=Path(p.relative_to(R/'v12_freeze/code'));assert live.exists() and sha(live)==sha(p),str(live)
            protected.append(str(live))
    for dirname in ['paper_v11','paper_v12']:
        for p in (Path('manuscript_q2_frozen')/dirname).rglob('*'):
            if p.is_file():
                live=Path(p.relative_to('manuscript_q2_frozen'));assert live.exists() and sha(live)==sha(p),str(live)
                protected.append(str(live))
    stats['protected_live_v12_and_manuscript_files']={'n':len(protected),'mismatches':[]}
    (R/'analysis').mkdir(exist_ok=True);dump(R/'analysis/NUMERICAL_AUDIT.json',stats)
    return stats

def amendment_comparison():
    rows=[];payoff=[]
    for phase in ['discovery','confirmatory','capability']:
        for p in sorted((OLD/phase).glob('*.json')):
            old=read(p)
            if not isinstance(old,dict) or 'values' not in old:continue
            q=R/phase/p.name;new=read(q)
            for s,v in old['values'].items():
                a=v['V'];b=new['values'][s]['V'];rows.append({'phase':phase,'cell':p.stem,'metric':s,'old':a,'amended':b,'difference':b-a})
        for p in sorted((OLD/phase).glob('*_payoff.npz')):
            q=R/phase/p.name;A=np.load(p)['A'];B=np.load(q)['A'];delta=abs(B-A)
            payoff.append({'phase':phase,'cell':p.stem,'entries':int(A.size),'changed_above_1e_8':int(np.count_nonzero(delta>1e-8)),'max_difference':float(delta.max())})
    for phase in ['discovery','confirmatory']:
        for p in sorted((OLD/'mechanism'/phase).glob('*.json')):
            old=read(p)
            if not isinstance(old,dict) or 'summary' not in old:continue
            new=read(R/'mechanism'/phase/p.name)
            for a,b in zip(old['summary'],new['summary']):
                for k in ['Theta','R_raw','directed_drift','centroid_drift','hausdorff','raw_ratio']:
                    if a[k] is not None and b[k] is not None:rows.append({'phase':'mechanism_'+phase,'cell':p.stem,'metric':f'{k}_alpha{a["alpha"]}','old':a[k],'amended':b[k],'difference':b[k]-a[k]})
    for name,rs in [('AMENDMENT_COMPARISON',rows),('AMENDMENT_PAYOFF_COMPARISON',payoff)]:
        with (R/'analysis'/f'{name}.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
    result={'comparison_rows':len(rows),'payoff_matrices_compared':len(payoff),'changed_matrices':sum(r['changed_above_1e_8']>0 for r in payoff),
      'max_payoff_change':max(r['max_difference'] for r in payoff),'max_value_change':max(abs(r['difference']) for r in rows if not r['phase'].startswith('mechanism')),
      'max_Theta_change':max(abs(r['difference']) for r in rows if r['metric'].startswith('Theta')),
      'changed_value_rows_above_1e_8':[r for r in rows if not r['phase'].startswith('mechanism') and abs(r['difference'])>1e-8],
      'scope':'Compare all available pre-amendment outputs, including failed original confirmation. Original parallel speeds .90/1.10/1.25 were never computed; no old result is imputed.'}
    dump(R/'analysis/AMENDMENT_AUDIT.json',result)
    return result

def main():
    a=audit();b=amendment_comparison();source_tables();print(json.dumps({'main':a['all_main_values'],'capability':a['capability'],'amendment':{k:b[k] for k in ['max_payoff_change','max_value_change','max_Theta_change','changed_matrices']}},indent=2))
if __name__=='__main__':main()
