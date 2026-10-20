"""Steepest-Ascent Hill Climbing with random restarts until the evaluation budget is used up."""
from .common import BudgetExhausted, Tracker, algorithm_rng, all_moves, apply_move, candidates, initial_permutation


def solve(inst, budget=20000, seed=0):
    """Each step evaluates the full shared neighbourhood (O(n^2) evaluations) and takes the best
    improving neighbour; at a local optimum it restarts from a random permutation. The first start is
    the shared initial permutation; its local optimum is logged as single_start_fitness."""
    tracker = Tracker(inst, budget); rng = algorithm_rng(seed); nodes = candidates(inst)
    start = initial_permutation(inst, seed); moves = all_moves(len(nodes))
    restarts = 0; steps = 0; single_start = None; cur = start
    try:
        while True:
            cv = tracker.evaluate(cur); restarts += 1
            try:
                while True:
                    best_q, best_v = None, cv
                    for m in moves:
                        q = apply_move(cur, m); v = tracker.evaluate(q)
                        if v > best_v + 1e-12: best_q, best_v = q, v
                    if best_q is None: break  # local optimum
                    cur, cv = best_q, best_v; steps += 1
            finally:
                if single_start is None: single_start = cv
            if not moves: break
            cur = [int(x) for x in rng.permutation(nodes)]
    except BudgetExhausted:
        pass
    return tracker.result(start, restarts=restarts, single_start_fitness=float(single_start),
                          neighbourhood_size=len(moves), steps=steps)
