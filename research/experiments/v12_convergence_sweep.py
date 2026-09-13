"""Predeclared 4 tolerances x 5 caps on all three controls; failed episodes retained."""
import sys,json
from pathlib import Path
from research.experiments.v12_controls import control
geo=sys.argv[1]
for tol in (.05,.02,.01,.005):
    for cap in (15,30,60,120,200):
        tag=f'sweep_tol{tol:g}_cap{cap}'
        p=Path(f'research/final_v12/audit/{tag}_{geo}_summary.json')
        if p.exists():continue
        try:control(geo,8,'exact_history',True,cap,tol,tag,cadences=(1,6))
        except Exception as e:
            p.write_text(json.dumps({'geometry':geo,'tol':tol,'cap':cap,'status':'AUDIT_EXCEPTION','error':repr(e)},indent=2))
            raise
