# Kerangka Slide Presentasi (maks. 15 menit)

> Total alokasi 14 menit, menyisakan ±1 menit cadangan. Angka di slide diambil dari file yang disebut di kolom gambar/sumber. Istilah mengikuti `GLOSSARY.md`.

| # | Judul slide | Poin utama | Gambar / sumber | Waktu |
|--:|:--|:--|:--|--:|
| 1 | Perutean Armada Udara Karhutla: HC vs SA vs GA | Judul, Kelompok 8, nama anggota, mata kuliah KKA | — | 0:20 |
| 2 | Masalah: satu armada, waktu terbatas, api terus meluas | Karhutla 2019 dan 2026; armada udara harus memilih provinsi **dan** urutannya; makin lambat tiba, makin kecil kerusakan yang dicegah | `reports/data_quality.md` (luas terbakar per tahun) | 0:45 |
| 3 | Data dan Risiko | Dua dataset REAL (luas terbakar 38 provinsi 2018–2026, snapshot operasional 6 provinsi); Risiko = 0.4·hist + 0.3·cur + 0.3·ops, dinormalisasi sekali atas 38 provinsi; inkonsistensi Riau (hotspot 0) sebagai alasan tidak memakai hotspot saja | `reports/data_quality.md`, `DATA_PROVENANCE.md` | 1:00 |
| 4 | Formulasi: orienteering dengan Prize meluruh | Prize = Risiko·exp(−g_i·t), g_i naik dengan keparahan operasional; kendala Batas waktu misi termasuk kembali ke Depot; NP-hard (pemilihan + pengurutan) | Rumus dari Bab 2.2 | 1:00 |
| 5 | Encoding dan decoder "lewati lalu lanjut" | Permutasi → selalu feasible; Node dilewati dibuang, node berikutnya tetap dicoba; move set bersama swap / relocate / 2-opt | Diagram contoh permutasi → rute (buat manual) | 1:00 |
| 6 | Tiga algoritma + dua pembanding | HC steepest-ascent + restart; SA dengan T0 terkalibrasi dan pendinginan dari budget; GA (OX, tournament, elitisme, tanpa seeding greedy); Greedy rasio Prize/waktu; Exact n ≤ 9 | Pseudocode ringkas Bab 2.4 | 1:00 |
| 7 | Aturan keadilan dan setup | Budget evaluasi sama (20.000 / 50.000), solusi awal sama per seed, move set sama, 30 seed, Wilcoxon + Holm; Batas waktu misi 72 jam hasil kalibrasi (21/37 node) | `results/tables/instances.md` | 0:45 |
| 8 | Validasi: optimality gap n=6 | HC, SA, GA = optimum Exact di semua seed; Greedy −1.704% (2026) | `results/tables/optimality_gap.md` | 0:30 |
| 9 | Hasil utama | Tabel fitness rata-rata per n; n ≤ 25: HC ≈ SA; n=38: SA terbaik (9.079 vs HC 8.708 vs Greedy 8.699 vs GA 7.156, skenario 2026) | Tabel ringkasan `README.md` (dari `results/tables/summary.csv`), `results/figures/boxplot_fitness_n38.png` | 1:15 |
| 10 | Uji statistik | n=38 2026: SA > HC (25/30 seed) dan SA > Greedy (29/30), p Holm 5.974e-06; HC vs Greedy tidak signifikan; GA kalah 30/30 dari semua | `results/tables/wilcoxon_holm.md` | 0:45 |
| 11 | Konvergensi: kenapa HC dan GA tertinggal | SA naik paling cepat; HC berundak (2.556 evaluasi per langkah, ±1.3 restart; pada sebagian besar seed pendakian pertama belum selesai saat budget habis); GA mendatar (±509 generasi) — penjelasan diberi label **hipotesis** | `results/figures/convergence_n38.png`, tabel diagnostik `README.md` | 1:00 |
| 12 | Skalabilitas | Runtime vs n (log); kualitas SA > 97% di semua n, GA turun ke 76–78% di n=38 | `results/figures/scalability.png`, `results/tables/scalability.md` | 0:45 |
| 13 | Sensitivitas | Batas waktu misi 24–120 jam dan g0 0–0.02: urutan SA > HC > GA tetap; Greedy vs HC berubah-ubah | `results/figures/sensitivity.png`, `results/tables/sensitivity.md` | 0:45 |
| 14 | Ablasi decay: apakah decay penting? | Mengabaikan decay → provinsi ber-data operasional tiba rata-rata 36.62 jam alih-alih 10.05 jam; Prize hilang rata-rata 6.46% (SA) s.d. 15.78% (HC) | `results/tables/decay_ablation_routes.md`, `results/tables/decay_ablation_seeds.md` | 0:45 |
| 15 | Studi kasus: rute terbaik 2026, n=38 | 23 Kunjungan, 14 Node dilewati, 9603 km, 71.02 dari 72 jam; Sumatra–Kalimantan operasional didahulukan; Papua dilewati karena jarak | `results/figures/best_route_map.png`, `results/tables/case_study_route.md` | 1:00 |
| 16 | Instance FIRMS: apakah peringkat tetap berlaku? | 28.983 hotspot VIIRS → k ∈ {50, 100, 200} Klaster hotspot, budget 100.000; SA tetap pertama di semua k (kualitas ≥ 96,86%); peringkat provinsi **tidak tetap berlaku sepenuhnya**: HC turun di bawah Greedy (semua k) dan GA (k ≥ 100) karena neighbourhood O(n²) (79.003 evaluasi per langkah pada k=200 → 1,3 langkah dalam budget); jujur: Batas waktu misi 72 jam adalah kandidat terdekat (39%, di luar target 40–60%), dan sekitar 260 hotspot Malaysia ikut masuk kotak | `results/figures/scalability_combined.png`, `results/figures/firms_cluster_map_k100.png`, `results/tables/firms_ranking.md`, `results/tables/firms_hc_cost.md` | 0:45 |
| 17 | Kesimpulan, keterbatasan, dan link GitHub | SA paling andal di instance terbesar, termasuk FIRMS k=200; HC setara SA di instance menengah tetapi runtuh pada FIRMS (O(n²)); GA lemah tanpa operator khusus; Prize adalah proksi, data 2026 parsial, satu armada; link repo | `README.md` bagian Batasan interpretasi | 0:40 |
| | **Total** | | | **14:00** |

## Catatan penyaji

- **Slide 9–11** adalah inti presentasi. Jika waktu mepet, ringkas slide 12–13 menjadi satu slide.
- Selalu sebut penjelasan kekalahan HC dan GA sebagai **hipotesis**. Yang terukur hanyalah jumlah evaluasi per langkah, jumlah restart, dan jumlah generasi.
- Siapkan jawaban untuk pertanyaan yang mungkin muncul:
  - "Kenapa Jambi Risikonya tidak 0?" Jawab: normalisasi global, CHANGELOG no. 1.
  - "Kenapa 72 jam?" Jawab: kalibrasi, `results/tables/instances.md`.
  - "Kenapa n=6 semua seri?" Jawab: batas waktu tidak mengikat.
