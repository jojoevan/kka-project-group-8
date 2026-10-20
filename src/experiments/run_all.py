"""Main comparison experiment: n x Skenario tahun x seeds x {Greedy, HC, SA, GA}, plus Exact for small n,
and the follow-up analyses (convergence, scalability, sensitivity sweep, decay ablation, case study).

    python -m src.experiments.run_all --config config.yaml [--quick] [--out results] [--workers K]
                                      [--firms | --firms-only]

--firms adds phase 2 (Klaster hotspot FIRMS, see src/experiments/firms_phase.py) after the province
experiment; --firms-only runs just phase 2 and reads the province runs from <out>/raw/runs.csv. Phase 2
is skipped with a log message if the FIRMS snapshot is missing. A full run into results/ refreshes the
generated documentation blocks (python -m src.docs_gen).

Writes (under --out): raw/runs.csv (one row per run), raw/histories.jsonl.gz (convergence history per
run), raw/sensitivity_runs.csv, tables/{summary,optimality_gap,wilcoxon_holm,instances,scalability,
sensitivity,decay_ablation_*,case_study_route}.{csv,md}, tables/convergence.csv,
figures/{boxplot_fitness_n*,convergence_n*,scalability,sensitivity,best_route_map}.png, routes/,
logs/run_all.log. Runs are spread over worker processes; every run depends only on
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

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.algorithms import SOLVERS
from src.algorithms.exact import MAX_NODES as EXACT_MAX_NODES
from src.config import load_config, province_coords, province_features, province_instance
from src.data_prep import SCENARIOS
from src.experiments import analysis, firms_phase, plots
from src.experiments.records import HEURISTICS, run_record
from src.numfmt import id_format
from src.experiments.reporting import (to_markdown_id, ABLATION_ORDER_ID, ABLATION_ROUTES_ID, ABLATION_SEEDS_ID, CASE_STUDY_ID,
                                       GAP_ID, INSTANCES_ID, SCALABILITY_ID, SENSITIVITY_ID, SUMMARY_ID,
                                       WILCOXON_ID, write_table)
from src.experiments.stats import (convergence_table, optimality_gap_table,
                                   scalability_table, sensitivity_table, summary_table, wilcoxon_holm_table)
from src.instance import INSTANCE_SIZES

EXACT_BUDGET = 10**7
log = logging.getLogger("run_all")

_features = _coords = _cfg = None
_instances = {}


def _init(features, coords, cfg):
    global _features, _coords, _cfg
    _features, _coords, _cfg = features, coords, cfg; _instances.clear()


def _instance(n, scenario, overrides=()):
    if (n, scenario, overrides) not in _instances:
        _instances[n, scenario, overrides] = province_instance(_cfg, _features, _coords, n, scenario, overrides)
    return _instances[n, scenario, overrides]


def run_one(task):
    """One run of one algorithm on one instance; returns (row, history, best_route, best_perm).

    task is (scenario, n, algorithm, seed, budget[, overrides])."""
    scenario, n, algorithm, seed, budget, *rest = task
    overrides = rest[0] if rest else ()
    res = SOLVERS[algorithm](_instance(n, scenario, overrides), budget=budget, seed=seed)
    return run_record(res, algorithm, seed, budget, {"n": n, "scenario": scenario})


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


SENSITIVITY_PARAMS = ("time_limit_hours", "decay_g0")


def analysis_n(cfg, quick, key):
    """Instance size for an analysis block (sensitivity / case_study); quick mode uses quick.sensitivity_n."""
    return int(cfg["quick"]["sensitivity_n"]) if quick else int(cfg["analysis"][key]["n"])


def plan_sensitivity(cfg, quick):
    """One-at-a-time sweep: for each parameter value (others at their defaults), every seed x heuristic.
    Returns [(parameter, value, task)]; the task carries the parameter as an instance override."""
    sens = cfg["analysis"]["sensitivity"]; n = analysis_n(cfg, quick, "sensitivity")
    seeds = cfg["quick"]["seeds"] if quick else cfg["seeds"]; budget = budget_for(n, cfg, quick)
    return [(p, v, (str(sens["scenario"]), n, a, s, budget, ((p, v),)))
            for p in SENSITIVITY_PARAMS for v in sens[p] for s in range(seeds) for a in HEURISTICS]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Eksperimen perbandingan utama")
    ap.add_argument("--config", default=str(ROOT / "config.yaml"))
    ap.add_argument("--quick", action="store_true", help="mode cepat (smoke test)")
    ap.add_argument("--out", default=str(ROOT / "results"))
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    ap.add_argument("--firms", action="store_true", help="jalankan juga fase FIRMS (Klaster hotspot)")
    ap.add_argument("--firms-only", action="store_true",
                    help="hanya fase FIRMS; hasil provinsi dibaca dari <out>/raw/runs.csv bila ada")
    args = ap.parse_args(argv)
    t_start = time.perf_counter()
    cfg = load_config(args.config)
    out = Path(args.out)
    for sub in ["raw", "tables", "routes", "figures", "logs"]: (out / sub).mkdir(parents=True, exist_ok=True)
    log_name = "firms.log" if args.firms_only else "run_all.log"
    handler = logging.FileHandler(out / "logs" / log_name, mode="w", encoding="utf8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    log.handlers.clear(); log.addHandler(handler); log.addHandler(logging.StreamHandler()); log.setLevel(logging.INFO)
    log.propagate = False
    try:
        _run(cfg, args, out, t_start)
    finally:
        handler.close(); log.handlers.clear()


def _run(cfg, args, out, t_start):
    coords = province_coords()
    if args.firms_only:
        prov_csv = out / "raw" / "runs.csv"
        runs = pd.read_csv(prov_csv) if prov_csv.exists() else None
        if runs is None: log.info("Hasil provinsi (%s) tidak ada; grafik gabungan hanya memuat FIRMS", prov_csv)
    else:
        runs = _run_province(cfg, args, out, coords)
    if args.firms or args.firms_only:
        firms_phase.run(cfg, out, coords, runs, quick=args.quick, workers=args.workers)
    if not args.quick and out.resolve() == (ROOT / "results").resolve():
        from src import docs_gen  # AUTO blocks (daftar gambar, ringkasan) of README/docs from results/
        docs_gen.main([])
    _finish(t_start, out)


def _run_province(cfg, args, out, coords):
    features = province_features(cfg)
    tasks = plan(cfg, args.quick)
    log.info("Mode: %s; %d run; %d worker; Batas waktu misi %s jam untuk semua instance",
             "cepat" if args.quick else "penuh", len(tasks), args.workers, cfg["time_limit_hours"])
    instance_rows = []
    for scenario, n in dict.fromkeys((t[0], t[1]) for t in tasks):
        inst = province_instance(cfg, features, coords, n, scenario)
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
    sens_plan = plan_sensitivity(cfg, args.quick)
    log.info("Sweep sensitivitas: %d run tambahan", len(sens_plan))
    all_tasks = tasks + [t for _, _, t in sens_plan]
    t_runs = time.perf_counter()
    if args.workers > 1:
        with Pool(args.workers, initializer=_init, initargs=(features, coords, cfg)) as pool:
            all_results = pool.map(run_one, all_tasks, chunksize=1)
    else:
        _init(features, coords, cfg); all_results = [run_one(t) for t in all_tasks]
    log.info("Semua run selesai dalam %.1f s", time.perf_counter() - t_runs)
    results, sens_results = all_results[:len(tasks)], all_results[len(tasks):]

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
    scal = scalability_table(runs, HEURISTICS)
    write_table(scal, out / "tables" / "scalability", SCALABILITY_ID)
    plots.scalability(scal, list(HEURISTICS), out / "figures" / "scalability.png")
    conv_sizes = sorted(runs.n.unique())[-2:]  # n=25 dan n=38 pada mode penuh
    conv = convergence_table([r[1] for r in results], runs, conv_sizes, HEURISTICS)
    conv.to_csv(out / "tables" / "convergence.csv", index=False)  # data kurva; terlalu panjang untuk .md
    for n in conv_sizes:
        plots.convergence(conv, n, list(HEURISTICS), out / "figures" / f"convergence_n{n}.png")

    sens_runs = pd.DataFrame([{"parameter": p, "value": v, **r[0],
                               "time_limit_h": dict(t[5]).get("time_limit_hours", cfg["time_limit_hours"]),
                               "decay_g0": dict(t[5]).get("decay_g0", cfg["decay_g0"]),
                               "best_perm": json.dumps(r[3])}
                              for (p, v, t), r in zip(sens_plan, sens_results)])
    sens_runs.to_csv(out / "raw" / "sensitivity_runs.csv", index=False)
    sens = sensitivity_table(sens_runs)
    write_table(sens, out / "tables" / "sensitivity", SENSITIVITY_ID)
    plots.sensitivity(sens, list(HEURISTICS), out / "figures" / "sensitivity.png")

    # Ablasi decay: g0 default vs g0=0 dari sweep sensitivitas (instance, seed dan budget sama).
    g = sens_runs[sens_runs.parameter == "decay_g0"]
    decay_runs, static_runs = g[g.value == cfg["decay_g0"]], g[g.value == 0]
    sn, ssc = int(decay_runs.n.iloc[0]), str(decay_runs.scenario.iloc[0])
    decay_inst = province_instance(cfg, features, coords, sn, ssc)
    static_inst = province_instance(cfg, features, coords, sn, ssc, (("decay_g0", 0.),))
    bd, bs = decay_runs.loc[decay_runs.fitness.idxmax()], static_runs.loc[static_runs.fitness.idxmax()]
    abl_routes, abl_order = analysis.decay_ablation(
        decay_inst, static_inst, json.loads(bd.best_perm), json.loads(bs.best_perm),
        {"algorithm": bd.algorithm, "seed": int(bd.seed)}, {"algorithm": bs.algorithm, "seed": int(bs.seed)})
    write_table(abl_routes, out / "tables" / "decay_ablation_routes", ABLATION_ROUTES_ID)
    write_table(abl_order, out / "tables" / "decay_ablation_order", ABLATION_ORDER_ID)
    write_table(analysis.decay_ablation_by_seed(decay_inst, decay_runs, static_runs),
                out / "tables" / "decay_ablation_seeds", ABLATION_SEEDS_ID)

    # Best route per instance (best heuristic run; ties -> first in run order).
    for (scenario, n), grp in runs.groupby(["scenario", "n"], sort=False):
        idx = grp[grp.algorithm.isin(HEURISTICS)].fitness.idxmax(); row = runs.loc[idx]
        detail = {"scenario": scenario, "n": int(n), "algorithm": row.algorithm, "seed": int(row.seed),
                  **results[idx][2]}
        (out / "routes" / f"best_route_{scenario}_n{n}.json").write_text(
            json.dumps(detail, indent=2, ensure_ascii=False), encoding="utf8")
        if (scenario, n) == (str(cfg["analysis"]["case_study"]["scenario"]), analysis_n(cfg, args.quick, "case_study")):
            inst = province_instance(cfg, features, coords, int(n), scenario)
            title = f"Studi kasus: rute terbaik skenario {scenario}, n={n} ({row.algorithm}, seed {row.seed})"
            plots.route_map(coords, inst, results[idx][2], title, out / "figures" / "best_route_map.png")
            cs = analysis.case_study_table(inst, results[idx][2])
            cs.to_csv(out / "tables" / "case_study_route.csv", index=False)
            r = results[idx][2]
            header = (f"# {title}\n\nDepot: {inst.names[inst.depot]}. Batas waktu misi "
                      f"{id_format(inst.time_limit, 'g')} jam; total Prize {id_format(r['fitness'], '.4f')}; "
                      f"{len(r['route'])} Kunjungan, {len(r['skipped'])} Node dilewati; total jarak "
                      f"{id_format(r['distance_km'], ',.0f')} km; waktu misi {id_format(r['mission_time_h'], '.2f')} "
                      f"jam (sisa {id_format(r['remaining_time_h'], '.2f')} jam).\n\n")
            (out / "tables" / "case_study_route.md").write_text(
                header + to_markdown_id(cs.rename(columns=CASE_STUDY_ID)) + "\n",
                encoding="utf8")
    return runs


def _finish(t_start, out):
    total = time.perf_counter() - t_start
    log.info("Total runtime eksperimen: %.1f s (%.1f menit)", total, total / 60)
    print(f"Selesai. Keluaran ada di {out}.")


if __name__ == "__main__":
    main()
