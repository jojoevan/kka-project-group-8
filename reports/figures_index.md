# Daftar gambar

- `results/figures/boxplot_fitness_n{6,10,15,25,38}.png`: Sebaran fitness akhir 30 seed per algoritma (Greedy, HC, SA, GA) untuk tiap n, satu panel per Skenario tahun.
- `results/figures/convergence_n{25,38}.png`: Kurva konvergensi (fitness terbaik sejauh ini, rata-rata ± simpangan baku 30 seed) terhadap jumlah evaluasi, per algoritma dan Skenario tahun.
- `results/figures/scalability.png`: Runtime per run (skala log) dan kualitas solusi (% best-known) terhadap ukuran instance n, per algoritma dan Skenario tahun.
- `results/figures/sensitivity.png`: Sensitivitas fitness akhir dan jumlah Kunjungan terhadap Batas waktu misi (24/48/72/120 jam) dan g0 (0/0,005/0,01/0,02), n=38 skenario 2026, 30 seed (tabel: `results/tables/sensitivity.md`).
- `results/figures/best_route_map.png`: Peta studi kasus rute terbaik skenario 2026 n=38: Depot, panah arah, nomor urut, waktu tiba, dan Node dilewati (tabel: `results/tables/case_study_route.md`).

## Tabel analisis lanjutan (tanpa gambar)

- `results/tables/decay_ablation_routes.md`: Rute terbaik dengan decay vs dengan g0=0, keduanya dievaluasi dengan dan tanpa decay; Prize hilang bila decay diabaikan.
- `results/tables/decay_ablation_order.md`: Urutan dan waktu tiba tiap provinsi pada kedua rute.
- `results/tables/decay_ablation_seeds.md`: Prize hilang per algoritma, berpasangan per seed.
- `results/tables/scalability.md`, `results/tables/convergence.csv`: data grafik skalabilitas dan kurva konvergensi.
