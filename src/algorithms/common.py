"""Shared pieces of the solver contract: budgeted evaluation, initial solution, move set, result.

Every solver has the signature ``solve(inst, budget, seed) -> dict`` and returns ``best_perm``,
``best_route``, ``best_fitness``, ``history`` [(evals, best_so_far)], ``runtime``, ``evals`` and an
``extra`` dict of solver-specific logs. ``evals`` never exceeds ``budget``.
"""
import time
import numpy as np

MOVES = ("swap", "relocate", "reverse")


class BudgetExhausted(Exception):
    """Raised by Tracker.evaluate when the evaluation budget is used up."""


class Tracker:
    """Counts evaluations against the budget and keeps the best-so-far and its history."""

    def __init__(self, inst, budget):
        if budget < 1: raise ValueError("Budget evaluasi minimal 1")
        self.inst = inst; self.budget = int(budget); self.evals = 0
        self.best = None; self.best_fitness = -np.inf; self.history = []
        self.start = time.perf_counter()

    @property
    def remaining(self):
        return self.budget - self.evals

    def evaluate(self, perm):
        if self.evals >= self.budget: raise BudgetExhausted
        self.evals += 1
        v = self.inst.evaluate(perm)
        if v > self.best_fitness:
            self.best, self.best_fitness = list(perm), v
            self.history.append((self.evals, v))
        return v

    def result(self, initial_perm=None, **extra):
        best = [int(x) for x in self.best]
        out = {"best_perm": best, "best_route": self.inst.evaluate(best, details=True),
               "best_fitness": float(self.best_fitness), "history": list(self.history),
               "runtime": time.perf_counter() - self.start, "evals": self.evals, "extra": extra}
        if initial_perm is not None: out["initial_perm"] = [int(x) for x in initial_perm]
        return out


def candidates(inst):
    """All non-depot node indices, in index order."""
    return [i for i in range(len(inst.names)) if i != inst.depot]


def initial_permutation(inst, seed):
    """The shared starting permutation for seed: HC's first start, SA's start, GA's first individual."""
    rng = np.random.default_rng(seed)
    return [int(x) for x in rng.permutation(candidates(inst))]


def algorithm_rng(seed):
    """Solver-internal randomness, independent of the stream used by initial_permutation."""
    return np.random.default_rng([seed, 1])


def apply_move(perm, move):
    """New permutation after one move (kind, i, j) from the shared move set."""
    kind, i, j = move; q = list(perm)
    if kind == "swap":
        q[i], q[j] = q[j], q[i]
    elif kind == "relocate":
        q.insert(j, q.pop(i))
    elif kind == "reverse":
        q[i:j + 1] = q[i:j + 1][::-1]
    else:
        raise ValueError(f"Move tidak dikenal: {kind}")
    return q


def all_moves(n):
    """Full neighbourhood: every swap, relocate (both directions) and 2-opt reversal.

    Moves equivalent to a swap (adjacent relocate, length-2 reversal) are left out once. Size O(n^2).
    """
    out = []
    for i in range(n - 1):
        for j in range(i + 1, n):
            out.append(("swap", i, j))
            if j - i >= 2:
                out.append(("relocate", i, j)); out.append(("relocate", j, i)); out.append(("reverse", i, j))
    return out


def random_move(n, rng):
    """One uniformly drawn move type, then uniformly drawn positions (same move set as all_moves)."""
    kinds = MOVES if n >= 3 else ("swap",)
    kind = kinds[int(rng.integers(len(kinds)))]
    if kind == "swap":
        i, j = sorted(int(x) for x in rng.choice(n, 2, replace=False))
        return ("swap", i, j)
    while True:
        i, j = (int(x) for x in rng.choice(n, 2, replace=False))
        if abs(i - j) >= 2: break
    return ("reverse", min(i, j), max(i, j)) if kind == "reverse" else ("relocate", i, j)
