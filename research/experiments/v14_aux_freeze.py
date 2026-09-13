"""Pin supplemental algorithms before their held-out evaluation."""
import json
import shutil
from pathlib import Path
from research.experiments.v14_setup import ROOT,sha,save
from research.experiments.v14_run import stamp

FILES=[
 'research/formation/frontier_v14.py','research/formation/policy_v14.py','research/formation/recovery_v14.py',
 'research/experiments/v14_resources.py','research/experiments/v14_resume.py',
 'research/experiments/v14_benchmark.py','research/experiments/v14_inner_benchmark.py',
 'research/experiments/v14_certificates.py','research/experiments/v14_aux_freeze.py',
 'research/final_v14/BENCHMARK_PROTOCOL.md',
 'tests/test_frontier_v14.py','tests/test_policy_v14.py','tests/test_recovery_v14.py','tests/test_workflow_v14.py']


def check():
    meta=json.loads((ROOT/'AUXILIARY_FREEZE.json').read_text())
    bad=[p for p,h in meta['source_hashes'].items() if sha(p)!=h]
    if bad:raise RuntimeError('auxiliary algorithm freeze mismatch: '+str(bad))


def main():
    dest=ROOT/'AUXILIARY_FREEZE.json'
    if dest.exists():check();return
    design=json.loads((ROOT/'DESIGN.json').read_text())
    viewed_test=[str(p) for c in design['cells'] if 'test' in c['phases'] for p in (ROOT/'runs'/c['id']).glob('*_S*.json')]
    if viewed_test:raise RuntimeError('cannot label an initial algorithm freeze before already present test outputs')
    hashes={p:sha(p) for p in FILES}
    for source in FILES:
        target=ROOT/'auxiliary_snapshot'/source;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,target)
    save(dest,{'created_utc':stamp(),'design_sha256':sha(ROOT/'DESIGN.json'),
          'source_hashes':hashes,'test_outputs_present':viewed_test,
          'scope':'auxiliary method and construction freeze; primary value solver separately frozen in RUN_FREEZE.json'})


if __name__=='__main__':main()
