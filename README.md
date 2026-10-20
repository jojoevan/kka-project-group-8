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
data/external/              koordinat ibu kota provinsi (ASSUMED)
data/processed/             fitur 38 provinsi hasil data prep
src/data_prep.py            parsing data, Risiko global 38 provinsi, laporan kualitas data
src/instance.py             Instance, jarak Haversine, decoder O(n) "lewati lalu lanjut"
src/calibration.py          kalibrasi Batas waktu misi dengan Greedy
src/algorithms/             greedy, hill_climbing, simulated_annealing, genetic_algorithm, exact
src/experiments/run_all.py  satu titik masuk semua eksperimen, tabel, dan gambar
src/docs_gen.py             mengisi tabel/angka di dokumentasi dari config.yaml dan results/
results/                    raw/, tables/, figures/, routes/, logs/ (hasil yang dipakai laporan)
reports/                    data_quality.md, figures_index.md
docs/laporan/               draf Bab 2, draf Bab 3, kerangka slide
tests/                      pytest
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

# 3b. Eksperimen penuh: menulis ulang seluruh isi results/
python -m src.experiments.run_all --config config.yaml [--workers K]

# 4. Perbarui tabel dan angka di dokumentasi dari results/ (atau --check untuk memeriksa saja)
python -m src.docs_gen

# Tes
python -m pytest
```

Perkiraan runtime:

- **Eksperimen penuh**: 1.202 run perbandingan utama ditambah 960 run sweep sensitivitas. Total 687.4 detik (±11,5 menit) dengan 12 worker (`results/logs/run_all.log`). Dengan lebih sedikit core, runtime naik kira-kira sebanding.
- **Mode cepat**: ±10 detik (diukur dengan 12 core saat dokumen ini ditulis).

Setiap run hanya bergantung pada (instance, algoritma, seed), sehingga hasilnya identik untuk jumlah worker berapa pun.

Catatan: eksperimen penuh juga menulis ulang `reports/figures_index.md` dengan versi lama tanpa penanda AUTO. Setelah eksperimen penuh, jalankan `python -m src.docs_gen` lalu periksa diff file tersebut.

## Ringkasan hasil

Fitness adalah total Prize, rata-rata 30 seed. Budget evaluasi 20.000 untuk n ≤ 15 dan 50.000 untuk n ≥ 25. Batas waktu misi 72 jam. Nilai tertinggi per baris dicetak tebal. Best-known adalah fitness terbaik dari semua run dan algoritma pada instance tersebut (Exact untuk n=6). Sumber: `results/tables/summary.csv`. Tabel lengkap (best, std, median, runtime, success rate) ada di `results/tables/summary.md`.

<!-- AUTO:summary -->
| skenario | n | best-known | Greedy rata-rata | HC rata-rata | SA rata-rata | GA rata-rata | rata-rata tertinggi |
|:--|:--|:--|:--|:--|:--|:--|:--|
| 2019 | 6 | 4.101 | **4.101** | **4.101** | **4.101** | **4.101** | Greedy / HC / SA / GA |
| 2019 | 10 | 6.767 | 6.731 | **6.767** | **6.767** | **6.767** | HC / SA / GA |
| 2019 | 15 | 9.215 | 9.044 | **9.157** | 9.092 | 9.018 | HC |
| 2019 | 25 | 12.243 | 12.019 | **12.121** | 12.120 | 11.402 | HC |
| 2019 | 38 | 12.687 | 12.268 | 12.050 | **12.333** | 9.668 | SA |
| 2026 | 6 | 3.244 | 3.188 | **3.244** | **3.244** | **3.244** | HC / SA / GA |
| 2026 | 10 | 5.225 | 5.224 | **5.225** | **5.225** | **5.225** | HC / SA / GA |
| 2026 | 15 | 6.933 | 6.294 | **6.933** | **6.933** | 6.921 | HC / SA |
| 2026 | 25 | 8.579 | 8.384 | **8.543** | 8.532 | 8.203 | HC |
| 2026 | 38 | 9.174 | 8.699 | 8.708 | **9.079** | 7.156 | SA |
<!-- /AUTO:summary -->

Ringkasan temuan:

- **Instance kecil (n ≤ 10)**: HC, SA, dan GA selalu mencapai best-known. Pada n=6, hasilnya sama dengan optimum Exact (gap 0%, `results/tables/optimality_gap.md`). Greedy meleset 1.704% dari optimum pada n=6 skenario 2026.
- **n=15 dan n=25**: HC dan SA setara. Wilcoxon-Holm HC vs SA tidak signifikan pada 2019 n=25 (p=0.6666), 2026 n=25 (p=0.2102), dan 2026 n=15 (p=1). Pengecualian: pada 2019 n=15, HC lebih baik dari SA (p Holm 0.02014). Sumber: `results/tables/wilcoxon_holm.md`.
- **n=38 (instance utama)**: SA terbaik di kedua Skenario tahun. Pada 2026, SA mengalahkan HC di 25 dari 30 seed dan mengalahkan Greedy di 29 dari 30 seed (keduanya p Holm 5.974e-06). GA kalah dari semua algoritma lain, termasuk Greedy, di 30 dari 30 seed. Sumber: `results/tables/wilcoxon_holm.md`.
- **Ablasi decay**: mengabaikan decay (g0=0) saat merencanakan rute membuat Prize yang benar-benar terkumpul turun rata-rata 6.46% untuk SA, 15.78% untuk HC, 9.348% untuk Greedy, dan 8.346% untuk GA (`results/tables/decay_ablation_seeds.md`).

### Diagnostik algoritma

Dihitung dari `results/raw/runs.csv`. Kolom "evaluasi per langkah HC" adalah ukuran neighbourhood penuh dari move set bersama.

<!-- AUTO:diagnostics -->
| skenario | n | evaluasi per langkah HC (neighbourhood) | HC single-start rata-rata | HC akhir rata-rata | restart HC rata-rata | acceptance rate SA rata-rata | generasi GA rata-rata |
|:--|:--|:--|:--|:--|:--|:--|:--|
| 2019 | 6 | 28 | 4.101 | 4.101 | 235.5 | 0.069 | 203 |
| 2019 | 10 | 120 | 6.767 | 6.767 | 29.7 | 0.118 | 203 |
| 2019 | 15 | 325 | 9.080 | 9.157 | 6.5 | 0.114 | 203 |
| 2019 | 25 | 1035 | 11.889 | 12.121 | 3.1 | 0.119 | 509 |
| 2019 | 38 | 2556 | 11.989 | 12.050 | 1.3 | 0.238 | 509 |
| 2026 | 6 | 28 | 3.244 | 3.244 | 234.4 | 0.083 | 203 |
| 2026 | 10 | 120 | 5.225 | 5.225 | 28.5 | 0.107 | 203 |
| 2026 | 15 | 325 | 6.933 | 6.933 | 6.4 | 0.072 | 203 |
| 2026 | 25 | 1035 | 8.324 | 8.543 | 3.3 | 0.140 | 509 |
| 2026 | 38 | 2556 | 8.688 | 8.708 | 1.3 | 0.232 | 509 |
<!-- /AUTO:diagnostics -->

## Observasi

Label **[Hipotesis]** menandai penjelasan yang belum diuji dengan eksperimen tersendiri. Label **[Data]** menandai pernyataan yang langsung terbaca dari hasil tersimpan.

1. **[Data]** Pada n=38, satu langkah HC mengevaluasi 2.556 tetangga, sehingga dengan budget 50.000 HC hanya sempat melakukan rata-rata 1.3 restart (tabel diagnostik di atas). Kurva konvergensi HC n=38 masih naik saat budget habis (`results/figures/convergence_n38.png`). Rata-rata HC pada 2026 n=38 (8.708) tidak berbeda signifikan dari Greedy (8.699, p Holm 0.6408).
   **[Hipotesis]** Kekalahan HC di n=38 lebih disebabkan biaya per langkah yang O(n²) daripada local optimum. Pendakian pertama belum selesai saat budget habis. Hipotesis ini bisa diuji dengan menaikkan budget HC atau memakai first-improvement.
2. **[Data]** GA adalah algoritma terlemah di n ≥ 25. Kualitas rata-ratanya 78% dari best-known pada 2026 n=38 dan 76.2% pada 2019 n=38 (`results/tables/scalability.md`), dengan hanya sekitar 509 generasi dalam budget 50.000 (tabel diagnostik).
   **[Hipotesis]** Fitness ditentukan oleh *prefix* permutasi yang muat dalam Batas waktu misi. Order Crossover mempertahankan urutan relatif tetapi menggeser posisi absolut, sehingga prefix yang baik sering rusak. Populasi acak tanpa local search juga membutuhkan lebih banyak generasi daripada yang tersedia.
3. **[Data]** SA paling stabil di n=38: simpangan baku 0.143 (2026) dan 0.1427 (2019), terkecil di antara HC, SA, dan GA (`results/tables/summary.md`). Acceptance rate rata-ratanya pada n=38 sekitar 0.23 (tabel diagnostik).
   **[Hipotesis]** Pendinginan yang diturunkan dari budget membuat SA tetap menjelajah selama seluruh budget. Satu evaluasi per langkah juga membuat SA memakai budget lebih efisien daripada HC yang harus menyapu seluruh neighbourhood.
4. **[Data]** Greedy kompetitif di n=38 skenario 2019: rata-ratanya 12.27, di atas HC (12.05) dan hanya di bawah SA (12.33) (`results/tables/summary.md`). Sebaliknya, pada 2026 n=15, Greedy hanya mencapai 90.78% dari best-known (`results/tables/scalability.md`).
   **[Hipotesis]** Di 2019, komponen operasional tidak dipakai, sehingga laju decay seragam dan rasio Prize/waktu menjadi heuristik yang baik. Di 2026, laju decay berbeda antar-node, dan pilihan myopic Greedy lebih sering salah.
5. **[Data]** Pemodelan decay mengubah rute. Pada rute SA terbaik, provinsi ber-data operasional rata-rata dikunjungi di urutan ke-4 (tiba rata-rata 10.05 jam) jika decay dimodelkan, dibandingkan urutan ke-12 (36.62 jam) jika decay diabaikan. Jambi bergeser dari urutan 2 ke 21, dan Sumatera Selatan dari urutan 3 ke 20 (`results/tables/decay_ablation_routes.md`, `results/tables/decay_ablation_order.md`).

## Batasan interpretasi

- **Prize adalah proksi pemodelan**, bukan ukuran resmi kerusakan yang dicegah. Bentuk eksponensial, `g0`, dan κ adalah asumsi (ASSUMED). Sensitivitas terhadap `g0` dan Batas waktu misi ada di `results/tables/sensitivity.md`.
- **Data 2026 parsial** sampai 2026-10-19. Data operasional hanya ada untuk 6 provinsi. 32 provinsi lain mendapat `ops=0` tanpa imputasi, dan ketiadaan data bukan bukti tidak ada kebakaran (`reports/data_quality.md`).
- **Koordinat node adalah ibu kota provinsi**, bukan lokasi api. Jarak adalah Haversine × 1.15 dengan kecepatan tetap 200 km/jam. Tidak ada cuaca, pengisian bahan bakar/air, atau batas jam terbang kru.
- **Satu armada.** Masalah team orienteering (beberapa armada) di luar cakupan.
- **Batas waktu misi 72 jam tidak mengikat pada n=6 dan n=10** (`results/tables/instances.md`). Pada ukuran ini masalahnya mendekati TSP dengan Prize meluruh, sehingga perbedaan antar-algoritma kecil.
- **Parameter algoritma ditetapkan sebelum eksperimen** dan tidak di-tuning. Peringkat algoritma berlaku untuk budget dan parameter ini saja. Hasil dengan budget atau tuning lain bisa berbeda.
- **Best-known untuk n ≥ 10 bukan optimum terbukti.** Optimality gap terhadap Exact hanya tersedia untuk n=6.
- **Generalisasi ke instance lain**:

<!-- FIRMS: isi setelah #6 -->

_(Pernyataan apakah peringkat algoritma pada instance provinsi tetap berlaku pada instance Klaster hotspot FIRMS k ∈ {50, 100, 200}, beserta tabel ringkasan dan grafik skalabilitas gabungan.)_

## Dokumen lain

- [`DATA_PROVENANCE.md`](DATA_PROVENANCE.md): status REAL / DERIVED / ASSUMED / SYNTHETIC setiap parameter.
- [`CHANGELOG.md`](CHANGELOG.md): keputusan pemodelan yang direvisi beserta alasannya.
- [`reports/data_quality.md`](reports/data_quality.md): laporan kualitas data.
- [`reports/figures_index.md`](reports/figures_index.md): daftar gambar dan tabel dengan caption.
- [`docs/laporan/bab2_metode.md`](docs/laporan/bab2_metode.md): draf Bab 2 (Metode).
- [`docs/laporan/bab3_eksperimen.md`](docs/laporan/bab3_eksperimen.md): draf Bab 3 (Eksperimen & Pembahasan).
- [`docs/laporan/kerangka_slide.md`](docs/laporan/kerangka_slide.md): kerangka slide presentasi 15 menit.
- [`docs/adr/`](docs/adr/): catatan keputusan arsitektur.
