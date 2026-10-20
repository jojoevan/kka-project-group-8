
import numpy as np, time, math, random
def neighbours(p, rng=None, limit=None):
    n=len(p); out=[]
    if n<2:return out
    # all swap, relocate, and reversal neighbours
    for i in range(n-1):
        for j in range(i+1,n):
            q=p.copy(); q[i],q[j]=q[j],q[i]; out.append(q)
            q=p.copy(); v=q.pop(i); q.insert(j,v); out.append(q)
            q=p.copy(); q[i:j+1]=reversed(q[i:j+1]); out.append(q)
    if limit and len(out)>limit:
        ids=np.random.default_rng().choice(len(out),limit,replace=False); out=[out[i] for i in ids]
    return out
def result(inst, perm, history, start, evals):
    return {"best_perm":list(map(int,perm)),"best_route":inst.evaluate(perm,True),"best_fitness":inst.evaluate(perm),
            "history":history,"runtime":time.perf_counter()-start,"evals":evals}
def greedy(inst, budget=None, seed=0):
    start=time.perf_counter(); n=len(inst.names); unvisited=set(range(1,n)); p=[]; prev=0; t=0
    while unvisited:
        choices=[]
        for i in unvisited:
            leg=inst.dist[prev,i]/inst.speed; back=inst.dist[i,0]/inst.speed
            if t+leg+inst.dwell+back<=inst.time_limit:
                arrival=t+leg; prize=inst.risk[i]*math.exp(-inst.g0*(1+inst.kappa*inst.ops[i])*arrival)
                choices.append((prize/max(leg+inst.dwell,1e-9),i,leg,prize))
        if not choices: break
        _,i,leg,_=max(choices,key=lambda x:(x[0],-x[1]))
        p.append(i); t+=leg+inst.dwell; prev=i; unvisited.remove(i)
    return result(inst,p,[(1,inst.evaluate(p))],start,1)
