"""One bounded auxiliary worker at a time; same 8 GiB process-tree policy."""
import os
import signal
import subprocess
import sys
import time
from research.experiments.v14_run import rss_tree


def bounded(module,arguments,wall_limit,log):
    env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',VECLIB_MAXIMUM_THREADS='1')
    start=time.perf_counter();peak=0;reason='completed'
    log.parent.mkdir(parents=True,exist_ok=True)
    with log.open('a') as f:
        p=subprocess.Popen([sys.executable,'-u','-m',module,*arguments],stdout=f,stderr=f,
                           env=env,start_new_session=True)
        while p.poll() is None:
            peak=max(peak,rss_tree(p.pid))
            if peak>8*1024**3:reason='memory_limit'
            elif time.perf_counter()-start>wall_limit:reason='wall_limit'
            if reason!='completed':
                os.killpg(p.pid,signal.SIGTERM)
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
                break
            time.sleep(1.)
    if p.returncode and reason=='completed':reason='worker_error'
    return {'reason':reason,'returncode':p.returncode,'wall_seconds':time.perf_counter()-start,
            'tree_peak_rss_bytes':peak,'wall_limit_seconds':wall_limit,'memory_limit_bytes':8*1024**3}
