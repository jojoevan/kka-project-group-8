"""Simulated Annealing over the shared move set with auto-calibrated T0 and budget-derived cooling."""
import math
import numpy as np
from .common import BudgetExhausted, Tracker, algorithm_rng, apply_move, candidates, initial_permutation, random_move

FINAL_TEMPERATURE_RATIO = 1e-3  # T_end ~= 0.001 * T0 when the budget is used up
CALIBRATION_MOVES = 100
TRACE_POINTS = 200


def solve(inst, budget=20000, seed=0):
    """T0 = mean positive |delta| of random moves from the start (these evaluations count towards the
    budget); geometric cooling c = ratio^(1/steps) over the remaining budget. No reheating."""
    tracker = Tracker(inst, budget); rng = algorithm_rng(seed); n = len(candidates(inst))
    start = initial_permutation(inst, seed)
    T0 = T = cooling = None; accepted = steps = 0; trace = []
    try:
        cur = start; cv = tracker.evaluate(cur)
        if n < 2: raise BudgetExhausted
        deltas = [abs(tracker.evaluate(apply_move(cur, random_move(n, rng))) - cv)
                  for _ in range(min(CALIBRATION_MOVES, max(1, (budget - 1) // 10)))]
        positive = [d for d in deltas if d > 0]
        T0 = T = float(np.mean(positive)) if positive else 1e-3
        total = tracker.remaining; cooling = FINAL_TEMPERATURE_RATIO ** (1 / max(total, 1))
        every = max(1, total // TRACE_POINTS)
        trace.append((tracker.evals, T))
        while True:
            q = apply_move(cur, random_move(n, rng)); v = tracker.evaluate(q); steps += 1
            delta = v - cv
            if delta >= 0 or rng.random() < math.exp(delta / T):
                cur, cv = q, v; accepted += 1
            T *= cooling
            if steps % every == 0: trace.append((tracker.evals, T))
    except BudgetExhausted:
        pass
    return tracker.result(start, T0=T0, cooling=cooling, final_temperature=T,
                          acceptance_rate=accepted / steps if steps else 0., temperature_trace=trace)
