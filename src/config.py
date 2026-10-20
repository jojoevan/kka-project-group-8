"""config.yaml -> model inputs: the one place that maps config keys to Risiko weights and mission parameters.

Used by the calibration CLI, the province experiment and the FIRMS phase so every Instance is built
from the same keys.
"""
from pathlib import Path
import pandas as pd
import yaml
from src.data_prep import ROOT, prepare
from src.instance import build_instance

COORDS_CSV = ROOT / "data" / "external" / "province_coords.csv"


def load_config(path=ROOT / "config.yaml"):
    return yaml.safe_load(Path(path).read_text(encoding="utf8"))


def province_features(cfg):
    """Feature table of the 38 provinces (Risiko per Skenario tahun) with the config's weights and gamma."""
    w = cfg["weights"]
    return prepare(weights=(w["hist"], w["cur"], w["ops"]), gamma=cfg["gamma"])[0]


def province_coords():
    return pd.read_csv(COORDS_CSV)


def mission_params(cfg, overrides=()):
    """Mission keyword arguments of the instance builders (speed, detour, dwell, time_limit, g0, kappa).

    overrides are (config key, value) pairs applied first, e.g. (("decay_g0", 0.),)."""
    c = {**cfg, **dict(overrides)}
    return {"speed": c["speed_kmh"], "detour": c["detour_factor"], "dwell": c["dwell_hours"],
            "time_limit": c["time_limit_hours"], "g0": c["decay_g0"], "kappa": c["decay_kappa"]}


def cluster_mission_params(cfg, time_limit):
    """mission_params for Klaster hotspot instances: no kappa, since clusters have no operational data
    and decay at the constant g0 (ADR-0001); the Batas waktu misi is the FIRMS-calibrated one."""
    p = mission_params(cfg); del p["kappa"]
    return {**p, "time_limit": time_limit}


def province_instance(cfg, features, coords, n, scenario, overrides=()):
    """Province Instance of size n for a Skenario tahun, with the config's Depot and mission parameters."""
    c = {**cfg, **dict(overrides)}
    return build_instance(features, coords, n=n, scenario=scenario, depot_name=c["depot"], **mission_params(c))
