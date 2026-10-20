"""Phase 2 (#6, ADR-0001): scalability experiment on Klaster hotspot instances from the FIRMS snapshot.

k in firms.sizes x seeds x {Greedy, HC, SA, GA} with the FIRMS evaluation budget. The Batas waktu misi
is calibrated once (greedy on k = firms.calibration_k, same utility as the province instance) and
used for every k. Writes raw/firms_runs.csv, raw/firms_histories.jsonl.gz, tables/firms_*.{csv,md},
tables/scalability_combined.{csv,md}, figures/{firms_boxplot_fitness,scalability_combined,
firms_cluster_map_k*}.png and routes/best_route_firms_k*.json. Skipped cleanly if the snapshot is missing.
"""
import gzip
import json
import logging
import time
from multiprocessing import Pool
from pathlib import Path
from typing import NamedTuple
import numpy as np
import pandas as pd
from src.algorithms import SOLVERS
from src.algorithms.common import all_moves
from src.calibration import calibrate_time_limit
from src.config import cluster_mission_params
from src.data_prep import ROOT
from src.experiments import plots
from src.experiments.records import HEURISTICS, run_record
from src.experiments.reporting import (to_markdown_id, FIRMS_CALIBRATION_ID, FIRMS_CLUSTERS_ID, FIRMS_INSTANCES_ID, HC_COST_ID,
                                       SCALABILITY_COMBINED_ID, SUMMARY_ID, WILCOXON_ID, write_table)
from src.experiments.stats import scalability_table, summary_table, wilcoxon_holm_table
from src.firms import build_firms_instance, load_hotspots

FAMILY = "FIRMS"
log = logging.getLogger("run_all.firms")  # handlers of the run_all logger (log file + console)
_instances = {}


def _init(instances):
    _instances.clear(); _instances.update(instances)


def run_one(task):
    k, algorithm, seed, budget = task
    inst = _instances[k]
    res = SOLVERS[algorithm](inst, budget=budget, seed=seed)
    row, hist, route, perm = run_record(res, algorithm, seed, budget, {"k": k, "n": k + 1, "scenario": FAMILY})
    row["time_limit_h"] = inst.time_limit
    return row, hist, route, perm


def snapshot_path(cfg, root=ROOT):
    p = Path(cfg["firms"]["snapshot"])
    return p if p.is_absolute() else Path(root) / p


class FirmsSettings(NamedTuple):
    sizes: list         # k values (Klaster hotspot per instance)
    seeds: int
    budget: int         # evaluation budget per run
    calibration_k: int  # k of the instance the Batas waktu misi is calibrated on
    map_k: int          # k of the instance drawn on the cluster map


def settings(cfg, quick):
    f = cfg["firms"]
    if quick:
        q = f["quick"]; sizes = list(q["sizes"])
        return FirmsSettings(sizes, int(q["seeds"]), int(q["budget"]), max(sizes), max(sizes))
    return FirmsSettings(list(f["sizes"]), int(cfg["seeds"]), int(f["budget"]), int(f["calibration_k"]),
                         int(f["map_k"]))


def depot_of(cfg, coords):
    row = coords.set_index("Provinsi").loc[cfg["depot"]]
    return {"name": str(row.Ibukota), "lat": float(row.lat), "lon": float(row.lon)}


def build_all(cfg, hotspots, depot, sizes, calibration_k):
    """Instances per k with one calibrated Batas waktu misi; returns (instances, nodes, calibration)."""
    def make(k, T):
        return build_firms_instance(hotspots, k, depot=depot, seed=int(cfg["firms"]["kmeans_seed"]),
                                    **cluster_mission_params(cfg, T))
    cal = calibrate_time_limit(make(calibration_k, float(cfg["time_limit_hours"]))[0])  # T replaced per candidate
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


TIE_RTOL = 1e-9  # mean fitness within this relative tolerance counts as a tie


def ranking(summary):
    """Per instance: tie groups of algorithms by mean fitness, best group first; names sorted in a group.

    A group holds every algorithm within TIE_RTOL (relative) of the group's best mean."""
    out = {}
    for key, g in summary.groupby(["scenario", "n"]):
        groups = []; top = None
        for a, m in g.sort_values("mean", ascending=False, kind="stable")[["algorithm", "mean"]].itertuples(index=False):
            if groups and top - m <= TIE_RTOL * max(abs(top), abs(m)): groups[-1].append(a)
            else: groups.append([a]); top = m
        out[key] = [sorted(grp) for grp in groups]
    return out


def format_ranking(groups):
    """Tie groups as text, e.g. 'SA > Greedy = HC > GA'."""
    return " > ".join(" = ".join(grp) for grp in groups)


def _strict_pairs(groups):
    """(a, b) for every a ranked strictly above b."""
    return {(a, b) for i, grp in enumerate(groups) for a in grp for later in groups[i + 1:] for b in later}


def ranking_report(province_summary, province_wilcoxon, firms_summary, firms_wilcoxon, sizes):
    """Markdown statement (generated from the data) of whether the province ranking holds on FIRMS,
    and the per-instance ranking table.

    The reference is the largest province instance (scenario 2026 if present). On a FIRMS instance the
    ranking holds if every pair strictly ordered on the reference keeps that order; a reversed pair
    breaks it, and a pair that ties on FIRMS is reported as a tie (neither kept nor reversed)."""
    def sig(w, sc, n, a, b):
        r = w[(w.scenario.astype(str) == str(sc)) & (w.n == n) & (((w.algorithm_a == a) & (w.algorithm_b == b)) |
                                                                ((w.algorithm_a == b) & (w.algorithm_b == a)))]
        return bool(r["significant_0.05"].iloc[0]) if len(r) else False
    col = "peringkat (rata-rata fitness, terbaik dulu; = berarti seri)"
    rows = []; lines = ["# Apakah peringkat algoritma instance provinsi tetap berlaku pada instance FIRMS?", ""]
    pr = ranking(province_summary) if province_summary is not None else {}
    fr = ranking(firms_summary)
    for (sc, n), order in sorted(pr.items(), key=lambda x: (str(x[0][0]), x[0][1])):
        rows.append({"instance": f"provinsi {sc}, n={n}", col: format_ranking(order)})
    for (sc, n), order in sorted(fr.items(), key=lambda x: x[0][1]):
        rows.append({"instance": f"FIRMS k={n - 1} (n={n})", col: format_ranking(order)})
    if not pr:
        lines += ["Hasil provinsi tidak tersedia, sehingga peringkat tidak dapat dibandingkan.", ""]
    else:
        ref_key = max((k for k in pr if str(k[0]) == "2026"), key=lambda k: k[1], default=max(pr, key=lambda k: k[1]))
        ref = sorted(_strict_pairs(pr[ref_key]))
        lines += [f"Acuan: instance provinsi terbesar, skenario {ref_key[0]} n={ref_key[1]}: "
                  f"**{format_ranking(pr[ref_key])}** (urut rata-rata fitness 30 seed; `=` berarti seri dalam "
                  f"toleransi relatif {TIE_RTOL:g}).", ""]
        any_flip = any_tie = False
        for (sc, n), order in sorted(fr.items(), key=lambda x: x[0][1]):
            here = _strict_pairs(order)
            flipped = [(a, b) for a, b in ref if (b, a) in here]  # a above b on provinces, b above a here
            tied = [(a, b) for a, b in ref if (a, b) not in here and (b, a) not in here]
            any_flip |= bool(flipped); any_tie |= bool(tied)
            head = f"- FIRMS k={n - 1}: {format_ranking(order)}. "
            ties = "; ".join(f"{' = '.join(sorted((a, b)))} seri (provinsi: {a} di atas {b})" for a, b in tied)
            if flipped:
                desc = []
                for a, b in flipped:
                    s_f = "signifikan" if sig(firms_wilcoxon, sc, n, a, b) else "tidak signifikan"
                    s_p = "signifikan" if sig(province_wilcoxon, ref_key[0], ref_key[1], a, b) else "tidak signifikan"
                    desc.append(f"{b} di atas {a} (FIRMS: {s_f}; provinsi: {s_p}, Wilcoxon-Holm 0,05)")
                lines.append(head + "Peringkat provinsi **tidak tetap berlaku**: " + "; ".join(desc)
                             + (f"; selain itu {ties}" if tied else "") + ".")
            elif tied:
                lines.append(head + f"Tidak ada pasangan yang bertukar, tetapi ada yang seri: {ties}.")
            else:
                lines.append(head + "Peringkat provinsi **tetap berlaku**.")
        verdict = ("**tidak tetap berlaku** sepenuhnya pada instance FIRMS (lihat pasangan yang bertukar di atas)."
                   if any_flip else
                   "tidak dibantah pada instance FIRMS, tetapi sebagian pasangan seri (lihat di atas)."
                   if any_tie else "**tetap berlaku** pada semua instance FIRMS.")
        lines += ["", "Kesimpulan: peringkat provinsi " + verdict]
    table = pd.DataFrame(rows)
    return "\n".join(lines) + "\n\n" + to_markdown_id(table) + "\n", table


def combined_scalability(province_runs, firms_runs, algorithms):
    parts = []
    if province_runs is not None and not province_runs.empty:
        parts.append(scalability_table(province_runs, algorithms).assign(instance_family="provinsi"))
    parts.append(scalability_table(firms_runs, algorithms).assign(instance_family=FAMILY))
    t = pd.concat(parts, ignore_index=True)
    t["scenario"] = t.scenario.astype(str); t["candidates"] = t.n - 1
    return t


def run(cfg, out, coords, province_runs, quick=False, workers=1):
    """Runs the FIRMS phase into out/; returns False (after logging) if the snapshot is missing.

    coords are the province coordinates (the Depot); province_runs (or None) are compared against."""
    path = snapshot_path(cfg)
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
    write_table(cal["table"], out / "tables" / "firms_calibration", FIRMS_CALIBRATION_ID)
    tasks = [(k, a, s, budget) for k in sizes for s in range(seeds) for a in HEURISTICS]
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
            f"{a} {runs[(runs.k == k) & (runs.algorithm == a)].runtime_s.mean():.2f} s" for a in HEURISTICS))

    inst_rows = []
    for k in sizes:
        g = SOLVERS["Greedy"](instances[k])["best_route"]
        inst_rows.append({"k": k, "n": k + 1, "hotspots": int(nodes[k].hotspots.sum()),
                          "frp_total": float(nodes[k].frp_sum.sum()), "depot": depot["name"], "budget": budget,
                          "time_limit_h": T, "greedy_visited": len(g["route"]),
                          "greedy_visited_fraction": len(g["route"]) / k,
                          "greedy_mission_time_h": g["mission_time_h"], "g0": cfg["decay_g0"]})
        write_table(nodes[k], out / "tables" / f"firms_clusters_k{k}", FIRMS_CLUSTERS_ID)
    write_table(pd.DataFrame(inst_rows), out / "tables" / "firms_instances", FIRMS_INSTANCES_ID)
    fsum = summary_table(runs); fw = wilcoxon_holm_table(runs, list(HEURISTICS))
    write_table(fsum.assign(k=fsum.n - 1), out / "tables" / "firms_summary", SUMMARY_ID)
    write_table(fw.assign(k=fw.n - 1), out / "tables" / "firms_wilcoxon_holm", WILCOXON_ID)
    plots.boxplot_fitness_firms(runs, list(HEURISTICS), out / "figures" / "firms_boxplot_fitness.png")

    prov = province_runs[province_runs.algorithm.isin(HEURISTICS)] if province_runs is not None else None
    hc = hc_cost_table(runs, prov)
    write_table(hc, out / "tables" / "firms_hc_cost", HC_COST_ID)

    psum = summary_table(prov) if prov is not None and not prov.empty else None
    pw = wilcoxon_holm_table(prov, list(HEURISTICS)) if psum is not None else None
    md, table = ranking_report(psum, pw, fsum, fw, sizes)
    table.to_csv(out / "tables" / "firms_ranking.csv", index=False)
    (out / "tables" / "firms_ranking.md").write_text(md, encoding="utf8")

    comb = combined_scalability(province_runs, runs, HEURISTICS)  # Exact ikut menentukan best-known provinsi
    write_table(comb, out / "tables" / "scalability_combined", SCALABILITY_COMBINED_ID)
    plots.scalability_combined(comb, list(HEURISTICS), out / "figures" / "scalability_combined.png")

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
