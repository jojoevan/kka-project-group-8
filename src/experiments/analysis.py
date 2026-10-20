"""Follow-up analyses on solved routes: decay ablation and the case-study route table."""
import json
import numpy as np
import pandas as pd

DECAY_VARIANT, STATIC_VARIANT = "dengan decay", "tanpa decay (g0=0)"


def _ops_order(inst, detail):
    """Count, mean position (1-based) and mean arrival time of the visited nodes with ops > 0."""
    hits = [(k, node["arrival_h"]) for k, node in enumerate(detail["route"], 1) if inst.ops[node["index"]] > 0]
    if not hits: return 0, np.nan, np.nan
    return len(hits), float(np.mean([k for k, _ in hits])), float(np.mean([a for _, a in hits]))


def decay_ablation(decay_inst, static_inst, perm_decay, perm_static, meta_decay, meta_static):
    """Compare the best route found with decay against the best one found with g0=0.

    Both routes are evaluated on both instances. Prize lost = F_decay(decay route) - F_decay(static route),
    i.e. what is lost if decay is ignored when planning but still happens in reality. Returns
    (routes table, per-province order table)."""
    base = decay_inst.evaluate(perm_decay)
    details = {}; rows = []
    for variant, perm, meta in ((DECAY_VARIANT, perm_decay, meta_decay), (STATIC_VARIANT, perm_static, meta_static)):
        d = decay_inst.evaluate(perm, details=True); details[variant] = d
        with_decay = d["fitness"]; ops_visited, ops_pos, ops_arr = _ops_order(decay_inst, d)
        rows.append({"variant": variant, **meta, "fitness_with_decay": with_decay,
                     "fitness_without_decay": static_inst.evaluate(perm), "visited": len(d["route"]),
                     "mission_time_h": d["mission_time_h"], "distance_km": d["distance_km"],
                     "ops_visited": ops_visited, "ops_mean_position": ops_pos, "ops_mean_arrival_h": ops_arr,
                     "prize_lost": base - with_decay, "prize_lost_pct": 100 * (base - with_decay) / base})
    routes = pd.DataFrame(rows)

    def positions(d):
        return {node["province"]: (k, node["arrival_h"]) for k, node in enumerate(d["route"], 1)}
    pd_, ps_ = positions(details[DECAY_VARIANT]), positions(details[STATIC_VARIANT])
    order = []
    for i, name in enumerate(decay_inst.names):
        if i == decay_inst.depot or (name not in pd_ and name not in ps_): continue
        kd, ad = pd_.get(name, (np.nan, np.nan)); ks, as_ = ps_.get(name, (np.nan, np.nan))
        order.append({"province": name, "risk": float(decay_inst.risk[i]), "ops": float(decay_inst.ops[i]),
                      "position_decay": kd, "arrival_decay_h": ad, "position_static": ks, "arrival_static_h": as_,
                      "position_shift": ks - kd})
    order = pd.DataFrame(order).sort_values(["position_decay", "position_static"], na_position="last")
    for col in ("position_decay", "position_static", "position_shift"): order[col] = order[col].astype("Int64")
    return routes, order.reset_index(drop=True)


def case_study_table(inst, detail):
    """One row per non-Depot node: Kunjungan in route order (leg distance, arrival, departure, Prize),
    then Node dilewati by descending Risiko."""
    rows = []; prev = inst.depot
    for k, node in enumerate(detail["route"], 1):
        i = node["index"]
        rows.append({"order": k, "province": node["province"], "status": "dikunjungi", "risk": node["risk"],
                     "ops": float(inst.ops[i]), "leg_km": float(inst.dist[prev, i]), "arrival_h": node["arrival_h"],
                     "departure_h": node["arrival_h"] + inst.dwell, "prize": node["prize"]})
        prev = i
    for s in sorted(detail["skipped"], key=lambda s: -s["risk"]):
        rows.append({"order": None, "province": s["province"], "status": "dilewati", "risk": s["risk"],
                     "ops": float(inst.ops[s["index"]]), "leg_km": None, "arrival_h": None, "departure_h": None,
                     "prize": 0.})
    df = pd.DataFrame(rows); df["order"] = df["order"].astype("Int64")
    return df


def decay_ablation_by_seed(decay_inst, decay_runs, static_runs):
    """Per algorithm, paired by seed: the decay objective of the route found with decay vs of the route
    found with g0=0 (both runs carry best_perm as JSON)."""
    m = decay_runs.merge(static_runs, on=["algorithm", "seed"], suffixes=("_d", "_s"))
    m["static_with_decay"] = [decay_inst.evaluate(json.loads(p)) for p in m.best_perm_s]
    m["lost"] = m.fitness_d - m.static_with_decay; m["lost_pct"] = 100 * m.lost / m.fitness_d
    return m.groupby("algorithm", sort=False).agg(
        seeds=("seed", "size"), decay_route_with_decay_mean=("fitness_d", "mean"),
        static_route_with_decay_mean=("static_with_decay", "mean"), prize_lost_mean=("lost", "mean"),
        prize_lost_mean_pct=("lost_pct", "mean"), prize_lost_max_pct=("lost_pct", "max"),
        seeds_static_worse=("lost", lambda x: int((x > 1e-12).sum()))).reset_index()
