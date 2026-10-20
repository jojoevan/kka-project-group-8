"""Seam 4: experiment runner end to end (quick mode) and its statistics helpers."""
import gzip
import json
import numpy as np
import pandas as pd
import pytest
from matplotlib.image import imread
from PIL import Image
from src.data_prep import ROOT
from src.experiments.run_all import main
from src.experiments.stats import evals_to_fraction, holm

HEURISTICS = ["Greedy", "HC", "SA", "GA"]


@pytest.fixture(scope="module")
def out(tmp_path_factory):
    d = tmp_path_factory.mktemp("results")
    main(["--config", str(ROOT / "config.yaml"), "--quick", "--out", str(d), "--workers", "2"])
    return d


@pytest.fixture(scope="module")
def quick(out):
    import yaml
    return yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf8"))["quick"]


def test_one_row_per_run(out, quick):
    runs = pd.read_csv(out / "raw" / "runs.csv")
    for col in ("algorithm", "n", "scenario", "seed", "fitness", "runtime_s", "evals", "evals_to_95",
                "hc_single_start_fitness"):
        assert col in runs
    heur = runs[runs.algorithm.isin(HEURISTICS)]
    n_inst = len(quick["sizes"]) * 2
    assert len(heur) == n_inst * quick["seeds"] * len(HEURISTICS)
    assert not heur.duplicated(["algorithm", "n", "scenario", "seed"]).any()
    exact = runs[runs.algorithm == "Exact"]
    assert set(exact.n) == {n for n in quick["sizes"] if n <= 9} and len(exact) == 2
    hc = runs[runs.algorithm == "HC"]
    assert hc.hc_single_start_fitness.notna().all() and (hc.hc_single_start_fitness <= hc.fitness + 1e-12).all()
    assert runs[runs.algorithm != "HC"].hc_single_start_fitness.isna().all()
    assert (heur.evals_to_95 <= heur.evals).all() and (heur.evals_to_95 >= 1).all()


def test_convergence_histories_saved_for_every_run(out):
    runs = pd.read_csv(out / "raw" / "runs.csv")
    with gzip.open(out / "raw" / "histories.jsonl.gz", "rt", encoding="utf8") as fh:
        hist = [json.loads(line) for line in fh]
    assert len(hist) == len(runs)
    last = {(h["algorithm"], h["n"], str(h["scenario"]), h["seed"]): h["history"][-1][1] for h in hist}
    for r in runs.itertuples():
        assert last[(r.algorithm, r.n, str(r.scenario), r.seed)] == pytest.approx(r.fitness)


def test_summary_table(out):
    s = pd.read_csv(out / "tables" / "summary.csv")
    for col in ("best", "mean", "std", "median", "runtime_mean_s", "evals_to_95_mean", "success_rate"):
        assert col in s
    assert s.success_rate.between(0, 1).all()
    assert (s.groupby(["n", "scenario"]).success_rate.max() > 0).all()  # someone hits best-known
    assert (out / "tables" / "summary.md").read_text(encoding="utf8").count("|") > 0


def test_optimality_gap_vs_exact(out):
    g = pd.read_csv(out / "tables" / "optimality_gap.csv")
    assert set(g.algorithm) == set(HEURISTICS) and set(g.n) == {6}
    assert (g.gap_mean_pct >= -1e-9).all() and (g.gap_max_pct >= g.gap_mean_pct - 1e-9).all()
    assert (out / "tables" / "optimality_gap.md").exists()


def test_boxplot_per_n_at_300_dpi(out, quick):
    for n in quick["sizes"]:
        path = out / "figures" / f"boxplot_fitness_n{n}.png"
        assert imread(path).shape[0] > 0
        assert round(Image.open(path).info["dpi"][0]) == 300


def test_wilcoxon_holm_table(out, quick):
    w = pd.read_csv(out / "tables" / "wilcoxon_holm.csv")
    assert len(w) == len(quick["sizes"]) * 2 * 6  # 6 pairs of 4 heuristics per instance
    assert (w.p_holm >= w.p_value - 1e-12).all() and w.p_holm.between(0, 1).all()
    assert (out / "tables" / "wilcoxon_holm.md").exists()


def test_log_records_total_runtime(out):
    text = (out / "logs" / "run_all.log").read_text(encoding="utf8")
    assert "Total runtime eksperimen" in text


def test_runs_are_deterministic_across_worker_counts(out, tmp_path):
    main(["--config", str(ROOT / "config.yaml"), "--quick", "--out", str(tmp_path), "--workers", "1"])
    a = pd.read_csv(out / "raw" / "runs.csv").drop(columns="runtime_s")
    b = pd.read_csv(tmp_path / "raw" / "runs.csv").drop(columns="runtime_s")
    pd.testing.assert_frame_equal(a, b)


def test_holm_matches_worked_example():
    # p = .01, .04, .03, .005 -> sorted .005*4=.02, .01*3=.03, .03*2=.06, .04*1=.04 -> monotone .06
    assert holm([.01, .04, .03, .005]) == pytest.approx([.03, .06, .06, .02])
    assert holm([.02, .9]) == pytest.approx([.04, .9])
    assert holm([.6, .7]) == pytest.approx([1., 1.])  # capped at 1


def test_evals_to_fraction_of_final_best():
    history = [(1, 1.), (10, 5.), (40, 9.6), (90, 10.)]
    assert evals_to_fraction(history, .95) == 40
    assert evals_to_fraction([(1, 0.)], .95) == 1


# --- Ticket #5: analisis lanjutan ---------------------------------------------------------------

def _dpi(path):
    assert imread(path).shape[0] > 0
    return round(Image.open(path).info["dpi"][0])


def test_convergence_curve_is_mean_and_band_of_best_so_far_steps():
    from src.experiments.stats import convergence_curve
    # seed A: 1 until eval 5, then 3; seed B: 2 until eval 3, then 4
    c = convergence_curve([[(1, 1.), (5, 3.)], [(1, 2.), (3, 4.)]], grid=[1, 3, 5])
    assert c["mean"] == pytest.approx([1.5, 2.5, 3.5])
    assert c["std"] == pytest.approx([.5, 1.5, .5])  # population std across seeds
    # a deterministic run (single history point) stays flat over the whole grid
    assert convergence_curve([[(1, 7.)]], grid=[1, 10, 100])["mean"] == pytest.approx([7., 7., 7.])


def test_convergence_figure_and_table_for_two_largest_sizes(out, quick):
    sizes = sorted(quick["sizes"])[-2:]
    conv = pd.read_csv(out / "tables" / "convergence.csv")
    assert set(conv.n) == set(sizes) and set(conv.algorithm) == set(HEURISTICS)
    runs = pd.read_csv(out / "raw" / "runs.csv")
    for (alg, n, sc), g in conv.groupby(["algorithm", "n", "scenario"]):
        g = g.sort_values("evals")
        assert (np.diff(g["mean"]) >= -1e-12).all()  # best-so-far never drops
        final = runs[(runs.algorithm == alg) & (runs.n == n) & (runs.scenario == sc)].fitness.mean()
        assert g["mean"].iloc[-1] == pytest.approx(final)
    for n in sizes:
        assert _dpi(out / "figures" / f"convergence_n{n}.png") == 300


def test_scalability_table_and_figure_over_n(out, quick):
    s = pd.read_csv(out / "tables" / "scalability.csv")
    assert set(s.n) == set(quick["sizes"]) and set(s.algorithm) == set(HEURISTICS)
    assert len(s) == len(quick["sizes"]) * 2 * len(HEURISTICS)
    runs = pd.read_csv(out / "raw" / "runs.csv")
    # quality is relative to the best-known fitness of the instance (Exact included), so it is <= 100%
    assert s.quality_mean_pct.between(0, 100 + 1e-9).all()
    ga6 = runs[(runs.algorithm == "GA") & (runs.n == 6) & (runs.scenario == 2026)]
    row = s[(s.algorithm == "GA") & (s.n == 6) & (s.scenario == 2026)].iloc[0]
    assert row.runtime_mean_s == pytest.approx(ga6.runtime_s.mean())
    assert (out / "tables" / "scalability.md").exists()
    assert _dpi(out / "figures" / "scalability.png") == 300


@pytest.fixture(scope="module")
def cfg():
    import yaml
    return yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf8"))


def test_sensitivity_sweep_runs_every_setting_with_every_seed(out, quick, cfg):
    sens = cfg["analysis"]["sensitivity"]
    assert sens["time_limit_hours"] == [24, 48, 72, 120] and sens["decay_g0"] == [0, .005, .01, .02]
    raw = pd.read_csv(out / "raw" / "sensitivity_runs.csv")
    settings = ([("time_limit_hours", v) for v in sens["time_limit_hours"]]
                + [("decay_g0", v) for v in sens["decay_g0"]])
    assert len(raw) == len(settings) * quick["seeds"] * len(HEURISTICS)
    assert set(raw.n) == {quick["sensitivity_n"]} and set(raw.scenario.astype(str)) == {sens["scenario"]}
    assert (raw.mission_time_h <= raw.time_limit_h + 1e-9).all()
    assert set(zip(raw.parameter, raw.value)) == set(settings)
    t = pd.read_csv(out / "tables" / "sensitivity.csv")
    assert len(t) == len(settings) * len(HEURISTICS)
    assert {"parameter", "value", "algorithm", "mean", "std", "best", "visited_mean"} <= set(t.columns)
    assert (out / "tables" / "sensitivity.md").exists()
    assert _dpi(out / "figures" / "sensitivity.png") == 300


def test_sensitivity_default_setting_reproduces_main_comparison(out, quick, cfg):
    raw = pd.read_csv(out / "raw" / "sensitivity_runs.csv")
    runs = pd.read_csv(out / "raw" / "runs.csv")
    n, sc = quick["sensitivity_n"], int(cfg["analysis"]["sensitivity"]["scenario"])
    for param, value in (("decay_g0", cfg["decay_g0"]), ("time_limit_hours", cfg["time_limit_hours"])):
        default = raw[(raw.parameter == param) & (raw.value == value)]
        main_ = runs[(runs.n == n) & (runs.scenario == sc) & runs.algorithm.isin(HEURISTICS)]
        merged = default.merge(main_, on=["algorithm", "seed"], suffixes=("_s", "_m"))
        assert len(merged) == len(default) > 0
        assert merged.fitness_s.to_numpy() == pytest.approx(merged.fitness_m.to_numpy())


def _quick_instance(cfg, quick, g0):
    from src.data_prep import prepare
    from src.instance import build_instance
    w = cfg["weights"]
    features = prepare(weights=(w["hist"], w["cur"], w["ops"]), gamma=cfg["gamma"])[0]
    coords = pd.read_csv(ROOT / "data" / "external" / "province_coords.csv")
    return build_instance(features, coords, n=quick["sensitivity_n"], scenario=cfg["analysis"]["case_study"]["scenario"],
                          depot_name=cfg["depot"], speed=cfg["speed_kmh"], detour=cfg["detour_factor"],
                          dwell=cfg["dwell_hours"], time_limit=cfg["time_limit_hours"], g0=g0,
                          kappa=cfg["decay_kappa"])


def test_decay_ablation_prize_lost_when_static_route_is_flown_with_decay(out, quick, cfg):
    raw = pd.read_csv(out / "raw" / "sensitivity_runs.csv")
    g = raw[raw.parameter == "decay_g0"]
    best_decay = g[g.value == cfg["decay_g0"]].sort_values("fitness", ascending=False, kind="stable").iloc[0]
    best_static = g[g.value == 0].sort_values("fitness", ascending=False, kind="stable").iloc[0]
    decay_inst, static_inst = _quick_instance(cfg, quick, cfg["decay_g0"]), _quick_instance(cfg, quick, 0.)
    perm_d, perm_s = json.loads(best_decay.best_perm), json.loads(best_static.best_perm)
    r = pd.read_csv(out / "tables" / "decay_ablation_routes.csv").set_index("variant")
    assert list(r.index) == ["dengan decay", "tanpa decay (g0=0)"]
    assert r.loc["dengan decay", "fitness_with_decay"] == pytest.approx(best_decay.fitness)
    assert r.loc["tanpa decay (g0=0)", "fitness_without_decay"] == pytest.approx(best_static.fitness)
    assert r.loc["tanpa decay (g0=0)", "fitness_with_decay"] == pytest.approx(decay_inst.evaluate(perm_s))
    assert r.loc["dengan decay", "fitness_without_decay"] == pytest.approx(static_inst.evaluate(perm_d))
    lost = best_decay.fitness - decay_inst.evaluate(perm_s)
    assert r.loc["tanpa decay (g0=0)", "prize_lost"] == pytest.approx(lost)
    assert r.loc["tanpa decay (g0=0)", "prize_lost_pct"] == pytest.approx(100 * lost / best_decay.fitness)
    assert r.loc["dengan decay", "prize_lost"] == pytest.approx(0.)
    assert {"ops_visited", "ops_mean_position", "ops_mean_arrival_h"} <= set(r.columns)
    assert (out / "tables" / "decay_ablation_routes.md").exists()


def test_decay_ablation_visiting_order_per_province(out):
    o = pd.read_csv(out / "tables" / "decay_ablation_order.csv")
    assert {"province", "risk", "ops", "position_decay", "position_static", "arrival_decay_h",
            "arrival_static_h", "position_shift"} <= set(o.columns)
    for col in ("position_decay", "position_static"):
        pos = sorted(o[col].dropna().astype(int))
        assert pos == list(range(1, len(pos) + 1))  # 1..k, each Kunjungan once
    assert (out / "tables" / "decay_ablation_order.md").exists()


def test_decay_ablation_paired_by_seed_per_algorithm(out, quick, cfg):
    s = pd.read_csv(out / "tables" / "decay_ablation_seeds.csv")
    assert set(s.algorithm) == set(HEURISTICS) and (s.seeds == quick["seeds"]).all()
    raw = pd.read_csv(out / "raw" / "sensitivity_runs.csv")
    static = raw[(raw.parameter == "decay_g0") & (raw.value == 0) & (raw.algorithm == "SA")]
    decay_inst = _quick_instance(cfg, quick, cfg["decay_g0"])
    expected = np.mean([decay_inst.evaluate(json.loads(p)) for p in static.best_perm])
    assert s.set_index("algorithm").loc["SA", "static_route_with_decay_mean"] == pytest.approx(expected)
    assert (out / "tables" / "decay_ablation_seeds.md").exists()


def test_case_study_route_table_and_map(out, quick, cfg):
    n, sc = quick["sensitivity_n"], cfg["analysis"]["case_study"]["scenario"]
    best = json.loads((out / "routes" / f"best_route_{sc}_n{n}.json").read_text(encoding="utf8"))
    t = pd.read_csv(out / "tables" / "case_study_route.csv")
    assert len(t) == n - 1  # every non-Depot node is either a Kunjungan or a Node dilewati
    visited = t[t.status == "dikunjungi"].sort_values("order")
    assert visited.province.tolist() == [v["province"] for v in best["route"]]
    assert visited.order.tolist() == list(range(1, len(best["route"]) + 1))
    assert visited.arrival_h.to_numpy() == pytest.approx([v["arrival_h"] for v in best["route"]])
    assert visited.prize.sum() == pytest.approx(best["fitness"])
    assert (visited.departure_h.to_numpy() == pytest.approx(visited.arrival_h.to_numpy() + cfg["dwell_hours"]))
    skipped = t[t.status == "dilewati"]
    assert sorted(skipped.province) == sorted(s["province"] for s in best["skipped"])
    assert skipped.order.isna().all() and skipped.risk.notna().all()
    md = (out / "tables" / "case_study_route.md").read_text(encoding="utf8")
    assert "Depot" in md and "dilewati" in md
    assert _dpi(out / "figures" / "best_route_map.png") == 300
