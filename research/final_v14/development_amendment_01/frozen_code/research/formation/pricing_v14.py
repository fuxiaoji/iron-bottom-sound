"""Exact contingent-policy pricing against a committed opponent.

Full opponent plan support is retained. Dynamic programming aggregates the
probability of revealed opponent prefixes, never truncates a mixture, and
returns a feasible pure block policy. Column generation is standard; its
game-specific pricing and common-update use are separately documented.
"""
import time
import numpy as np
from research.formation.schedule_v14 import calendar
from research.formation.commitment_v12 import matrix_lp


def price(A, q, base, T, S):
    """Maximize E_q A against ALL pure policies consistent with S.

    Values are unnormalized by the opponent-prefix probability. This makes
    zero-probability histories well-defined without invented posteriors.
    """
    n = base**T
    if A.shape != (n,n) or np.shape(q) != (n,): raise ValueError('bad pricing shape')
    bounds = calendar(S,T)
    current = A*np.asarray(q)[None,:]; decisions = {}
    for t,end in reversed(list(zip(bounds[:-1],bounds[1:]))):
        prefix, block = base**t, base**(end-t)
        # Keep the known own/opponent prefixes; sum future opponent actions
        # before maximizing the own block, so future actions remain hidden.
        candidates = current.reshape(prefix,block,prefix,block).sum(axis=3)
        decisions[t] = candidates.argmax(axis=1)
        current = candidates.max(axis=1)
    cols = np.arange(n); rows = np.zeros(n,dtype=np.int64)
    for t,end in zip(bounds[:-1],bounds[1:]):
        oprefix = cols//base**(T-t)
        action = decisions[t][rows,oprefix]
        rows = rows*base**(end-t)+action
    rewards = A[rows,cols]
    value = float(rewards@q)
    if abs(value-float(current[0,0])) > 1e-8*max(1.,np.max(abs(A))):
        raise RuntimeError('pricing policy reconstruction disagrees with DP')
    return value, rewards, rows


def column_generation(A, base, T, S, time_limit=1200., max_iters=10000,
                      tolerance=1e-6, return_strategies=False, seed_policies=None):
    start = time.perf_counter(); n = base**T
    scale = max(1.,float(np.max(abs(A)))); padding = 1e-8*scale
    rows, maps = [], []
    if seed_policies is not None:
        for rowmap in seed_policies:
            # Caller must verify calendar compatibility. Default no transfer.
            rows.append(A[np.asarray(rowmap),np.arange(n)]); maps.append(np.asarray(rowmap))
    if not rows:
        _, rewards, rowmap = price(A,np.full(n,1/n),base,T,S)
        rows.append(rewards); maps.append(rowmap)
    seen = {v.tobytes() for v in maps}; trace = []; status = 'iteration_limit'
    for it in range(max_iters):
        restricted = matrix_lp(np.asarray(rows))
        lo = float(np.min(restricted['x']@np.asarray(rows)))
        hi, rewards, rowmap = price(A,restricted['y'],base,T,S)
        gap = hi-lo+2*padding
        trace.append({'iteration':it+1,'policies':len(rows),'LB':lo-padding,'UB':hi+padding,
                      'elapsed':time.perf_counter()-start})
        if gap <= tolerance*scale:
            status = 'certified_numeric'; break
        if time.perf_counter()-start >= time_limit:
            status = 'time_limit'; break
        key = rowmap.tobytes()
        if key in seen:
            status = 'pricing_stall'; break
        seen.add(key); rows.append(rewards); maps.append(rowmap)
    # Last restricted mixture only covers the rows present at its solve.
    count = len(restricted['x'])
    result = {'V':float(restricted['V']),'LB':lo-padding,'UB':hi+padding,'gap':gap,
              'S':list(S),'S_R':[],'opponent':'C','T':T,'base':base,
              'status':status,'seconds':time.perf_counter()-start,
              'iterations':it+1,'policy_count':count,'trace':trace,
              'numerical_padding':padding,'pricing':'exact full-history dynamic program',
              'algorithm':'one-sided contingent-policy generation; full committed opponent space',
              'certification_scope':'finite game; full-space floating-point response bounds'}
    if return_strategies:
        return result, {'weights':restricted['x'],'q':restricted['y'],
                        'rowmaps':np.asarray(maps[:count]),'br_rowmap':rowmap}
    return result


def evaluate_policy_mixture(A, policy, base, T, target_S):
    """Validate a policy transfer by observable-prefix consistency.

    A rowmap gives the own terminal path for every full opponent plan. At
    each block beginning, equal observed opponent prefixes must induce the
    same own block. This ensures no unseen future action affects commands.
    """
    n=base**T; cols=np.arange(n); boundaries=calendar(target_S,T)
    maps=np.asarray(policy['rowmaps']); weights=np.asarray(policy['weights'])
    if len(maps)!=len(weights) or abs(weights.sum()-1)>1e-8 or np.min(weights)<0:
        raise ValueError('invalid policy mixture')
    for t,end in zip(boundaries[:-1],boundaries[1:]):
        # The own executed prefix is already determined by the opponent prefix
        # for a fixed pure policy, so checking through end is stronger/direct.
        prefix=maps//base**(T-end)
        grouped=prefix.reshape(len(maps),base**t,base**(T-t))
        if np.any(grouped!=grouped[...,:1]):
            raise ValueError('policy is incompatible with target calendar')
    expected=weights@A[maps,cols[None,:]]
    return float(expected.min())


def conditional_matrix(policy, n):
    """P[own terminal path, opponent open-loop path], not a joint law."""
    out=np.zeros((n,n))
    maps=np.asarray(policy['rowmaps'],dtype=np.int64)
    weights=np.asarray(policy['weights'])
    np.add.at(out,(maps,np.arange(n)[None,:]),weights[:,None])
    if np.max(abs(out.sum(0)-1))>1e-8:raise ValueError('invalid conditional policy')
    return out


def response_to_policy(A, opponent_policy, base, T, S):
    """Exact own response to a mixture of causal CONTINGENT opponent policies.

    Opponent realization probabilities are counterfactual weights. At a fixed
    own path, the opponent policy induces a distribution over its paths.
    Causality ensures aggregation is independent of not-yet-chosen controls.
    """
    n=base**T
    weights=conditional_matrix(opponent_policy,n).T
    return price(A*weights,np.ones(n),base,T,S)


def coarsen_policy(policy, base, T, target_S, reference_action=None):
    """Commit shadow-policy blocks using a fixed hypothetical future.

    Only the actually observed opponent prefix enters each block. All weights
    are preserved. The construction requires state-independent action menus,
    as in this finite formation model; it need not approximate well.
    """
    if reference_action is None:reference_action=base//2
    n=base**T;cols=np.arange(n);maps=np.asarray(policy['rowmaps'])
    out=np.zeros_like(maps);boundaries=calendar(target_S,T)
    for t,end in zip(boundaries[:-1],boundaries[1:]):
        tail=base**(T-t)
        ref=reference_action*(tail-1)//(base-1) if base>1 else 0
        index=(cols//tail)*tail+ref
        block=(maps[:,index]//base**(T-end))%base**(end-t)
        out=out*base**(end-t)+block
    return {'rowmaps':out,'weights':np.asarray(policy['weights']).copy()}


def loss_certificate(A, source_upper, policy, base, T, target_S, opponent='C'):
    projected=coarsen_policy(policy,base,T,target_S)
    # This validation is independent of the response DP.
    evaluate_policy_mixture(A,projected,base,T,target_S)
    sr=tuple(range(1,T)) if opponent=='F' else ()
    hi_red,_,_=response_to_policy(-A.T,projected,base,T,sr)
    padding=1e-8*max(1.,float(np.max(abs(A))))
    lower=-hi_red-padding
    return {'target_S':list(target_S),'lower_value':lower,
            'loss_upper':float(source_upper-lower),'source_upper':float(source_upper),
            'construction':'fixed-straight hypothetical continuation; original mixture retained',
            'opponent':opponent},projected
