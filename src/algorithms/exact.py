
"""Exact permutation enumeration for tiny instances only."""
import itertools, time
def solve(inst, max_n=9):
    start=time.perf_counter(); n=len(inst.names)-1
    if n>max_n: raise ValueError(f"Exact solver limited to {max_n} candidates")
    best=[]; bv=-1
    for p in itertools.permutations(range(1,n+1)):
        v=inst.evaluate(p)
        if v>bv: best=list(p); bv=v
    return {"best_perm":best,"best_route":inst.evaluate(best,True),"best_fitness":bv,
            "history":[(math_factorial(n),bv)],"runtime":time.perf_counter()-start,"evals":math_factorial(n)}
def math_factorial(n):
    import math
    return math.factorial(n)
