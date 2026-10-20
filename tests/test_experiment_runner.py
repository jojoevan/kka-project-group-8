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
