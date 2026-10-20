"""Seam 3: solver contract solve(instance, budget, seed) -> result, shared by all five solvers."""
import numpy as np
import pytest
from src.algorithms import SOLVERS, initial_permutation
from src.instance import Instance, haversine_matrix

ALL = list(SOLVERS)
HEURISTICS = ["Greedy", "HC", "SA", "GA"]
LOCAL_SEARCH = ["HC", "SA", "GA"]
BUDGET = 3000


def small_instance(seed=11, n=7, time_limit=24.):
    """Depot + 6 candidates scattered over ~Sumatra/Kalimantan; the time limit binds."""
    rng = np.random.default_rng(seed)
    lat, lon = rng.uniform(-4, 3, n), rng.uniform(98, 116, n)
    risk = rng.uniform(.1, 1, n); risk[0] = 0
    return Instance([f"N{i}" for i in range(n)], risk, rng.uniform(0, 1, n), haversine_matrix(lat, lon) * 1.15,
                    speed=200., dwell=1., time_limit=time_limit, g0=.01, kappa=1.)


@pytest.fixture(scope="module")
def inst():
    return small_instance()


@pytest.mark.parametrize("name", ALL)
def test_result_has_contract_fields(inst, name):
    res = SOLVERS[name](inst, budget=BUDGET, seed=0)
    for key in ("best_perm", "best_route", "best_fitness", "history", "runtime", "evals"):
        assert key in res
    assert res["runtime"] >= 0
    evals, best = zip(*res["history"])
    assert list(evals) == sorted(evals) and list(best) == sorted(best)
    assert best[-1] == pytest.approx(res["best_fitness"])
    route = res["best_route"]
    for key in ("route", "distance_km", "mission_time_h", "remaining_time_h", "skipped"):
        assert key in route


@pytest.mark.parametrize("name", ALL)
def test_best_perm_is_a_permutation_of_all_candidates(inst, name):
    perm = SOLVERS[name](inst, budget=BUDGET, seed=1)["best_perm"]
    assert sorted(perm) == list(range(1, len(inst.names)))


@pytest.mark.parametrize("budget", [1, 7, 50, 150, BUDGET])
@pytest.mark.parametrize("name", ALL)
def test_evaluations_never_exceed_budget(inst, name, budget):
    res = SOLVERS[name](inst, budget=budget, seed=2)
    assert 1 <= res["evals"] <= budget
    assert all(e <= budget for e, _ in res["history"])


@pytest.mark.parametrize("name", ALL)
def test_reported_fitness_equals_reevaluation(inst, name):
    res = SOLVERS[name](inst, budget=BUDGET, seed=3)
    assert res["best_fitness"] == pytest.approx(inst.evaluate(res["best_perm"]))
    assert res["best_route"]["fitness"] == pytest.approx(res["best_fitness"])


@pytest.mark.parametrize("name", ALL)
def test_same_seed_same_result(inst, name):
    a, b = (SOLVERS[name](inst, budget=BUDGET, seed=4) for _ in range(2))
    assert a["best_perm"] == b["best_perm"] and a["best_fitness"] == b["best_fitness"]
    assert a["history"] == b["history"] and a["evals"] == b["evals"]


@pytest.mark.parametrize("inst_seed", [11, 12, 13])
def test_exact_is_at_least_every_heuristic(inst_seed):
    inst = small_instance(seed=inst_seed)
    exact = SOLVERS["Exact"](inst, budget=10**6, seed=0)
    assert exact["extra"]["optimal"]
    for name in HEURISTICS:
        for seed in range(3):
            assert SOLVERS[name](inst, budget=BUDGET, seed=seed)["best_fitness"] <= exact["best_fitness"] + 1e-12


def test_exact_matches_brute_force_over_all_permutations():
    import itertools
    inst = small_instance(seed=5)
    brute = max(inst.evaluate(p) for p in itertools.permutations(range(1, len(inst.names))))
    assert SOLVERS["Exact"](inst, budget=10**6, seed=0)["best_fitness"] == pytest.approx(brute)


def test_exact_rejects_instances_above_nine_nodes():
    with pytest.raises(ValueError):
        SOLVERS["Exact"](small_instance(n=10), budget=10**6, seed=0)


@pytest.mark.parametrize("seed", [0, 5, 9])
def test_local_search_solvers_share_initial_solution(inst, seed):
    start = initial_permutation(inst, seed)
    assert sorted(start) == list(range(1, len(inst.names)))
    for name in LOCAL_SEARCH:
        res = SOLVERS[name](inst, budget=BUDGET, seed=seed)
        assert res["initial_perm"] == start
        # The first evaluation of every local-search solver is that shared start.
        assert res["history"][0] == (1, pytest.approx(inst.evaluate(start)))
    assert initial_permutation(inst, 0) != initial_permutation(inst, 5)


def test_ga_is_not_seeded_with_greedy():
    # On a bigger instance a random population almost surely lacks the greedy order.
    inst = small_instance(seed=21, n=15, time_limit=30.)
    greedy_perm = SOLVERS["Greedy"](inst, budget=1, seed=0)["best_perm"]
    res = SOLVERS["GA"](inst, budget=100, seed=0)  # exactly the initial population
    assert res["evals"] == 100 and res["extra"]["population"] == 100
    assert greedy_perm not in res["extra"]["initial_population"]


def test_hc_records_single_start_result(inst):
    res = SOLVERS["HC"](inst, budget=BUDGET, seed=0)
    extra = res["extra"]
    assert extra["restarts"] >= 2
    assert extra["single_start_fitness"] <= res["best_fitness"] + 1e-12


def test_sa_logs_temperature_and_acceptance(inst):
    extra = SOLVERS["SA"](inst, budget=BUDGET, seed=0)["extra"]
    assert extra["T0"] > 0 and 0 <= extra["acceptance_rate"] <= 1
    assert extra["final_temperature"] == pytest.approx(.001 * extra["T0"], rel=.05)
    temps = [T for _, T in extra["temperature_trace"]]
    assert temps == sorted(temps, reverse=True)
