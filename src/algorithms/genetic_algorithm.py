
import time, numpy as np
from .common import result, greedy
def ox(a,b,rng):
    n=len(a); i,j=sorted(rng.choice(n,2,replace=False)); child=[None]*n
    child[i:j+1]=a[i:j+1]; fill=[x for x in b if x not in child]; k=(j+1)%n
    for x in fill:
        while child[k] is not None:k=(k+1)%n
        child[k]=x
    return child
def solve(inst,budget=20000,seed=0,population=60,mutation=.2,memetic_seed=True):
    rng=np.random.default_rng(seed); start=time.perf_counter(); n=len(inst.names)-1
    pop=[list(rng.permutation(np.arange(1,n+1))) for _ in range(population)]
    if memetic_seed:
        gp=greedy(inst).get("best_perm",[])
        pop[0]=gp+[x for x in range(1,n+1) if x not in gp]
    vals=[inst.evaluate(p) for p in pop]; evals=len(pop); bi=int(np.argmax(vals)); best=pop[bi].copy(); bv=vals[bi]; hist=[(evals,bv)]
    while evals<budget:
        new=[best.copy()]
        while len(new)<population and evals+len(new)<budget:
            def tourney():
                ids=rng.integers(0,len(pop),size=3); return pop[max(ids,key=lambda z:vals[z])]
            child=ox(tourney(),tourney(),rng)
            if rng.random()<mutation:
                i,j=sorted(rng.choice(n,2,replace=False)); child[i:j+1]=reversed(child[i:j+1])
            new.append(child)
        pop=new; vals=[inst.evaluate(p) for p in pop]; evals+=len(pop)
        bi=int(np.argmax(vals))
        if vals[bi]>bv: best,bv=pop[bi].copy(),vals[bi]
        hist.append((evals,bv))
    return result(inst,best,hist,start,min(evals,budget))
