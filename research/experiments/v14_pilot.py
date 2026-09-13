"""Engineering pilot on already observed v13 head-on speed-one instance."""
import json,time,resource
from pathlib import Path
from research.formation.physical_v14 import matrix
from research.formation.schedule_v14 import solve,decompose
from research.formation.pricing_v14 import column_generation
from research.experiments.v14_setup import ROOT,sha,save

def main():
    freeze=json.loads((ROOT/'PILOT_FREEZE.json').read_text())
    for p,h in freeze['files'].items():
        if sha(p)!=h:raise RuntimeError('pilot freeze mismatch '+p)
    c={'geometry':'head_on','speed':1.,'distance':16.,'T':6,'grid':3,'ablation':'none'}
    A=matrix(c); records=[]
    old=json.loads(Path('research/final_v13/discovery/head_on_1_blue.json').read_text())
    for S in [(),(2,4),tuple(range(1,6))]:
        for opponent in ['C','F']:
            start=time.perf_counter()
            r=(column_generation(A,3,6,S) if opponent=='C' else decompose(A,3,6,S,tuple(range(1,6)),pricing=True))
            r.update(opponent=opponent,process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
            key=('F' if len(S)==5 else 'C')+opponent
            if S in [(),tuple(range(1,6))]:
                r['legacy_reference']=old['values'][key]['V']
                if not r['LB']-1e-7<=r['legacy_reference']<=r['UB']+1e-7:raise RuntimeError('endpoint mismatch')
            records.append(r);save(ROOT/'pilot/results.json',records)
            print(S,opponent,round(r['V'],9),r['status'],round(time.perf_counter()-start,2),flush=True)
    print('pilot complete',flush=True)

if __name__=='__main__':main()
