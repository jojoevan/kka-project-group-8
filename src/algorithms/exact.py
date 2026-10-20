"""Exact solver for tiny instances: depth-first enumeration of visit orders, pruned by Batas waktu misi.

Only orders whose every Kunjungan fits (including the return to the Depot) are enumerated. Every
decoded permutation is such an order, so the best one is optimal. No earliest-arrival DP, because
Prize depends on arrival time. Each enumerated order counts as one evaluation.
"""
from .common import BudgetExhausted, Tracker, candidates

MAX_NODES = 9


def solve(inst, budget=10**6, seed=0):
    """Optimal order for instances of at most MAX_NODES nodes (depot included); seed is ignored.

    If the budget runs out first, the best order found so far is returned with optimal=False.
    """
    if len(inst.names) > MAX_NODES:
        raise ValueError(f"Solver Exact hanya untuk instance dengan maksimal {MAX_NODES} node")
    tracker = Tracker(inst, budget); nodes = candidates(inst)

    def extend(prefix, prev, t):
        for i in nodes:
            if i in prefix: continue
            leg = inst.dist[prev, i] / inst.speed
            if t + leg + inst.dwell + inst.dist[i, inst.depot] / inst.speed > inst.time_limit + 1e-9: continue
            prefix.append(i); tracker.evaluate(prefix)
            extend(prefix, i, t + leg + inst.dwell); prefix.pop()

    optimal = True
    try:
        tracker.evaluate([])  # the empty route, so a result exists even if nothing fits
        extend([], inst.depot, 0.)
    except BudgetExhausted:
        optimal = False
    # Complete the best order into a permutation. For the optimum the tail adds nothing; otherwise
    # the decoder may fit extra tail nodes, so the fitness is re-read to keep the contract exact.
    best = tracker.best + [i for i in nodes if i not in tracker.best]
    tracker.best, tracker.best_fitness = best, inst.evaluate(best)
    tracker.history[-1] = (tracker.history[-1][0], tracker.best_fitness)
    return tracker.result(optimal=optimal)
