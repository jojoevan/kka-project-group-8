# Klaster hotspot FIRMS menggantikan generator instance sintetis

Instance provinsi (maks. 38 node) terlalu kecil dan secara geografis kurang realistis untuk menguji skalabilitas algoritma. PLAN awal (Part B) mengusulkan generator data sintetis. Kami memilih membangun instance besar (n ∈ {50, 100, 200}) dari data hotspot NASA FIRMS VIIRS 7 hari terakhir di Sumatra dan Kalimantan. Hotspot diklaster dengan k-means, dan risiko klaster dihitung dari Σ FRP. Alasannya, semua instance tetap berasal dari data nyata, waktunya selaras dengan snapshot operasional 2026-10-19, dan jarak antar-node masuk akal untuk helikopter.

## Konsekuensi

- Klaster tidak punya data operasional, sehingga laju decay-nya konstan (`g = g0`), berbeda dari instance provinsi.
- Instance bergantung pada snapshot unduhan. File mentahnya harus disimpan di repo agar hasil bisa direproduksi, karena feed 7 hari FIRMS terus bergeser.
- Generator sintetis (PLAN Part B2) tidak dibangun.
