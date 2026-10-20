"""Seam 5: documentation generator. Numbers and lists in the docs come from config.yaml and results/."""
import re
import pandas as pd
import pytest
from src.docs_gen import fill_blocks


def test_fill_blocks_replaces_only_the_marked_block_and_is_idempotent():
    text = "intro\n<!-- AUTO:tabel -->\nlama\n<!-- /AUTO:tabel -->\npenutup\n"
    once = fill_blocks(text, {"tabel": "| a |\n|---|\n| 1 |"})
    assert once == "intro\n<!-- AUTO:tabel -->\n| a |\n|---|\n| 1 |\n<!-- /AUTO:tabel -->\npenutup\n"
    assert fill_blocks(once, {"tabel": "| a |\n|---|\n| 1 |"}) == once


def test_fill_blocks_rejects_a_block_without_generator():
    with pytest.raises(KeyError):
        fill_blocks("<!-- AUTO:asing -->\n<!-- /AUTO:asing -->\n", {"tabel": "x"})


def _md_rows(md):
    """Data rows of a markdown table as lists of stripped cells."""
    rows = [[c.strip() for c in re.split(r"(?<!\\)\|", line.strip()[1:-1])] for line in md.splitlines()
            if line.startswith("|")]
    return rows[2:]


def _cfg(**over):
    import yaml
    from src.data_prep import ROOT
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf8"))
    cfg.update(over)
    return cfg


def test_provenance_values_come_from_the_config():
    from src.docs_gen import provenance_table
    rows = {r[0]: r for r in _md_rows(provenance_table(_cfg(time_limit_hours=48, speed_kmh=250, depot="Jambi")))}
    assert rows["Batas waktu misi `T_max`"][1] == "48 jam"
    assert rows["Batas waktu misi `T_max`"][3] == "DERIVED"
    assert rows["Kecepatan armada `v`"][1] == "250 km/jam"
    assert rows["Kecepatan armada `v`"][3] == "ASSUMED"
    assert rows["Depot"][1] == "Jambi"


def test_every_provenance_row_has_a_known_status():
    from src.docs_gen import provenance_table
    rows = _md_rows(provenance_table(_cfg()))
    assert len(rows) >= 20
    assert {r[3] for r in rows} <= {"REAL", "DERIVED", "ASSUMED", "SYNTHETIC"}
    assert all(r[1] and r[2] for r in rows)  # nilai dan sumber selalu terisi


def _summary(tmp_path):
    (tmp_path / "tables").mkdir(exist_ok=True)
    rows = [("2026", 6, "Exact", 3.0, 3.0), ("2026", 6, "Greedy", 2.5, 3.0), ("2026", 6, "HC", 3.0, 3.0),
            ("2026", 6, "SA", 2.9996, 3.0), ("2026", 6, "GA", 2.0, 3.0),
            ("2026", 38, "Greedy", 8.0, 9.5), ("2026", 38, "HC", 8.5, 9.5), ("2026", 38, "SA", 9.25, 9.5),
            ("2026", 38, "GA", 7.0, 9.5)]
    pd.DataFrame(rows, columns=["scenario", "n", "algorithm", "mean", "best_known"]).to_csv(
        tmp_path / "tables" / "summary.csv", index=False)
    return tmp_path


def test_results_summary_lists_mean_fitness_per_algorithm_and_the_winner(tmp_path):
    from src.docs_gen import results_summary
    rows = _md_rows(results_summary(_summary(tmp_path)))
    assert rows == [["2026", "6", "3.000", "2.500", "**3.000**", "3.000", "2.000", "HC"],
                    ["2026", "38", "9.500", "8.000", "8.500", "**9.250**", "7.000", "SA"]]


def test_algorithm_diagnostics_come_from_the_runs(tmp_path):
    from src.docs_gen import algorithm_diagnostics
    (tmp_path / "raw").mkdir()
    runs = pd.DataFrame({
        "algorithm": ["HC", "HC", "SA", "SA", "GA", "GA", "Greedy"], "n": [38] * 7, "scenario": ["2026"] * 7,
        "fitness": [9.0, 8.0, 9.5, 9.0, 7.0, 6.0, 8.7],
        "hc_single_start_fitness": [8.0, 8.0, None, None, None, None, None],
        "hc_restarts": [1, 2, None, None, None, None, None],
        "sa_acceptance_rate": [None, None, .2, .3, None, None, None],
        "ga_generations": [None, None, None, None, 509, 509, None]})
    runs.to_csv(tmp_path / "raw" / "runs.csv", index=False)
    assert _md_rows(algorithm_diagnostics(tmp_path)) == [
        # 37 kandidat: 666 swap + 3 × 630 (relocate dua arah dan 2-opt dengan jarak ≥ 2) = 2556 tetangga
        ["2026", "38", "2556", "8.000", "8.500", "1.5", "0.250", "509"]]


def test_check_reports_stale_docs_and_a_rewrite_fixes_them(tmp_path):
    import shutil
    from src.data_prep import ROOT
    from src.docs_gen import main
    shutil.copy(ROOT / "config.yaml", tmp_path / "config.yaml")
    doc = tmp_path / "DATA_PROVENANCE.md"
    doc.write_text("# P\n<!-- AUTO:provenance -->\nusang\n<!-- /AUTO:provenance -->\n", encoding="utf8")
    assert main(["--root", str(tmp_path), "--check"]) == 1
    assert "usang" in doc.read_text(encoding="utf8")
    assert main(["--root", str(tmp_path)]) == 0
    assert "Batas waktu misi `T_max`" in doc.read_text(encoding="utf8")
    assert main(["--root", str(tmp_path), "--check"]) == 0


def test_committed_docs_match_the_saved_results():
    """Every generated block in the repo docs equals what config.yaml and results/ produce now."""
    from src.docs_gen import main
    assert main(["--check"]) == 0


def _results(tmp_path, figures=(), tables=()):
    for sub, names in (("figures", figures), ("tables", tables)):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
        for name in names: (tmp_path / sub / name).write_text("x")
    return tmp_path


def test_figure_list_gives_every_figure_and_table_its_caption(tmp_path):
    from src.docs_gen import figure_list
    res = _results(tmp_path, figures=["peta.png"], tables=["ringkas.md", "ringkas.csv"])
    out = figure_list(res, {"figures/peta.png": "Peta rute.", "tables/ringkas.md": "Ringkasan."})
    assert "`results/figures/peta.png`: Peta rute." in out
    assert "`results/tables/ringkas.md`: Ringkasan." in out
    assert out.index("peta.png") < out.index("ringkas.md")  # gambar sebelum tabel


def test_figure_list_refuses_an_uncaptioned_or_missing_file(tmp_path):
    from src.docs_gen import figure_list
    res = _results(tmp_path, figures=["peta.png", "baru.png"])
    with pytest.raises(ValueError, match="baru.png"):
        figure_list(res, {"figures/peta.png": "Peta rute."})
    with pytest.raises(ValueError, match="hilang.png"):
        figure_list(res, {"figures/peta.png": "a", "figures/baru.png": "b", "figures/hilang.png": "c"})
