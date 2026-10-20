# BAB 2 — METODE (draf)

> Draf untuk difinalkan kelompok. Istilah mengikuti `GLOSSARY.md`. Nilai parameter diambil dari `DATA_PROVENANCE.md`, yang dibuat otomatis dari `config.yaml`.

## 2.1 Data dan Risiko node

Model memakai dua dataset (REAL):

1. **Luas terbakar per provinsi** 2018–2026 untuk 38 provinsi (`data/raw/luas-karhutla-provinsi.xlsx`). Nilai 2026 adalah data parsial sampai 2026-10-19.
2. **Snapshot operasional 2026-10-19** untuk enam provinsi (`data/raw/karhutla-2026_semua-provinsi_2026-10-19.csv`): Riau, Jambi, Sumatera Selatan, Kalimantan Barat, Kalimantan Tengah, dan Kalimantan Selatan.

Data prep (`src/data_prep.py`) melakukan langkah berikut:

- Mengurai angka berformat Indonesia ("1.284,70").
- Memakai baris Total sebagai checksum.
- Memetakan nama provinsi singkatan ke nama baku.
- Mengubah kategori PM2.5 ke ordinal 0–4, memakai tingkat terburuk untuk kategori berbentuk rentang.
- Mengambil angka visibilitas minimum dari teks.

Hasil pemeriksaan kualitas data ada di `reports/data_quality.md`.

**Risiko** provinsi *i* untuk Skenario tahun *s* adalah:

    hist_i  = minmax( Σ_{y=2018}^{2025} γ^(2025−y) · log1p(luas_{i,y}) )
    cur_i^s = minmax( log1p(luas_{i,s}) )
    ops_i   = minmax antar-6 provinsi( rata-rata[luas indikatif, fire spot, PM2.5/4, 1/visibilitas] )
              ops_i = 0 untuk 32 provinsi lain, dan untuk semua provinsi bila s ≠ 2026
    Risiko_i^s = minmax_{38 provinsi}( α·hist_i + β·cur_i^s + δ·ops_i )

Default: α=0.4, β=0.3, δ=0.3, γ=0.8 (ASSUMED). Min-max dilakukan **sekali atas 38 provinsi**, sehingga Risiko sebuah provinsi sama di instance mana pun (CHANGELOG no. 1).

Jumlah hotspot tidak dipakai sendirian sebagai ukuran keparahan. Alasannya, Riau mencatat hotspot 0 tetapi punya fire spot, kualitas udara berbahaya, dan luas terbakar indikatif yang besar (`reports/data_quality.md`).

## 2.2 Formulasi masalah: orienteering dengan Prize meluruh

Diberikan sebuah **Instance** dengan:

- Himpunan node V = {0, 1, …, n−1}. Node 0 adalah **Depot** (Riau).
- Risiko r_i ∈ [0,1] untuk setiap node.
- Jarak d_ij = Haversine(i, j) × faktor detour (1.15).
- Kecepatan v (200 km/jam).
- Waktu tinggal per Kunjungan w (1 jam).
- **Batas waktu misi** T_max (72 jam).

Sebuah rute adalah barisan node berbeda R = (i_1, …, i_m) ⊆ V \ {0}. Waktu tiba di node ke-k adalah

    t_{i_1} = d_{0,i_1}/v,     t_{i_k} = t_{i_{k−1}} + w + d_{i_{k−1},i_k}/v

**Prize** node i yang dikunjungi pada waktu t_i adalah

    Prize_i(t_i) = r_i · exp(−g_i · t_i),   g_i = g0 · (1 + κ · ops_i)

dengan g0 = 0.01/jam dan κ = 1.0 (ASSUMED). Provinsi dengan keparahan operasional tinggi meluruh lebih cepat. Dengan g0 = 0, masalah ini kembali menjadi orienteering statis.

Masalah optimisasinya:

    maksimumkan  F(R) = Σ_{i ∈ R} Prize_i(t_i)
    dengan kendala  t_{i_m} + w + d_{i_m,0}/v ≤ T_max,   setiap node paling banyak satu Kunjungan.

Masalah ini menggabungkan **pemilihan** node (knapsack waktu) dan **pengurutan** (TSP). Karena Prize bergantung pada waktu tiba, masalah ini juga mirip *traveling repairman*. Orienteering termasuk NP-hard, sehingga metode pencarian lokal dan metaheuristik relevan.

## 2.3 Encoding permutasi dan decoder "lewati lalu lanjut"

Sebuah solusi dikodekan sebagai **permutasi** semua node kandidat (tanpa Depot). Decoder `Instance.evaluate` (O(n)) membaca permutasi dari kiri ke kanan:

```
fungsi EVALUATE(perm):
    t ← 0; prev ← Depot; F ← 0
    untuk setiap i dalam perm:
        tiba ← t + d[prev,i]/v
        jika tiba + w + d[i,Depot]/v > T_max:
            lanjut                      ▷ Node dilewati: dibuang, node berikutnya tetap dicoba
        F ← F + r_i · exp(−g_i · tiba)
        t ← tiba + w; prev ← i
    kembalikan F
```

Sifat encoding ini:

- **Setiap permutasi selalu feasible.** Rute hasil decoding tidak pernah melampaui T_max, termasuk waktu kembali ke Depot. Karena itu operator permutasi standar bisa dipakai tanpa perbaikan atau penalti.
- **Aturan "lewati lalu lanjut".** Node yang tidak muat tidak menghentikan decoding, sehingga node dekat di belakangnya masih bisa dikunjungi. Aturan ini mengurangi plateau di ekor permutasi dibanding aturan "berhenti di node pertama yang tidak muat" (CHANGELOG no. 4).
- **Plateau tetap ada.** Permutasi yang berbeda hanya pada urutan Node dilewati menghasilkan fitness yang sama.

**Move set bersama** (`src/algorithms/common.py`) untuk posisi i < j:

- *swap*: tukar elemen di posisi i dan j.
- *relocate*: pindahkan elemen dari posisi i ke posisi j, ke dua arah.
- *2-opt*: balik segmen [i..j].

Neighbourhood penuhnya berukuran O(n²). Untuk 37 node kandidat (n=38), ukurannya 2.556 tetangga (tabel diagnostik di `README.md`).

## 2.4 Algoritma

Semua solver punya kontrak yang sama: `solve(instance, budget, seed)`. Setiap solver mengembalikan permutasi terbaik, detail rute, fitness, riwayat (evaluasi, best-so-far), runtime, dan jumlah evaluasi. Jumlah evaluasi tidak pernah melebihi budget.

### 2.4.1 Steepest-Ascent Hill Climbing (HC)

```
fungsi HC(instance, budget, seed):
    cur ← PERMUTASI_AWAL(seed)
    selama budget tersisa:
        f_cur ← EVALUATE(cur)
        ulangi:
            (best, f_best) ← (∅, f_cur)
            untuk setiap move m dalam NEIGHBOURHOOD_PENUH:   ▷ swap, relocate, 2-opt
                q ← APPLY(cur, m); f ← EVALUATE(q)
                jika f > f_best: (best, f_best) ← (q, f)
            jika best = ∅: keluar                          ▷ local optimum
            (cur, f_cur) ← (best, f_best)
        catat f_cur sebagai single-start jika ini restart pertama
        cur ← PERMUTASI_ACAK()                             ▷ random restart
    kembalikan solusi terbaik yang pernah dievaluasi
```

### 2.4.2 Simulated Annealing (SA)

```
fungsi SA(instance, budget, seed):
    cur ← PERMUTASI_AWAL(seed); f_cur ← EVALUATE(cur)
    T0 ← rata-rata |Δ| positif dari 100 move acak dari cur   ▷ evaluasinya dihitung dalam budget
    c  ← 0.001^(1 / sisa budget)                              ▷ suhu akhir ≈ 0.001·T0
    T ← T0
    selama budget tersisa:
        q ← APPLY(cur, MOVE_ACAK())                           ▷ jenis move acak, lalu posisi acak
        Δ ← EVALUATE(q) − f_cur
        jika Δ ≥ 0 atau RANDOM() < exp(Δ/T): (cur, f_cur) ← (q, f_cur + Δ)
        T ← c · T
    kembalikan solusi terbaik yang pernah dievaluasi
```

Tanpa reheating. Laju pendinginan diturunkan dari budget agar seluruh budget terpakai untuk pencarian (CHANGELOG no. 7).

### 2.4.3 Genetic Algorithm (GA)

```
fungsi GA(instance, budget, seed):
    P ← [PERMUTASI_AWAL(seed)] + 99 permutasi acak; evaluasi semuanya
    selama budget tersisa:
        P' ← 2 individu terbaik dari P                       ▷ elitisme, tanpa evaluasi ulang
        selama |P'| < 100:
            a ← TOURNAMENT(P, k=3); b ← TOURNAMENT(P, k=3)
            anak ← ORDER_CROSSOVER(a, b)
            dengan peluang 0.2: anak ← APPLY(anak, MOVE_ACAK())  ▷ mutasi dari move set bersama
            evaluasi anak; tambahkan ke P'
        P ← P'
    kembalikan solusi terbaik yang pernah dievaluasi
```

Order Crossover (OX) menyalin segmen a[i..j] di posisinya, lalu mengisi sisanya dengan urutan b mulai setelah posisi j. Populasi awal **tidak** di-*seed* dengan Greedy (CHANGELOG no. 8).

## 2.5 Pembanding: Greedy dan Exact

**Greedy** (baseline, deterministik, dihitung sebagai 1 evaluasi):

```
fungsi GREEDY(instance):
    t ← 0; prev ← Depot; rute ← []
    ulangi:
        kandidat ← node belum dikunjungi yang masih muat (termasuk kembali ke Depot)
        jika kandidat kosong: keluar
        pilih i ∈ kandidat dengan rasio Prize_i(t + d[prev,i]/v) / (d[prev,i]/v + w) tertinggi
        tambahkan i ke rute; perbarui t dan prev
    kembalikan rute
```

**Exact** (referensi optimum, hanya untuk n ≤ 9 node termasuk Depot): enumerasi depth-first semua urutan kunjungan. Cabang dipangkas begitu node berikutnya tidak muat dalam Batas waktu misi. DP *earliest-arrival* tidak dipakai, karena Prize bergantung pada waktu tiba sehingga tiba paling awal di sebuah subset belum tentu optimal. Setiap permutasi hasil decoding adalah salah satu urutan yang dienumerasi, sehingga hasil Exact adalah optimum. Di eksperimen ini, Exact dijalankan untuk n=6.

## 2.6 Aturan keadilan eksperimen

Aturan ini ditetapkan **sebelum** eksperimen dijalankan:

1. **Budget evaluasi fitness sama** untuk HC, SA, dan GA dalam satu instance: 20.000 untuk n ≤ 15 dan 50.000 untuk n ≥ 25. Penghitung evaluasi menghentikan solver tepat saat budget habis. Runtime dicatat terpisah.
2. **Solusi awal sama per seed.** Permutasi awal diturunkan dari seed lewat satu fungsi bersama. Permutasi ini menjadi titik awal HC, titik awal SA, dan individu pertama GA. Keacakan internal setiap algoritma memakai aliran acak terpisah.
3. **Move set sama** untuk neighbourhood HC, tetangga SA, dan mutasi GA.
4. **Tanpa seeding greedy** dan **tanpa tuning parameter** untuk memenangkan algoritma tertentu. Parameter algoritma tercatat di `DATA_PROVENANCE.md`.
5. **30 seed** per (algoritma, n, Skenario tahun). Perbandingan antar-algoritma diuji dengan **Wilcoxon signed-rank berpasangan per seed**, dan p-value dikoreksi dengan metode **Holm** dalam setiap (Skenario tahun, n).
6. **Batas waktu misi dikalibrasi**, bukan dipilih bebas. Greedy pada n=38 skenario 2026 memilih nilai terkecil dari {24, 48, 72, 120} jam yang membuat 40–60% node terkunjungi. Hasilnya 72 jam (`results/tables/instances.md`).
7. **Reproducible.** Satu perintah (`python -m src.experiments.run_all`) menghasilkan ulang semua tabel, gambar, rute, dan uji statistik. Setiap run hanya bergantung pada (instance, algoritma, seed).

<!-- FIRMS: isi setelah #6 -->

_(Subbab 2.7 Instance Klaster hotspot FIRMS: sumber snapshot VIIRS, filter confidence dan bounding box, k-means k ∈ {50, 100, 200}, Risiko klaster = Σ FRP → log1p → min-max, decay konstan g0, dan budget 100.000.)_
