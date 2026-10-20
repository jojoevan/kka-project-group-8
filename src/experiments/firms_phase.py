"""Phase 2 (#6, ADR-0001): scalability experiment on Klaster hotspot instances from the FIRMS snapshot.

k in firms.sizes x seeds x {Greedy, HC, SA, GA} with the FIRMS evaluation budget. The Batas waktu misi
is calibrated once (greedy on k = firms.calibration_k, same utility as the province instance) and
used for every k. Writes raw/firms_runs.csv, raw/firms_histories.jsonl.gz, tables/firms_*.{csv,md},
tables/scalability_combined.{csv,md}, figures/{firms_boxplot_fitness,scalability_combined,
firms_cluster_map_k*}.png and routes/best_route_firms_k*.json. Skipped cleanly if the snapshot is missing.
"""
import gzip
import json
import time
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd
from src.algorithms import SOLVERS
from src.algorithms.common import all_moves
from src.calibration import calibrate_time_limit
from src.experiments import plots
from src.experiments.stats import evals_to_fraction, scalability_table, summary_table, wilcoxon_holm_table
from src.firms import build_firms_instance, load_hotspots

FAMILY = "FIRMS"
_instances = {}


def _init(instances):
    _instances.clear(); _instances.update(instances)


def run_one(task):
    k, algorithm, seed, budget = task
    inst = _instances[k]
    res = SOLVERS[algorithm](inst, budget=budget, seed=seed); extra = res.get("extra", {})
    route = res["best_route"]
    row = {"algorithm": algorithm, "k": k, "n": k + 1, "scenario": FAMILY, "seed": seed,
           "fitness": res["best_fitness"], "runtime_s": res["runtime"], "evals": res["evals"], "budget": budget,
           "evals_to_95": evals_to_fraction(res["history"], .95),
           "hc_single_start_fitness": extra.get("single_start_fitness") if algorithm == "HC" else None,
           "hc_restarts": extra.get("restarts") if algorithm == "HC" else None,
           "hc_steps": extra.get("steps") if algorithm == "HC" else None,
           "sa_acceptance_rate": extra.get("acceptance_rate") if algorithm == "SA" else None,
           "ga_generations": extra.get("generations") if algorithm == "GA" else None,
           "visited": len(route["route"]), "mission_time_h": route["mission_time_h"],
           "time_limit_h": inst.time_limit}
    hist = {"algorithm": algorithm, "k": k, "seed": seed, "history": [[int(e), float(v)] for e, v in res["history"]]}
    return row, hist, route, [int(x) for x in res["best_perm"]]


def snapshot_path(cfg, root):
    p = Path(cfg["firms"]["snapshot"])
    return p if p.is_absolute() else Path(root) / p


def settings(cfg, quick):
    f = cfg["firms"]
    if quick:
        q = f["quick"]; sizes = list(q["sizes"])
        return sizes, int(q["seeds"]), int(q["budget"]), max(sizes), max(sizes)
    return list(f["sizes"]), int(cfg["seeds"]), int(f["budget"]), int(f["calibration_k"]), int(f["map_k"])


def depot_of(cfg, coords):
    row = coords.set_index("Provinsi").loc[cfg["depot"]]
    return {"name": str(row.Ibukota), "lat": float(row.lat), "lon": float(row.lon)}


def build_all(cfg, hotspots, depot, sizes, calibration_k):
    """Instances per k with one calibrated Batas waktu misi; returns (instances, nodes, calibration)."""
    def make(k, T):
        return build_firms_instance(hotspots, k, depot=depot, seed=int(cfg["firms"]["kmeans_seed"]),
                                    speed=cfg["speed_kmh"], detour=cfg["detour_factor"], dwell=cfg["dwell_hours"],
                                    time_limit=T, g0=cfg["decay_g0"])
    cal = calibrate_time_limit(make(calibration_k, 72.)[0])
    T = float(cal["time_limit"]); instances, nodes = {}, {}
    for k in sizes: instances[k], nodes[k] = make(k, T)
    return instances, nodes, cal


def hc_cost_table(firms_runs, province_runs):
    """Per instance size: Steepest-Ascent HC neighbourhood size (O(n^2)) against the budget, with the
    restarts/steps HC actually made, and the runtime per evaluation of each algorithm."""
    rows = []
    for family, runs in (("provinsi", province_runs), (FAMILY, firms_runs)):
        if runs is None or runs.empty: continue
        for (sc, n), g in runs[runs.algorithm.isin(["HC", "SA", "GA"])].groupby(["scenario", "n"]):
            hc = g[g.algorithm == "HC"]; m = int(n) - 1; budget = int(hc.budget.iloc[0])
            neigh = len(all_moves(m))
            row = {"instance_family": family, "scenario": str(sc), "n": int(n), "candidates": m,
                   "neighbourhood_size": neigh, "budget": budget, "budget_per_neighbourhood": budget / neigh,
                   "hc_restarts_mean": hc.hc_restarts.mean(),
                   "hc_steps_mean": hc.hc_steps.mean() if "hc_steps" in hc else np.nan,
                   "hc_single_start_mean": hc.hc_single_start_fitness.mean(), "hc_fitness_mean": hc.fitness.mean()}
            for a in ("HC", "SA", "GA"):
                s = g[g.algorithm == a]
                row[f"{a.lower()}_us_per_eval"] = 1e6 * (s.runtime_s / s.evals).mean()
            rows.append(row)
    return pd.DataFrame(rows)


def ranking(summary):
    """Algorithm order by mean fitness per instance (best first)."""
    return {key: g.sort_values("mean", ascending=False, kind="stable").algorithm.tolist()
            for key, g in summary.groupby(["scenario", "n"])}


def _pairs(order):
    return {(a, b) for i, a in enumerate(order) for b in order[i + 1:]}


def ranking_report(province_summary, province_wilcoxon, firms_summary, firms_wilcoxon, sizes):
    """Markdown statement (generated from the data) of whether the province ranking holds on FIRMS,
    and the per-instance ranking table."""
    def sig(w, sc, n, a, b):
        r = w[(w.scenario.astype(str) == str(sc)) & (w.n == n) & (((w.algorithm_a == a) & (w.algorithm_b == b)) |
                                                                ((w.algorithm_a == b) & (w.algorithm_b == a)))]
        return bool(r["significant_0.05"].iloc[0]) if len(r) else False
    rows = []; lines = ["# Apakah peringkat algoritma instance provinsi tetap berlaku pada instance FIRMS?", ""]
    pr = ranking(province_summary) if province_summary is not None else {}
    fr = ranking(firms_summary)
    for (sc, n), order in sorted(pr.items(), key=lambda x: (str(x[0][0]), x[0][1])):
        rows.append({"instance": f"provinsi {sc}, n={n}", "peringkat (rata-rata fitness, terbaik dulu)": " > ".join(order)})
    for (sc, n), order in sorted(fr.items(), key=lambda x: x[0][1]):
        rows.append({"instance": f"FIRMS k={n - 1} (n={n})", "peringkat (rata-rata fitness, terbaik dulu)": " > ".join(order)})
    if not pr:
        lines += ["Hasil provinsi tidak tersedia, sehingga peringkat tidak dapat dibandingkan.", ""]
    else:
        ref_key = max((k for k in pr if str(k[0]) == "2026"), key=lambda k: k[1], default=max(pr, key=lambda k: k[1]))
        ref = pr[ref_key]
        lines += [f"Acuan: instance provinsi terbesar, skenario {ref_key[0]} n={ref_key[1]}: **{' > '.join(ref)}** "
                  "(urut rata-rata fitness 30 seed).", ""]
        holds_all = True
        for (sc, n), order in sorted(fr.items(), key=lambda x: x[0][1]):
            flipped = sorted(_pairs(ref) - _pairs(order))
            if not flipped:
                lines.append(f"- FIRMS k={n - 1}: {' > '.join(order)}. Peringkat provinsi **tetap berlaku**.")
                continue
            holds_all = False
            desc = []
            for a, b in flipped:  # a above b on provinces, b above a on FIRMS
                s_f = "signifikan" if sig(firms_wilcoxon, sc, n, a, b) else "tidak signifikan"
                s_p = "signifikan" if sig(province_wilcoxon, ref_key[0], ref_key[1], a, b) else "tidak signifikan"
                desc.append(f"{b} di atas {a} (FIRMS: {s_f}; provinsi: {s_p}, Wilcoxon-Holm 0,05)")
            lines.append(f"- FIRMS k={n - 1}: {' > '.join(order)}. Peringkat provinsi **tidak tetap berlaku**: "
                         + "; ".join(desc) + ".")
        lines += ["", "Kesimpulan: peringkat provinsi " + ("**tetap berlaku** pada semua instance FIRMS."
                                                          if holds_all else
                                                          "**tidak tetap berlaku** sepenuhnya pada instance FIRMS "
                                                          "(lihat pasangan yang bertukar di atas).")]
    table = pd.DataFrame(rows)
    return "\n".join(lines) + "\n\n" + table.to_markdown(index=False) + "\n", table


def combined_scalability(province_runs, firms_runs, algorithms):
    parts = []
    if province_runs is not None and not province_runs.empty:
        parts.append(scalability_table(province_runs, algorithms).assign(instance_family="provinsi"))
    parts.append(scalability_table(firms_runs, algorithms).assign(instance_family=FAMILY))
    t = pd.concat(parts, ignore_index=True)
    t["scenario"] = t.scenario.astype(str); t["candidates"] = t.n - 1
    return t


def run(cfg, quick, workers, out, root, coords, province_runs, log, write_table, heuristics):
    """Runs the FIRMS phase; returns False (after logging) if the snapshot is missing."""
    path = snapshot_path(cfg, root)
    if not path.exists():
        log.warning("Snapshot FIRMS tidak ditemukan (%s); fase FIRMS dilewati.", path)
        return False
    f = cfg["firms"]
    hotspots = load_hotspots(path, f["confidence"], f["bboxes"])
    log.info("Snapshot FIRMS %s: %d hotspot setelah filter confidence %s dan bounding box (%s)", path.name,
             len(hotspots), "/".join(f["confidence"]),
             ", ".join(f"{r} {c}" for r, c in hotspots.region.value_counts().sort_index().items()))
    sizes, seeds, budget, cal_k, map_k = settings(cfg, quick)
    depot = depot_of(cfg, coords)
    instances, nodes, cal = build_all(cfg, hotspots, depot, sizes, cal_k)
    T = float(cal["time_limit"])
    log.info("Batas waktu misi FIRMS: %g jam (greedy k=%d mengunjungi %.0f%% klaster, %s)", T, cal_k,
             100 * cal["visited_fraction"], "dalam target" if cal["in_target"] else "TIDAK dalam target; terdekat")
    write_table(cal["table"], out / "tables" / "firms_calibration",
                {"time_limit_h": "Batas waktu misi (jam)", "visited": "klaster terkunjungi Greedy",
                 "visited_fraction": "fraksi terkunjungi"})
    tasks = [(k, a, s, budget) for k in sizes for s in range(seeds) for a in heuristics]
    log.info("FIRMS: %d run (k=%s, %d seed, budget %d), %d worker", len(tasks), sizes, seeds, budget, workers)
    t0 = time.perf_counter()
    if workers > 1:
        with Pool(workers, initializer=_init, initargs=(instances,)) as pool:
            results = pool.map(run_one, tasks, chunksize=1)
    else:
        _init(instances); results = [run_one(t) for t in tasks]
    log.info("Semua run FIRMS selesai dalam %.1f s", time.perf_counter() - t0)

    runs = pd.DataFrame([r[0] for r in results])
    runs.to_csv(out / "raw" / "firms_runs.csv", index=False)
    with gzip.open(out / "raw" / "firms_histories.jsonl.gz", "wt", encoding="utf8") as fh:
        for r in results: fh.write(json.dumps(r[1]) + "\n")
    for k in sizes:
        log.info("FIRMS k=%d: runtime rata-rata %s", k, ", ".join(
            f"{a} {runs[(runs.k == k) & (runs.algorithm == a)].runtime_s.mean():.2f} s" for a in heuristics))

    inst_rows = []
    for k in sizes:
        g = SOLVERS["Greedy"](instances[k])["best_route"]
        inst_rows.append({"k": k, "n": k + 1, "hotspots": int(nodes[k].hotspots.sum()),
                          "frp_total": float(nodes[k].frp_sum.sum()), "depot": depot["name"], "budget": budget,
                          "time_limit_h": T, "greedy_visited": len(g["route"]),
                          "greedy_visited_fraction": len(g["route"]) / k,
                          "greedy_mission_time_h": g["mission_time_h"], "g0": cfg["decay_g0"]})
        write_table(nodes[k], out / "tables" / f"firms_clusters_k{k}",
                    {"name": "klaster", "lat": "lintang", "lon": "bujur", "hotspots": "jumlah hotspot",
                     "frp_sum": "Σ FRP (MW)", "region": "wilayah", "risk": "Risiko"})
    write_table(pd.DataFrame(inst_rows), out / "tables" / "firms_instances",
                {"hotspots": "hotspot", "frp_total": "Σ FRP total (MW)", "budget": "budget evaluasi",
                 "time_limit_h": "Batas waktu misi (jam)", "greedy_visited": "terkunjungi Greedy",
                 "greedy_visited_fraction": "fraksi terkunjungi Greedy",
                 "greedy_mission_time_h": "waktu misi Greedy (jam)"})
    from src.experiments.run_all import SCALABILITY_ID, SUMMARY_ID, WILCOXON_ID
    fsum = summary_table(runs); fw = wilcoxon_holm_table(runs, list(heuristics))
    write_table(fsum.assign(k=fsum.n - 1), out / "tables" / "firms_summary", SUMMARY_ID)
    write_table(fw.assign(k=fw.n - 1), out / "tables" / "firms_wilcoxon_holm", WILCOXON_ID)
    plots.boxplot_fitness_firms(runs, list(heuristics), out / "figures" / "firms_boxplot_fitness.png")

    prov = province_runs[province_runs.algorithm.isin(heuristics)] if province_runs is not None else None
    hc = hc_cost_table(runs, prov)
    write_table(hc, out / "tables" / "firms_hc_cost",
                {"instance_family": "jenis instance", "scenario": "skenario", "candidates": "node kandidat",
                 "neighbourhood_size": "ukuran neighbourhood HC", "budget": "budget evaluasi",
                 "budget_per_neighbourhood": "budget / neighbourhood (langkah penuh maks.)",
                 "hc_restarts_mean": "restart HC rata-rata", "hc_steps_mean": "langkah naik HC rata-rata",
                 "hc_single_start_mean": "fitness HC single-start rata-rata", "hc_fitness_mean": "fitness HC rata-rata",
                 "hc_us_per_eval": "HC µs/evaluasi", "sa_us_per_eval": "SA µs/evaluasi", "ga_us_per_eval": "GA µs/evaluasi"})

    psum = summary_table(prov) if prov is not None and not prov.empty else None
    pw = wilcoxon_holm_table(prov, list(heuristics)) if psum is not None else None
    md, table = ranking_report(psum, pw, fsum, fw, sizes)
    table.to_csv(out / "tables" / "firms_ranking.csv", index=False)
    (out / "tables" / "firms_ranking.md").write_text(md, encoding="utf8")

    comb = combined_scalability(province_runs, runs, heuristics)  # Exact ikut menentukan best-known provinsi
    write_table(comb, out / "tables" / "scalability_combined",
                {**SCALABILITY_ID, "instance_family": "jenis instance", "candidates": "node kandidat"})
    plots.scalability_combined(comb, list(heuristics), out / "figures" / "scalability_combined.png")

    for k in sizes:
        grp = runs[runs.k == k]; idx = grp.fitness.idxmax(); row = runs.loc[idx]
        detail = {"instance": FAMILY, "k": int(k), "algorithm": row.algorithm, "seed": int(row.seed),
                  "time_limit_h": T, **results[idx][2]}
        (out / "routes" / f"best_route_firms_k{k}.json").write_text(
            json.dumps(detail, indent=2, ensure_ascii=False), encoding="utf8")
        if k == map_k:
            title = (f"Klaster hotspot FIRMS k={k}: rute terbaik ({row.algorithm}, seed {row.seed})")
            plots.firms_cluster_map(hotspots, nodes[k], depot, instances[k], results[idx][2], f["bboxes"], title,
                                    out / "figures" / f"firms_cluster_map_k{k}.png")
    return True
