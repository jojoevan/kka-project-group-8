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
| Exact | enumerasi urutan dengan pemangkasan Batas waktu misi, maks. 9 node termasuk Depot (n ≤ 9, n mencakup Depot; 8 node kandidat) | `src/algorithms/exact.py` | ASSUMED |
| Sweep sensitivitas | n=38, skenario 2026; T_max [24, 48, 72, 120] jam; g0 [0, 0.005, 0.01, 0.02] | `config.yaml: analysis.sensitivity` | ASSUMED |
| Mode cepat (`--quick`) | n [6, 10], 3 seed, budget 300 | `config.yaml: quick` | ASSUMED |
<!-- /AUTO:provenance -->

Catatan:

- Nilai Batas waktu misi berasal dari kalibrasi: Greedy pada instance n=38 skenario 2026 mengunjungi 21 dari 37 node kandidat (57%) dengan 72 jam (`results/tables/instances.md`). Nilai ini dipakai untuk semua instance. Pada n=6 dan n=10, batas ini tidak mengikat (kolom "batas waktu mengikat" = False di `results/tables/instances.md`; dicatat juga di `results/logs/run_all.log`).
- Data 2026 adalah data **parsial** sampai 2026-10-19 (`reports/data_quality.md`).
- Selisih luas terbakar indikatif CSV vs xlsx 2026 dilaporkan apa adanya di `reports/data_quality.md`, tidak direkonsiliasi.

## Instance Klaster hotspot FIRMS

Tabel ini juga dibuat otomatis oleh `python -m src.docs_gen`, dari `config.yaml`, konstanta di kode, dan tabel hasil FIRMS tersimpan (`results/tables/firms_*.csv`).

<!-- AUTO:provenance-firms -->
| parameter | nilai | sumber | status |
|:--|:--|:--|:--|
| Snapshot hotspot VIIRS 7 hari | NASA FIRMS VIIRS S-NPP 375 m, Asia Tenggara, diunduh 2026-10-20 06:30 UTC | `data/external/firms/SUOMI_VIIRS_C2_SouthEast_Asia_7d_2026-10-20.csv` (+ `.source.txt`) | REAL |
| Filter confidence | nominal/high | `config.yaml: firms.confidence` | ASSUMED |
| Bounding box | Sumatra [-6.0, 6.0, 95.0, 106.0]; Kalimantan [-4.5, 4.5, 108.5, 119.0] ([lat_min, lat_max, lon_min, lon_max], kotak kasar pulau) | `config.yaml: firms.bboxes` | ASSUMED |
| Hotspot setelah filter | 28983 (Kalimantan 22152, Sumatra 6831) | `results/tables/firms_instances.md` | DERIVED |
| Jumlah Klaster hotspot k | 50, 100, 200 (instance = k node + Depot) | `config.yaml: firms.sizes` | ASSUMED |
| Klasterisasi | k-means (Lloyd, seeding k-means++), seed 0, atas (lat, lon·cos lat) | `src/firms.py`, `config.yaml: firms.kmeans_seed` | ASSUMED |
| Lokasi node klaster | pusat klaster; hotspot anggota terdekat bila pusatnya jatuh di luar kotak (klaster lintas wilayah) | `src/firms.py` | DERIVED |
| Risiko klaster | Σ FRP → log1p → min-max antar-klaster dalam satu instance | `src/firms.py` | DERIVED |
| Laju decay klaster | konstan g0 = 0.01 /jam (tanpa data operasional, κ tidak dipakai) | `docs/adr/0001-firms-clusters-instead-of-synthetic.md` | ASSUMED |
| Depot FIRMS | Pekanbaru (ibu kota provinsi Riau) | `config.yaml: depot` | ASSUMED |
| Batas waktu misi FIRMS | 72 jam (tidak ada kandidat dalam target, dipilih yang terdekat: 39% klaster terkunjungi) | kalibrasi Greedy k=100, kandidat 24 jam → 13%, 48 jam → 23%, 72 jam → 39%, 120 jam → 73%, target 40%–60% (`src/calibration.py`; hasil: `results/tables/firms_calibration.md`) | DERIVED |
| Budget evaluasi FIRMS | 100000 | `config.yaml: firms.budget` | ASSUMED |
| Mode cepat FIRMS (`--quick`) | k [3, 6], 2 seed, budget 300 | `config.yaml: firms.quick` | ASSUMED |
<!-- /AUTO:provenance-firms -->

Catatan:

- **Kalibrasi Batas waktu misi FIRMS jatuh ke nilai cadangan.** Tidak ada kandidat yang masuk target 40–60% pada k=100, sehingga dipilih kandidat terdekat, 72 jam (39% klaster terkunjungi; `results/tables/firms_calibration.md`). Karena satu batas dipakai untuk semua k, fraksi terkunjungi Greedy adalah 72% pada k=50 dan 22,5% pada k=200 (`results/tables/firms_instances.md`). Pada k=50, masalahnya lebih longgar daripada target kalibrasi.
- **Bounding box adalah kotak kasar** (ASSUMED). Sekitar 260 hotspot di Malaysia (±60 di Semenanjung Malaysia, ±200 di Sarawak/Sabah) ikut masuk kotak. Angka ini perkiraan yang dicatat saat unduh di `data/external/firms/SUOMI_VIIRS_C2_SouthEast_Asia_7d_2026-10-20.source.txt`. Jumlahnya kurang dari 1% dari 28.983 hotspot setelah filter.
- **Risiko klaster tidak sebanding dengan Risiko provinsi.** Risiko klaster dinormalisasi per instance (lihat `GLOSSARY.md`), sedangkan Risiko provinsi dinormalisasi sekali atas 38 provinsi. Akibatnya, fitness FIRMS hanya bisa dibandingkan antar-algoritma dalam k yang sama, tidak antar-k dan tidak dengan instance provinsi.
- Snapshot mentah disimpan apa adanya (SHA-256 di file `.source.txt`). Pipeline tidak pernah membaca feed langsung, karena feed 7 hari terus bergeser.
