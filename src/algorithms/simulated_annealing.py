
import time, math, numpy as np
from .common import neighbours, result
def solve(inst,budget=20000,seed=0,cooling=.995):
    rng=np.random.default_rng(seed); start=time.perf_counter(); n=len(inst.names)-1
    cur=list(rng.permutation(np.arange(1,n+1))); cv=inst.evaluate(cur); best=cur.copy(); bv=cv; evals=1
    diffs=[]
    for _ in range(min(100,max(10,n*3))):
        q=cur.copy(); i,j=rng.choice(n,2,replace=False); q[i],q[j]=q[j],q[i]; diffs.append(abs(inst.evaluate(q)-cv))
    positive=[d for d in diffs if d>0]; T=max(np.mean(positive) if positive else .01,.001)
    hist=[(evals,bv)]; accepted=0
    while evals<budget:
        i,j=rng.choice(n,2,replace=False); q=cur.copy(); q[i],q[j]=q[j],q[i]
        v=inst.evaluate(q); evals+=1; delta=v-cv
        if delta>=0 or rng.random()<math.exp(max(-700,delta/max(T,1e-12))):
            cur,cv=q,v; accepted+=1
        if cv>bv: best,bv=cur.copy(),cv
        T*=cooling
        if evals%max(1,budget//200)==0: hist.append((evals,bv))
    return result(inst,best,hist,start,evals)
