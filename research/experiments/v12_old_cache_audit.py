"""Legacy-cache ablation failures are data; never suppress skew-check failures."""
import json,traceback
from pathlib import Path
from research.experiments.v12_controls import control
for geo in ('head_on','parallel','crossing'):
    try:control(geo,8,'old_pose_key',True,200,.005,'old_cache_spatial')
    except Exception as e:
        result={'geometry':geo,'status':'CACHE_ABLATION_ABORTED','error':repr(e),'traceback':traceback.format_exc(),
                'C6':None,'reason':'contaminated payoff arrays must not be projected, silently solved, or included in statistics'}
        Path(f'research/final_v12/audit/old_cache_spatial_{geo}_failure.json').write_text(json.dumps(result,indent=2));print(result,flush=True)
