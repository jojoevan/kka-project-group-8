"""Seam 1: province data -> Instance."""
import logging
import numpy as np
import pandas as pd
import pytest
from src.data_prep import (RAW, canonical_province_name, load_burned_area,
                           parse_id_number, parse_pm25, parse_visibility, prepare)
from src.instance import build_instance, select_provinces

COORDS = pd.read_csv(RAW.parent / "external" / "province_coords.csv")
OPS_PROVINCES = ["Riau", "Jambi", "Sumatera Selatan", "Kalimantan Barat", "Kalimantan Tengah",
                 "Kalimantan Selatan"]


@pytest.fixture(scope="module")
def features(tmp_path_factory):
    out = tmp_path_factory.mktemp("prep")
    return prepare(processed_dir=out / "processed", reports_dir=out / "reports")[0]


def test_indonesian_number_thousands_and_decimal():
    assert parse_id_number("336.798,00") == 336798.0
    assert np.isnan(parse_id_number("-"))


def test_pm25_takes_worst_level_case_insensitive():
    assert parse_pm25("sedang – TIDAK  SEHAT") == 2
    assert parse_pm25("Baik") == 0


def test_visibility_minimum_token():
    assert parse_visibility("< 2") == 2
    assert parse_visibility("0.1 - 9") == 0.1


@pytest.mark.parametrize("short,full", [("Sumsel", "Sumatera Selatan"), ("Kalbar", "Kalimantan Barat"),
                                        ("Kalteng", "Kalimantan Tengah"), ("Kalsel", "Kalimantan Selatan"),
                                        ("Riau", "Riau"), (" Jambi ", "Jambi")])
def test_abbreviated_names_map_to_canonical(short, full):
    assert canonical_province_name(short) == full


def test_checksum_mismatch_logs_but_does_not_stop(tmp_path, caplog):
    years = [str(y) for y in range(2018, 2027)]
    rows = [["11.0", "Aceh"] + ["1.000,50"] * 9, ["12.0", "Sumatera Utara"] + ["2,00"] * 9,
            [None, "Total"] + ["9.999,00"] * 9]
    path = tmp_path / "luas.xlsx"
    pd.DataFrame(rows, columns=["Kode Wilayah", "Provinsi"] + years).to_excel(path, index=False)
    with caplog.at_level(logging.WARNING):
        prov, checks = load_burned_area(path)
    assert len(prov) == 2 and prov["2018"].tolist() == [1000.5, 2.0]
    assert (checks["relative_difference"] > 0.01).all()
    assert "checksum" in caplog.text.lower()


def test_prepare_completes_despite_checksum_mismatch(tmp_path):
    raw = tmp_path / "raw"; raw.mkdir()
    x = pd.read_excel(RAW / "luas-karhutla-provinsi.xlsx", dtype=str)
    x.loc[x.Provinsi.str.strip().str.lower() == "total", "2018"] = "1,00"
    x.to_excel(raw / "luas-karhutla-provinsi.xlsx", index=False)
    (raw / "karhutla-2026_semua-provinsi_2026-10-19.csv").write_bytes(
        (RAW / "karhutla-2026_semua-provinsi_2026-10-19.csv").read_bytes())
    features, _, checks = prepare(raw, tmp_path / "processed", tmp_path / "reports")
    assert len(features) == 38 and checks.set_index("year").loc["2018", "relative_difference"] > 0.01
    assert (tmp_path / "reports" / "data_quality.md").exists()


def test_real_xlsx_has_38_provinces_and_passing_checksum(features):
    assert len(features) == 38
    _, checks = load_burned_area(RAW / "luas-karhutla-provinsi.xlsx")
    assert (checks["relative_difference"] < 0.01).all()


@pytest.mark.parametrize("scenario", ["2019", "2026"])
def test_risk_is_globally_normalised(features, scenario):
    risk = features[f"risk_{scenario}"]
    assert risk.min() == pytest.approx(0) and risk.max() == pytest.approx(1)


def test_operational_provinces_have_positive_risk_in_2026(features):
    ops = features[features.Provinsi.isin(OPS_PROVINCES)]
    assert len(ops) == 6 and ops["has_ops"].all()
    assert (ops["risk_2026"] > 0).all()
    inst = build_instance(features, COORDS, n=6, scenario="2026")
    assert (inst.risk[1:] > 0).all()


def test_2019_scenario_ignores_operational_component(features):
    inst = build_instance(features, COORDS, n=38, scenario="2019")
    assert not inst.ops.any()


@pytest.mark.parametrize("scenario", ["2019", "2026"])
def test_risk_identical_across_instance_sizes(features, scenario):
    small = build_instance(features, COORDS, n=6, scenario=scenario)
    full = build_instance(features, COORDS, n=38, scenario=scenario)
    full_risk = dict(zip(full.names, full.risk))
    for name, r in zip(small.names, small.risk):
        assert r == full_risk[name]
        assert r == features.set_index("Provinsi").loc[name, f"risk_{scenario}"]


def test_n6_is_operational_provinces_with_depot_first(features):
    inst = build_instance(features, COORDS, n=6, scenario="2019")
    assert inst.names[0] == "Riau" and inst.depot == 0
    assert sorted(inst.names) == sorted(OPS_PROVINCES)


@pytest.mark.parametrize("n", [10, 15, 25, 38])
@pytest.mark.parametrize("scenario", ["2019", "2026"])
def test_top_k_by_risk_with_depot(features, n, scenario):
    names = select_provinces(features, n, scenario)
    assert len(names) == n == len(set(names)) and names[0] == "Riau"
    risk = features.set_index("Provinsi")[f"risk_{scenario}"]
    others = risk.drop("Riau")
    if n < 38:
        assert risk[names[1:]].min() >= others.drop(names[1:]).max()
    assert names == select_provinces(features.sample(frac=1, random_state=1), n, scenario)


def test_top_k_breaks_ties_by_name():
    f = pd.DataFrame({"Provinsi": ["Riau", "B", "A", "C"], "risk_2026": [0.1, 0.5, 0.5, 0.9],
                      "has_ops": [True, False, False, False]})
    assert select_provinces(f, 3, "2026") == ["Riau", "C", "A"]


def test_depot_is_always_included(features):
    names = select_provinces(features, 10, "2026", depot_name="DKI Jakarta")
    assert names[0] == "DKI Jakarta" and len(names) == 10
    ops = select_provinces(features, 6, "2026", depot_name="DKI Jakarta")
    assert ops[0] == "DKI Jakarta" and len(ops) == 6
    assert set(ops[1:]) < set(OPS_PROVINCES)


def test_invalid_size_or_scenario_rejected(features):
    with pytest.raises(ValueError):
        select_provinces(features, 39, "2026")
    with pytest.raises(ValueError):
        select_provinces(features, 10, "2020")
