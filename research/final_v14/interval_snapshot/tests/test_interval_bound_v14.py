import itertools
import numpy as np
from research.formation.interval_bound_v14 import interval_certificates,shortest_calendars
from research.formation.schedule_v14 import schedules,solve


def test_interval_loss_bounds_every_binary_calendar():
    A=np.random.default_rng(1492).normal(size=(8,8));T=3
    cert=interval_certificates(A,2,T)
    vf=solve(A,2,T,(1,2),'F');edges={(r['t'],r['end']):r['loss_UB'] for r in cert['edges']}
    for s in schedules(T):
        value=solve(A,2,T,s,'F');bounds=(0,)+s+(T,)
        loss=sum(edges[t,e] for t,e in zip(bounds[:-1],bounds[1:]))
        assert vf['LB']-value['UB']<=loss+1e-8
    front=shortest_calendars(cert)
    for row in front:
        candidates=[]
        for s in schedules(T):
            if len(s)>row['K']:continue
            b=(0,)+s+(T,);candidates.append(sum(edges[t,e] for t,e in zip(b[:-1],b[1:])))
        assert abs(row['loss_UB']-min(candidates))<1e-12
    assert front[-1]['loss_UB']==0


def test_shortest_path_uses_at_most_budget_without_triangle_assumption():
    cert={'T':4,'V_full_LB':0,'V_full_UB':0,'edges':[
        {'t':t,'end':e,'loss_UB':1 if (t,e)==(0,4) else 10}
        for t in range(4) for e in range(t+1,5)]}
    front=shortest_calendars(cert)
    assert [r['S'] for r in front]==[[],[],[],[]]
    assert all(r['loss_UB']==1 for r in front)
