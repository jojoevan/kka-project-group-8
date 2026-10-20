"""Greedy baseline: repeatedly visit the fitting node with the best Prize / (flight + dwell) ratio."""
import math
from .common import Tracker, candidates


def solve(inst, budget=1, seed=0):
    """Deterministic (seed is ignored); one recorded evaluation of the constructed order."""
    tracker = Tracker(inst, budget); unvisited = set(candidates(inst)); order = []; prev = inst.depot; t = 0.
    while unvisited:
        best = None
        for i in sorted(unvisited):
            leg = inst.dist[prev, i] / inst.speed; back = inst.dist[i, inst.depot] / inst.speed
            if t + leg + inst.dwell + back > inst.time_limit + 1e-9: continue
            prize = inst.risk[i] * math.exp(-inst.g0 * (1 + inst.kappa * inst.ops[i]) * (t + leg))
            ratio = prize / max(leg + inst.dwell, 1e-9)
            if best is None or ratio > best[0]: best = (ratio, i, leg)
        if best is None: break
        _, i, leg = best
        order.append(i); t += leg + inst.dwell; prev = i; unvisited.remove(i)
    perm = order + sorted(unvisited)  # the unvisited tail no longer fits, so it is never decoded
    tracker.evaluate(perm)
    return tracker.result(visited=len(order))
