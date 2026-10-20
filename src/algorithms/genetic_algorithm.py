"""Genetic Algorithm: random population, tournament selection, Order Crossover, shared-move mutation,
elitism. The first individual is the shared initial permutation; no greedy seeding."""
from .common import BudgetExhausted, Tracker, algorithm_rng, apply_move, candidates, initial_permutation, random_move

POPULATION = 100
TOURNAMENT = 3
MUTATION = .2
ELITES = 2


def order_crossover(a, b, rng):
    """OX: keep a[i..j] in place, fill the other positions in b's order starting after j."""
    n = len(a); i, j = sorted(int(x) for x in rng.choice(n, 2, replace=False))
    child = [None] * n; child[i:j + 1] = a[i:j + 1]; kept = set(a[i:j + 1])
    fill = [x for x in b[j + 1:] + b[:j + 1] if x not in kept]
    for k, x in zip([(j + 1 + s) % n for s in range(n - (j - i + 1))], fill): child[k] = x
    return child


def solve(inst, budget=20000, seed=0):
    """Each child costs one evaluation; elites carry their fitness over without re-evaluation."""
    tracker = Tracker(inst, budget); rng = algorithm_rng(seed); nodes = candidates(inst); n = len(nodes)
    start = initial_permutation(inst, seed)
    initial = [start] + [[int(x) for x in rng.permutation(nodes)] for _ in range(POPULATION - 1)]
    pop, vals = [], []; generations = 0
    try:
        for p in initial:
            vals.append(tracker.evaluate(p)); pop.append(p)
        if n < 2: raise BudgetExhausted

        def tournament():
            ids = rng.integers(0, len(pop), size=TOURNAMENT)
            return pop[max(ids, key=lambda z: vals[z])]

        while True:
            order = sorted(range(len(pop)), key=lambda z: -vals[z])
            new = [pop[z] for z in order[:ELITES]]; new_vals = [vals[z] for z in order[:ELITES]]
            while len(new) < POPULATION:
                child = order_crossover(tournament(), tournament(), rng)
                if rng.random() < MUTATION: child = apply_move(child, random_move(n, rng))
                new_vals.append(tracker.evaluate(child)); new.append(child)
            pop, vals = new, new_vals; generations += 1
    except BudgetExhausted:
        pass
    return tracker.result(start, population=POPULATION, generations=generations,
                          initial_population=initial)
