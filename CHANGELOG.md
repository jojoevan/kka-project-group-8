# CHANGELOG Keputusan Pemodelan

Catatan keputusan pemodelan yang **direvisi** dari rencana awal (PLAN) atau dari prototipe pertama, beserta alasannya. Urutan mengikuti tiket pengerjaan (#2–#7). Istilah mengikuti `GLOSSARY.md`.

## 1. Risiko dinormalisasi global atas 38 provinsi (#2)

- **Sebelumnya**: Risiko di-min-max ulang di setiap instance. Node dengan Risiko terendah di instance mana pun selalu bernilai 0. Di instance 6 provinsi, Jambi mendapat Risiko 0 padahal sedang ada kebakaran aktif.
- **Sekarang**: Risiko dihitung dan dinormalisasi **sekali** atas 38 provinsi di `src/data_prep.py`, per Skenario tahun. Pembangun instance memakai nilainya apa adanya. Risiko sebuah provinsi sama di n=6 dan n=38.
- **Alasan**: Risiko harus menjadi sifat provinsi, bukan sifat instance. Hasilnya, Jambi kini mendapat Risiko 2026 sebesar 0.501 (`reports/data_quality.md`).

## 2. Komponen operasional hanya untuk Skenario tahun 2026 (#2)

- **Sebelumnya**: rencana awal memakai 9 skenario tahun (2018–2026).
- **Sekarang**: hanya dua Skenario tahun, yaitu 2019 (tahun ekstrem) dan 2026 (tahun berjalan). Komponen `ops` hanya dipakai di 2026, karena CSV operasional adalah snapshot 2026-10-19.
- **Alasan**: tenggat ±12 jam, dan dua skenario sudah cukup untuk membandingkan tahun ekstrem dengan tahun berjalan.

## 3. Batas waktu misi dikalibrasi (#3)

- **Sebelumnya**: 72 jam ditetapkan tanpa kalibrasi. Di prototipe, instance 6 provinsi selesai dalam ±22 jam, sehingga masalahnya merosot menjadi TSP dan semua algoritma seri dengan Exact.
- **Sekarang**: `python -m src.calibration` menjalankan Greedy pada n=38 skenario 2026 untuk kandidat {24, 48, 72, 120} jam dan memilih nilai terkecil yang membuat 40–60% node terkunjungi. Hasilnya tetap 72 jam (21 dari 37 node kandidat terkunjungi, `results/tables/instances.md`), dan kali ini nilainya berdasar kalibrasi.
- **Konsekuensi**: pada n=6 dan n=10, batas ini tetap tidak mengikat (`results/tables/instances.md`). Pemilik proyek menerima hal ini, dan hal ini dicatat di `results/logs/run_all.log`. Instance n=6 tetap berguna sebagai validasi terhadap Exact.

## 4. Decoder "lewati lalu lanjut" (#3)

- **Sebelumnya**: PLAN A4 membuang seluruh ekor permutasi setelah node pertama yang tidak muat, dan mengusulkan tie-breaker ε untuk mengatasi plateau.
- **Sekarang**: Node dilewati dibuang, lalu node berikutnya dalam urutan tetap dicoba (`Instance.evaluate`). Tie-breaker ε tidak dipakai.
- **Alasan**: plateau di ekor permutasi berkurang tanpa mengubah fungsi tujuan, dan perilakunya masuk akal secara operasional: armada tetap mengunjungi node dekat yang masih muat.

## 5. Move set bersama untuk HC, SA, dan GA (#3)

- **Sebelumnya**: SA di prototipe hanya memakai move swap, sedangkan HC memakai swap, insert, dan 2-opt.
- **Sekarang**: ketiganya memakai move set yang sama, yaitu swap, relocate dua arah, dan pembalikan 2-opt (`src/algorithms/common.py`). HC menelusuri seluruh neighbourhood, SA mengambil satu tetangga acak, dan mutasi GA mengambil satu move acak.
- **Alasan**: keadilan perbandingan. Perbedaan hasil harus berasal dari strategi pencarian, bukan dari operator.

## 6. HC dengan restart sampai budget habis (#3)

- **Sebelumnya**: HC memakai jumlah restart tetap, sehingga budget evaluasinya tidak setara dengan SA dan GA.
- **Sekarang**: HC restart dari permutasi acak sampai budget evaluasi habis. Hasil restart pertama dicatat sebagai *single-start* (`results/raw/runs.csv`, kolom `hc_single_start_fitness`). Neighbourhood tidak di-sampling pada n besar.
- **Alasan**: budget setara. Biaya per langkah yang O(n²) sengaja dipertahankan dan dilaporkan sebagai temuan.

## 7. Pendinginan SA diturunkan dari budget (#3)

- **Sebelumnya**: PLAN A4 memakai laju pendinginan tetap c ≈ 0,995. Setelah 2.000 langkah suhunya tinggal 0,995^2000 ≈ 4,5·10⁻⁵·T0, jadi lebih dari 95% budget 50.000 terbuang untuk pencarian yang sudah beku.
- **Sekarang**: c = 0,001^(1/sisa budget), sehingga suhu akhir ≈ 0,001·T0 tepat saat budget habis. T0 dikalibrasi dari rata-rata |Δ| positif 100 move acak. Evaluasi kalibrasi ini ikut dihitung dalam budget.
- **Alasan**: jadwal suhu harus memanfaatkan seluruh budget yang sama dengan algoritma lain.

## 8. GA tanpa seeding greedy (#3)

- **Sebelumnya**: populasi awal GA di prototipe di-*seed* dengan solusi Greedy.
- **Sekarang**: populasi awal acak. Individu pertama sama dengan solusi awal HC dan SA untuk seed yang sama.
- **Alasan**: seeding memberi GA titik awal yang tidak dimiliki HC dan SA. Varian memetic/seeded di luar cakupan.

## 9. Exact hanya untuk n ≤ 9 (#3)

- **Sebelumnya**: PLAN menyebut n ≤ 9–10.
- **Sekarang**: maksimum 9 node termasuk Depot. Karena itu optimality gap hanya dihitung untuk n=6 (`results/tables/optimality_gap.md`).
- **Alasan**: enumerasi urutan berkembang faktorial, dan n=10 sudah tidak praktis dalam tenggat.

## 10. Klaster hotspot FIRMS menggantikan data sintetis (ADR-0001)

- **Sebelumnya**: PLAN Part B mengusulkan generator instance sintetis untuk uji skalabilitas.
- **Sekarang**: instance besar (k ∈ {50, 100, 200}) dibangun dari Klaster hotspot NASA FIRMS VIIRS (#6). Generator sintetis tidak dibangun.
- **Alasan**: semua instance tetap berasal dari data nyata, waktunya selaras dengan snapshot operasional 2026-10-19, dan jarak antar-node masuk akal untuk helikopter. Lihat `docs/adr/0001-firms-clusters-instead-of-synthetic.md`.

<!-- FIRMS: isi setelah #6 -->

_(Catat di sini keputusan FIRMS yang direvisi saat implementasi #6, misalnya tanggal snapshot, perubahan filter, atau nilai Batas waktu misi FIRMS hasil kalibrasi.)_

## 11. Dokumentasi berbahasa Indonesia (#1, #7)

- **Sebelumnya**: PLAN menetapkan kode, komentar, dan README berbahasa Inggris.
- **Sekarang**: README, dokumentasi, label gambar, dan tabel berbahasa Indonesia. Nama di kode tetap berbahasa Inggris.
- **Alasan**: penilai dan laporan berbahasa Indonesia.

## 12. Angka dokumentasi diambil dari hasil tersimpan (#7)

- **Sekarang**: tabel provenance, ringkasan hasil di README, tabel diagnostik algoritma, dan daftar gambar diisi oleh `python -m src.docs_gen` dari `config.yaml` dan `results/`. Tes `tests/test_docs_gen.py` gagal jika dokumen tidak lagi cocok dengan hasil tersimpan.
- **Alasan**: angka di dokumen tidak boleh ditulis ulang manual tanpa sumber.
