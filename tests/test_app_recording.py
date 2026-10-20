"""The interactive view's recording wrapper must not change what a solver does."""
import pytest

pytest.importorskip("streamlit")

from app.core import RecordingInstance, instance  # noqa: E402
from src.algorithms import SOLVERS  # noqa: E402


@pytest.mark.parametrize("algorithm", ["Greedy", "HC", "SA", "GA"])
def test_recording_matches_plain_run(algorithm):
    inst = instance(10, "2026")
    plain = SOLVERS[algorithm](inst, 500, 3)
    rec = RecordingInstance.of(inst)
    recorded = SOLVERS[algorithm](rec, 500, 3)
    assert recorded["best_perm"] == plain["best_perm"]
    assert recorded["best_fitness"] == plain["best_fitness"]
    assert rec.evals == plain["evals"]
    assert [(e, v) for e, _, v in rec.snapshots] == [tuple(h) for h in plain["history"]]


def test_charts_use_decimal_comma():
    import numpy as np
    import pandas as pd
    from app import charts
    df = pd.DataFrame({"algorithm": ["SA", "GA"], "fitness": [9.1, 7.2], "n": [38, 38]})
    figs = [charts.risk_map(["A", "B"], np.array([0., 1.]), np.array([100., 101.]), np.array([.2, .8]), "A"),
            charts.convergence({"SA": ([1, 10], [1.5, 2.5])}),
            charts.prize_decay(72, .01, 1., 1., [0, .5]),
            charts.boxplot(df),
            charts.lines(df, "n", "fitness", "algorithm", "n", "Fitness")]
    assert all(f.layout.separators == ",." for f in figs)
