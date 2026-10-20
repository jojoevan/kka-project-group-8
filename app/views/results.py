"""Page 3: the saved comparison (results/), the same numbers as the report."""
import pandas as pd
import streamlit as st

from app import charts
from app.core import ALGORITHMS, SCENARIOS, SIZES, fmt, raw_runs, readme_section, rows_height, styled, table, term


def _summary(scenario):
    s = table("summary"); s = s[s.scenario.astype(str) == scenario]
    wide = s.pivot_table(index="n", columns="algorithm", values="mean")
    out = wide[[a for a in ALGORITHMS if a in wide]].copy()
    out.insert(0, "Best-known", s.groupby("n").best_known.first())
    if "Exact" in wide: out["Exact"] = wide["Exact"]
    out["rata-rata tertinggi"] = [" / ".join(a for a in ALGORITHMS if abs(row[a] - row[list(ALGORITHMS)].max()) < 5e-4)
                                  for _, row in out.iterrows()]
    if "Exact" in out:  # text column: Exact only ran for n = 6, other rows show a dash
        out["Exact"] = [fmt(v, ".3f") for v in out["Exact"]]
    return out.reset_index()


def render():
    st.title("Hasil perbandingan")
    st.markdown("Semua angka di halaman ini dibaca dari `results/` (eksperimen penuh: 30 seed per algoritma, "
                "Budget evaluasi 20.000 untuk n ≤ 15 dan 50.000 untuk n ≥ 25), sama dengan yang dipakai laporan.")
    scenario = st.radio("Skenario tahun", SCENARIOS, index=1, horizontal=True, help=term("Skenario tahun"))

    st.subheader("Fitness rata-rata 30 seed", help=term("Fitness"))
    s = _summary(scenario)
    st.dataframe(styled(s, {c: ".3f" for c in s.columns if c not in ("n", "Exact", "rata-rata tertinggi")})
                 .highlight_max(subset=[a for a in ALGORITHMS if a in s], axis=1, color="#e3f1dc"),
                 hide_index=True, width="stretch", height=rows_height(len(s)))
    st.caption("Sel hijau: rata-rata tertinggi di antara Greedy, HC, SA, dan GA. Exact hanya dijalankan untuk n = 6.")

    sc = table("scalability"); sc = sc[sc.scenario.astype(str) == scenario]
    a, b = st.columns(2, gap="large")
    a.plotly_chart(charts.lines(sc, "n", "quality_mean_pct", "algorithm", "n (jumlah node)",
                                "Kualitas rata-rata (% dari Best-known)", "Kualitas vs ukuran instance"),
                   width="stretch")
    b.plotly_chart(charts.lines(sc, "n", "runtime_mean_s", "algorithm", "n (jumlah node)", "Runtime rata-rata (detik)",
                                "Runtime vs ukuran instance"), width="stretch")

    _spread(scenario)

    st.subheader("Observasi")
    st.caption("Dari README. **[Data]** terbaca langsung dari hasil; **[Hipotesis]** belum diuji tersendiri.")
    st.markdown(readme_section("Observasi", start_marker="1. "))
    with st.expander("Batasan interpretasi"):
        st.markdown(readme_section("Batasan interpretasi"))


@st.fragment
def _spread(scenario):
    """Per-n part of the page; moving the n slider reruns only this part."""
    st.subheader("Sebaran 30 seed")
    n = st.select_slider("n (jumlah node, termasuk Depot)", SIZES, value=38)
    runs = raw_runs(); runs = runs[(runs.scenario.astype(str) == scenario) & (runs.n == n)
                                   & runs.algorithm.isin(ALGORITHMS)]
    ref = table("summary"); ref = ref[(ref.scenario.astype(str) == scenario) & (ref.n == n)].best_known.iloc[0]
    left, right = st.columns(2, gap="large")
    left.plotly_chart(charts.boxplot(runs, title=f"Fitness per seed, {scenario} n = {n}", reference=ref),
                      width="stretch")
    conv = table("convergence"); conv = conv[(conv.scenario.astype(str) == scenario) & (conv.n == n)]
    if len(conv):
        series = {alg: (g.evals.tolist(), g["mean"].tolist()) for alg, g in conv.groupby("algorithm")}
        band = {alg: g["std"].tolist() for alg, g in conv.groupby("algorithm")}
        right.plotly_chart(charts.convergence(series, f"Konvergensi rata-rata ± simpangan baku, n = {n}", band=band),
                           width="stretch")
    else:
        right.info("Kurva konvergensi rata-rata disimpan untuk n = 25 dan n = 38 saja.")

    st.subheader("Uji Wilcoxon signed-rank (koreksi Holm)")
    st.caption("Membandingkan dua algoritma pada seed yang sama. *menang* = jumlah seed di mana algoritma itu lebih "
               "baik. Signifikan jika p Holm < 0,05.")
    w = table("wilcoxon_holm"); w = w[(w.scenario.astype(str) == scenario) & (w.n == n)]
    w = pd.DataFrame({"A": w.algorithm_a, "B": w.algorithm_b, "median A": w.median_a.map(lambda v: fmt(v, ".3f")),
                      "median B": w.median_b.map(lambda v: fmt(v, ".3f")), "A menang": w.wins_a, "B menang": w.wins_b,
                      "p Holm": w.p_holm.map(lambda v: fmt(v, ".4g")),
                      "signifikan": w["significant_0.05"].map({True: "ya", False: "tidak"})})
    st.dataframe(w, hide_index=True, width="stretch", height=rows_height(len(w)))

    if n == 6:
        st.subheader("Optimality gap terhadap Exact (n = 6)")
        g = table("optimality_gap"); g = g[g.scenario.astype(str) == scenario]
        g = g[["algorithm", "exact", "mean_fitness", "gap_mean_pct", "gap_max_pct", "optimal_rate"]].rename(
            columns={"algorithm": "algoritma", "mean_fitness": "rata-rata", "gap_mean_pct": "gap rata-rata (%)",
                     "gap_max_pct": "gap maks (%)", "optimal_rate": "fraksi seed optimal"})
        st.dataframe(styled(g, {"exact": ".3f", "rata-rata": ".3f", "gap rata-rata (%)": ".2f", "gap maks (%)": ".2f",
                                "fraksi seed optimal": ".2f"}), hide_index=True, width="stretch",
                     height=rows_height(len(g)))
