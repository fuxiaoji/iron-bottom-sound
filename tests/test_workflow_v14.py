import json
import numpy as np
from research.experiments.v14_resume import strengthen
from research.experiments.v14_certificates import replay
from research.formation.physical_v14 import matrix
from research.formation.recovery_v14 import full_update_policies


def test_inclusion_strengthening_preserves_validity():
    records={():{'LB':-1.,'UB':1.},(1,):{'LB':-8.,'UB':8.},(2,):{'LB':2.,'UB':4.},(1,2):{'LB':5.,'UB':7.}}
    out=strengthen(records)
    assert out[(1,)]['LB']==-1 and out[(1,)]['UB']==7
    assert out[(2,)]['LB']==2 and out[()]['UB']==1


def test_replay_complete_law_and_physical_value(tmp_path):
    c={'id':'micro_replay_only','geometry':'crossing','speed':1.,'distance':16.,'T':2,'grid':3,'ablation':'none'}
    A=matrix(c);r,p=full_update_policies(A,3,2)
    for k in ['F','C']:
        got=replay(c,k,(1,),A,p,tmp_path/k)
        assert abs(got['probability_sum']-1)<1e-9
        assert 0<got['representative_probability']<=1
        if k=='F':assert r['LB']<=got['expected_payoff_all_leaves']<=r['UB']
        assert json.loads((tmp_path/k).with_suffix('.json').read_text())['opponent']==k
