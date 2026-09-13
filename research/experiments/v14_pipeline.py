"""Serial continuation of the already approved fixed v14 experiment phases.

This is a local foreground research runner, not a scheduled automation. It
stops on an implementation error; scientific negative results do not change
the frozen design. It never submits a manuscript or creates external tasks.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from research.experiments.v14_setup import ROOT,save,sha
from research.experiments.v14_run import stamp,core_hashes
from research.experiments.v14_aux_freeze import check


def verify():
    check()
    frozen=json.loads((ROOT/'RUN_FREEZE.json').read_text())
    if frozen!={'core_hashes':core_hashes(),'design_sha256':sha(ROOT/'DESIGN.json')}:
        raise RuntimeError('primary solver freeze mismatch')
    deps=json.loads((ROOT/'DEPENDENCY_FREEZE.json').read_text())
    # Dependency manifest shape is deliberately checked rather than inferred.
    hashes=deps.get('source_hashes',deps.get('files',deps.get('hashes',{})))
    if isinstance(hashes,dict):
        for p,h in hashes.items():
            if isinstance(h,str) and Path(p).is_file() and sha(p)!=h:
                raise RuntimeError('imported dependency changed: '+p)


def main():
    p=argparse.ArgumentParser();p.add_argument('--wait-development-pid',type=int);a=p.parse_args()
    if a.wait_development_pid:
        save(ROOT/'PIPELINE_PROGRESS.json',{'stage':'await_existing_development','pid':a.wait_development_pid,'updated_utc':stamp()})
        while not (ROOT/'DEVELOPMENT_RUN_COMPLETE.json').exists():
            try:os.kill(a.wait_development_pid,0)
            except ProcessLookupError:raise RuntimeError('existing development runner stopped without completion marker')
            time.sleep(10)
    stages=[]
    if not (ROOT/'DEVELOPMENT_RUN_COMPLETE.json').exists():stages.append(('development','v14_run',['--phase','development']))
    for phase in ['development','test','robustness','ablation']:
        if phase!='development':stages.append((phase,'v14_run',['--phase',phase]))
        stages.extend([(phase+'_continuation','v14_resume',['--phase',phase]),
                       (phase+'_analysis','v14_analysis',[])])
        if phase in ['development','test']:
            stages.extend([(phase+'_certificates','v14_certificates',['--phase',phase]),
                           (phase+'_interval_bounds','v14_interval_experiment',['--phase',phase]),
                           (phase+'_cold_benchmarks','v14_benchmark',['--mode','cold','--phase',phase]),
                           (phase+'_trace_benchmarks','v14_benchmark',['--mode','trace','--phase',phase])])
    stages.extend([('interval_controls','v14_interval_experiment',['--phase','controls']),
                   ('inner_benchmarks','v14_inner_benchmark',[]),('final_analysis','v14_analysis',[])])
    env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',VECLIB_MAXIMUM_THREADS='1')
    done=ROOT/'pipeline_stages';done.mkdir(exist_ok=True)
    for stage,module,args in stages:
        if (done/(stage+'.json')).exists():continue
        verify();start=time.perf_counter()
        save(ROOT/'PIPELINE_PROGRESS.json',{'stage':stage,'module':module,'arguments':args,'updated_utc':stamp()})
        print('START',stage,stamp(),flush=True)
        with (ROOT/(stage+'_pipeline.log')).open('a') as log:
            r=subprocess.run([sys.executable,'-u','-m','research.experiments.'+module,*args],stdout=log,stderr=log,env=env)
        record={'stage':stage,'returncode':r.returncode,'wall_seconds':time.perf_counter()-start,'finished_utc':stamp()}
        if r.returncode:
            save(ROOT/'PIPELINE_ERROR.json',record);raise RuntimeError('stage failed: '+stage)
        save(done/(stage+'.json'),record);print('FINISH',stage,stamp(),flush=True)
    save(ROOT/'EXPERIMENT_PIPELINE_COMPLETE.json',{'finished_utc':stamp(),'scope':'fixed experimental stages completed or explicitly resource-limited; manuscript and final review are separate tasks'})


if __name__=='__main__':main()
