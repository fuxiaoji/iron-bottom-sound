import numpy as np
from research.formation.schedule_v14 import solve,build_flow,payoff_matrix,best_response,schedules
from research.formation.pricing_v14 import column_generation
from research.formation.policy_v14 import conditional_flow,full_flow,coarsen_full_behavior,certify_coarsening


def test_mixture_to_flow_and_coarsening_responses():
    A=np.random.default_rng(1462).normal(size=(27,27));S=(1,2)
    r,pol=column_generation(A,3,3,S,return_strategies=True)
    F,x=full_flow(pol,3,3)
    for opponent in ['F','C']:
      for target in schedules(3):
        cert,(flow,tx,_)=certify_coarsening(A,r['UB'],pol,3,3,target,opponent)
        R=build_flow(3,3,3,(1,2) if opponent=='F' else ())
        P=payoff_matrix(A,flow,R)
        lo,_=best_response(P.T@tx,R)
        assert abs(cert['lower_value']+1e-8*max(1,np.max(abs(A)))-lo)<1e-7
        assert np.max(abs(flow.E@tx-flow.e))<1e-9
        if target==S:assert np.max(abs(conditional_flow(flow,tx)-conditional_flow(F,x)))<1e-8


def test_sequence_form_source_preserved_at_full_calendar():
    A=np.random.default_rng(1463).normal(size=(8,8))
    r,p,(B,R,P)=solve(A,2,3,(1,2),'C',return_strategies=True)
    saved={'representation':np.array('sequence_form'),'x':p['x'],'S':np.array([1,2])}
    f,x=coarsen_full_behavior(saved,2,3,(1,2))
    assert np.max(abs(x-p['x']))<1e-9
