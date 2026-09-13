import numpy as np
import pytest
from research.formation.pricing_v14 import price,column_generation,evaluate_policy_mixture
from research.formation.schedule_v14 import build_flow,pure_plans,schedules,solve,decompose


def test_pricing_against_complete_pure_policies():
    A=np.random.default_rng(1450).normal(size=(8,8));q=np.arange(1,9)/36
    from research.formation.schedule_v14 import pure_policy_payoffs
    for S in schedules(3):
        B=build_flow(2,2,3,S);R=build_flow(2,2,3,())
        normal=pure_policy_payoffs(A,B,R)
        assert abs(price(A,q,2,3,S)[0]-np.max(normal@q))<1e-10


@pytest.mark.parametrize('base,T',[(2,3),(3,3)])
def test_generation_equals_full_sequence_form(base,T):
    A=np.random.default_rng(1470+base).normal(size=(base**T,base**T))
    for S in schedules(T):
        a,policy=column_generation(A,base,T,S,return_strategies=True)
        ref=solve(A,base,T,S,'C')['V']
        assert a['LB']-1e-7<=ref<=a['UB']+1e-7
        assert a['status']=='certified_numeric'
        lower=evaluate_policy_mixture(A,policy,base,T,S)
        assert lower>=a['LB']-1e-7
        evaluate_policy_mixture(A,policy,base,T,tuple(range(1,T)))


def test_decomposed_pricing_equals_monolithic():
    A=np.random.default_rng(1479).normal(size=(27,27))
    for S in schedules(3):
        a=decompose(A,3,3,S,(1,2),pricing=True)
        v=solve(A,3,3,S,'F')['V']
        assert a['LB']-1e-7<=v<=a['UB']+1e-7


def test_no_future_leak_in_price():
    # A would allow value 1 by reading the opponent's last action; commitment
    # can only attain .5 and pricing must not select separately per column.
    A=np.array([[1.,0.],[0.,1.]])
    v,_,rows=price(A,np.array([.5,.5]),2,1,())
    assert v==.5 and rows[0]==rows[1]


def test_contingent_response_and_projection_against_sequence_form():
    from research.formation.pricing_v14 import response_to_policy,coarsen_policy,loss_certificate
    from research.formation.schedule_v14 import pure_policy_payoffs
    A=np.random.default_rng(1488).normal(size=(8,8))
    # Generate a flexible opponent strategy, then independently enumerate ALL
    # own pure policies to check response values using mutual causal rollout.
    _,rpol=column_generation(-A.T,2,3,(1,2),return_strategies=True)
    from research.formation.schedule_v14 import pure_plans
    def rollout(bp,rm):
        b=r=0
        for t in range(3):
            if t==0 or t in sb:
                end=next(v for v in (*sb,3) if v>t)
                block=bp[t,b,r]
                bq=[(block//2**k)%2 for k in reversed(range(end-t))]
            ra=(rm[b*2**(3-t)]//2**(2-t))%2
            ba=bq.pop(0);b=b*2+ba;r=r*2+ra
        return A[b,r]
    for sb in schedules(3):
        policies=pure_plans(build_flow(2,2,3,sb))
        reference=max(sum(w*rollout(bp,rm) for w,rm in zip(rpol['weights'],rpol['rowmaps'])) for bp in policies)
        ans=response_to_policy(A,rpol,2,3,sb)[0]
        assert abs(ans-reference)<1e-9
    r,bpol=column_generation(A,2,3,(1,2),return_strategies=True)
    for target in schedules(3):
        cert,projected=loss_certificate(A,r['UB'],bpol,2,3,target,'C')
        truth=solve(A,2,3,target,'C')['V']
        assert cert['lower_value']<=truth+1e-7
        assert cert['loss_upper']>=r['V']-truth-1e-7


def test_supermodular_counterexample():
    A=np.zeros((8,8))
    for i in range(8):
        for j in range(8):
            A[i,j]=int((i//2)%2==j//4 and i%2==(j//2)%2)
    vals=[column_generation(A,2,3,s)['V'] for s in [(),(1,),(2,),(1,2)]]
    assert np.max(abs(np.array(vals)-[.25,.5,.5,1]))<1e-8
