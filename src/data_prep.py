"""Preprocess the supplied Indonesian wildfire datasets into 38 province features."""
from pathlib import Path
import logging
import re
import numpy as np
import pandas as pd
from src.numfmt import id_format

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
XLSX_NAME = "luas-karhutla-provinsi.xlsx"
OPS_CSV_NAME = "karhutla-2026_semua-provinsi_2026-10-19.csv"

YEARS = [str(y) for y in range(2018, 2027)]
HIST_YEARS = [str(y) for y in range(2018, 2026)]
SCENARIOS = ("2019", "2026")
OPS_SCENARIO = "2026"  # the operations CSV is a 2026 snapshot; other scenarios ignore it
DEFAULT_WEIGHTS = (.4, .3, .3)  # hist, cur, ops
DEFAULT_GAMMA = .8
CHECKSUM_TOLERANCE = .01

NAME_MAP = {"Sumsel":"Sumatera Selatan", "Kalbar":"Kalimantan Barat",
            "Kalteng":"Kalimantan Tengah", "Kalsel":"Kalimantan Selatan"}
PM_LEVELS = {"baik":0, "sedang":1, "tidak sehat":2,
             "sangat tidak sehat":3, "berbahaya":4}
CHECK_COLUMNS = ["year","sum_provinces_ha","total_row_ha","relative_difference"]

log = logging.getLogger(__name__)

def _missing(value):
    return pd.isna(value) or str(value).strip() in {"", "-", "—"}

def parse_id_number(value):
    """Parse Indonesian formatted numeric strings; missing tokens become NaN."""
    if _missing(value): return np.nan
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    s = str(value).strip().replace(".", "").replace(",", ".")
    try: return float(s)
    except ValueError: return np.nan

def parse_pm25(value):
    """Map PM2.5 text/ranges to the worst ordinal level found."""
    if _missing(value): return np.nan
    s = re.sub(r"\s+", " ", str(value).lower().replace("–", "-"))
    hits = [v for k, v in PM_LEVELS.items() if k in s]
    return max(hits) if hits else np.nan

def parse_visibility(value):
    """Conservative visibility: minimum numeric token in the text."""
    if _missing(value): return np.nan
    nums = re.findall(r"\d+(?:[.,]\d+)?", str(value))
    return min(float(x.replace(",", ".")) for x in nums) if nums else np.nan

def canonical_province_name(name):
    """Map abbreviated CSV province names to the canonical xlsx names."""
    s = str(name).strip()
    return NAME_MAP.get(s, s)

def minmax(series):
    s = pd.to_numeric(series, errors="coerce")
    lo, hi = s.min(), s.max()
    if pd.isna(lo) or pd.isna(hi) or hi == lo: return pd.Series(0.0, index=s.index)
    return (s-lo)/(hi-lo)

def load_burned_area(path):
    """Read the burned-area xlsx; the Total row is used as a per-year checksum, then dropped.

    Checksum mismatches are logged, never raised.
    """
    x = pd.read_excel(path, dtype=str)
    # Excel column labels may be inferred as integers.
    x.columns = [str(c).strip() for c in x.columns]
    total_mask = x["Provinsi"].astype(str).str.strip().str.lower().eq("total")
    total_row = x.loc[total_mask].iloc[0] if total_mask.any() else None
    if total_row is None: log.warning("Baris Total tidak ditemukan di %s; checksum dilewati", path)
    prov = x.loc[~total_mask].copy().reset_index(drop=True)
    prov["Provinsi"] = prov["Provinsi"].str.strip()
    prov["Kode Wilayah"] = prov["Kode Wilayah"].astype(str)
    for y in YEARS: prov[y] = prov[y].map(parse_id_number)
    checks = []
    for y in YEARS:
        reported = parse_id_number(total_row[y]) if total_row is not None else np.nan
        actual = prov[y].sum()
        rel = abs(actual-reported)/max(abs(reported),1) if pd.notna(reported) else np.nan
        if pd.notna(rel) and rel > CHECKSUM_TOLERANCE:
            log.warning("Checksum tahun %s tidak cocok: jumlah provinsi %.2f ha vs baris Total %.2f ha (selisih %.2f%%)",
                        y, actual, reported, 100*rel)
        checks.append((y, actual, reported, rel))
    return prov, pd.DataFrame(checks, columns=CHECK_COLUMNS)

def load_operations(path):
    """Read the 2026-10-19 operations snapshot and derive a raw severity proxy per province."""
    c = pd.read_csv(path, encoding="utf-8-sig")
    c["Provinsi"] = c["Provinsi"].map(canonical_province_name)
    c = c.replace(r"^\s*-\s*$", np.nan, regex=True).replace(r"^\s*$", np.nan, regex=True)
    for col in ["Total Hotspot","Fire Spot","Lahan Terbakar Indikatif (Ha)",
                "Lahan Terbakar Harian (Ha)","Total Personel","Total Unit Udara Hari Ini",
                "Total Unit Standby"]:
        if col in c: c[col+"_num"] = c[col].map(parse_id_number)
    c["pm25_ordinal"] = c["Kualitas Udara (PM 25)"].map(parse_pm25)
    c["visibility_km_conservative"] = c["Jarak Pandang Bandara (Km)"].map(parse_visibility)
    # Build operational severity from available observed fields only.
    c["ops_burn_norm"] = minmax(c.get("Lahan Terbakar Indikatif (Ha)_num", pd.Series(np.nan,index=c.index))).fillna(0)
    c["ops_fire_norm"] = minmax(c.get("Fire Spot_num", pd.Series(np.nan,index=c.index))).fillna(0)
    c["ops_pm_norm"] = c["pm25_ordinal"].fillna(0)/4
    inv_vis = 1/(c["visibility_km_conservative"].clip(lower=0.1))
    c["ops_visibility_norm"] = minmax(inv_vis).fillna(0)
    c["ops_raw"] = c[["ops_burn_norm","ops_fire_norm","ops_pm_norm","ops_visibility_norm"]].mean(axis=1)
    return c

def add_risk(merged, weights=DEFAULT_WEIGHTS, gamma=DEFAULT_GAMMA):
    """Add components and the final Risiko per scenario, min-max normalised once over all provinces."""
    a, b, d = weights
    # Historical recency-weighted log sum 2018–2025; 2026 partial year handled separately.
    last = int(HIST_YEARS[-1])
    merged["hist_raw"] = sum(gamma**(last-int(y))*np.log1p(merged[y].clip(lower=0)) for y in HIST_YEARS)
    merged["hist_norm"] = minmax(merged["hist_raw"])
    for y in YEARS:
        merged[f"cur_{y}_raw"] = np.log1p(merged[y].clip(lower=0))
        merged[f"cur_{y}_norm"] = minmax(merged[f"cur_{y}_raw"])
    # Ops missing for 32 provinces are zero and explicitly flagged, not imputed.
    merged["ops_norm"] = minmax(merged["ops_raw"].where(merged["has_ops"])).fillna(0)
    for s in SCENARIOS:
        ops = merged["ops_norm"] if s == OPS_SCENARIO else 0
        merged[f"risk_{s}_raw"] = a*merged["hist_norm"] + b*merged[f"cur_{s}_norm"] + d*ops
        merged[f"risk_{s}"] = minmax(merged[f"risk_{s}_raw"])
    return merged

def _md(df):
    from src.experiments.reporting import to_markdown_id
    return to_markdown_id(df)

def write_quality_report(path, merged, checks, disc):
    riau = merged.set_index("Provinsi").loc["Riau"]
    ops = merged[merged["has_ops"]].sort_values("risk_2026", ascending=False)
    text = ["# Laporan Kualitas Data","",
      f"- Jumlah baris provinsi setelah baris Total dibuang: **{len(merged)}** (harapan 38).",
      "- Nilai xlsx 2026 adalah data **parsial** sampai 2026-10-19, bukan total setahun penuh.",
      "- Koordinat ibu kota provinsi adalah asumsi geografi publik (ASSUMED), bukan bagian dataset, dan perlu diverifikasi.",
      "- Kolom operasional yang kosong dibiarkan kosong di file operasional bersih. Untuk Risiko, provinsi tanpa data operasional mendapat `ops_norm=0` dengan penanda `has_ops=False` (tanpa imputasi).",
      "- Kategori PM2.5 berbentuk rentang memakai tingkat terburuk (maksimum). Visibilitas memakai angka minimum di dalam teks.",
      "- Risiko dinormalisasi min-max **sekali atas 38 provinsi** per skenario tahun, sehingga nilainya sama di instance mana pun. Komponen operasional hanya dipakai untuk skenario 2026.",
      "", "## Checksum baris Total xlsx", "", _md(checks.rename(columns={
          "year":"tahun","sum_provinces_ha":"jumlah_provinsi_ha","total_row_ha":"baris_total_ha","relative_difference":"selisih_relatif"})),
      "", f"Selisih relatif di atas {CHECKSUM_TOLERANCE:.0%} dicatat sebagai peringatan; pipeline tidak dihentikan.",
      "", "## Luas terbakar indikatif (CSV) vs xlsx 2026", "", _md(disc.rename(columns={
          "2026":"xlsx_2026_ha","Lahan Terbakar Indikatif (Ha)_num":"indikatif_csv_ha",
          "difference_ha":"selisih_ha","absolute_difference_ha":"selisih_absolut_ha"})),
      "", "Selisih dilaporkan apa adanya, tidak direkonsiliasi. Perbedaan tanggal laporan atau definisi dapat menjelaskan sebagian selisih.",
      "", "## Inkonsistensi Riau", "",
      f"Riau mencatat Total Hotspot = {riau['Total Hotspot_num']:g}, tetapi Fire Spot = {riau['Fire Spot_num']:g}, "
      f"kualitas udara \"{riau['Kualitas Udara (PM 25)']}\", dan luas terbakar indikatif {id_format(riau['Lahan Terbakar Indikatif (Ha)_num'], ',.2f')} ha. "
      "Karena itu jumlah hotspot **tidak pernah** dipakai sendirian sebagai ukuran keparahan.",
      "", "## Risiko provinsi operasional", "", _md(ops[["Provinsi","hist_norm","cur_2026_norm","ops_norm","risk_2026","risk_2019"]].rename(columns={
          "hist_norm":"historis","cur_2026_norm":"tahun_berjalan_2026","ops_norm":"operasional",
          "risk_2026":"Risiko_2026","risk_2019":"Risiko_2019"})),
      "", "## Keterbatasan", "",
      "- CSV hanya berisi snapshot operasional enam provinsi; ketiadaan baris bukan bukti tidak ada kebakaran.",
      "- Keparahan operasional yang dinormalisasi adalah proksi pemodelan dari kolom yang tersedia, bukan indeks bahaya resmi.",
      "- Jarak antar-ibu kota, kecepatan 200 km/jam, faktor detour 1,15, dan waktu tinggal adalah asumsi pemodelan."]
    path.write_text("\n".join(text)+"\n", encoding="utf-8")

def prepare(raw_dir=RAW, processed_dir=PROCESSED, reports_dir=REPORTS, weights=DEFAULT_WEIGHTS, gamma=DEFAULT_GAMMA):
    """Build the 38-province feature table and data-quality report; returns (features, discrepancy, checks)."""
    raw_dir, processed_dir, reports_dir = Path(raw_dir), Path(processed_dir), Path(reports_dir)
    processed_dir.mkdir(parents=True, exist_ok=True); reports_dir.mkdir(parents=True, exist_ok=True)
    prov, checks = load_burned_area(raw_dir/XLSX_NAME)
    if len(prov) != 38: log.warning("Jumlah provinsi %d, bukan 38", len(prov))
    c = load_operations(raw_dir/OPS_CSV_NAME)
    ops_cols = ["Provinsi","Total Hotspot_num","Fire Spot_num","Lahan Terbakar Indikatif (Ha)_num",
                "Kualitas Udara (PM 25)","pm25_ordinal","Jarak Pandang Bandara (Km)",
                "visibility_km_conservative","Total Personel_num","Total Unit Udara Hari Ini_num",
                "Total Unit Standby_num","ops_raw"]
    ops = c[[z for z in ops_cols if z in c.columns]].copy()
    unknown = set(ops["Provinsi"]) - set(prov["Provinsi"])
    if unknown: log.warning("Provinsi di CSV operasional tidak ada di xlsx: %s", sorted(unknown))
    merged = prov.merge(ops, on="Provinsi", how="left", validate="one_to_one")
    merged["has_ops"] = merged["ops_raw"].notna()
    merged["ops_raw"] = merged["ops_raw"].fillna(0)
    merged = add_risk(merged, weights, gamma)
    disc = merged[["Provinsi","2026"]].merge(c[["Provinsi","Lahan Terbakar Indikatif (Ha)_num"]],on="Provinsi",how="inner")
    disc["difference_ha"] = disc["Lahan Terbakar Indikatif (Ha)_num"] - disc["2026"]
    disc["absolute_difference_ha"] = disc["difference_ha"].abs()
    merged.to_csv(processed_dir/"province_features.csv", index=False)
    c.to_csv(processed_dir/"operations_2026_clean.csv", index=False)
    checks.to_csv(processed_dir/"xlsx_total_checks.csv", index=False)
    disc.to_csv(processed_dir/"indicative_vs_xlsx_2026.csv", index=False)
    write_quality_report(reports_dir/"data_quality.md", merged, checks, disc)
    return merged, disc, checks

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    features, discrepancy, checks = prepare()
    print(f"Selesai menyiapkan {len(features)} provinsi")
    print("\nCek silang luas indikatif 2026 (CSV vs xlsx):")
    print(discrepancy.to_string(index=False))
    print("\nChecksum baris Total:")
    print(checks.to_string(index=False))
    print("\nRisiko provinsi operasional:")
    print(features.loc[features["has_ops"], ["Provinsi","risk_2026","risk_2019"]].to_string(index=False))
