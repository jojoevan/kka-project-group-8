"""Seam 1 (calibration): Batas waktu misi chosen so greedy visits 40-60% of the nodes."""
import re
import numpy as np
import pandas as pd
import pytest
import yaml
from src.calibration import CANDIDATE_TIME_LIMITS, calibrate_time_limit, write_time_limit
from src.data_prep import RAW, ROOT, prepare
from src.instance import Instance, build_instance


def line_instance(n_nodes):
    """Depot at 0 and n_nodes nodes 100 km apart on a line, speed 100 km/h, dwell 1 h, equal risk."""
    x = np.arange(n_nodes + 1) * 100.
    return Instance(["Depot"] + [f"N{i}" for i in range(n_nodes)], np.r_[0., np.ones(n_nodes)],
                    np.zeros(n_nodes + 1), np.abs(x[:, None] - x[None, :]), speed=100., dwell=1., g0=0.)


def test_picks_smallest_candidate_in_target_range():
    # Greedy walks outwards; visiting the first k nodes takes 2k h (k flights + k dwells) + k h back.
    # 10 nodes: 6 h -> 2 nodes (20%), 9 h -> 3 (30%), 12 h -> 4 (40%), 15 h -> 5 (50%).
    out = calibrate_time_limit(line_instance(10), candidates=(6, 9, 15, 12))
    assert out["time_limit"] == 12 and out["visited_fraction"] == pytest.approx(.4) and out["in_target"]
    table = out["table"].set_index("time_limit_h")
    assert table.loc[6, "visited"] == 2 and table.loc[15, "visited_fraction"] == pytest.approx(.5)
    assert list(out["table"].time_limit_h) == [6, 9, 12, 15]


def test_falls_back_to_closest_when_no_candidate_hits_target():
    out = calibrate_time_limit(line_instance(10), candidates=(3, 6))
    assert out["time_limit"] == 6 and not out["in_target"]


def test_calibration_leaves_instance_untouched():
    inst = line_instance(10); inst.time_limit = 99.
    calibrate_time_limit(inst, candidates=(6, 12))
    assert inst.time_limit == 99.


def test_write_time_limit_updates_only_that_line(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("depot: Riau\ntime_limit_hours: 72\nseeds: 30\n", encoding="utf8")
    write_time_limit(cfg, 48)
    text = cfg.read_text(encoding="utf8")
    assert yaml.safe_load(text) == {"depot": "Riau", "time_limit_hours": 48, "seeds": 30}
    assert re.search(r"time_limit_hours: 48 +# ", text)  # documented as calibrated


def test_real_n38_2026_calibration_visits_40_to_60_percent_and_is_the_config_default(tmp_path):
    features = prepare(processed_dir=tmp_path / "processed", reports_dir=tmp_path / "reports")[0]
    coords = pd.read_csv(RAW.parent / "external" / "province_coords.csv")
    inst = build_instance(features, coords, n=38, scenario="2026")
    out = calibrate_time_limit(inst)
    assert out["in_target"] and .4 <= out["visited_fraction"] <= .6
    assert out["time_limit"] in CANDIDATE_TIME_LIMITS
    smaller = out["table"][out["table"].time_limit_h < out["time_limit"]]
    assert not smaller.visited_fraction.between(.4, .6).any()
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf8"))
    assert cfg["time_limit_hours"] == out["time_limit"]
