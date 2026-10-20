# Daftar Gambar dan Tabel

Setiap gambar (300 dpi) dan tabel hasil di `results/`, masing-masing dengan caption satu baris. Daftar ini dibuat otomatis oleh `python -m src.docs_gen`. Generator menolak gambar atau tabel yang belum punya caption, jadi daftar ini selalu lengkap. File `.csv` pasangan setiap tabel `.md` berisi angka yang sama dengan presisi penuh.

<!-- AUTO:figures -->
**Gambar**

- `results/figures/best_route_map.png`: Peta studi kasus rute terbaik skenario 2026 n=38 (SA, seed 3): Depot, panah arah, nomor urut, waktu tiba, dan Node dilewati.
- `results/figures/boxplot_fitness_n6.png`: Sebaran fitness akhir 30 seed per algoritma untuk n=6, satu panel per Skenario tahun.
- `results/figures/boxplot_fitness_n10.png`: Sebaran fitness akhir 30 seed per algoritma untuk n=10, satu panel per Skenario tahun.
- `results/figures/boxplot_fitness_n15.png`: Sebaran fitness akhir 30 seed per algoritma untuk n=15, satu panel per Skenario tahun.
- `results/figures/boxplot_fitness_n25.png`: Sebaran fitness akhir 30 seed per algoritma untuk n=25, satu panel per Skenario tahun.
- `results/figures/boxplot_fitness_n38.png`: Sebaran fitness akhir 30 seed per algoritma untuk n=38, satu panel per Skenario tahun.
- `results/figures/convergence_n25.png`: Kurva konvergensi n=25: fitness terbaik sejauh ini (rata-rata ± simpangan baku 30 seed) terhadap jumlah evaluasi.
- `results/figures/convergence_n38.png`: Kurva konvergensi n=38: fitness terbaik sejauh ini (rata-rata ± simpangan baku 30 seed) terhadap jumlah evaluasi.
- `results/figures/scalability.png`: Runtime per run (skala log) dan kualitas solusi (% best-known) terhadap ukuran instance n, per algoritma dan Skenario tahun.
- `results/figures/sensitivity.png`: Sensitivitas fitness akhir dan jumlah Kunjungan terhadap Batas waktu misi dan g0, n=38 skenario 2026, 30 seed.

**Tabel**

- `results/tables/case_study_route.md`: Detail rute studi kasus: urutan, waktu tiba, Prize per node, dan Node dilewati beserta Risikonya.
- `results/tables/decay_ablation_order.md`: Urutan dan waktu tiba tiap provinsi pada rute terbaik dengan decay vs tanpa decay (g0=0).
- `results/tables/decay_ablation_routes.md`: Rute terbaik dengan decay vs g0=0, dievaluasi dengan dan tanpa decay; Prize hilang bila decay diabaikan.
- `results/tables/decay_ablation_seeds.md`: Prize hilang bila decay diabaikan, per algoritma, berpasangan per seed.
- `results/tables/instances.md`: Ringkasan instance: budget evaluasi, Batas waktu misi, node terkunjungi Greedy, dan apakah batas waktu mengikat.
- `results/tables/optimality_gap.md`: Optimality gap Greedy, HC, SA, GA terhadap Exact untuk n=6.
- `results/tables/scalability.md`: Runtime dan kualitas (% best-known) rata-rata per algoritma terhadap n.
- `results/tables/sensitivity.md`: Statistik fitness per algoritma untuk setiap nilai Batas waktu misi dan g0 (n=38, skenario 2026).
- `results/tables/summary.md`: Perbandingan utama: best/mean/std/median fitness, runtime, evaluasi ke 95%, dan success rate per algoritma, n, dan Skenario tahun.
- `results/tables/wilcoxon_holm.md`: Uji Wilcoxon signed-rank berpasangan per seed dengan koreksi Holm untuk setiap pasangan algoritma.
<!-- /AUTO:figures -->

**Data mentah pendukung** (tanpa caption, tidak masuk laporan secara langsung):

- `results/raw/runs.csv`: satu baris per run (fitness, runtime, evaluasi, fitness single-start HC, restart HC, acceptance rate SA, generasi GA).
- `results/raw/sensitivity_runs.csv`: satu baris per run sweep sensitivitas.
- `results/raw/histories.jsonl.gz`: riwayat konvergensi (evaluasi, best-so-far) per run.
- `results/tables/convergence.csv`: data kurva konvergensi.
- `results/routes/best_route_{2019,2026}_n{6,10,15,25,38}.json`: detail rute terbaik setiap instance.

## Instance FIRMS

<!-- FIRMS: isi setelah #6 -->

- _(gambar skalabilitas gabungan provinsi + FIRMS)_
- _(peta sebaran klaster dengan rute terbaik, k=100)_
- _(tabel ringkasan skalabilitas FIRMS)_
