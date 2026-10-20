"""Statistics for the main comparison: summary metrics, optimality gap, paired Wilcoxon with Holm."""
from itertools import combinations
import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

SUCCESS_TOLERANCE = .01  # a run succeeds if it is within 1% of the best-known fitness of its instance
KEYS = ["scenario", "n"]


def holm(pvalues):
    """Holm-Bonferroni adjusted p-values, in the input order, capped at 1."""
    p = np.asarray(pvalues, float); m = len(p)
    order = np.argsort(p, kind="stable")
    adj = np.maximum.accumulate((m - np.arange(m)) * p[order]).clip(max=1.)
    out = np.empty(m); out[order] = adj
    return out.tolist()


def evals_to_fraction(history, fraction=.95):
    """First evaluation count at which best-so-far reached fraction * final best (history is
    [(evals, best_so_far)], increasing)."""
    final = history[-1][1]
    for evals, best in history:
        if best >= fraction * final - 1e-12: return int(evals)
    return int(history[-1][0])


def best_known(runs):
    """Best fitness over every run (Exact included) per instance."""
    return runs.groupby(KEYS).fitness.max().rename("best_known")


def summary_table(runs):
    """Per algorithm x n x scenario: best, mean, std, median, runtime, evals to 95%, success rate."""
    r = runs.join(best_known(runs), on=KEYS)
    r["success"] = r.fitness >= (1 - SUCCESS_TOLERANCE) * r.best_known - 1e-12
    g = r.groupby(KEYS + ["algorithm"])
    s = g.agg(runs=("fitness", "size"), best=("fitness", "max"), mean=("fitness", "mean"),
              std=("fitness", "std"), median=("fitness", "median"), runtime_mean_s=("runtime_s", "mean"),
              evals_mean=("evals", "mean"), evals_to_95_mean=("evals_to_95", "mean"),
              success_rate=("success", "mean"), best_known=("best_known", "first")).reset_index()
    s["std"] = s["std"].fillna(0.)
    return s


def optimality_gap_table(runs, algorithms):
    """Gap (%) of each heuristic run to the Exact optimum, for instances that have an Exact row."""
    ex = runs[runs.algorithm == "Exact"].set_index(KEYS).fitness.rename("exact")
    r = runs[runs.algorithm.isin(algorithms)].join(ex, on=KEYS, how="inner")
    r["gap_pct"] = 100 * (r.exact - r.fitness) / r.exact
    r["optimal"] = r.gap_pct <= 1e-9
    return r.groupby(KEYS + ["algorithm"]).agg(
        exact=("exact", "first"), mean_fitness=("fitness", "mean"), gap_mean_pct=("gap_pct", "mean"),
        gap_max_pct=("gap_pct", "max"), optimal_rate=("optimal", "mean")).reset_index()


def wilcoxon_holm_table(runs, algorithms):
    """Two-sided Wilcoxon signed-rank test per pair of algorithms per instance, paired by seed, with
    Holm correction over the pairs of the same instance. Identical samples get p = 1."""
    rows = []
    for key, inst in runs[runs.algorithm.isin(algorithms)].groupby(KEYS):
        wide = inst.pivot(index="seed", columns="algorithm", values="fitness")
        block = []
        for a, b in combinations(algorithms, 2):
            d = (wide[a] - wide[b]).to_numpy()
            if np.allclose(d, 0, atol=1e-12):
                stat, p = 0., 1.
            else:
                res = wilcoxon(wide[a], wide[b], zero_method="wilcox", alternative="two-sided")
                stat, p = float(res.statistic), float(res.pvalue)
            block.append({"scenario": key[0], "n": key[1], "algorithm_a": a, "algorithm_b": b,
                          "median_a": float(wide[a].median()), "median_b": float(wide[b].median()),
                          "median_diff": float(np.median(d)), "wins_a": int((d > 1e-12).sum()),
                          "wins_b": int((d < -1e-12).sum()), "statistic": stat, "p_value": p})
        for row, ph in zip(block, holm([x["p_value"] for x in block])):
            row["p_holm"] = ph; row["significant_0.05"] = ph < .05
        rows += block
    return pd.DataFrame(rows)


def convergence_curve(histories, grid):
    """Mean and population std across seeds of the best-so-far step function at each grid point.

    Each history is [(evals, best_so_far)] with increasing evals; before its first point a run counts
    as its first value, after its last point it stays at its final best.
    """
    grid = np.asarray(grid)
    values = []
    for h in histories:
        ev = np.array([e for e, _ in h]); best = np.array([v for _, v in h], float)
        idx = np.searchsorted(ev, grid, side="right") - 1
        values.append(best[np.clip(idx, 0, None)])
    values = np.vstack(values)
    return {"mean": values.mean(axis=0).tolist(), "std": values.std(axis=0).tolist()}


def scalability_table(runs, algorithms):
    """Per algorithm x n x scenario: mean/std runtime and solution quality as % of the best-known fitness
    of the instance (Exact included), so different n are comparable."""
    r = runs.join(best_known(runs), on=KEYS)
    r = r[r.algorithm.isin(algorithms)].assign(quality_pct=lambda d: 100 * d.fitness / d.best_known)
    return r.groupby(KEYS + ["algorithm"]).agg(
        runtime_mean_s=("runtime_s", "mean"), runtime_std_s=("runtime_s", "std"),
        quality_mean_pct=("quality_pct", "mean"), quality_std_pct=("quality_pct", "std"),
        visited_mean=("visited", "mean")).reset_index().fillna({"runtime_std_s": 0., "quality_std_pct": 0.})


def sensitivity_table(sens_runs):
    """Per swept parameter x value x algorithm: fitness statistics, visited nodes, mission time, runtime,
    and quality as % of the best run of that setting (fitness is only comparable within one setting)."""
    keys = ["parameter", "value"]
    r = sens_runs.join(sens_runs.groupby(keys).fitness.max().rename("setting_best"), on=keys)
    r["quality_pct"] = 100 * r.fitness / r.setting_best
    s = r.groupby(keys + ["n", "scenario", "algorithm"], sort=False).agg(
        runs=("fitness", "size"), best=("fitness", "max"), mean=("fitness", "mean"), std=("fitness", "std"),
        median=("fitness", "median"), visited_mean=("visited", "mean"),
        mission_time_mean_h=("mission_time_h", "mean"), runtime_mean_s=("runtime_s", "mean"),
        quality_mean_pct=("quality_pct", "mean")).reset_index()
    s["std"] = s["std"].fillna(0.)
    return s


CONVERGENCE_POINTS = 200


def convergence_table(histories, runs, sizes, algorithms):
    """Long table (algorithm, n, scenario, evals, mean, std, seeds) of convergence curves for the given
    sizes; the grid runs linearly from 1 to the evaluation budget of the instance."""
    rows = []
    hist = pd.DataFrame(histories)
    for (alg, n, sc), g in hist[hist.n.isin(sizes) & hist.algorithm.isin(algorithms)].groupby(
            ["algorithm", "n", "scenario"]):
        budget = int(runs[(runs.n == n) & (runs.scenario == sc)].budget.max())
        grid = np.unique(np.linspace(1, budget, CONVERGENCE_POINTS).astype(int))
        c = convergence_curve(g.history.tolist(), grid)
        rows += [{"algorithm": alg, "n": n, "scenario": sc, "evals": int(e), "mean": m, "std": s,
                  "seeds": len(g)} for e, m, s in zip(grid, c["mean"], c["std"])]
    return pd.DataFrame(rows)
