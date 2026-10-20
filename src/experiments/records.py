"""One record per solver run, shared by the province experiment and the FIRMS phase.

Every row has the same columns whatever the algorithm; algorithm-specific diagnostics (HC restarts,
SA temperature, GA generations, Exact optimality) are filled for their algorithm and None elsewhere.
"""
from src.experiments.stats import evals_to_fraction

HEURISTICS = ("Greedy", "HC", "SA", "GA")

# runs.csv column -> key in the solver's `extra`, per algorithm.
EXTRA_COLUMNS = {
    "HC": {"hc_single_start_fitness": "single_start_fitness", "hc_restarts": "restarts", "hc_steps": "steps"},
    "SA": {"sa_acceptance_rate": "acceptance_rate", "sa_t0": "T0", "sa_cooling": "cooling",
           "sa_final_temperature": "final_temperature"},
    "GA": {"ga_generations": "generations"},
    "Exact": {"exact_optimal": "optimal"},
}


def run_record(res, algorithm, seed, budget, keys):
    """(row, history, best_route, best_perm) of one solver result.

    keys are the instance columns placed first in the row and history (e.g. {"n": 38, "scenario": "2026"})."""
    extra = res.get("extra", {}); route = res["best_route"]
    row = {"algorithm": algorithm, **keys, "seed": seed, "fitness": res["best_fitness"],
           "runtime_s": res["runtime"], "evals": res["evals"], "budget": budget,
           "evals_to_95": evals_to_fraction(res["history"], .95)}
    for alg, cols in EXTRA_COLUMNS.items():
        for col, key in cols.items(): row[col] = extra.get(key) if algorithm == alg else None
    row.update(visited=len(route["route"]), mission_time_h=route["mission_time_h"])
    hist = {"algorithm": algorithm, **keys, "seed": seed,
            "history": [[int(e), float(v)] for e, v in res["history"]]}
    return row, hist, route, [int(x) for x in res["best_perm"]]
