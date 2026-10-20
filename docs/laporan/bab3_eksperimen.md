# BAB 3 — EKSPERIMEN DAN PEMBAHASAN (draf)

> Draf untuk difinalkan kelompok. Setiap angka disertai file sumbernya di `results/`. Blok di antara penanda `AUTO` diisi otomatis oleh `python -m src.docs_gen`, jadi jangan diedit manual. Label **hipotesis** menandai penjelasan yang belum diuji dengan eksperimen tersendiri. Istilah mengikuti `GLOSSARY.md`.

**Kode dan data:** _[link GitHub repo — isi sebelum pengumpulan]_

## 3.1 Setup eksperimen

- **Instance**: provinsi, n ∈ {6, 10, 15, 25, 38} termasuk Depot (Riau), dengan Skenario tahun 2019 dan 2026. Ringkasannya ada di `results/tables/instances.md`.
- **Parameter misi**: kecepatan 200 km/jam, faktor detour 1.15, waktu tinggal 1 jam, g0 = 0.01/jam, κ = 1.0. Batas waktu misi 72 jam berasal dari kalibrasi: Greedy pada n=38 skenario 2026 mengunjungi 21 dari 37 node kandidat (`results/tables/instances.md`). Daftar lengkap ada di `DATA_PROVENANCE.md`.
- **Batas waktu misi tidak mengikat pada n=6 dan n=10.** Greedy mengunjungi semua node kandidat dalam 24.38 jam (2019, n=6), 59.03 jam (2019, n=10), 25.83 jam (2026, n=6), dan 54.32 jam (2026, n=10) (`results/tables/instances.md`). Pada ukuran ini masalahnya mendekati TSP dengan Prize meluruh.
- **Algoritma**: Greedy, HC, SA, dan GA untuk semua instance. Exact hanya untuk n=6.
- **Budget evaluasi**: 20.000 (n ≤ 15) dan 50.000 (n ≥ 25).
- **Jumlah seed**: 30 seed per (algoritma, n, Skenario tahun).
- **Total run**: 1.202 run perbandingan utama dan 960 run sweep sensitivitas. Runtime total 687.4 detik dengan 12 worker (`results/logs/run_all.log`).
- **Metrik**:
  - Fitness akhir (total Prize): best, mean, std, dan median.
  - Runtime.
  - Evaluasi sampai 95% fitness akhir.
  - *Success rate*: proporsi run yang berada dalam 1% dari best-known.
  - Optimality gap terhadap Exact.
- **Uji statistik**: Wilcoxon signed-rank dua sisi, berpasangan per seed, dengan koreksi Holm per (Skenario tahun, n).
- **Aturan keadilan**: lihat Bab 2.6.

## 3.2 Perbandingan utama

Tabel 3.1 berisi fitness rata-rata 30 seed (sumber: `results/tables/summary.csv`; tabel lengkap di `results/tables/summary.md`). Sebaran per seed ditampilkan pada Gambar 3.1 (`results/figures/boxplot_fitness_n{6,10,15,25,38}.png`).

**Tabel 3.1** Fitness rata-rata per algoritma.

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

Pembahasan:

- **n ≤ 10.** HC, SA, dan GA mencapai best-known di semua 30 seed (*success rate* 1). Greedy tertinggal sedikit, misalnya 6.731 vs 6.767 pada 2019 n=10. Karena Batas waktu misi tidak mengikat, instance ini terlalu mudah untuk membedakan metaheuristik.
- **n=15 dan n=25.** HC dan SA hampir identik. Success rate pada 2026 n=25 adalah 1 untuk HC dan SA, dan 0.2 untuk GA. Pada 2026 n=15, Greedy hanya mencapai 6.294, sedangkan HC dan SA mencapai 6.933. Ini selisih terbesar Greedy terhadap best-known di semua instance (90.78%, `results/tables/scalability.md`).
- **n=38.** SA memiliki rata-rata tertinggi di kedua Skenario tahun: 9.079 (2026) dan 12.33 (2019). SA juga yang paling stabil, dengan simpangan baku 0.143 dan 0.1427. HC tertinggal (8.708 dan 12.05, simpangan baku 0.3175 dan 0.3827). GA jauh di bawah semua algoritma lain (7.156 dan 9.668). Success rate pada 2026 n=38 adalah 0.5667 untuk SA, 0.1333 untuk HC, dan 0 untuk GA maupun Greedy (`results/tables/summary.md`).
- **Peringkat berubah dengan ukuran instance.** Pada n ≤ 25, HC sama baik atau sedikit lebih baik dari SA. Pada n=38, SA lebih unggul secara signifikan (subbab 3.7).

## 3.3 Optimality gap

Sumber: `results/tables/optimality_gap.md`. Exact hanya praktis sampai 9 node, sehingga gap hanya tersedia untuk n=6.

- HC, SA, dan GA mencapai optimum Exact di **semua** 30 seed untuk kedua Skenario tahun: gap 0%, proporsi optimal 1. Optimumnya 4.101 (2019) dan 3.244 (2026).
- Greedy optimal pada 2019. Pada 2026, Greedy meleset 1.704%.
- Exact memeriksa 326 urutan feasible dalam 0.0056–0.0067 detik (`results/tables/summary.md`).

Hasil ini memvalidasi implementasi decoder dan ketiga metaheuristik, karena tidak ada heuristik yang melampaui optimum. Namun gap di n=6 tidak cukup untuk membedakan HC, SA, dan GA. Untuk n ≥ 10, kualitas diukur relatif terhadap best-known, yang bukan optimum terbukti.

## 3.4 Konvergensi

Sumber: Gambar 3.2 `results/figures/convergence_n25.png`, Gambar 3.3 `results/figures/convergence_n38.png`, dan data `results/tables/convergence.csv`.

- **SA** naik paling cepat dan stabil. Pada 2026 n=38, SA mencapai 95% fitness akhirnya rata-rata setelah 1.7e4 evaluasi. HC membutuhkan 3.573e4 evaluasi dan GA 2.79e4 (`results/tables/summary.md`, kolom "evaluasi ke 95%").
- **HC** naik berundak. Setiap undakan adalah satu langkah steepest-ascent yang menyapu seluruh neighbourhood. Pada n=38, satu langkah berisi 2.556 evaluasi, sehingga rata-rata hanya 1.3 restart muat dalam budget (tabel diagnostik di `README.md`, dihitung dari `results/raw/runs.csv`). Kurva HC n=38 masih naik saat budget habis. Fitness single-start HC (8.688) hampir sama dengan fitness akhirnya (8.708) pada 2026 n=38, jadi restart hampir tidak berkontribusi.
- **GA** naik cepat di awal, lalu mendatar jauh di bawah SA dan HC. Dalam budget 50.000, GA hanya menjalankan sekitar 509 generasi.
- **Greedy** berupa garis datar (1 evaluasi). Pada n=38 skenario 2026, SA melampaui Greedy di sekitar sepertiga awal budget, sedangkan HC baru menyamainya di akhir budget.

**Hipotesis:** pada n besar, efisiensi budget lebih menentukan daripada kemampuan keluar dari local optimum. SA memakai satu evaluasi per langkah, sedangkan HC memakai O(n²) evaluasi per langkah.

## 3.5 Skalabilitas

Sumber: Gambar 3.4 `results/figures/scalability.png` dan `results/tables/scalability.md`.

- **Runtime.** Greedy membutuhkan ≈0.0001–0.002 detik. HC, SA, dan GA membutuhkan beberapa detik per run. Pada 2026 n=38, runtime rata-ratanya 4.777 detik (HC), 7.354 detik (SA), dan 9.159 detik (GA). Karena budget evaluasinya sama, perbedaan runtime mencerminkan *overhead* per evaluasi: OX dan manajemen populasi di GA, serta kalkulasi move dan penerimaan di SA.
- **Kualitas (% best-known).**
  - SA bertahan di atas 97% untuk semua n: 97.21% (2019 n=38) dan 98.97% (2026 n=38).
  - HC turun ke ≈95% di n=38: 94.98% (2019) dan 94.93% (2026).
  - GA turun tajam: 93.13% → 76.2% (2019, n=25 → 38) dan 95.62% → 78% (2026).

**Hipotesis** penyebab penurunan GA: fitness ditentukan oleh prefix permutasi yang muat dalam Batas waktu misi. OX mempertahankan urutan relatif tetapi menggeser posisi absolut, sehingga prefix yang baik dari induk sering rusak. Populasi acak tanpa local search juga membutuhkan lebih dari ±509 generasi. Hipotesis ini belum diuji. Salah satu cara mengujinya adalah GA dengan crossover yang mempertahankan prefix, atau GA dengan budget lebih besar.

### 3.5.1 Skalabilitas pada instance Klaster hotspot FIRMS

<!-- FIRMS: isi setelah #6 -->

_(Hasil 30 seed × {Greedy, HC, SA, GA} × k ∈ {50, 100, 200}, budget 100.000. Grafik skalabilitas gabungan provinsi + FIRMS. Penjelasan biaya per langkah HC yang O(n²) berdasarkan data. Pernyataan apakah peringkat algoritma pada instance provinsi tetap berlaku pada instance FIRMS.)_

## 3.6 Sensitivitas

Sumber: Gambar 3.5 `results/figures/sensitivity.png` dan `results/tables/sensitivity.md`. Semua sweep dilakukan pada n=38 skenario 2026 dengan 30 seed. Satu parameter diubah, dan parameter lain tetap di nilai default.

**Batas waktu misi (24 / 48 / 72 / 120 jam).**

- Jumlah Kunjungan SA naik dari 7 ke 15.67, 22.43, lalu 33.03.
- Pada 24 jam, HC dan SA hampir selalu mencapai solusi terbaik setting tersebut (99.79% dan 99.93%). Greedy hanya mencapai 86.7%, karena saat hanya ±7 node yang muat, satu pilihan myopic yang salah sangat mahal.
- Pada 120 jam, keunggulan SA melebar: SA 98.41%, HC 91.24%, Greedy 90.69%, dan GA 81.26%.
- SA memiliki kualitas tertinggi di semua nilai. GA terendah di semua nilai kecuali 24 jam, di mana GA mengungguli Greedy (96.51% vs 86.7%).

**Laju decay dasar g0 (0 / 0.005 / 0.01 / 0.02).**

- Fitness turun ketika g0 naik. Untuk SA: 12.3 → 10.54 → 9.079 → 6.853.
- Tanpa decay (g0=0), masalahnya menjadi orienteering statis. Di sini HC (85.33%) dan Greedy (83.94%) paling jauh dari solusi terbaik, sedangkan SA mencapai 96.56%.
- Pada g0=0.02, semua algoritma kecuali GA berada di atas 93%.

**Hipotesis:** decay yang kuat membuat urutan "dekat dan berisiko tinggi dulu" makin dominan, sehingga landscape lebih mudah bagi heuristik lokal dan Greedy.

Di seluruh sweep, urutan SA > HC > GA tidak berubah (kolom "kualitas rata-rata"). Kesimpulan utama tentang ketiga metaheuristik karena itu tidak bergantung pada pilihan T_max = 72 jam atau g0 = 0.01 dalam rentang yang diuji.

Posisi Greedy relatif terhadap HC justru berubah-ubah:

- HC jelas lebih baik pada 24 jam, 48 jam, g0=0, dan g0=0.02.
- Keduanya hampir seri pada setting default (94.93% vs 94.82%) dan pada 120 jam (91.24% vs 90.69%).
- Greedy lebih baik pada g0=0.005 (95.55% vs 93.89%).

## 3.7 Uji statistik

Sumber: `results/tables/wilcoxon_holm.md`. Tabel ini berisi Wilcoxon signed-rank berpasangan per seed, dengan koreksi Holm atas 6 pasangan dalam setiap (Skenario tahun, n), pada α = 0.05.

- **n=6 dan n=10**: HC, SA, dan GA identik di semua seed (p = 1). Greedy kalah signifikan dari ketiganya, kecuali pada 2019 n=6 karena semua algoritma seri.
- **n=15**:
  - 2026: HC = SA = GA secara statistik (p Holm 0.3074 untuk HC vs GA dan SA vs GA).
  - 2019: HC > SA (p Holm 0.02014) dan HC > GA (p Holm 0.003159).
- **n=25**: HC vs SA tidak signifikan, dengan p Holm 0.6666 (2019) dan 0.2102 (2026). HC dan SA sama-sama signifikan lebih baik dari GA dan Greedy di kedua Skenario tahun. Greedy vs GA signifikan pada 2019 (Greedy lebih baik) tetapi tidak pada 2026 (p Holm 0.05997).
- **n=38**:
  - 2026: SA > HC (25 dari 30 seed, p Holm 5.974e-06) dan SA > Greedy (29 dari 30 seed, p Holm 5.974e-06). HC vs Greedy tidak signifikan (p Holm 0.6408). Semua algoritma mengalahkan GA di 30 dari 30 seed (p Holm 1.118e-08).
  - 2019: SA > HC (p Holm 0.00768) dan SA > Greedy (p Holm 0.01949). Greedy justru mengalahkan HC (20 vs 10 seed, p Holm 0.01854).

Kesimpulan statistik: **SA adalah satu-satunya algoritma yang konsisten tidak kalah signifikan dari algoritma lain pada instance terbesar.** Pada instance menengah, HC setara dengan SA. GA tidak pernah signifikan lebih baik dari HC atau SA.

## 3.8 Ablasi decay

Sumber: `results/tables/decay_ablation_routes.md`, `results/tables/decay_ablation_order.md`, dan `results/tables/decay_ablation_seeds.md`. Eksperimen ini membandingkan rute yang direncanakan **dengan** decay dan rute yang direncanakan **tanpa** decay (g0=0). Kedua rute lalu dievaluasi dengan decay, yaitu kondisi yang dianggap nyata.

- **Rute terbaik SA.** Kedua rute mengunjungi 23 node, termasuk 4 provinsi ber-data operasional. Bedanya hanya pada urutan:
  - Dengan decay, provinsi operasional rata-rata dikunjungi di urutan ke-4 (tiba 10.05 jam).
  - Tanpa decay, mereka dikunjungi di urutan ke-12 (tiba 36.62 jam).
  - Jambi bergeser dari urutan 2 ke 21, dan Sumatera Selatan dari 3 ke 20.
  - Akibatnya, rute tanpa decay kehilangan 0.3144 Prize (3.428%).
- **Berpasangan per seed (30 seed).** Mengabaikan decay menurunkan Prize rata-rata 6.46% (SA), 15.78% (HC), 9.348% (Greedy), dan 8.346% (GA). Rute tanpa decay lebih buruk di 29 dari 30 seed untuk SA dan HC, 30 dari 30 untuk Greedy, dan 23 dari 30 untuk GA.

Pemodelan decay terbukti mengubah keputusan: provinsi dengan kebakaran aktif dikunjungi lebih awal. Kerugian bila decay diabaikan juga terukur. Besarnya kerugian bergantung pada asumsi g0 dan κ (subbab 3.6).

## 3.9 Studi kasus: rute terbaik skenario 2026, n=38

Sumber: Gambar 3.6 `results/figures/best_route_map.png` dan `results/tables/case_study_route.md`. Rute ini adalah rute SA seed 3, dengan total Prize 9.1736 (sama dengan best-known HC pada instance ini).

- **Statistik rute**: 23 Kunjungan dan 14 Node dilewati. Total jarak 9603 km dan waktu misi 71.02 dari 72 jam, sehingga sisa waktunya 0.98 jam.
- **Urutan kunjungan.** Rute dimulai dari Kepulauan Riau (tiba 1.936 jam). Setelah itu rute mendahulukan klaster Sumatra-Kalimantan yang ber-data operasional: Jambi (4.64 jam), Sumatera Selatan (6.779 jam), Kalimantan Barat (12.26 jam, Risiko 1), dan Kalimantan Tengah (16.51 jam). Rute lalu bergerak ke Sulawesi, Maluku, Nusa Tenggara, dan Jawa, kemudian kembali melalui Lampung, Bengkulu, dan Sumatera Barat.
- **Node dilewati.**
  - Papua (6 provinsi), Maluku Utara, Sulawesi Utara, Gorontalo, dan Kalimantan Utara dilewati karena terlalu jauh dari Depot untuk muat bersama node lain dalam 72 jam.
  - Aceh (Risiko 0.5373) dan Sumatera Utara (0.5328) juga dilewati meskipun dekat Depot. **Hipotesis:** keduanya berada di arah berlawanan dari klaster Kalimantan yang Risikonya tinggi, sehingga waktu tempuh bolak-baliknya lebih baik dipakai untuk node lain.
  - DKI Jakarta (Risiko 0) dan Yogyakarta (0.0737) dilewati karena Risikonya rendah.

## 3.10 Keterbatasan

- **Prize adalah proksi pemodelan.** Bentuk eksponensial, g0, κ, dan bobot Risiko (0.4/0.3/0.3) adalah asumsi. Sensitivitas sudah diuji untuk T_max dan g0, tetapi belum untuk bobot Risiko (di luar cakupan).
- **Data**:
  - Data 2026 parsial (sampai 2026-10-19).
  - Data operasional hanya ada untuk 6 provinsi, tanpa imputasi untuk 32 provinsi lain.
  - Luas indikatif CSV berbeda dari xlsx untuk Jambi, Kalimantan Tengah, dan Riau (`reports/data_quality.md`).
- **Geometri**:
  - Node adalah ibu kota provinsi, bukan lokasi api.
  - Jarak memakai Haversine × 1.15 dengan kecepatan tetap.
  - Tidak ada cuaca, pengisian bahan bakar/air, batas jam terbang, atau armada lebih dari satu.
  - Provinsi Depot (Riau) tidak menjadi node kandidat, sehingga Risikonya (0.7083 pada 2026, `reports/data_quality.md`) tidak ikut dihitung dalam Prize.
- **Instance kecil kurang diskriminatif.** Batas waktu misi tidak mengikat pada n=6 dan n=10. Optimum terbukti juga hanya tersedia untuk n=6.
- **Parameter algoritma tidak di-tuning.** Peringkat berlaku untuk budget 20.000/50.000 dan parameter default. GA mungkin membaik dengan operator atau budget lain (hipotesis, subbab 3.5).
- **Penyebab** kekalahan HC dan GA pada n=38 masih berupa hipotesis. Eksperimen ablasi operator atau budget belum dijalankan.
- **Generalisasi ke instance lain**:

<!-- FIRMS: isi setelah #6 -->

_(Ringkas apakah temuan pada instance provinsi berlaku pada instance Klaster hotspot FIRMS.)_
