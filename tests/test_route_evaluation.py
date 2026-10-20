"""Seam 2: route evaluation (Instance.evaluate)."""
import numpy as np
import pytest
from src.instance import Instance, haversine_matrix


def line_instance(time_limit=10.0, g0=0.0, ops=None, risk=(0., 1., .8, .6)):
    """Depot at km 0, nodes A, B, C at km 100, 200, 300 on a line; speed 100 km/h, dwell 1 h."""
    x = np.array([0., 100., 200., 300.])
    dist = np.abs(x[:, None] - x[None, :])
    ops = np.zeros(4) if ops is None else np.asarray(ops, float)
    return Instance(["Depot", "A", "B", "C"], np.array(risk, float), ops, dist, depot=0, speed=100.,
                    dwell=1., time_limit=time_limit, g0=g0, kappa=1.)


def test_mission_never_exceeds_time_limit_including_return_to_depot():
    rng = np.random.default_rng(3)
    n = 9
    lat, lon = rng.uniform(-5, 5, n), rng.uniform(95, 115, n)
    inst = Instance([f"N{i}" for i in range(n)], rng.uniform(0, 1, n), rng.uniform(0, 1, n),
                    haversine_matrix(lat, lon), speed=200., dwell=1., time_limit=20.)
    for _ in range(50):
        out = inst.evaluate(list(rng.permutation(np.arange(1, n))), details=True)
        assert out["mission_time_h"] <= inst.time_limit + 1e-9
        assert out["remaining_time_h"] == pytest.approx(inst.time_limit - out["mission_time_h"])


def test_return_leg_counts_towards_time_limit():
    # Going to C takes 3 h + 1 h dwell; returning takes another 3 h -> 7 h total.
    assert line_instance(time_limit=6.9).evaluate([3], details=True)["route"] == []
    assert [v["province"] for v in line_instance(time_limit=7.0).evaluate([3], details=True)["route"]] == ["C"]


def test_skipped_node_does_not_stop_checking_later_nodes():
    # Order [B, C, A] with 7.5 h: B ends at t=3 (incl. dwell); C needs 3+1+1+3 = 8 h > 7.5 so it is
    # skipped; A is still tried and fits: 3+1+1+1 = 6 h.
    out = line_instance(time_limit=7.5).evaluate([2, 3, 1], details=True)
    assert [v["province"] for v in out["route"]] == ["B", "A"]
    assert [s["province"] for s in out["skipped"]] == ["C"]
    assert out["skipped"][0]["risk"] == pytest.approx(.6)


def test_prize_decreases_when_arrival_is_later():
    inst = line_instance(time_limit=100., g0=.05)
    early = inst.evaluate([1, 2], details=True)["route"]  # A arrives at 1 h
    late = inst.evaluate([2, 1], details=True)["route"]   # A arrives at 2+1+1 = 4 h
    a_early = next(v for v in early if v["province"] == "A")
    a_late = next(v for v in late if v["province"] == "A")
    assert a_early["arrival_h"] == pytest.approx(1.) and a_late["arrival_h"] == pytest.approx(4.)
    assert a_late["prize"] < a_early["prize"]
    assert a_early["prize"] == pytest.approx(1. * np.exp(-.05 * 1.))


def test_operational_severity_speeds_up_decay():
    calm = line_instance(time_limit=100., g0=.05).evaluate([1])
    severe = line_instance(time_limit=100., g0=.05, ops=[0, 1, 0, 0]).evaluate([1])
    assert severe == pytest.approx(np.exp(-.1)) and severe < calm


def test_zero_decay_prize_equals_risk():
    out = line_instance(time_limit=100., g0=0., ops=[0, 1, 1, 1]).evaluate([3, 1, 2], details=True)
    assert len(out["route"]) == 3
    for v in out["route"]:
        assert v["prize"] == pytest.approx(v["risk"])
    assert out["fitness"] == pytest.approx(1. + .8 + .6)


def test_each_node_visited_at_most_once():
    out = line_instance(time_limit=100.).evaluate([1, 1, 2, 1, 2, 0, 3], details=True)
    visited = [v["province"] for v in out["route"]]
    assert visited == ["A", "B", "C"]
    assert out["fitness"] == pytest.approx(1. + .8 + .6)


def test_route_detail_is_consistent_with_fitness():
    inst = line_instance(time_limit=9., g0=.02, ops=[0, .5, 1, 0])
    for perm in ([1, 2, 3], [3, 2, 1], [2, 3, 1], [3, 1, 2]):
        out = inst.evaluate(perm, details=True)
        assert sum(v["prize"] for v in out["route"]) == pytest.approx(out["fitness"])
        assert out["fitness"] == pytest.approx(inst.evaluate(perm))
        seq = [0] + [v["index"] for v in out["route"]] + [0]
        assert out["distance_km"] == pytest.approx(sum(inst.dist[a, b] for a, b in zip(seq, seq[1:])))
        assert {v["province"] for v in out["route"]}.isdisjoint(s["province"] for s in out["skipped"])
        assert len(out["route"]) + len(out["skipped"]) == 3


def test_skipped_list_excludes_depot_when_depot_is_not_first():
    inst = line_instance(time_limit=100.)
    inst.depot = 2
    out = inst.evaluate([0, 1, 3], details=True)
    assert "B" not in {v["province"] for v in out["route"]} | {s["province"] for s in out["skipped"]}


def test_haversine_is_symmetric_with_zero_diagonal():
    rng = np.random.default_rng(0)
    d = haversine_matrix(rng.uniform(-10, 6, 12), rng.uniform(95, 141, 12))
    assert np.allclose(d, d.T) and np.allclose(np.diag(d), 0)
    # Jakarta -> Surabaya is roughly 660 km great-circle.
    assert haversine_matrix([-6.21, -7.25], [106.85, 112.75])[0, 1] == pytest.approx(663, abs=15)
