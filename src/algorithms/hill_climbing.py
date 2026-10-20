
import time, numpy as np
from .common import neighbours, result
def solve(inst,budget=20000,seed=0,restarts=3):
    rng=np.random.default_rng(seed); start=time.perf_counter(); n=len(inst.names)-1
    best=list(rng.permutation(np.arange(1,n+1))); bestv=inst.evaluate(best); evals=1; hist=[(evals,bestv)]
    per=max(1,budget//max(1,restarts))
    for r in range(restarts):
        cur=list(rng.permutation(np.arange(1,n+1))) if r else best.copy()
        cv=inst.evaluate(cur); evals+=1
        improved=True
        while improved and evals<budget and evals < (r+1)*per:
            improved=False; local=cur; lv=cv
            for q in neighbours(cur):
                v=inst.evaluate(q); evals+=1
                if v>lv+1e-12: local,lv=q,v
                if evals>=budget or evals >= (r+1)*per: break
            if lv>cv+1e-12: cur,cv=local,lv; improved=True
            if cv>bestv: best,bestv=cur.copy(),cv
            hist.append((evals,bestv))
    return result(inst,best,hist,start,evals)
