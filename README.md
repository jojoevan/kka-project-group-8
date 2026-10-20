# Perutean Armada Udara Karhutla: HC vs SA vs GA

Proyek UTS mata kuliah KKA, Kelompok 8. Proyek ini membandingkan **Steepest-Ascent Hill Climbing (HC)**, **Simulated Annealing (SA)**, dan **Genetic Algorithm (GA)** pada masalah *orienteering* dengan **Prize** yang meluruh terhadap waktu tiba. **Greedy** dipakai sebagai baseline dan **Exact** sebagai referensi optimum untuk instance kecil.

Istilah di semua dokumen mengikuti [`GLOSSARY.md`](GLOSSARY.md).

## Deskripsi masalah

Satu armada udara pemadam kebakaran hutan dan lahan (karhutla), misalnya helikopter *water-bombing* atau pesawat OMC, berangkat dari **Depot** di Pekanbaru (Riau). Armada harus kembali ke Depot sebelum **Batas waktu misi** habis. Setiap provinsi adalah satu **Node** dengan **Risiko** dalam [0,1]. Risiko dihitung dari luas terbakar historis 2018–2025, luas terbakar tahun berjalan, dan keparahan operasional dari snapshot 2026-10-19.

Setiap Node paling banyak mendapat satu **Kunjungan**. Kunjungan ke node *i* pada waktu tiba *t_i* menghasilkan Prize

    Prize_i = Risiko_i · exp(−g_i · t_i),   g_i = g0 · (1 + κ · ops_i)

Prize adalah proksi kerusakan yang dicegah. Nilainya meluruh karena api terus meluas, dan provinsi dengan keparahan operasional tinggi meluruh lebih cepat. Ini asumsi pemodelan, bukan ukuran resmi.

Tujuannya memilih node yang dikunjungi **dan** urutannya agar total Prize maksimum, tanpa melampaui Batas waktu misi (termasuk waktu kembali ke Depot). Karena tidak semua node muat, masalah ini lebih sulit daripada TSP: algoritma harus memilih sekaligus mengurutkan.

Instance yang dipakai:

- Instance provinsi berukuran n ∈ {6, 10, 15, 25, 38} node, termasuk Depot.
  - n=6 berisi enam provinsi yang punya data operasional.
  - n=10, 15, dan 25 berisi provinsi dengan Risiko tertinggi.
  - n=38 berisi semua provinsi.
- Dua Skenario tahun: 2019 (tahun ekstrem) dan 2026 (tahun berjalan, data parsial sampai 2026-10-19).

Sumber setiap parameter ada di [`DATA_PROVENANCE.md`](DATA_PROVENANCE.md). Perubahan keputusan pemodelan dicatat di [`CHANGELOG.md`](CHANGELOG.md).

## Struktur repo

```
config.yaml                 parameter misi, Risiko, budget evaluasi, seed, sweep sensitivitas
data/raw/                   data mentah (tidak pernah diubah)
data/external/              koordinat ibu kota provinsi (ASSUMED), snapshot NASA FIRMS (firms/)
data/processed/             fitur 38 provinsi hasil data prep
src/data_prep.py            parsing data, Risiko global 38 provinsi, laporan kualitas data
src/instance.py             Instance, jarak Haversine, decoder O(n) "lewati lalu lanjut"
src/calibration.py          kalibrasi Batas waktu misi dengan Greedy
src/config.py               config.yaml → fitur provinsi dan parameter misi (satu tempat)
src/firms.py                hotspot FIRMS → instance Klaster hotspot (k-means, Risiko klaster)
src/algorithms/             greedy, hill_climbing, simulated_annealing, genetic_algorithm, exact
src/experiments/run_all.py  satu titik masuk semua eksperimen, tabel, dan gambar
src/experiments/firms_phase.py  fase 2: eksperimen skalabilitas Klaster hotspot FIRMS (--firms)
src/experiments/records.py  satu baris runs.csv per run (dipakai provinsi dan FIRMS)
src/experiments/reporting.py  label kolom tabel berbahasa Indonesia + penulis tabel csv/md
src/docs_gen.py             mengisi tabel/angka di dokumentasi dari config.yaml dan results/
results/                    raw/, tables/, figures/, routes/, logs/ (hasil yang dipakai laporan)
reports/                    data_quality.md, figures_index.md
docs/laporan/               draf Bab 2, draf Bab 3, kerangka slide
tests/                      pytest
app/                        tampilan interaktif Streamlit (membaca results/, menjalankan solver yang sama)
```

## Instalasi

Butuh Python 3.10+ (diuji dengan Python 3.12).

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Cara menjalankan

Semua perintah dijalankan dari root repo.

```bash
# 1. Data prep: fitur 38 provinsi + reports/data_quality.md
python -m src.data_prep

# 2. (Opsional) Kalibrasi ulang Batas waktu misi; --write mencatat hasilnya di config.yaml
python -m src.calibration

# 3a. Mode cepat (smoke test): n ∈ {6, 10}, 3 seed, budget 300
python -m src.experiments.run_all --quick --out /tmp/hasil_cepat

# 3b. Eksperimen penuh: menulis ulang seluruh isi results/ (--firms: termasuk fase FIRMS)
python -m src.experiments.run_all --config config.yaml --firms [--workers K]

# 4. Perbarui tabel dan angka di dokumentasi dari results/ (atau --check untuk memeriksa saja)
python -m src.docs_gen

# Tes
python -m pytest
```

### Menjalankan tampilan interaktif

```bash
pip install -r requirements-app.txt
streamlit run app/main.py          # buka http://localhost:8501
```

Tampilan ini punya lima halaman:

1. **Masalahnya**: peta Risiko, Prize yang meluruh, dan menyusun rute sendiri.
2. **Coba sendiri**: menjalankan Greedy/HC/SA/GA/Exact langsung pada instance provinsi dan memutar ulang perbaikan rutenya.
3. **Hasil perbandingan**: tabel, boxplot, konvergensi, dan Wilcoxon-Holm.
4. **Studi kasus & ablasi decay**.
5. **Klaster hotspot FIRMS**.

Halaman 3–5 hanya membaca `results/`, jadi angkanya sama dengan laporan. Halaman 2 memakai solver yang sama, dibungkus perekam yang tidak mengubah hasilnya (`tests/test_app_recording.py`). Tampilan ini tidak menulis apa pun ke repo dan bisa dipakai tanpa internet.

Perkiraan runtime:

- **Eksperimen penuh**: 1.202 run perbandingan utama, 960 run sweep sensitivitas, dan 360 run FIRMS (`--firms`). Total 1.231,7 detik (±20,5 menit) dengan 12 worker (`results/logs/run_all.log`). Dengan lebih sedikit core, runtime naik kira-kira sebanding.
- **Mode cepat**: ±10 detik (diukur dengan 12 core saat dokumen ini ditulis).

Setiap run hanya bergantung pada (instance, algoritma, seed), sehingga hasilnya identik untuk jumlah worker berapa pun.

Eksperimen penuh ke `results/` otomatis memperbarui blok AUTO di dokumentasi (`python -m src.docs_gen`). Periksa diff dokumen setelahnya.

## Ringkasan hasil

Fitness adalah total Prize, rata-rata 30 seed. Budget evaluasi 20.000 untuk n ≤ 15 dan 50.000 untuk n ≥ 25. Batas waktu misi 72 jam. Nilai tertinggi per baris dicetak tebal. Best-known adalah fitness terbaik dari semua run dan algoritma pada instance tersebut (Exact untuk n=6). Sumber: `results/tables/summary.csv`. Tabel lengkap (best, std, median, runtime, success rate) ada di `results/tables/summary.md`.

<!-- AUTO:summary -->
| skenario | n | best-known | Greedy rata-rata | HC rata-rata | SA rata-rata | GA rata-rata | rata-rata tertinggi |
|:--|:--|:--|:--|:--|:--|:--|:--|
| 2019 | 6 | 4,101 | **4,101** | **4,101** | **4,101** | **4,101** | Greedy / HC / SA / GA |
| 2019 | 10 | 6,767 | 6,731 | **6,767** | **6,767** | **6,767** | HC / SA / GA |
| 2019 | 15 | 9,215 | 9,044 | **9,157** | 9,092 | 9,018 | HC |
| 2019 | 25 | 12,243 | 12,019 | **12,121** | 12,120 | 11,402 | HC |
| 2019 | 38 | 12,687 | 12,268 | 12,050 | **12,333** | 9,668 | SA |
| 2026 | 6 | 3,244 | 3,188 | **3,244** | **3,244** | **3,244** | HC / SA / GA |
| 2026 | 10 | 5,225 | 5,224 | **5,225** | **5,225** | **5,225** | HC / SA / GA |
| 2026 | 15 | 6,933 | 6,294 | **6,933** | **6,933** | 6,921 | HC / SA |
| 2026 | 25 | 8,579 | 8,384 | **8,543** | 8,532 | 8,203 | HC |
| 2026 | 38 | 9,174 | 8,699 | 8,708 | **9,079** | 7,156 | SA |
<!-- /AUTO:summary -->

Ringkasan temuan:

- **Instance kecil (n ≤ 10)**: HC, SA, dan GA selalu mencapai best-known. Pada n=6, hasilnya sama dengan optimum Exact (gap 0%, `results/tables/optimality_gap.md`). Greedy meleset 1,704% dari optimum pada n=6 skenario 2026.
- **n=15 dan n=25**: HC dan SA setara. Wilcoxon-Holm HC vs SA tidak signifikan pada 2019 n=25 (p=0,6666), 2026 n=25 (p=0,2102), dan 2026 n=15 (p=1). Pengecualian: pada 2019 n=15, HC lebih baik dari SA (p Holm 0,02014). Sumber: `results/tables/wilcoxon_holm.md`.
- **n=38 (instance utama)**: SA terbaik di kedua Skenario tahun. Pada 2026, SA mengalahkan HC di 25 dari 30 seed dan mengalahkan Greedy di 29 dari 30 seed (keduanya p Holm 5,974e-06). GA kalah dari semua algoritma lain, termasuk Greedy, di 30 dari 30 seed. Sumber: `results/tables/wilcoxon_holm.md`.
- **Ablasi decay**: mengabaikan decay (g0=0) saat merencanakan rute membuat Prize yang benar-benar terkumpul turun rata-rata 6,46% untuk SA, 15,78% untuk HC, 9,348% untuk Greedy, dan 8,346% untuk GA (`results/tables/decay_ablation_seeds.md`).

### Diagnostik algoritma

Dihitung dari `results/raw/runs.csv`. Kolom "evaluasi per langkah HC" adalah ukuran neighbourhood penuh dari move set bersama.

<!-- AUTO:diagnostics -->
| skenario | n | evaluasi per langkah HC (neighbourhood) | HC single-start rata-rata | HC akhir rata-rata | restart HC rata-rata | seed dengan 1 pendakian HC (pendakian pertama belum selesai saat budget habis) | acceptance rate SA rata-rata | generasi GA rata-rata |
|:--|:--|:--|:--|:--|:--|:--|:--|:--|
| 2019 | 6 | 28 | 4,101 | 4,101 | 235,5 | 0/30 | 0,069 | 203 |
| 2019 | 10 | 120 | 6,767 | 6,767 | 29,7 | 0/30 | 0,118 | 203 |
| 2019 | 15 | 325 | 9,080 | 9,157 | 6,5 | 0/30 | 0,114 | 203 |
| 2019 | 25 | 1035 | 11,889 | 12,121 | 3,1 | 0/30 | 0,119 | 509 |
| 2019 | 38 | 2556 | 11,989 | 12,050 | 1,3 | 21/30 | 0,238 | 509 |
| 2026 | 6 | 28 | 3,244 | 3,244 | 234,4 | 0/30 | 0,083 | 203 |
| 2026 | 10 | 120 | 5,225 | 5,225 | 28,5 | 0/30 | 0,107 | 203 |
| 2026 | 15 | 325 | 6,933 | 6,933 | 6,4 | 0/30 | 0,072 | 203 |
| 2026 | 25 | 1035 | 8,324 | 8,543 | 3,3 | 0/30 | 0,140 | 509 |
| 2026 | 38 | 2556 | 8,688 | 8,708 | 1,3 | 20/30 | 0,232 | 509 |
<!-- /AUTO:diagnostics -->

## Observasi

Label **[Hipotesis]** menandai penjelasan yang belum diuji dengan eksperimen tersendiri. Label **[Data]** menandai pernyataan yang langsung terbaca dari hasil tersimpan.

1. **[Data]** Pada n=38, satu langkah HC mengevaluasi 2.556 tetangga, sehingga dengan budget 50.000 HC hanya sempat melakukan rata-rata 1,3 restart (tabel diagnostik di atas). Kurva konvergensi HC n=38 masih naik saat budget habis (`results/figures/convergence_n38.png`). Rata-rata HC pada 2026 n=38 (8,708) tidak berbeda signifikan dari Greedy (8,699, p Holm 0,6408).
   **[Data]** Rata-rata 1,3 restart berarti tidak semua seed sama: pada sebagian besar seed HC hanya sempat satu pendakian (pendakian pertama belum selesai saat budget habis), sedangkan pada seed lainnya pendakian pertama mencapai local optimum dan satu restart sempat dimulai. Jumlah seed per instance ada di kolom "seed dengan 1 pendakian HC" pada tabel diagnostik di atas (kolom `hc_restarts` = 1 di `results/raw/runs.csv`).
   **[Hipotesis]** Kekalahan HC di n=38 lebih disebabkan biaya per langkah yang O(n²) daripada local optimum, karena pada sebagian besar seed pendakian pertama pun belum selesai. Hipotesis ini bisa diuji dengan menaikkan budget HC atau memakai first-improvement.
2. **[Data]** GA adalah algoritma terlemah di n ≥ 25. Kualitas rata-ratanya 78% dari best-known pada 2026 n=38 dan 76,2% pada 2019 n=38 (`results/tables/scalability.md`), dengan hanya sekitar 509 generasi dalam budget 50.000 (tabel diagnostik).
   **[Hipotesis]** Fitness ditentukan oleh *prefix* permutasi yang muat dalam Batas waktu misi. Order Crossover mempertahankan urutan relatif tetapi menggeser posisi absolut, sehingga prefix yang baik sering rusak. Populasi acak tanpa local search juga membutuhkan lebih banyak generasi daripada yang tersedia.
3. **[Data]** SA paling stabil di n=38: simpangan baku 0,143 (2026) dan 0,1427 (2019), terkecil di antara HC, SA, dan GA (`results/tables/summary.md`). Acceptance rate rata-ratanya pada n=38 sekitar 0,23 (tabel diagnostik).
   **[Hipotesis]** Pendinginan yang diturunkan dari budget membuat SA tetap menjelajah selama seluruh budget. Satu evaluasi per langkah juga membuat SA memakai budget lebih efisien daripada HC yang harus menyapu seluruh neighbourhood.
4. **[Data]** Greedy kompetitif di n=38 skenario 2019: rata-ratanya 12,27, di atas HC (12,05) dan hanya di bawah SA (12,33) (`results/tables/summary.md`). Sebaliknya, pada 2026 n=15, Greedy hanya mencapai 90,78% dari best-known (`results/tables/scalability.md`).
   **[Hipotesis]** Di 2019, komponen operasional tidak dipakai, sehingga laju decay seragam dan rasio Prize/waktu menjadi heuristik yang baik. Di 2026, laju decay berbeda antar-node, dan pilihan myopic Greedy lebih sering salah.
5. **[Data]** Pemodelan decay mengubah rute. Pada rute SA terbaik, provinsi ber-data operasional rata-rata dikunjungi di urutan ke-4 (tiba rata-rata 10,05 jam) jika decay dimodelkan, dibandingkan urutan ke-12 (36,62 jam) jika decay diabaikan. Jambi bergeser dari urutan 2 ke 21, dan Sumatera Selatan dari urutan 3 ke 20 (`results/tables/decay_ablation_routes.md`, `results/tables/decay_ablation_order.md`).

## Batasan interpretasi

- **Prize adalah proksi pemodelan**, bukan ukuran resmi kerusakan yang dicegah. Bentuk eksponensial, `g0`, dan κ adalah asumsi (ASSUMED). Sensitivitas terhadap `g0` dan Batas waktu misi ada di `results/tables/sensitivity.md`.
- **Data 2026 parsial** sampai 2026-10-19. Data operasional hanya ada untuk 6 provinsi. 32 provinsi lain mendapat `ops=0` tanpa imputasi, dan ketiadaan data bukan bukti tidak ada kebakaran (`reports/data_quality.md`).
- **Koordinat node adalah ibu kota provinsi**, bukan lokasi api. Jarak adalah Haversine × 1,15 dengan kecepatan tetap 200 km/jam. Tidak ada cuaca, pengisian bahan bakar/air, atau batas jam terbang kru.
- **Satu armada.** Masalah team orienteering (beberapa armada) di luar cakupan.
- **Batas waktu misi 72 jam tidak mengikat pada n=6 dan n=10** (`results/tables/instances.md`). Pada ukuran ini masalahnya mendekati TSP dengan Prize meluruh, sehingga perbedaan antar-algoritma kecil.
- **Parameter algoritma ditetapkan sebelum eksperimen** dan tidak di-tuning. Peringkat algoritma berlaku untuk budget dan parameter ini saja. Hasil dengan budget atau tuning lain bisa berbeda.
- **Best-known untuk n ≥ 10 bukan optimum terbukti.** Optimality gap terhadap Exact hanya tersedia untuk n=6.
- **Generalisasi ke instance lain**: peringkat provinsi **tidak tetap berlaku sepenuhnya** pada instance Klaster hotspot FIRMS. Rinciannya ada di bagian berikut.

## Instance Klaster hotspot FIRMS (fase 2)

Instance besar dibangun dari snapshot hotspot NASA FIRMS VIIRS 7 hari (diunduh 2026-10-20, `data/external/firms/`), sesuai ADR-0001. Hotspot difilter (confidence nominal/high, bounding box Sumatra + Kalimantan), lalu diklaster dengan k-means menjadi k ∈ {50, 100, 200} Klaster hotspot. **Risiko klaster** = Σ FRP → log1p → min-max antar-klaster dalam satu instance (lihat `GLOSSARY.md`). Decay-nya konstan g0, Depot tetap Pekanbaru, budget evaluasi 100.000, dan 30 seed per (algoritma, k). Parameter lengkap ada di `DATA_PROVENANCE.md`.

Jalankan dengan `python -m src.experiments.run_all --firms` (provinsi + FIRMS) atau `--firms-only` (hanya FIRMS, membaca hasil provinsi dari `results/raw/runs.csv`).

Fitness rata-rata 30 seed per k. Sumber: `results/tables/firms_summary.csv`, `results/tables/firms_instances.csv`; peringkat dari `results/tables/firms_ranking.md`.

<!-- AUTO:firms-summary -->
| k | Batas waktu misi (jam) | klaster terkunjungi Greedy | best-known | Greedy rata-rata | HC rata-rata | SA rata-rata | GA rata-rata | peringkat (= berarti seri) |
|:--|:--|:--|:--|:--|:--|:--|:--|:--|
| 50 | 72 | 36 (72%) | 22,436 | 19,707 | 18,903 | **22,388** | 18,614 | SA > Greedy > HC > GA |
| 100 | 72 | 39 (39%) | 24,618 | 19,940 | 13,042 | **24,269** | 15,276 | SA > Greedy > GA > HC |
| 200 | 72 | 45 (22%) | 27,204 | 20,936 | 10,497 | **26,350** | 14,286 | SA > Greedy > GA > HC |
<!-- /AUTO:firms-summary -->

Catatan jujur tentang instance ini:

- **Kalibrasi Batas waktu misi FIRMS jatuh ke nilai cadangan.** Pada k=100, tidak ada kandidat yang membuat Greedy mengunjungi 40–60% klaster: 72 jam menghasilkan 39% dan 120 jam 73%. Kalibrasi memilih kandidat terdekat, 72 jam (`results/tables/firms_calibration.md`). Batas yang sama dipakai untuk semua k, sehingga fraksi terkunjungi Greedy adalah 72% pada k=50 dan 22,5% pada k=200 (`results/tables/firms_instances.md`).
- **Bounding box adalah kotak kasar pulau.** Sekitar 260 hotspot di Malaysia (±60 di Semenanjung Malaysia, ±200 di Sarawak/Sabah) ikut masuk kotak (`data/external/firms/SUOMI_VIIRS_C2_SouthEast_Asia_7d_2026-10-20.source.txt`), dari 28.983 hotspot setelah filter (`results/tables/firms_instances.md`).
- **[Data] Peringkat provinsi tidak tetap berlaku sepenuhnya** (`results/tables/firms_ranking.md`, `results/tables/firms_wilcoxon_holm.md`). Acuannya adalah instance provinsi terbesar (2026, n=38): SA > HC > Greedy > GA.
  - SA tetap pertama di semua k, dan mengalahkan setiap algoritma lain di 30 dari 30 seed.
  - HC turun di bawah Greedy di semua k. Pada k=50, Greedy menang di 26 dari 30 seed (p Holm 1,259e-06). Pada k=100 dan k=200, Greedy menang di 30 dari 30 seed.
  - Pada k ≥ 100, HC juga turun di bawah GA: GA menang di 27 dari 30 seed pada k=100 (p Holm 2,049e-07) dan 30 dari 30 pada k=200. Pada k=50, HC vs GA tidak berbeda signifikan (p Holm 0,4645).
- **[Data] Biaya per langkah Steepest-Ascent HC yang O(n²)** menjelaskan kekalahan HC (`results/tables/firms_hc_cost.md`). Satu langkah HC mengevaluasi seluruh neighbourhood. Ukurannya 4.753 tetangga pada k=50, 19.503 pada k=100, dan 79.003 pada k=200, sehingga budget 100.000 hanya cukup untuk 21; 5,1; dan 1,3 langkah penuh. HC tidak pernah sempat restart (restart rata-rata 1 di semua k), dan langkah naik rata-ratanya 21, 5, dan 1. Pada k=200, HC praktis hanya menyelesaikan satu langkah dari permutasi awal acak.

<!-- AUTO:firms-hc-cost -->
| instance | node kandidat | ukuran neighbourhood HC (evaluasi per langkah) | budget evaluasi | budget / neighbourhood (langkah penuh maks.) | restart HC rata-rata | langkah naik HC rata-rata |
|:--|:--|:--|:--|:--|:--|:--|
| provinsi 2026, n=38 | 37 | 2556 | 50000 | 19,6 | 1,33 | 18,7 |
| FIRMS k=50 | 50 | 4753 | 100000 | 21,0 | 1,00 | 21,0 |
| FIRMS k=100 | 100 | 19503 | 100000 | 5,1 | 1,00 | 5,0 |
| FIRMS k=200 | 200 | 79003 | 100000 | 1,3 | 1,00 | 1,0 |
<!-- /AUTO:firms-hc-cost -->

- **[Hipotesis]** HC kalah dari Greedy dan GA pada FIRMS bukan karena terjebak di local optimum, tetapi karena budget habis jauh sebelum pendakian pertama selesai. Varian first-improvement atau neighbourhood sampling kemungkinan mengubah peringkat ini, tetapi tidak diuji karena parameter algoritma tidak di-tuning.

Grafik: `results/figures/scalability_combined.png` (skalabilitas gabungan provinsi + FIRMS), `results/figures/firms_cluster_map_k100.png` (peta klaster dan rute terbaik k=100), dan `results/figures/firms_boxplot_fitness.png`.

## Dokumen lain

- [`DATA_PROVENANCE.md`](DATA_PROVENANCE.md): status REAL / DERIVED / ASSUMED / SYNTHETIC setiap parameter.
- [`CHANGELOG.md`](CHANGELOG.md): keputusan pemodelan yang direvisi beserta alasannya.
- [`reports/data_quality.md`](reports/data_quality.md): laporan kualitas data.
- [`reports/figures_index.md`](reports/figures_index.md): daftar gambar dan tabel dengan caption.
- [`docs/laporan/bab2_metode.md`](docs/laporan/bab2_metode.md): draf Bab 2 (Metode).
- [`docs/laporan/bab3_eksperimen.md`](docs/laporan/bab3_eksperimen.md): draf Bab 3 (Eksperimen & Pembahasan).
- [`docs/laporan/kerangka_slide.md`](docs/laporan/kerangka_slide.md): kerangka slide presentasi 15 menit.
- [`docs/adr/`](docs/adr/): catatan keputusan arsitektur.
