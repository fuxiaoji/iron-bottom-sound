"""Additive interval-loss certificates and a budgeted shortest-path calendar.

The opposing calendar MUST be F. Common public boundaries then make the
blockwise loss comparison valid. No corresponding C-opponent assertion is
made. Bounds include uniform errors in the full-feedback continuation tree.
"""
import time
import numpy as np
from research.formation.exact_v12 import values_3x3
from research.formation.commitment_v12 import matrix_lp
from research.formation.pricing_v14 import hybrid


def full_value_tree(A,base,T):
    tree={T:np.asarray(A).copy()};errors={T:0.};trace=[]
    for t in reversed(range(T)):
        n=base**t
        mats=tree[t+1].reshape(n,base,n,base).transpose(0,2,1,3).reshape(n*n,base,base)
        if base==3:vals,gaps,_=values_3x3(mats)
        else:
            rr=[matrix_lp(m) for m in mats];vals=np.array([r['V'] for r in rr]);gaps=np.array([r['gap'] for r in rr])
        pad=1e-8*max(1.,float(np.max(abs(mats))))
        errors[t]=errors[t+1]+float(max(gaps))+pad
        tree[t]=vals.reshape(n,n)
        trace.append({'t':t,'nodes':n*n,'uniform_error':errors[t]})
    return tree,errors,trace


def interval_certificates(A,base,T,checkpoint=None):
    tick=time.perf_counter();tree,errors,trace=full_value_tree(A,base,T);edges=[]
    def report():
        vf=float(tree[0][0,0])
        return {'T':T,'base':base,'opponent':'F','V_full':vf,'V_full_LB':vf-errors[0],
                'V_full_UB':vf+errors[0],'edges':edges,'tree_trace':trace,'seconds':time.perf_counter()-tick,
                'scope':'finite F-opponent game; ex-post uniform interval-loss upper bounds with floating-point error padding'}
    for t in range(T):
      for end in range(t+1,T+1):
        if end==t+1:
            edges.append({'t':t,'end':end,'loss_UB':0.,'reason':'identical one-epoch decision game',
                          'local_solves':0,'seconds':0.})
            if checkpoint:checkpoint(report())
            continue
        begin=time.perf_counter();n,m=base**t,base**(end-t)
        mats=tree[end].reshape(n,m,n,m).transpose(0,2,1,3).reshape(n*n,m,m)
        lower=np.empty(n*n);maxgap=0.
        for i,sub in enumerate(mats):
            r=hybrid(-sub.T,base,end-t,tuple(range(1,end-t)))
            # Opponent is the local maximizer; negate its UPPER bound.
            lower[i]=-r['UB']-errors[end]
            maxgap=max(maxgap,r['gap'])
        deficits=tree[t].ravel()+errors[t]-lower
        ix=int(deficits.argmax())
        edges.append({'t':t,'end':end,'loss_UB':max(0.,float(deficits[ix])),
                      'worst_own_prefix':ix//n,'worst_opponent_prefix':ix%n,
                      'source_uniform_error':errors[t],'terminal_uniform_error':errors[end],
                      'max_local_numeric_gap':maxgap,'local_solves':n*n,
                      'seconds':time.perf_counter()-begin})
        if checkpoint:checkpoint(report())
    return report()


def shortest_calendars(certificate):
    T=certificate['T'];edge={(x['t'],x['end']):x['loss_UB'] for x in certificate['edges']}
    # d[j,e] uses exactly j nonempty forward intervals from 0 to e.
    d=np.full((T+1,T+1),np.inf);d[0,0]=0.;paths={(0,0):()};rows=[]
    for j in range(1,T+1):
        for end in range(1,T+1):
            options=[(d[j-1,t]+edge[t,end],t) for t in range(end) if np.isfinite(d[j-1,t])]
            if not options:continue
            val,t=min(options);d[j,end]=val;paths[j,end]=paths[j-1,t]+(end,)
        K=j-1
        best=min((d[h,T],h) for h in range(1,j+1))
        value,h=best;s=paths[h,T][:-1]
        rows.append({'K':K,'S':list(s),'loss_UB':float(value),
                     'value_LB':certificate['V_full_LB']-float(value),
                     'value_UB':certificate['V_full_UB']})
    return rows
