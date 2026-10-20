"""Indonesian number format in everything a reader sees: decimal comma in figures and .md tables,
decimal point kept in CSV."""
import pandas as pd
from src.numfmt import id_format, id_table_cell


def test_id_format_swaps_decimal_and_thousands_separators():
    assert id_format(9603.2, ",.0f") == "9.603"
    assert id_format(1284.7, ",.2f") == "1.284,70"
    assert id_format(0.005, "g") == "0,005"
    assert id_format(9.0794, ".3f") == "9,079"
    assert id_format(5.974e-06, ".4g") == "5,974e-06"
    assert id_format(72, "g") == "72"


def test_table_cell_formats_floats_only():
    assert id_table_cell(0.5, ".4g") == "0,5"
    assert id_table_cell(float("nan"), ".4g") == ""
    assert id_table_cell(20000, ".4g") == 20000
    assert id_table_cell("SA", ".4g") == "SA"
    assert id_table_cell(True, ".4g") is True


def test_write_table_md_uses_decimal_comma_and_csv_keeps_point(tmp_path):
    from src.experiments.reporting import write_table
    df = pd.DataFrame({"algorithm": ["SA"], "mean": [9.0794], "evals": [50000]})
    write_table(df, tmp_path / "t", rename={"mean": "rata-rata"})
    assert pd.read_csv(tmp_path / "t.csv")["mean"].iloc[0] == 9.0794
    md = (tmp_path / "t.md").read_text(encoding="utf8")
    assert "9,079" in md and "9.079" not in md and "50000" in md


def test_figure_tick_labels_use_decimal_comma(tmp_path):
    import matplotlib.pyplot as plt
    from src.experiments.plots import save
    fig, ax = plt.subplots()
    ax.plot([0, 0.005, 0.01, 0.02], [0.5, 1.5, 2.5, 3.5])
    save(fig, tmp_path / "f.png")
    labels = [t.get_text() for t in ax.get_xticklabels() + ax.get_yticklabels() if t.get_text()]
    assert labels and all("." not in s for s in labels)
    assert any("," in s for s in labels)


def test_id_text_converts_decimals_outside_code_spans():
    from src.numfmt import id_text
    assert id_text("g0 0.01 /jam; `config.yaml: decay_g0` = `0.01`") == "g0 0,01 /jam; `config.yaml: decay_g0` = `0.01`"
    assert id_text("p 5.974e-06; 72 jam; n=38") == "p 5,974e-06; 72 jam; n=38"
    assert id_text("`src/instance.py` v1.2.3") == "`src/instance.py` v1.2.3"
    assert id_text("naik ke 33.03.") == "naik ke 33,03."
