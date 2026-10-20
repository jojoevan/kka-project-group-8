"""Seam 1 (FIRMS): hotspot snapshot -> Klaster hotspot Instance."""
from pathlib import Path
import numpy as np
import pytest
from src.firms import load_hotspots

FIXTURE = Path(__file__).parent / "fixtures" / "firms_small.csv"
# The fixture has three tight blobs (Jambi: 4 points, FRP sum 10; Kalimantan Tengah: 5 points, sum 100;
# Kalimantan Barat: 4 points, sum 1000), 3 low-confidence points inside the boxes and 4 nominal/high
# points outside both boxes (Thailand, Papua, Jawa, Filipina).
BBOXES = {"Sumatra": [-6.0, 6.0, 95.0, 106.0], "Kalimantan": [-4.5, 4.5, 108.5, 119.0]}
CONFIDENCE = ["nominal", "high"]


def test_keeps_only_nominal_high_inside_sumatra_kalimantan_boxes():
    h = load_hotspots(FIXTURE, CONFIDENCE, BBOXES)
    assert len(h) == 13
    assert set(h.confidence) <= {"nominal", "high"}
    assert h.frp.sum() == pytest.approx(1110.)


DEPOT = {"name": "Pekanbaru", "lat": .51, "lon": 101.45}


def build(k, seed=0, **kw):
    from src.firms import build_firms_instance
    return build_firms_instance(load_hotspots(FIXTURE, CONFIDENCE, BBOXES), k, depot=DEPOT, seed=seed, **kw)


def _inside_any_box(lat, lon):
    return any(a <= lat <= b and c <= lon <= d for a, b, c, d in BBOXES.values())


@pytest.mark.parametrize("k", [2, 3, 6, 13])
def test_exactly_k_cluster_nodes_plus_depot_all_inside_the_boxes(k):
    inst, nodes = build(k)
    assert len(inst.names) == k + 1 and inst.depot == 0 and inst.names[0] == "Pekanbaru"
    assert len(nodes) == k and nodes.name.tolist() == inst.names[1:]
    assert nodes.hotspots.sum() == 13  # every kept hotspot belongs to exactly one cluster
    assert all(_inside_any_box(r.lat, r.lon) for r in nodes.itertuples())
    assert inst.dist.shape == (k + 1, k + 1) and np.allclose(inst.dist, inst.dist.T)


def test_risk_is_log1p_frp_sum_min_max_over_clusters():
    inst, nodes = build(3)
    # blobs with Σ FRP 1000, 100, 10 -> log1p -> min-max: 1, (ln 101 - ln 11)/(ln 1001 - ln 11) = 0.49153, 0
    assert nodes.frp_sum.tolist() == pytest.approx([1000., 100., 10.])
    assert nodes.risk.tolist() == pytest.approx([1., .49153, 0.], abs=1e-5)
    assert inst.risk.tolist() == pytest.approx([0., 1., .49153, 0.], abs=1e-5)  # Depot has no Risiko
    assert nodes.hotspots.tolist() == [4, 5, 4]


@pytest.mark.parametrize("k", [3, 6])
def test_risk_in_unit_interval(k):
    inst, _ = build(k)
    assert ((inst.risk >= 0) & (inst.risk <= 1)).all() and inst.risk[1:].max() == pytest.approx(1.)


def test_deterministic_for_the_same_seed():
    a_inst, a = build(6, seed=7); b_inst, b = build(6, seed=7)
    assert a.equals(b) and np.array_equal(a_inst.dist, b_inst.dist) and a_inst.names == b_inst.names


def test_decay_is_constant_g0_for_every_cluster():
    inst, _ = build(3, g0=.02)
    assert (inst.ops == 0).all() and inst.g0 == .02
    # Prize at arrival t is Risiko * exp(-g0 t): first node (Risiko 1) reached after flying from the depot
    route = inst.evaluate([1], details=True)["route"][0]
    assert route["prize"] == pytest.approx(np.exp(-.02 * route["arrival_h"]))


def test_more_clusters_than_hotspots_is_rejected():
    with pytest.raises(ValueError):
        build(14)
