#!/usr/bin/env python3
"""Verify the final v13 experiment packet, or recompute only its frozen analyses."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',nargs='?',default='verify',choices=['verify','analyze'])
    a=p.parse_args();os.chdir(ROOT)
    manifest=ROOT/'research/final_v13/FINAL_MANIFEST.json'
    if not manifest.exists():raise SystemExit('Final packet manifest has not yet been issued.')
    d=json.loads(manifest.read_text());bad=[]
    for name,want in d['sha256'].items():
        f=ROOT/name
        if not f.exists() or hashlib.sha256(f.read_bytes()).hexdigest()!=want:bad.append(name)
    if bad:raise SystemExit('Checksum mismatch: '+', '.join(bad))
    print(f"Verified {len(d['sha256'])} final packet checksums.",flush=True)
    if a.action=='analyze':
        for module in ['research.experiments.v13_analysis','research.experiments.v13_audit']:
            subprocess.run([sys.executable,'-m',module],check=True)
    gate=json.loads((ROOT/'research/final_v13/analysis/GATE_DATA.json').read_text())
    print(json.dumps({'gate':gate['pre_refinement_verdict'],'positive':gate['n_positive'],
      'denominator':gate['n_primary'],'refinement_allowed':gate['refinement_allowed'],
      'manuscript_writing_authorized':False},ensure_ascii=False,indent=2))
    print('No new experiments or manuscript writing were triggered.')
if __name__=='__main__':main()
