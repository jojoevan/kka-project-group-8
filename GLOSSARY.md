# Perutean Armada Udara Karhutla

Model keputusan untuk memilih dan mengurutkan wilayah kebakaran hutan dan lahan (karhutla) yang dikunjungi satu armada udara dalam batas waktu misi, agar kerusakan yang dicegah sebesar mungkin.

## Wilayah & misi

**Node**:
Satu lokasi kandidat kunjungan. Bisa berupa provinsi atau klaster hotspot.
_Hindari_: kota, titik, target

**Klaster hotspot**:
Node yang berupa pusat kelompok titik panas satelit (NASA FIRMS) yang berdekatan.
_Hindari_: titik api, fire spot (istilah ini sudah dipakai di dataset operasional)

**Depot**:
Pangkalan udara tempat armada berangkat dan wajib kembali sebelum batas waktu misi habis.
_Hindari_: base, markas, posko

**Batas waktu misi** (`T_max`):
Total jam yang tersedia dari keberangkatan sampai kembali ke depot, termasuk terbang dan waktu tinggal.
_Hindari_: budget (bisa tertukar dengan budget evaluasi algoritma)

**Instance**:
Satu masalah konkret: himpunan node, depot, risiko, dan parameter misi.
_Hindari_: kasus, dataset

**Skenario tahun**:
Varian instance provinsi yang komponen risiko tahun berjalannya diambil dari satu tahun tertentu.

## Nilai

**Risiko**:
Nilai kepentingan sebuah provinsi dalam rentang [0,1], dinormalisasi sekali atas seluruh 38 provinsi. Nilainya sama di instance mana pun.
_Hindari_: bobot, prioritas

**Kunjungan**:
Satu kali sortie pemadaman (water-bombing/OMC) di sebuah node selama waktu tinggal (dwell). Setiap node paling banyak dikunjungi sekali.
_Hindari_: singgah, servis, patroli

**Prize**:
Proksi kerusakan yang dicegah jika sebuah node dikunjungi. Nilainya adalah risiko node yang meluruh secara eksponensial terhadap waktu tiba, karena api terus meluas. Ini asumsi pemodelan, bukan ukuran resmi.
_Hindari_: reward, skor, nilai

**Node dilewati**:
Node dalam urutan kandidat yang tidak muat dalam sisa waktu misi (termasuk waktu kembali ke depot). Node ini dibuang, lalu node berikutnya dalam urutan tetap dicoba.
_Hindari_: node gagal, node infeasible
