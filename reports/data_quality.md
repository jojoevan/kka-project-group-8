# Laporan Kualitas Data

- Jumlah baris provinsi setelah baris Total dibuang: **38** (harapan 38).
- Nilai xlsx 2026 adalah data **parsial** sampai 2026-10-19, bukan total setahun penuh.
- Koordinat ibu kota provinsi adalah asumsi geografi publik (ASSUMED), bukan bagian dataset, dan perlu diverifikasi.
- Kolom operasional yang kosong dibiarkan kosong di file operasional bersih. Untuk Risiko, provinsi tanpa data operasional mendapat `ops_norm=0` dengan penanda `has_ops=False` (tanpa imputasi).
- Kategori PM2.5 berbentuk rentang memakai tingkat terburuk (maksimum). Visibilitas memakai angka minimum di dalam teks.
- Risiko dinormalisasi min-max **sekali atas 38 provinsi** per skenario tahun, sehingga nilainya sama di instance mana pun. Komponen operasional hanya dipakai untuk skenario 2026.

## Checksum baris Total xlsx

|   tahun |   jumlah_provinsi_ha |   baris_total_ha |   selisih_relatif |
|--------:|---------------------:|-----------------:|------------------:|
|    2018 |            5.293e+05 |        5.293e+05 |         2.2e-16   |
|    2019 |            1.649e+06 |        1.649e+06 |         0         |
|    2020 |            2.969e+05 |        2.969e+05 |         0         |
|    2021 |            3.589e+05 |        3.589e+05 |         0         |
|    2022 |            2.049e+05 |        2.049e+05 |         0         |
|    2023 |            1.161e+06 |        1.161e+06 |         2.005e-16 |
|    2024 |            3.768e+05 |        3.768e+05 |         1.545e-16 |
|    2025 |            3.596e+05 |        3.596e+05 |         0         |
|    2026 |            2.02e+05  |        2.02e+05  |         1.441e-16 |

Selisih relatif di atas 1% dicatat sebagai peringatan; pipeline tidak dihentikan.

## Luas terbakar indikatif (CSV) vs xlsx 2026

| Provinsi           |   xlsx_2026_ha |   indikatif_csv_ha |   selisih_ha |   selisih_absolut_ha |
|:-------------------|---------------:|-------------------:|-------------:|---------------------:|
| Jambi              |    379         |       4853         | 4474         |         4474         |
| Kalimantan Barat   |      3.831e+04 |          3.831e+04 |    0.03      |            0.03      |
| Kalimantan Selatan |   8020         |       8020         |    0         |            0         |
| Kalimantan Tengah  |   7634         |          2.41e+04  |    1.647e+04 |            1.647e+04 |
| Riau               |      1.574e+04 |          2.07e+04  | 4957         |         4957         |
| Sumatera Selatan   |   1926         |       1926         |    0         |            0         |

Selisih dilaporkan apa adanya, tidak direkonsiliasi. Perbedaan tanggal laporan atau definisi dapat menjelaskan sebagian selisih.

## Inkonsistensi Riau

Riau mencatat Total Hotspot = 0, tetapi Fire Spot = 3, kualitas udara "Sedang - Berbahaya", dan luas terbakar indikatif 20,696.00 ha. Karena itu jumlah hotspot **tidak pernah** dipakai sendirian sebagai ukuran keparahan.

## Risiko provinsi operasional

| Provinsi           |   historis |   tahun_berjalan_2026 |   operasional |   Risiko_2026 |   Risiko_2019 |
|:-------------------|-----------:|----------------------:|--------------:|--------------:|--------------:|
| Kalimantan Barat   |     0.8982 |                1      |        1      |        1      |        0.9436 |
| Kalimantan Tengah  |     0.8145 |                0.8472 |        0.817  |        0.8601 |        0.9199 |
| Sumatera Selatan   |     0.8146 |                0.7167 |        0.6128 |        0.7555 |        0.922  |
| Riau               |     0.8205 |                0.9157 |        0.2551 |        0.7083 |        0.8799 |
| Kalimantan Selatan |     0.8092 |                0.8518 |        0      |        0.6038 |        0.8878 |
| Jambi              |     0.6928 |                0.5629 |        0.1155 |        0.501  |        0.7883 |

## Keterbatasan

- CSV hanya berisi snapshot operasional enam provinsi; ketiadaan baris bukan bukti tidak ada kebakaran.
- Keparahan operasional yang dinormalisasi adalah proksi pemodelan dari kolom yang tersedia, bukan indeks bahaya resmi.
- Jarak antar-ibu kota, kecepatan 200 km/jam, faktor detour 1,15, dan waktu tinggal adalah asumsi pemodelan.
