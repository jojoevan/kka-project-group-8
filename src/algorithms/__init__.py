"""Solver registry; every solver is solve(inst, budget, seed) -> result dict (see common.py)."""
from .common import initial_permutation
from .exact import solve as exact
from .genetic_algorithm import solve as genetic_algorithm
from .greedy import solve as greedy
from .hill_climbing import solve as hill_climbing
from .simulated_annealing import solve as simulated_annealing

SOLVERS = {"Greedy": greedy, "HC": hill_climbing, "SA": simulated_annealing, "GA": genetic_algorithm,
           "Exact": exact}
