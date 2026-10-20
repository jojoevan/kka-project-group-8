"""Fill the generated blocks of the documentation from config.yaml and the saved results.

A block is delimited by ``<!-- AUTO:key -->`` and ``<!-- /AUTO:key -->``; everything between the markers
is replaced by the output of the generator for ``key``. Text outside the markers is never touched.
"""
import re
from pathlib import Path
import pandas as pd
from src.experiments.records import HEURISTICS

_BLOCK = re.compile(r"(<!-- AUTO:([\w-]+) -->\n)(.*?)(<!-- /AUTO:\2 -->)", re.S)


def fill_blocks(text, blocks):
    """Replace the body of every AUTO block in text with blocks[key]; unknown keys raise KeyError."""
    def sub(m):
        return m.group(1) + blocks[m.group(2)].rstrip("\n") + "\n" + m.group(4)
    return _BLOCK.sub(sub, text)


def _md_table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(":--" for _ in header) + "|"]
    cell = lambda c: str(c).replace("|", "\\|")
    return "\n".join(out + ["| " + " | ".join(cell(c) for c in r) + " |" for r in rows])


def provenance_table(cfg):
    """One row per model parameter: parameter | nilai | sumber | status (REAL/DERIVED/ASSUMED/SYNTHETIC).

    Values are read from cfg (config.yaml) and from the constants in the code, never typed by hand."""
    from src import calibration, data_prep
    from importlib import import_module  # src.algorithms re-exports solve() under the module names
    exact, ga, sa = (import_module(f"src.algorithms.{m}")
                     for m in ("exact", "genetic_algorithm", "simulated_annealing"))
    from src.instance import INSTANCE_SIZES
    w = cfg["weights"]; b = cfg["evaluation_budget"]; sens = cfg["analysis"]["sensitivity"]
    q = cfg["quick"]; hist = data_prep.HIST_YEARS
    raw_xlsx = "`data/raw/luas-karhutla-provinsi.xlsx`"; raw_csv = f"`data/raw/{data_prep.OPS_CSV_NAME}`"
    prep = "`src/data_prep.py` → `data/processed/province_features.csv`"
    rows = [
        ("Luas terbakar per provinsi", f"38 provinsi × {data_prep.YEARS[0]}–{data_prep.YEARS[-1]} (ha); "
         f"{data_prep.YEARS[-1]} parsial s.d. 2026-10-19", raw_xlsx, "REAL"),
        ("Data operasional", "6 provinsi, snapshot 2026-10-19 (hotspot, fire spot, luas indikatif, PM2.5, "
         "visibilitas bandara, personel, unit udara)", raw_csv, "REAL"),
        ("Komponen historis `hist`", f"Σ γ^({hist[-1]}−tahun)·log1p(luas), {hist[0]}–{hist[-1]}, "
         "min-max atas 38 provinsi", prep, "DERIVED"),
        ("Komponen tahun berjalan `cur`", "log1p(luas tahun Skenario tahun), min-max atas 38 provinsi",
         prep, "DERIVED"),
        ("Ordinal PM2.5", "Baik=0, Sedang=1, Tidak Sehat=2, Sangat Tidak Sehat=3, Berbahaya=4; "
         "rentang → tingkat terburuk", prep, "DERIVED"),
        ("Visibilitas bandara", "angka minimum di dalam teks (km)", prep, "DERIVED"),
        ("Komponen operasional `ops`", "rata-rata luas indikatif, fire spot, PM2.5/4, 1/visibilitas "
         "(masing-masing ternormalisasi), min-max antar-6 provinsi; 0 untuk 32 provinsi lain "
         f"(`has_ops=False`, tanpa imputasi); hanya Skenario tahun {data_prep.OPS_SCENARIO}", prep, "DERIVED"),
        ("Risiko", "α·hist + β·cur + δ·ops, lalu min-max **sekali** atas 38 provinsi per Skenario tahun",
         prep, "DERIVED"),
        ("Jarak antar-node", f"Haversine antar-ibu kota × faktor detour {cfg['detour_factor']}",
         "`src/instance.py`", "DERIVED"),
        ("Laju decay node `g_i`", "g0·(1 + κ·ops_i); ops_i = 0 di luar Skenario tahun "
         f"{data_prep.OPS_SCENARIO}", "`src/instance.py`", "DERIVED"),
        ("Pemilihan node instance", "n=6: Depot + provinsi ber-data operasional; n lain: Depot + top-(n−1) "
         "Risiko; n=38: semua provinsi", "`src/instance.py`", "DERIVED"),
        ("Batas waktu misi `T_max`", f"{cfg['time_limit_hours']} jam", "kalibrasi Greedy n=38 skenario 2026, "
         f"kandidat {list(calibration.CANDIDATE_TIME_LIMITS)} jam, target "
         f"{calibration.TARGET_FRACTION[0]:.0%}–{calibration.TARGET_FRACTION[1]:.0%} node terkunjungi "
         "(`src/calibration.py`; hasil: `results/tables/instances.md`)", "DERIVED"),
        ("Bobot Risiko α, β, δ", f"{w['hist']}, {w['cur']}, {w['ops']}", "`config.yaml: weights`", "ASSUMED"),
        ("Faktor keterkinian γ", f"{cfg['gamma']}", "`config.yaml: gamma`", "ASSUMED"),
        ("Koordinat node provinsi", "koordinat ibu kota provinsi (geografi publik, perlu diverifikasi)",
         "`data/external/province_coords.csv`", "ASSUMED"),
        ("Depot", cfg["depot"], "`config.yaml: depot`", "ASSUMED"),
        ("Kecepatan armada `v`", f"{cfg['speed_kmh']} km/jam", "`config.yaml: speed_kmh`", "ASSUMED"),
        ("Faktor detour", f"{cfg['detour_factor']}", "`config.yaml: detour_factor`", "ASSUMED"),
        ("Waktu tinggal per Kunjungan", f"{cfg['dwell_hours']} jam", "`config.yaml: dwell_hours`", "ASSUMED"),
        ("Laju decay dasar `g0`", f"{cfg['decay_g0']} /jam", "`config.yaml: decay_g0`", "ASSUMED"),
        ("Pengali keparahan decay κ", f"{cfg['decay_kappa']}", "`config.yaml: decay_kappa`", "ASSUMED"),
        ("Bentuk Prize", "Risiko·exp(−g_i·waktu tiba); proksi kerusakan yang dicegah, bukan ukuran resmi",
         "`src/instance.py`", "ASSUMED"),
        ("Skenario tahun", ", ".join(data_prep.SCENARIOS), "`src/data_prep.py: SCENARIOS`", "ASSUMED"),
        ("Ukuran instance n (termasuk Depot)", ", ".join(map(str, INSTANCE_SIZES)),
         "`src/instance.py: INSTANCE_SIZES`", "ASSUMED"),
        ("Budget evaluasi per run", f"{b['small']} (n ≤ {b['small_max_n']}), {b['large']} (n > "
         f"{b['small_max_n']})", "`config.yaml: evaluation_budget`", "ASSUMED"),
        ("Jumlah seed per konfigurasi", f"{cfg['seeds']}", "`config.yaml: seeds`", "ASSUMED"),
        ("HC", "steepest-ascent atas seluruh neighbourhood swap/relocate/2-opt; restart acak sampai budget "
         "habis", "`src/algorithms/hill_climbing.py`", "ASSUMED"),
        ("SA: T0 dan pendinginan", f"T0 = rata-rata |Δ| positif dari {sa.CALIBRATION_MOVES} move acak; "
         f"geometris c = {sa.FINAL_TEMPERATURE_RATIO}^(1/sisa budget); tanpa reheating",
         "`src/algorithms/simulated_annealing.py`", "ASSUMED"),
        ("GA", f"populasi {ga.POPULATION}, tournament k={ga.TOURNAMENT}, OX, mutasi {ga.MUTATION}, "
         f"elitisme {ga.ELITES}, populasi awal acak (tanpa seeding greedy)",
         "`src/algorithms/genetic_algorithm.py`", "ASSUMED"),
        ("Exact", f"enumerasi urutan dengan pemangkasan Batas waktu misi, maks. {exact.MAX_NODES} node termasuk Depot "
         f"(n ≤ {exact.MAX_NODES}, n mencakup Depot; {exact.MAX_NODES - 1} node kandidat)",
         "`src/algorithms/exact.py`", "ASSUMED"),
        ("Sweep sensitivitas", f"n={sens['n']}, skenario {sens['scenario']}; T_max "
         f"{sens['time_limit_hours']} jam; g0 {sens['decay_g0']}", "`config.yaml: analysis.sensitivity`",
         "ASSUMED"),
        ("Mode cepat (`--quick`)", f"n {q['sizes']}, {q['seeds']} seed, budget {q['budget']}",
         "`config.yaml: quick`", "ASSUMED"),
    ]
    return _md_table(["parameter", "nilai", "sumber", "status"], rows)


_TIE = 1e-9


def results_summary(results_dir):
    """Mean fitness (30 seeds) per heuristic per Skenario tahun and n, from tables/summary.csv.

    The highest mean is bold and named in the last column; equal means (within 1e-9) are all named."""
    s = pd.read_csv(Path(results_dir) / "tables" / "summary.csv", dtype={"scenario": str})
    rows = []
    for (scen, n), g in s.groupby(["scenario", "n"], sort=True):
        mean = g.set_index("algorithm")["mean"]; top = max(mean[a] for a in HEURISTICS)
        winners = [a for a in HEURISTICS if mean[a] >= top - _TIE]
        cells = [f"**{mean[a]:.3f}**" if a in winners else f"{mean[a]:.3f}" for a in HEURISTICS]
        rows.append([scen, n, f"{g.best_known.iloc[0]:.3f}", *cells, " / ".join(winners)])
    return _md_table(["skenario", "n", "best-known", *(f"{a} rata-rata" for a in HEURISTICS),
                      "rata-rata tertinggi"], rows)


def algorithm_diagnostics(results_dir):
    """Per Skenario tahun and n, from raw/runs.csv: HC single-start vs final mean, mean HC restarts, seeds
    whose HC never restarted (hc_restarts counts climbs started, so 1 means the first climb was still
    running when the budget ran out, or ended on its very last evaluation), mean SA acceptance rate and
    mean GA generations. The HC neighbourhood size (evaluations per steepest-ascent step, n−1 candidate
    nodes) comes from the shared move set."""
    from src.algorithms.common import all_moves
    r = pd.read_csv(Path(results_dir) / "raw" / "runs.csv", dtype={"scenario": str})
    rows = []
    for (scen, n), g in r.groupby(["scenario", "n"], sort=True):
        hc, sa, ga = (g[g.algorithm == a] for a in ("HC", "SA", "GA"))
        rows.append([scen, n, len(all_moves(int(n) - 1)), f"{hc.hc_single_start_fitness.mean():.3f}",
                     f"{hc.fitness.mean():.3f}", f"{hc.hc_restarts.mean():.1f}",
                     f"{int((hc.hc_restarts == 1).sum())}/{len(hc)}",
                     f"{sa.sa_acceptance_rate.mean():.3f}", f"{ga.ga_generations.mean():.0f}"])
    return _md_table(["skenario", "n", "evaluasi per langkah HC (neighbourhood)", "HC single-start rata-rata",
                      "HC akhir rata-rata", "restart HC rata-rata",
                      "seed dengan 1 pendakian HC (pendakian pertama belum selesai saat budget habis)",
                      "acceptance rate SA rata-rata", "generasi GA rata-rata"], rows)


def firms_provenance_table(cfg, results_dir):
    """Provenance rows of the Klaster hotspot instances: values from cfg (config.yaml) and constants in
    the code; hotspot counts and the calibrated Batas waktu misi from the saved FIRMS tables."""
    from src import calibration
    f = cfg["firms"]; res = Path(results_dir) / "tables"; k_cal = int(f["calibration_k"])
    snap = Path(f["snapshot"]); source = Path(results_dir).parent / snap.with_suffix(".source.txt")
    downloaded = next((line.split(":", 1)[1].strip() for line in source.read_text(encoding="utf8").splitlines()
                       if line.startswith("Diunduh")), None) if source.exists() else None
    inst = pd.read_csv(res / "firms_instances.csv")
    regions = pd.read_csv(res / f"firms_clusters_k{k_cal}.csv").groupby("region").hotspots.sum().sort_index()
    cal = pd.read_csv(res / "firms_calibration.csv")
    T = float(inst.time_limit_h.iloc[0]); lo, hi = calibration.TARGET_FRACTION
    chosen = cal[cal.time_limit_h == T].iloc[0]; hit = lo <= chosen.visited_fraction <= hi
    status = ("dalam target" if hit else
              f"tidak ada kandidat dalam target, dipilih yang terdekat: {chosen.visited_fraction:.0%} klaster "
              "terkunjungi")
    candidates = ", ".join(f"{int(r.time_limit_h)} jam → {r.visited_fraction:.0%}" for r in cal.itertuples())
    boxes = "; ".join(f"{name} {box}" for name, box in f["bboxes"].items())
    rows = [
        ("Snapshot hotspot VIIRS 7 hari", "NASA FIRMS VIIRS S-NPP 375 m, Asia Tenggara"
         + (f", diunduh {downloaded}" if downloaded else ""), f"`{snap.as_posix()}` (+ `.source.txt`)", "REAL"),
        ("Filter confidence", "/".join(f["confidence"]), "`config.yaml: firms.confidence`", "ASSUMED"),
        ("Bounding box", f"{boxes} ([lat_min, lat_max, lon_min, lon_max], kotak kasar pulau)",
         "`config.yaml: firms.bboxes`", "ASSUMED"),
        ("Hotspot setelah filter", f"{int(inst.hotspots.iloc[0])} (" + ", ".join(
            f"{r} {int(c)}" for r, c in regions.items()) + ")", "`results/tables/firms_instances.md`", "DERIVED"),
        ("Jumlah Klaster hotspot k", ", ".join(map(str, f["sizes"])) + " (instance = k node + Depot)",
         "`config.yaml: firms.sizes`", "ASSUMED"),
        ("Klasterisasi", f"k-means (Lloyd, seeding k-means++), seed {f['kmeans_seed']}, atas (lat, lon·cos lat)",
         "`src/firms.py`, `config.yaml: firms.kmeans_seed`", "ASSUMED"),
        ("Lokasi node klaster", "pusat klaster; hotspot anggota terdekat bila pusatnya jatuh di luar kotak "
         "(klaster lintas wilayah)", "`src/firms.py`", "DERIVED"),
        ("Risiko klaster", "Σ FRP → log1p → min-max antar-klaster dalam satu instance", "`src/firms.py`",
         "DERIVED"),
        ("Laju decay klaster", f"konstan g0 = {cfg['decay_g0']} /jam (tanpa data operasional, κ tidak dipakai)",
         "`docs/adr/0001-firms-clusters-instead-of-synthetic.md`", "ASSUMED"),
        ("Depot FIRMS", f"{inst.depot.iloc[0]} (ibu kota provinsi {cfg['depot']})", "`config.yaml: depot`", "ASSUMED"),
        ("Batas waktu misi FIRMS", f"{T:g} jam ({status})",
         f"kalibrasi Greedy k={k_cal}, kandidat {candidates}, target {lo:.0%}–{hi:.0%} (`src/calibration.py`; "
         "hasil: `results/tables/firms_calibration.md`)", "DERIVED"),
        ("Budget evaluasi FIRMS", f"{f['budget']}", "`config.yaml: firms.budget`", "ASSUMED"),
        ("Mode cepat FIRMS (`--quick`)", f"k {f['quick']['sizes']}, {f['quick']['seeds']} seed, budget "
         f"{f['quick']['budget']}", "`config.yaml: firms.quick`", "ASSUMED"),
    ]
    return _md_table(["parameter", "nilai", "sumber", "status"], rows)


def firms_summary(results_dir):
    """Per k (Klaster hotspot instance), from tables/firms_summary.csv and tables/firms_instances.csv:
    Batas waktu misi, Greedy visits, best-known, mean fitness per heuristic (highest bold) and the
    tie-aware ranking of firms_phase.ranking."""
    from src.experiments.firms_phase import format_ranking, ranking
    res = Path(results_dir) / "tables"
    s = pd.read_csv(res / "firms_summary.csv", dtype={"scenario": str})
    inst = pd.read_csv(res / "firms_instances.csv").set_index("k")
    order = ranking(s); rows = []
    for (scen, n), g in s.groupby(["scenario", "n"], sort=True):
        mean = g.set_index("algorithm")["mean"]; k = int(g.k.iloc[0]); top = max(mean[a] for a in HEURISTICS)
        cells = [f"**{mean[a]:.3f}**" if mean[a] >= top - _TIE else f"{mean[a]:.3f}" for a in HEURISTICS]
        i = inst.loc[k]
        rows.append([k, f"{i.time_limit_h:g}", f"{int(i.greedy_visited)} ({i.greedy_visited_fraction:.0%})",
                     f"{g.best_known.iloc[0]:.3f}", *cells, format_ranking(order[scen, n])])
    return _md_table(["k", "Batas waktu misi (jam)", "klaster terkunjungi Greedy", "best-known",
                      *(f"{a} rata-rata" for a in HEURISTICS), "peringkat (= berarti seri)"], rows)


def firms_hc_cost(results_dir):
    """Steepest-Ascent HC cost from tables/firms_hc_cost.csv: the largest province instance of scenario
    2026 and every FIRMS instance — neighbourhood size (O(n^2)) against the budget, restarts and steps."""
    t = pd.read_csv(Path(results_dir) / "tables" / "firms_hc_cost.csv", dtype={"scenario": str})
    prov = t[(t.instance_family == "provinsi") & (t.scenario == "2026")]
    rows = []
    for _, r in pd.concat([prov[prov.n == prov.n.max()], t[t.instance_family == "FIRMS"]]).iterrows():
        name = f"provinsi {r.scenario}, n={r.n}" if r.instance_family == "provinsi" else f"FIRMS k={r.n - 1}"
        rows.append([name, r.candidates, r.neighbourhood_size, r.budget, f"{r.budget_per_neighbourhood:.1f}",
                     f"{r.hc_restarts_mean:.2f}", f"{r.hc_steps_mean:.1f}"])
    return _md_table(["instance", "node kandidat", "ukuran neighbourhood HC (evaluasi per langkah)",
                      "budget evaluasi", "budget / neighbourhood (langkah penuh maks.)", "restart HC rata-rata",
                      "langkah naik HC rata-rata"], rows)


def _listed_files(results_dir):
    """Every figure (figures/*.png) and table (tables/*.md) under results_dir, relative to it."""
    natural = lambda s: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]  # n6 before n10
    figs = sorted((f"figures/{p.name}" for p in (results_dir / "figures").glob("*.png")), key=natural)
    tabs = sorted((f"tables/{p.name}" for p in (results_dir / "tables").glob("*.md")), key=natural)
    return figs, tabs


def figure_list(results_dir, captions):
    """Markdown list of every figure, then every table, each with its one-line caption.

    Raises ValueError if a file has no caption, or a caption names a file that does not exist."""
    figs, tabs = _listed_files(Path(results_dir))
    missing = sorted(set(figs + tabs) - set(captions))
    if missing: raise ValueError(f"File hasil tanpa caption: {missing}")
    stale = sorted(set(captions) - set(figs + tabs))
    if stale: raise ValueError(f"Caption untuk file yang tidak ada: {stale}")
    lines = ["**Gambar**", ""] + [f"- `results/{f}`: {captions[f]}" for f in figs]
    lines += ["", "**Tabel**", ""] + [f"- `results/{t}`: {captions[t]}" for t in tabs]
    return "\n".join(lines)


CAPTIONS = {
    "figures/best_route_map.png": "Peta studi kasus rute terbaik skenario 2026 n=38 (SA, seed 3): Depot, panah "
                                  "arah, nomor urut, waktu tiba, dan Node dilewati.",
    **{f"figures/boxplot_fitness_n{n}.png": f"Sebaran fitness akhir 30 seed per algoritma untuk n={n}, satu "
                                            "panel per Skenario tahun." for n in (6, 10, 15, 25, 38)},
    **{f"figures/convergence_n{n}.png": f"Kurva konvergensi n={n}: fitness terbaik sejauh ini (rata-rata ± "
                                        "simpangan baku 30 seed) terhadap jumlah evaluasi." for n in (25, 38)},
    "figures/scalability.png": "Runtime per run (skala log) dan kualitas solusi (% best-known) terhadap ukuran "
                               "instance n, per algoritma dan Skenario tahun.",
    "figures/sensitivity.png": "Sensitivitas fitness akhir dan jumlah Kunjungan terhadap Batas waktu misi dan "
                               "g0, n=38 skenario 2026, 30 seed.",
    "tables/case_study_route.md": "Detail rute studi kasus: urutan, waktu tiba, Prize per node, dan Node "
                                  "dilewati beserta Risikonya.",
    "tables/decay_ablation_order.md": "Urutan dan waktu tiba tiap provinsi pada rute terbaik dengan decay vs "
                                      "tanpa decay (g0=0).",
    "tables/decay_ablation_routes.md": "Rute terbaik dengan decay vs g0=0, dievaluasi dengan dan tanpa decay; "
                                       "Prize hilang bila decay diabaikan.",
    "tables/decay_ablation_seeds.md": "Prize hilang bila decay diabaikan, per algoritma, berpasangan per seed.",
    "tables/instances.md": "Ringkasan instance: budget evaluasi, Batas waktu misi, node terkunjungi Greedy, dan "
                           "apakah batas waktu mengikat.",
    "tables/optimality_gap.md": "Optimality gap Greedy, HC, SA, GA terhadap Exact untuk n=6.",
    "tables/scalability.md": "Runtime dan kualitas (% best-known) rata-rata per algoritma terhadap n.",
    "tables/sensitivity.md": "Statistik fitness per algoritma untuk setiap nilai Batas waktu misi dan g0 "
                             "(n=38, skenario 2026).",
    "tables/summary.md": "Perbandingan utama: best/mean/std/median fitness, runtime, evaluasi ke 95%, dan "
                         "success rate per algoritma, n, dan Skenario tahun.",
    "tables/wilcoxon_holm.md": "Uji Wilcoxon signed-rank berpasangan per seed dengan koreksi Holm untuk setiap "
                               "pasangan algoritma.",
    # Fase 2: Klaster hotspot FIRMS (#6)
    "figures/scalability_combined.png": "Skalabilitas gabungan: runtime per run (log) dan kualitas (% best-known) "
                                        "terhadap jumlah node kandidat, instance provinsi skenario 2026 (garis "
                                        "penuh) dan instance FIRMS k=50/100/200 (garis putus-putus, area berlabel).",
    "figures/firms_cluster_map_k100.png": "Peta hotspot VIIRS dan 100 Klaster hotspot (warna = Risiko klaster) dengan rute "
                                          "terbaik, nomor urut, Node dilewati, dan Depot Pekanbaru.",
    "figures/firms_boxplot_fitness.png": "Sebaran fitness akhir 30 seed per algoritma untuk setiap k instance FIRMS.",
    "tables/firms_calibration.md": "Kalibrasi Batas waktu misi FIRMS: node terkunjungi Greedy pada k=100 untuk "
                                   "setiap kandidat batas waktu.",
    **{f"tables/firms_clusters_k{k}.md": f"Daftar {k} Klaster hotspot: lokasi, wilayah, jumlah hotspot, Σ FRP, dan "
                                         "Risiko klaster." for k in (50, 100, 200)},
    "tables/firms_hc_cost.md": "Biaya Steepest-Ascent HC: ukuran neighbourhood O(n²) terhadap budget evaluasi, "
                               "restart dan langkah naik HC, serta µs per evaluasi, untuk instance provinsi dan "
                               "FIRMS.",
    "tables/firms_instances.md": "Ringkasan instance FIRMS: jumlah hotspot, Σ FRP, Batas waktu misi, budget, dan "
                                 "node terkunjungi Greedy per k.",
    "tables/firms_ranking.md": "Pernyataan apakah peringkat algoritma instance provinsi tetap berlaku pada "
                               "instance FIRMS, dengan peringkat per instance.",
    "tables/firms_summary.md": "Ringkasan 30 seed per algoritma per k instance FIRMS (best/mean/std/median, "
                               "runtime, success rate).",
    "tables/firms_wilcoxon_holm.md": "Uji Wilcoxon-Holm berpasangan per seed untuk setiap pasangan algoritma per k "
                                     "instance FIRMS.",
    "tables/scalability_combined.md": "Data grafik skalabilitas gabungan provinsi + FIRMS.",
}

DOCS = ("README.md", "DATA_PROVENANCE.md", "CHANGELOG.md", "reports/figures_index.md", "docs/laporan/*.md")


def _generators(root):
    import yaml
    res = root / "results"
    return {"provenance": lambda: provenance_table(yaml.safe_load((root / "config.yaml").read_text("utf8"))),
            "figures": lambda: figure_list(res, CAPTIONS),
            "summary": lambda: results_summary(res),
            "diagnostics": lambda: algorithm_diagnostics(res),
            "provenance-firms": lambda: firms_provenance_table(
                yaml.safe_load((root / "config.yaml").read_text("utf8")), res),
            "firms-summary": lambda: firms_summary(res),
            "firms-hc-cost": lambda: firms_hc_cost(res)}


class _Lazy(dict):
    """Computes a block only when a document asks for it."""
    def __init__(self, gens): super().__init__(); self.gens = gens
    def __missing__(self, key): self[key] = v = self.gens[key](); return v


def main(argv=None):
    """Rewrite the AUTO blocks of DOCS under --root; with --check only report (exit 1) stale files.

        python -m src.docs_gen [--check]
    """
    import argparse
    from src.data_prep import ROOT
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT)); ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv); root = Path(args.root); blocks = _Lazy(_generators(root)); stale = []
    for path in sorted({p for pattern in DOCS for p in root.glob(pattern)}):
        text = path.read_text(encoding="utf8"); new = fill_blocks(text, blocks)
        if new == text: continue
        stale.append(path.relative_to(root))
        if not args.check: path.write_text(new, encoding="utf8")
    for p in stale: print(f"{'usang' if args.check else 'diperbarui'}: {p}")
    return 1 if args.check and stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
