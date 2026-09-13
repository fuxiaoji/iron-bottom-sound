import numpy as np
from research.formation.schedule_v14 import schedules
from research.formation.frontier_v14 import branch_bound,enumerate_frontier,retention_budget


def test_search_with_complements_not_submodular():
    N=5
    def f(s):return sum(t in s for t in [1,4])+.1*len(s)+4*int({2,3}<=set(s))
    def oracle(s):v=f(s);return {'LB':v-1e-9,'UB':v+1e-9,'V':v}
    truth={s:oracle(s) for s in schedules(N)}
    for K in range(N):
        opt=max(v['V'] for s,v in truth.items() if len(s)<=K)
        for cheap in [None,lambda s:f(s)+1e-9]:
            r=branch_bound(N,K,oracle,1e-7,cheap)
            assert r['LB']<=opt<=r['UB']+1e-8
            assert abs(f(r['S'])-opt)<1e-7
            assert r['status']=='certified_numeric'


def test_retention_interval_ambiguity_is_not_hidden():
    f=[{'K':k,'S':[],'V':v,'LB':v-1e-4,'UB':v+1e-4} for k,v in enumerate([0,.9,1])]
    r=retention_budget(f,.9,1)
    assert r['K_possible']==1 and r['K_certified']==2 and r['status']=='unresolved'
    r=retention_budget(f,.89,1)
    assert r['K_possible']==r['K_certified']==1
