"""Main comparison experiment: n x Skenario tahun x seeds x {Greedy, HC, SA, GA}, plus Exact for small n.

    python -m src.experiments.run_all --config config.yaml [--quick] [--out results] [--workers K]

Writes (under --out): raw/runs.csv (one row per run), raw/histories.jsonl.gz (convergence history per
run), tables/{summary,optimality_gap,wilcoxon_holm,instances}.{csv,md}, figures/boxplot_fitness_n*.png,
routes/, logs/run_all.log. Runs are spread over worker processes; every run depends only on
(instance, algorithm, seed), so results are identical for any worker count.
"""
import argparse
import gzip
import json
import logging
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.algorithms import SOLVERS
from src.algorithms.exact import MAX_NODES as EXACT_MAX_NODES
from src.data_prep import SCENARIOS, prepare
from src.experiments import plots
from src.experiments.stats import evals_to_fraction, optimality_gap_table, summary_table, wilcoxon_holm_table
from src.instance import INSTANCE_SIZES, build_instance

HEURISTICS = ("Greedy", "HC", "SA", "GA")
EXACT_BUDGET = 10**7
log = logging.getLogger("run_all")

_features = _coords = _cfg = None
_instances = {}


def _init(features, coords, cfg):
    global _features, _coords, _cfg
    _features, _coords, _cfg = features, coords, cfg; _instances.clear()


def make_instance(features, coords, cfg, n, scenario):
    return build_instance(features, coords, n=n, scenario=scenario, depot_name=cfg["depot"],
                          speed=cfg["speed_kmh"], detour=cfg["detour_factor"], dwell=cfg["dwell_hours"],
                          time_limit=cfg["time_limit_hours"], g0=cfg["decay_g0"], kappa=cfg["decay_kappa"])


def _instance(n, scenario):
    if (n, scenario) not in _instances:
        _instances[n, scenario] = make_instance(_features, _coords, _cfg, n, scenario)
    return _instances[n, scenario]


def run_one(task):
    """One run of one algorithm on one instance; returns (row, history, best_route)."""
    scenario, n, algorithm, seed, budget = task
    res = SOLVERS[algorithm](_instance(n, scenario), budget=budget, seed=seed)
    extra = res.get("extra", {})
    route = res["best_route"]
    row = {"algorithm": algorithm, "n": n, "scenario": scenario, "seed": seed, "fitness": res["best_fitness"],
           "runtime_s": res["runtime"], "evals": res["evals"], "budget": budget,
           "evals_to_95": evals_to_fraction(res["history"], .95),
           "hc_single_start_fitness": extra.get("single_start_fitness") if algorithm == "HC" else None,
           "hc_restarts": extra.get("restarts") if algorithm == "HC" else None,
           "sa_acceptance_rate": extra.get("acceptance_rate") if algorithm == "SA" else None,
           "ga_generations": extra.get("generations") if algorithm == "GA" else None,
           "exact_optimal": extra.get("optimal") if algorithm == "Exact" else None,
           "visited": len(route["route"]), "mission_time_h": route["mission_time_h"]}
    hist = {"algorithm": algorithm, "n": n, "scenario": scenario, "seed": seed,
            "history": [[int(e), float(v)] for e, v in res["history"]]}
    return row, hist, route


def budget_for(n, cfg, quick):
    if quick: return int(cfg["quick"]["budget"])
    b = cfg["evaluation_budget"]
    return int(b["small"] if n <= b["small_max_n"] else b["large"])


def plan(cfg, quick):
    """All runs in a fixed order: instances, then seeds, then algorithms; Exact once per small instance."""
    sizes = cfg["quick"]["sizes"] if quick else list(INSTANCE_SIZES)
    seeds = cfg["quick"]["seeds"] if quick else cfg["seeds"]
    tasks = []
    for scenario in SCENARIOS:
        for n in sizes:
            budget = budget_for(n, cfg, quick)
            tasks += [(scenario, n, a, s, budget) for s in range(seeds) for a in HEURISTICS]
            if n <= EXACT_MAX_NODES: tasks.append((scenario, n, "Exact", 0, EXACT_BUDGET))
    return tasks


def write_table(df, path_stem, rename=None, floatfmt=".4g"):
    df.to_csv(path_stem.with_suffix(".csv"), index=False)
    shown = df.rename(columns=rename or {})
    path_stem.with_suffix(".md").write_text(shown.to_markdown(index=False, floatfmt=floatfmt) + "\n", encoding="utf8")


SUMMARY_ID = {"scenario": "skenario", "algorithm": "algoritma", "runs": "jumlah run", "best": "terbaik",
              "mean": "rata-rata", "std": "simpangan baku", "median": "median",
              "runtime_mean_s": "runtime rata-rata (s)", "evals_mean": "evaluasi rata-rata",
              "evals_to_95_mean": "evaluasi ke 95% rata-rata", "success_rate": "success rate (1%)",
              "best_known": "best-known"}
GAP_ID = {"scenario": "skenario", "algorithm": "algoritma", "exact": "optimum Exact",
          "mean_fitness": "fitness rata-rata", "gap_mean_pct": "gap rata-rata (%)", "gap_max_pct": "gap maks (%)",
          "optimal_rate": "proporsi optimal"}
INSTANCES_ID = {"scenario": "skenario", "budget": "budget evaluasi", "time_limit_h": "Batas waktu misi (jam)",
                "greedy_visited": "terkunjungi Greedy", "candidates": "node kandidat",
                "time_limit_binds": "batas waktu mengikat", "greedy_mission_time_h": "waktu misi Greedy (jam)"}
WILCOXON_ID = {"scenario": "skenario", "algorithm_a": "algoritma A", "algorithm_b": "algoritma B",
               "median_a": "median A", "median_b": "median B", "median_diff": "median selisih (A-B)",
               "wins_a": "A menang", "wins_b": "B menang", "statistic": "statistik W",
               "p_value": "p-value", "p_holm": "p-value Holm", "significant_0.05": "signifikan (0,05)"}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Eksperimen perbandingan utama")
    ap.add_argument("--config", default=str(ROOT / "config.yaml"))
    ap.add_argument("--quick", action="store_true", help="mode cepat (smoke test)")
    ap.add_argument("--out", default=str(ROOT / "results"))
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    args = ap.parse_args(argv)
    t_start = time.perf_counter()
    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf8"))
    out = Path(args.out)
    for sub in ["raw", "tables", "routes", "figures", "logs"]: (out / sub).mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(out / "logs" / "run_all.log", mode="w", encoding="utf8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    log.handlers.clear(); log.addHandler(handler); log.addHandler(logging.StreamHandler()); log.setLevel(logging.INFO)
    log.propagate = False
    try:
        _run(cfg, args, out, t_start)
    finally:
        handler.close(); log.handlers.clear()


def _run(cfg, args, out, t_start):
    w = cfg["weights"]
    features = prepare(weights=(w["hist"], w["cur"], w["ops"]), gamma=cfg["gamma"])[0]
    coords = pd.read_csv(ROOT / "data" / "external" / "province_coords.csv")
    tasks = plan(cfg, args.quick)
    log.info("Mode: %s; %d run; %d worker; Batas waktu misi %s jam untuk semua instance",
             "cepat" if args.quick else "penuh", len(tasks), args.workers, cfg["time_limit_hours"])
    instance_rows = []
    for scenario, n in dict.fromkeys((t[0], t[1]) for t in tasks):
        inst = make_instance(features, coords, cfg, n, scenario)
        g = SOLVERS["Greedy"](inst)
        all_fit = len(g["best_route"]["route"]) == n - 1
        instance_rows.append({"scenario": scenario, "n": n, "budget": budget_for(n, cfg, args.quick),
                              "time_limit_h": cfg["time_limit_hours"], "greedy_visited": len(g["best_route"]["route"]),
                              "candidates": n - 1, "time_limit_binds": not all_fit,
                              "greedy_mission_time_h": g["best_route"]["mission_time_h"]})
        if all_fit:
            log.info("Catatan: skenario %s n=%d — Batas waktu misi %s jam tidak mengikat (Greedy mengunjungi "
                     "semua %d node dalam %.1f jam); diterima sesuai keputusan owner.", scenario, n,
                     cfg["time_limit_hours"], n - 1, g["best_route"]["mission_time_h"])
    t_runs = time.perf_counter()
    if args.workers > 1:
        with Pool(args.workers, initializer=_init, initargs=(features, coords, cfg)) as pool:
            results = pool.map(run_one, tasks, chunksize=1)
    else:
        _init(features, coords, cfg); results = [run_one(t) for t in tasks]
    log.info("Semua run selesai dalam %.1f s", time.perf_counter() - t_runs)

    runs = pd.DataFrame([r[0] for r in results])
    runs.to_csv(out / "raw" / "runs.csv", index=False)
    with gzip.open(out / "raw" / "histories.jsonl.gz", "wt", encoding="utf8") as fh:
        for r in results: fh.write(json.dumps(r[1]) + "\n")

    write_table(pd.DataFrame(instance_rows), out / "tables" / "instances", INSTANCES_ID)
    write_table(summary_table(runs), out / "tables" / "summary", SUMMARY_ID)
    write_table(optimality_gap_table(runs, HEURISTICS), out / "tables" / "optimality_gap", GAP_ID)
    write_table(wilcoxon_holm_table(runs, list(HEURISTICS)), out / "tables" / "wilcoxon_holm", WILCOXON_ID)
    for n in sorted(runs.n.unique()):
        plots.boxplot_fitness(runs, n, list(HEURISTICS), out / "figures" / f"boxplot_fitness_n{n}.png")

    # Best route per instance (best heuristic run; ties -> first in run order).
    for (scenario, n), grp in runs.groupby(["scenario", "n"], sort=False):
        idx = grp[grp.algorithm.isin(HEURISTICS)].fitness.idxmax(); row = runs.loc[idx]
        detail = {"scenario": scenario, "n": int(n), "algorithm": row.algorithm, "seed": int(row.seed),
                  **results[idx][2]}
        (out / "routes" / f"best_route_{scenario}_n{n}.json").write_text(
            json.dumps(detail, indent=2, ensure_ascii=False), encoding="utf8")
        if (scenario, n) == ("2026", max(runs.n)):
            inst = make_instance(features, coords, cfg, int(n), scenario)
            plots.route_map(coords, inst, results[idx][2],
                            f"Rute terbaik skenario {scenario}, n={n} ({row.algorithm}, seed {row.seed})",
                            out / "figures" / "best_route_map.png")
    if not args.quick:
        (ROOT / "reports" / "figures_index.md").write_text(
            "# Daftar gambar\n\n"
            "- `results/figures/boxplot_fitness_n{6,10,15,25,38}.png`: Sebaran fitness akhir 30 seed per "
            "algoritma (Greedy, HC, SA, GA) untuk tiap n, satu panel per Skenario tahun.\n"
            "- `results/figures/best_route_map.png`: Sketsa rute terbaik skenario 2026 n=38, urutan kunjungan, "
            "dan waktu kedatangan.\n", encoding="utf8")
    total = time.perf_counter() - t_start
    log.info("Total runtime eksperimen: %.1f s (%.1f menit)", total, total / 60)
    print(f"Selesai. Keluaran ada di {out}.")


if __name__ == "__main__":
    main()
