# Apakah peringkat algoritma instance provinsi tetap berlaku pada instance FIRMS?

Acuan: instance provinsi terbesar, skenario 2026 n=38: **SA > HC > Greedy > GA** (urut rata-rata fitness 30 seed; `=` berarti seri dalam toleransi relatif 1e-09).

- FIRMS k=50: SA > Greedy > HC > GA. Peringkat provinsi **tidak tetap berlaku**: Greedy di atas HC (FIRMS: signifikan; provinsi: tidak signifikan, Wilcoxon-Holm 0,05).
- FIRMS k=100: SA > Greedy > GA > HC. Peringkat provinsi **tidak tetap berlaku**: GA di atas HC (FIRMS: signifikan; provinsi: signifikan, Wilcoxon-Holm 0,05); Greedy di atas HC (FIRMS: signifikan; provinsi: tidak signifikan, Wilcoxon-Holm 0,05).
- FIRMS k=200: SA > Greedy > GA > HC. Peringkat provinsi **tidak tetap berlaku**: GA di atas HC (FIRMS: signifikan; provinsi: signifikan, Wilcoxon-Holm 0,05); Greedy di atas HC (FIRMS: signifikan; provinsi: tidak signifikan, Wilcoxon-Holm 0,05).

Kesimpulan: peringkat provinsi **tidak tetap berlaku** sepenuhnya pada instance FIRMS (lihat pasangan yang bertukar di atas).

| instance            | peringkat (rata-rata fitness, terbaik dulu; = berarti seri)   |
|:--------------------|:--------------------------------------------------------------|
| provinsi 2019, n=6  | GA = Greedy = HC = SA                                         |
| provinsi 2019, n=10 | GA = HC = SA > Greedy                                         |
| provinsi 2019, n=15 | HC > SA > Greedy > GA                                         |
| provinsi 2019, n=25 | HC > SA > Greedy > GA                                         |
| provinsi 2019, n=38 | SA > Greedy > HC > GA                                         |
| provinsi 2026, n=6  | GA = HC = SA > Greedy                                         |
| provinsi 2026, n=10 | GA = HC = SA > Greedy                                         |
| provinsi 2026, n=15 | HC = SA > GA > Greedy                                         |
| provinsi 2026, n=25 | HC > SA > Greedy > GA                                         |
| provinsi 2026, n=38 | SA > HC > Greedy > GA                                         |
| FIRMS k=50 (n=51)   | SA > Greedy > HC > GA                                         |
| FIRMS k=100 (n=101) | SA > Greedy > GA > HC                                         |
| FIRMS k=200 (n=201) | SA > Greedy > GA > HC                                         |
