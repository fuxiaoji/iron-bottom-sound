"""Replay archived calibration arithmetic and record historical design overlap.

This does not regenerate engine ground truth, refit a kernel, or treat old
rule-grid rows as physical observations. Missing class labels are recovered
only by the explicitly archived exporter order and checked block sizes.
"""
import csv
import json
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
from research.experiments.v14_setup import ROOT,save,sha
from research.experiments.e01_fire_kernel import ATTACKERS,split_rows,sector_angle,metrics
from research.geometry.firepower_kernel import KernelFit


def calibration():
    old=Path('research/results/e01');data=list(csv.DictReader((old/'truth.csv').open()))
    for row in data:
        for key in ['distance','rel','attacker_heading','target_heading','target_speed']:row[key]=int(row[key])
        row['total']=float(row['total'])
    archived=json.loads((old/'metrics.json').read_text());fits=json.loads((old/'kernel_fits.json').read_text())
    offset=0;result={};records=[];pooled_truth=[];pooled_pred=[]
    for _,_,name in ATTACKERS:
        n=sum(archived['per_class'][name][part]['n'] for part in ['train','test'])
        rows=data[offset:offset+n];offset+=n;train,test=split_rows(rows)
        fit=KernelFit(**fits[name]);result[name]={}
        for label,block in [('train',train),('test',test)]:
            got=metrics(block,fit);ref=archived['per_class'][name][label]
            for key in ['n','spearman','nmae']:
                if abs(got[key]-ref[key])>1e-12:raise RuntimeError('archived calibration arithmetic failed')
            result[name][label]={k:v for k,v in got.items() if k!='p_value'}
        for row in test:
            pred=fit.expected_hits(row['distance'],sector_angle(row),row['target_speed'],row['target_aspect'])
            pooled_truth.append(row['total']);pooled_pred.append(pred)
            records.append({'class':name,'archived_truth':row['total'],'prediction':pred,
                            'distance':row['distance'],'sector':row['sector'],'target_speed':row['target_speed'],
                            'target_aspect':row['target_aspect']})
    if offset!=len(data):raise RuntimeError('archived row-class reconstruction is incomplete')
    out=ROOT/'foundations';out.mkdir(exist_ok=True)
    with (out/'calibration_test_rows.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    save(out/'CALIBRATION_REPLAY.json',{'per_class':result,'all_rows':len(data),
        'arithmetic_mean_class_test_spearman':float(np.mean([v['test']['spearman'] for v in result.values()])),
        'actual_concatenated_test_spearman':float(spearmanr(pooled_truth,pooled_pred).statistic),
        'class_reconstruction':'contiguous DD,CL,CA,BB blocks from archived exporter ATTACKERS order and recorded n_train+n_test; class absent in source CSV',
        'scope':'arithmetic replay of archived fit and rule-grid table, without refitting or engine regeneration; not real engagement data',
        'correction':'legacy pooled_spearman and pooled_nmae are arithmetic means of per-class metrics, not pooled estimates',
        'source_hashes':{str(p):sha(p) for p in [old/'truth.csv',old/'kernel_fits.json',old/'metrics.json',Path('research/experiments/e01_fire_kernel.py'),Path('research/geometry/firepower_kernel.py')]}})


def overlap():
    design=json.loads((ROOT/'DESIGN.json').read_text());old=[]
    for phase in ['discovery','confirmatory']:
        for p in sorted((Path('research/final_v13')/phase).glob('*_blue.json')):
            d=json.loads(p.read_text());cfg=d['config']
            old.append({'geometry':cfg['geometry'],'speed':cfg['focal_speed_ratio'],'distance':16.,
                        'T':cfg['T'],'grid':cfg['grid'],'source':str(p),'sha256':sha(p),
                        'distance_provenance':'v13_exact.game -> make_lf_game; explicit fixed r0=16 in frozen factory'})
    rows=[]
    for c in design['cells']:
        matches=[r['source'] for r in old if all(r[k]==c[k] for k in ['geometry','speed','distance','T','grid']) and c['ablation']=='none']
        rows.append({'cell':c['id'],'phases':c['phases'],'known_v13_physical_overlap':matches,
                     'result_exposure':'already inspected historical endpoint values' if matches else 'no matching v13 physical configuration found'})
    save(ROOT/'HISTORICAL_OVERLAP_AUDIT.json',{'design_sha256':sha(ROOT/'DESIGN.json'),'cells':rows,'historical_metadata':old,
        'v12_boundary':'v12 complete formation-game factory also fixes r0=16; its range_ratio changes the kernel range, not separation. Frozen-test distances13.5,15,17,18.5 differ.',
        'earlier_boundary':'searched experiment and formation Python sources for r0 assignments; standalone kernel grids are not complete trajectory games. Engine snapshot experiments have different action/horizon/model semantics.',
        'limitation':'local source/metadata audit, not a claim that all prior human exposure or undocumented external experiments are known; no prospective external validation claim',
        'timing':'audit written before any v14 test-phase result; development outputs have been viewed',
        'source_hashes':{p:sha(p) for p in ['research/experiments/v13_exact.py','research/formation/path_following.py']}})


if __name__=='__main__':calibration();overlap()
