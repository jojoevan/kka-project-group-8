"""Main comparison experiment: n x Skenario tahun x seeds x {Greedy, HC, SA, GA}, plus Exact for small n,
and the follow-up analyses (convergence, scalability, sensitivity sweep, decay ablation, case study).

    python -m src.experiments.run_all --config config.yaml [--quick] [--out results] [--workers K]

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
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.algorithms import SOLVERS
from src.algorithms.exact import MAX_NODES as EXACT_MAX_NODES
from src.data_prep import SCENARIOS, prepare
from src.experiments import analysis, firms_phase, plots
from src.experiments.stats import (convergence_table, evals_to_fraction, optimality_gap_table,
                                   scalability_table, sensitivity_table, summary_table, wilcoxon_holm_table)
from src.instance import INSTANCE_SIZES, build_instance

HEURISTICS = ("Greedy", "HC", "SA", "GA")
EXACT_BUDGET = 10**7
log = logging.getLogger("run_all")

_features = _coords = _cfg = None
_instances = {}


def _init(features, coords, cfg):
    global _features, _coords, _cfg
    _features, _coords, _cfg = features, coords, cfg; _instances.clear()


def make_instance(features, coords, cfg, n, scenario, overrides=()):
    """Instance from the config; overrides are (config key, value) pairs, e.g. (("decay_g0", 0.),)."""
    c = {**cfg, **dict(overrides)}
    return build_instance(features, coords, n=n, scenario=scenario, depot_name=c["depot"],
                          speed=c["speed_kmh"], detour=c["detour_factor"], dwell=c["dwell_hours"],
                          time_limit=c["time_limit_hours"], g0=c["decay_g0"], kappa=c["decay_kappa"])


def _instance(n, scenario, overrides=()):
    if (n, scenario, overrides) not in _instances:
        _instances[n, scenario, overrides] = make_instance(_features, _coords, _cfg, n, scenario, overrides)
    return _instances[n, scenario, overrides]


def run_one(task):
    """One run of one algorithm on one instance; returns (row, history, best_route, best_perm).

    task is (scenario, n, algorithm, seed, budget[, overrides])."""
    scenario, n, algorithm, seed, budget, *rest = task
    overrides = rest[0] if rest else ()
    res = SOLVERS[algorithm](_instance(n, scenario, overrides), budget=budget, seed=seed)
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
    return row, hist, route, [int(x) for x in res["best_perm"]]


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
SCALABILITY_ID = {"scenario": "skenario", "algorithm": "algoritma", "runtime_mean_s": "runtime rata-rata (s)",
                  "runtime_std_s": "runtime simpangan baku (s)", "quality_mean_pct": "kualitas rata-rata (% best-known)",
                  "quality_std_pct": "kualitas simpangan baku (%)", "visited_mean": "node dikunjungi rata-rata"}
SENSITIVITY_ID = {"parameter": "parameter", "value": "nilai", "scenario": "skenario", "algorithm": "algoritma",
                  "runs": "jumlah run", "best": "terbaik", "mean": "rata-rata", "std": "simpangan baku",
                  "median": "median", "visited_mean": "node dikunjungi rata-rata",
                  "mission_time_mean_h": "waktu misi rata-rata (jam)", "runtime_mean_s": "runtime rata-rata (s)",
                  "quality_mean_pct": "kualitas rata-rata (% terbaik setting)"}
ABLATION_ROUTES_ID = {"variant": "varian rute", "algorithm": "algoritma",
                      "fitness_with_decay": "Prize dengan decay", "fitness_without_decay": "Prize tanpa decay",
                      "visited": "node dikunjungi", "mission_time_h": "waktu misi (jam)", "distance_km": "jarak (km)",
                      "ops_visited": "provinsi ber-data operasional dikunjungi",
                      "ops_mean_position": "urutan rata-rata provinsi ber-data operasional",
                      "ops_mean_arrival_h": "waktu tiba rata-rata provinsi ber-data operasional (jam)",
                      "prize_lost": "Prize hilang (dievaluasi dengan decay)", "prize_lost_pct": "Prize hilang (%)"}
ABLATION_ORDER_ID = {"province": "provinsi", "risk": "Risiko", "ops": "keparahan operasional (ops)",
                     "position_decay": "urutan (dengan decay)", "arrival_decay_h": "tiba (dengan decay, jam)",
                     "position_static": "urutan (tanpa decay)", "arrival_static_h": "tiba (tanpa decay, jam)",
                     "position_shift": "pergeseran urutan (tanpa - dengan)"}
CASE_STUDY_ID = {"order": "urutan", "province": "provinsi", "status": "status", "risk": "Risiko",
                 "ops": "keparahan operasional (ops)", "leg_km": "jarak dari node sebelumnya (km)",
                 "arrival_h": "tiba (jam)", "departure_h": "berangkat (jam)", "prize": "Prize"}
ABLATION_SEEDS_ID = {"algorithm": "algoritma", "seeds": "jumlah seed",
                     "decay_route_with_decay_mean": "Prize rute dengan decay (rata-rata)",
                     "static_route_with_decay_mean": "Prize rute tanpa decay, dievaluasi dengan decay (rata-rata)",
                     "prize_lost_mean": "Prize hilang rata-rata", "prize_lost_mean_pct": "Prize hilang rata-rata (%)",
                     "prize_lost_max_pct": "Prize hilang maks (%)",
                     "seeds_static_worse": "seed dengan rute tanpa decay lebih buruk"}


FIRMS_INDEX = (
    "\n## Fase 2: Klaster hotspot FIRMS (snapshot VIIRS S-NPP 7 hari, diunduh 2026-10-20 UTC)\n\n"
    "- `results/figures/scalability_combined.png`: Skalabilitas gabungan: runtime per run (log) dan kualitas "
    "(% best-known) terhadap jumlah node kandidat untuk instance provinsi (skenario 2026, garis penuh) dan "
    "instance FIRMS k=50/100/200 (garis putus-putus, area berlabel) (tabel: `results/tables/scalability_combined.md`).\n"
    "- `results/figures/firms_cluster_map_k100.png`: Peta sebaran hotspot dan 100 Klaster hotspot (warna = Risiko) "
    "dengan rute terbaik, nomor urut, Node dilewati, dan Depot Pekanbaru (rute: `results/routes/best_route_firms_k100.json`).\n"
    "- `results/figures/firms_boxplot_fitness.png`: Sebaran fitness akhir 30 seed per algoritma untuk tiap k FIRMS.\n"
    "\n### Tabel FIRMS\n\n"
    "- `results/tables/firms_instances.md`, `results/tables/firms_calibration.md`: ukuran instance, jumlah hotspot, "
    "dan kalibrasi Batas waktu misi (greedy k=100).\n"
    "- `results/tables/firms_summary.md`, `results/tables/firms_wilcoxon_holm.md`: ringkasan 30 seed dan uji "
    "Wilcoxon-Holm per k.\n"
    "- `results/tables/firms_ranking.md`: pernyataan apakah peringkat algoritma instance provinsi tetap berlaku "
    "pada instance FIRMS.\n"
    "- `results/tables/firms_hc_cost.md`: ukuran neighbourhood Steepest-Ascent HC (O(n²)) terhadap budget evaluasi, "
    "restart dan langkah naik HC, serta waktu per evaluasi.\n"
    "- `results/tables/firms_clusters_k{50,100,200}.md`: daftar klaster (lokasi, jumlah hotspot, Σ FRP, Risiko).\n")


def write_figures_index(firms):
    """reports/figures_index.md for a full run; the FIRMS section only if the FIRMS phase produced output."""
    text = (
            "# Daftar gambar\n\n"
            "- `results/figures/boxplot_fitness_n{6,10,15,25,38}.png`: Sebaran fitness akhir 30 seed per "
            "algoritma (Greedy, HC, SA, GA) untuk tiap n, satu panel per Skenario tahun.\n"
            "- `results/figures/convergence_n{25,38}.png`: Kurva konvergensi (fitness terbaik sejauh ini, "
            "rata-rata ± simpangan baku 30 seed) terhadap jumlah evaluasi, per algoritma dan Skenario tahun.\n"
            "- `results/figures/scalability.png`: Runtime per run (skala log) dan kualitas solusi (% best-known) "
            "terhadap ukuran instance n, per algoritma dan Skenario tahun.\n"
            "- `results/figures/sensitivity.png`: Sensitivitas fitness akhir dan jumlah Kunjungan terhadap Batas "
            "waktu misi (24/48/72/120 jam) dan g0 (0/0,005/0,01/0,02), n=38 skenario 2026, 30 seed "
            "(tabel: `results/tables/sensitivity.md`).\n"
            "- `results/figures/best_route_map.png`: Peta studi kasus rute terbaik skenario 2026 n=38: Depot, panah "
            "arah, nomor urut, waktu tiba, dan Node dilewati (tabel: `results/tables/case_study_route.md`).\n"
            "\n## Tabel analisis lanjutan (tanpa gambar)\n\n"
            "- `results/tables/decay_ablation_routes.md`: Rute terbaik dengan decay vs dengan g0=0, keduanya "
            "dievaluasi dengan dan tanpa decay; Prize hilang bila decay diabaikan.\n"
            "- `results/tables/decay_ablation_order.md`: Urutan dan waktu tiba tiap provinsi pada kedua rute.\n"
            "- `results/tables/decay_ablation_seeds.md`: Prize hilang per algoritma, berpasangan per seed.\n"
            "- `results/tables/scalability.md`, `results/tables/convergence.csv`: data grafik skalabilitas dan "
            "kurva konvergensi.\n")
    if firms: text += FIRMS_INDEX
    (ROOT / "reports" / "figures_index.md").write_text(text, encoding="utf8")


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
    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf8"))
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
    coords = pd.read_csv(ROOT / "data" / "external" / "province_coords.csv")
    if args.firms_only:
        prov_csv = out / "raw" / "runs.csv"
        runs = pd.read_csv(prov_csv) if prov_csv.exists() else None
        if runs is None: log.info("Hasil provinsi (%s) tidak ada; grafik gabungan hanya memuat FIRMS", prov_csv)
    else:
        runs = _run_province(cfg, args, out, coords)
    firms_done = False
    if args.firms or args.firms_only:
        firms_done = firms_phase.run(cfg, args.quick, args.workers, out, ROOT, coords, runs, log, write_table,
                                     HEURISTICS)
    if not args.quick:
        write_figures_index(firms_done or (out / "raw" / "firms_runs.csv").exists())
    _finish(t_start, out)


def _run_province(cfg, args, out, coords):
    w = cfg["weights"]
    features = prepare(weights=(w["hist"], w["cur"], w["ops"]), gamma=cfg["gamma"])[0]
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
    decay_inst = make_instance(features, coords, cfg, sn, ssc)
    static_inst = make_instance(features, coords, cfg, sn, ssc, (("decay_g0", 0.),))
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
            inst = make_instance(features, coords, cfg, int(n), scenario)
            title = f"Studi kasus: rute terbaik skenario {scenario}, n={n} ({row.algorithm}, seed {row.seed})"
            plots.route_map(coords, inst, results[idx][2], title, out / "figures" / "best_route_map.png")
            cs = analysis.case_study_table(inst, results[idx][2])
            cs.to_csv(out / "tables" / "case_study_route.csv", index=False)
            r = results[idx][2]
            header = (f"# {title}\n\nDepot: {inst.names[inst.depot]}. Batas waktu misi {inst.time_limit:g} jam; "
                      f"total Prize {r['fitness']:.4f}; {len(r['route'])} Kunjungan, {len(r['skipped'])} Node "
                      f"dilewati; total jarak {r['distance_km']:.0f} km; waktu misi {r['mission_time_h']:.2f} jam "
                      f"(sisa {r['remaining_time_h']:.2f} jam).\n\n")
            (out / "tables" / "case_study_route.md").write_text(
                header + cs.rename(columns=CASE_STUDY_ID).to_markdown(index=False, floatfmt=".4g") + "\n",
                encoding="utf8")
    return runs


def _finish(t_start, out):
    total = time.perf_counter() - t_start
    log.info("Total runtime eksperimen: %.1f s (%.1f menit)", total, total / 60)
    print(f"Selesai. Keluaran ada di {out}.")


if __name__ == "__main__":
    main()
