# Provenance Data dan Parameter

Setiap parameter model diberi satu label status:

- **REAL**: diambil langsung dari dataset.
- **DERIVED**: dihitung dari dataset atau dari hasil eksperimen.
- **ASSUMED**: pilihan pemodelan kelompok.
- **SYNTHETIC**: data hasil generator acak.

Proyek ini **tidak memakai data SYNTHETIC**. Generator instance sintetis tidak dibangun (lihat `docs/adr/0001-firms-clusters-instead-of-synthetic.md`).

Tabel di bawah dibuat otomatis oleh `python -m src.docs_gen` dari `config.yaml` dan konstanta di kode, jadi isinya selalu sama dengan konfigurasi yang dipakai eksperimen. Jangan edit isi di antara penanda `AUTO`.

## Instance provinsi

<!-- AUTO:provenance -->
| parameter | nilai | sumber | status |
|:--|:--|:--|:--|
| Luas terbakar per provinsi | 38 provinsi × 2018–2026 (ha); 2026 parsial s.d. 2026-10-19 | `data/raw/luas-karhutla-provinsi.xlsx` | REAL |
| Data operasional | 6 provinsi, snapshot 2026-10-19 (hotspot, fire spot, luas indikatif, PM2.5, visibilitas bandara, personel, unit udara) | `data/raw/karhutla-2026_semua-provinsi_2026-10-19.csv` | REAL |
| Komponen historis `hist` | Σ γ^(2025−tahun)·log1p(luas), 2018–2025, min-max atas 38 provinsi | `src/data_prep.py` → `data/processed/province_features.csv` | DERIVED |
| Komponen tahun berjalan `cur` | log1p(luas tahun Skenario tahun), min-max atas 38 provinsi | `src/data_prep.py` → `data/processed/province_features.csv` | DERIVED |
| Ordinal PM2.5 | Baik=0, Sedang=1, Tidak Sehat=2, Sangat Tidak Sehat=3, Berbahaya=4; rentang → tingkat terburuk | `src/data_prep.py` → `data/processed/province_features.csv` | DERIVED |
| Visibilitas bandara | angka minimum di dalam teks (km) | `src/data_prep.py` → `data/processed/province_features.csv` | DERIVED |
| Komponen operasional `ops` | rata-rata luas indikatif, fire spot, PM2.5/4, 1/visibilitas (masing-masing ternormalisasi), min-max antar-6 provinsi; 0 untuk 32 provinsi lain (`has_ops=False`, tanpa imputasi); hanya Skenario tahun 2026 | `src/data_prep.py` → `data/processed/province_features.csv` | DERIVED |
| Risiko | α·hist + β·cur + δ·ops, lalu min-max **sekali** atas 38 provinsi per Skenario tahun | `src/data_prep.py` → `data/processed/province_features.csv` | DERIVED |
| Jarak antar-node | Haversine antar-ibu kota × faktor detour 1.15 | `src/instance.py` | DERIVED |
| Laju decay node `g_i` | g0·(1 + κ·ops_i); ops_i = 0 di luar Skenario tahun 2026 | `src/instance.py` | DERIVED |
| Pemilihan node instance | n=6: Depot + provinsi ber-data operasional; n lain: Depot + top-(n−1) Risiko; n=38: semua provinsi | `src/instance.py` | DERIVED |
| Batas waktu misi `T_max` | 72 jam | kalibrasi Greedy n=38 skenario 2026, kandidat [24, 48, 72, 120] jam, target 40%–60% node terkunjungi (`src/calibration.py`; hasil: `results/tables/instances.md`) | DERIVED |
| Bobot Risiko α, β, δ | 0.4, 0.3, 0.3 | `config.yaml: weights` | ASSUMED |
| Faktor keterkinian γ | 0.8 | `config.yaml: gamma` | ASSUMED |
| Koordinat node provinsi | koordinat ibu kota provinsi (geografi publik, perlu diverifikasi) | `data/external/province_coords.csv` | ASSUMED |
| Depot | Riau | `config.yaml: depot` | ASSUMED |
| Kecepatan armada `v` | 200 km/jam | `config.yaml: speed_kmh` | ASSUMED |
| Faktor detour | 1.15 | `config.yaml: detour_factor` | ASSUMED |
| Waktu tinggal per Kunjungan | 1.0 jam | `config.yaml: dwell_hours` | ASSUMED |
| Laju decay dasar `g0` | 0.01 /jam | `config.yaml: decay_g0` | ASSUMED |
| Pengali keparahan decay κ | 1.0 | `config.yaml: decay_kappa` | ASSUMED |
| Bentuk Prize | Risiko·exp(−g_i·waktu tiba); proksi kerusakan yang dicegah, bukan ukuran resmi | `src/instance.py` | ASSUMED |
| Skenario tahun | 2019, 2026 | `src/data_prep.py: SCENARIOS` | ASSUMED |
| Ukuran instance n (termasuk Depot) | 6, 10, 15, 25, 38 | `src/instance.py: INSTANCE_SIZES` | ASSUMED |
| Budget evaluasi per run | 20000 (n ≤ 15), 50000 (n > 15) | `config.yaml: evaluation_budget` | ASSUMED |
| Jumlah seed per konfigurasi | 30 | `config.yaml: seeds` | ASSUMED |
| HC | steepest-ascent atas seluruh neighbourhood swap/relocate/2-opt; restart acak sampai budget habis | `src/algorithms/hill_climbing.py` | ASSUMED |
| SA: T0 dan pendinginan | T0 = rata-rata \|Δ\| positif dari 100 move acak; geometris c = 0.001^(1/sisa budget); tanpa reheating | `src/algorithms/simulated_annealing.py` | ASSUMED |
| GA | populasi 100, tournament k=3, OX, mutasi 0.2, elitisme 2, populasi awal acak (tanpa seeding greedy) | `src/algorithms/genetic_algorithm.py` | ASSUMED |
| Exact | enumerasi urutan dengan pemangkasan Batas waktu misi, maks. 9 node | `src/algorithms/exact.py` | ASSUMED |
| Sweep sensitivitas | n=38, skenario 2026; T_max [24, 48, 72, 120] jam; g0 [0, 0.005, 0.01, 0.02] | `config.yaml: analysis.sensitivity` | ASSUMED |
| Mode cepat (`--quick`) | n [6, 10], 3 seed, budget 300 | `config.yaml: quick` | ASSUMED |
<!-- /AUTO:provenance -->

Catatan:

- Nilai Batas waktu misi berasal dari kalibrasi: Greedy pada instance n=38 skenario 2026 mengunjungi 21 dari 37 node kandidat (57%) dengan 72 jam (`results/tables/instances.md`). Nilai ini dipakai untuk semua instance. Pada n=6 dan n=10, batas ini tidak mengikat (kolom "batas waktu mengikat" = False di `results/tables/instances.md`; dicatat juga di `results/logs/run_all.log`).
- Data 2026 adalah data **parsial** sampai 2026-10-19 (`reports/data_quality.md`).
- Selisih luas terbakar indikatif CSV vs xlsx 2026 dilaporkan apa adanya di `reports/data_quality.md`, tidak direkonsiliasi.

## Instance Klaster hotspot FIRMS

<!-- FIRMS: isi setelah #6 -->

| parameter | nilai | sumber | status |
|:--|:--|:--|:--|
| Snapshot hotspot VIIRS 7 hari | _(tanggal unduh)_ | _(path file snapshot)_ | REAL |
| Filter confidence | nominal/high | _(modul FIRMS)_ | ASSUMED |
| Bounding box Sumatra + Kalimantan | _(koordinat)_ | _(modul FIRMS)_ | ASSUMED |
| Jumlah klaster k | 50, 100, 200 | _(config)_ | ASSUMED |
| Seed k-means | _(nilai)_ | _(config)_ | ASSUMED |
| Risiko klaster | Σ FRP → log1p → min-max antar-klaster | _(modul FIRMS)_ | DERIVED |
| Laju decay klaster | konstan `g0` | ADR-0001 | ASSUMED |
| Batas waktu misi FIRMS | _(hasil kalibrasi)_ | `src/calibration.py` | DERIVED |
| Budget evaluasi FIRMS | 100000 | _(config)_ | ASSUMED |
