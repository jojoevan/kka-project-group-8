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
