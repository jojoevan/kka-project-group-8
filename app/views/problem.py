"""Page 1: the problem itself — Depot, Node, Risiko, Prize decay, and a hand-built route."""
import math

import pandas as pd
import streamlit as st

from app import charts
from app.core import SCENARIOS, config, coords, fmt, features, instance, rows_height, run, styled, term


def positions():
    c = coords(); return {p: (lon, lat) for p, lon, lat in zip(c.Provinsi, c.lon, c.lat)}


def route_table(route):
    """Kunjungan of a route as a formatted table."""
    df = pd.DataFrame([{"urutan": k, "provinsi": r["province"], "tiba (jam)": r["arrival_h"], "Risiko": r["risk"],
                        "Prize": r["prize"]} for k, r in enumerate(route, 1)])
    return styled(df, {"tiba (jam)": ".2f", "Risiko": ".3f", "Prize": ".3f"})


@st.fragment
def _risk_section(cfg):
    st.header("1. Setiap provinsi punya Risiko", help=term("Risiko"))
    scenario = st.radio("Skenario tahun", SCENARIOS, index=1, horizontal=True, help=term("Skenario tahun"))
    f = features().merge(coords(), on="Provinsi")
    w = cfg["weights"]
    left, right = st.columns([5, 2], gap="large")
    with left:
        ops = f.ops_norm.to_numpy() if scenario == "2026" else None
        st.plotly_chart(charts.risk_map(f.Provinsi.tolist(), f.lat.to_numpy(), f.lon.to_numpy(),
                                        f[f"risk_{scenario}"].to_numpy(), cfg["depot"], ops,
                                        f"Risiko 38 provinsi, Skenario tahun {scenario}"), width="stretch")
    with right:
        st.markdown(
            f"Risiko dalam [0, 1] adalah gabungan tiga komponen:\n\n"
            f"- **{fmt(w['hist'] * 100, 'g')}%** luas terbakar historis 2018–2025\n"
            f"- **{fmt(w['cur'] * 100, 'g')}%** luas terbakar tahun {scenario}\n"
            f"- **{fmt(w['ops'] * 100, 'g')}%** keparahan operasional (*ops*, hanya snapshot 2026, 6 provinsi)\n\n"
            "Ukuran dan warna titik menunjukkan Risiko. Arahkan kursor ke titik untuk melihat angkanya.")
        top = f.nlargest(8, f"risk_{scenario}")[["Provinsi", f"risk_{scenario}"]]
        st.dataframe(top.rename(columns={f"risk_{scenario}": "Risiko"}), hide_index=True, width="stretch",
                     height=rows_height(len(top)),
                     column_config={"Provinsi": st.column_config.TextColumn(width="medium"),
                                    "Risiko": st.column_config.ProgressColumn(min_value=0, max_value=1,
                                                                              format="%.2f", width="small")})


@st.fragment
def _decay_section(cfg):
    st.header("2. Prize meluruh terhadap waktu tiba", help=term("Prize"))
    st.latex(r"\text{Prize}_i = \text{Risiko}_i \cdot e^{-g_i\, t_i}, \qquad g_i = g_0\,(1 + \kappa \cdot ops_i)")
    a, b = st.columns([1, 3], gap="large")
    with a:
        g0 = st.slider("g0 (laju peluruhan dasar per jam)", 0.0, 0.05, float(cfg["decay_g0"]), 0.001, format="%.3f")
        kappa = st.slider("κ (pengaruh keparahan operasional)", 0.0, 3.0, float(cfg["decay_kappa"]), 0.1)
        risk = st.slider("Risiko node", 0.1, 1.0, 1.0, 0.05)
        if g0 > 0:
            st.info(f"Dengan g0 = {fmt(g0, 'g')}, Prize node tanpa data operasional tinggal separuh setelah "
                    f"**{fmt(math.log(2) / g0, '.0f')} jam**.")
        else:
            st.info("g0 = 0: Prize tidak meluruh, jadi urutan kunjungan tidak berpengaruh.")
    with b:
        st.plotly_chart(charts.prize_decay(cfg["time_limit_hours"], g0, kappa, risk, [0, 0.5, 1]), width="stretch")
    st.caption("Prize adalah proksi kerusakan yang dicegah, bukan ukuran resmi. Bentuk eksponensial, g0, dan κ "
               "adalah asumsi pemodelan.")


@st.fragment
def _manual_route_section():
    st.header("3. Coba susun rute sendiri")
    st.markdown(
        "Pakai instance kecil n=6 (Depot + 5 provinsi yang punya data operasional). Pilih provinsi **sesuai urutan "
        "kunjungan**. Provinsi yang tidak muat lagi dalam Batas waktu misi (termasuk waktu kembali ke Depot) "
        "menjadi **Node dilewati**, lalu provinsi berikutnya tetap dicoba. Ini cara yang sama dipakai semua "
        "algoritma untuk menilai sebuah urutan.")
    order_box = st.container()
    a, b, c = st.columns([2, 1, 1], gap="medium")
    t_max = a.slider("Batas waktu misi (jam)", 6, 72, 24, 1, key="manual_tmax",
                     help="Turunkan supaya tidak semua provinsi muat.")
    inst = instance(6, "2026", None, t_max)
    candidates = inst.names[1:]
    order = order_box.multiselect("Urutan kunjungan (klik sesuai urutan)", candidates, default=candidates,
                                  help=term("Kunjungan"))
    perm = [inst.names.index(p) for p in order]
    detail = inst.evaluate(perm, details=True)
    exact = run("Exact", 6, "2026", None, t_max, 1, 0)
    skipped = [s for s in detail["skipped"] if s["province"] in order]
    b.metric("Fitness rute Anda", fmt(detail["fitness"], ".3f"), help=term("Fitness"), border=True, height="stretch",
             delta=f"{fmt(100 * detail['fitness'] / exact['best_fitness'], '.1f')}% dari optimum"
             if exact["best_fitness"] > 0 else None, delta_color="off")
    c.metric("Optimum (Exact)", fmt(exact["best_fitness"], ".3f"), border=True, height="stretch",
             help="Dihitung dengan mencoba semua urutan (hanya mungkin untuk n kecil).")

    left, right = st.columns([3, 2], gap="large")
    with left:
        st.plotly_chart(charts.route_map(positions(), inst.names[0], [("", detail["route"], skipped)],
                                         title=f"Waktu misi {fmt(detail['mission_time_h'], '.1f')} dari {t_max} jam",
                                         height=380), width="stretch")
    with right:
        st.caption("Rute optimum: Depot → " + " → ".join(r["province"] for r in exact["best_route"]["route"])
                   + " → Depot")
        if detail["route"]:
            st.dataframe(route_table(detail["route"]), hide_index=True, width="stretch",
                         height=rows_height(len(detail["route"])))
        if skipped: st.warning("Node dilewati (tidak muat waktu): " + ", ".join(s["province"] for s in skipped))
        not_chosen = [p for p in candidates if p not in order]
        if not_chosen: st.caption("Tidak dipilih: " + ", ".join(not_chosen))


def render():
    cfg = config()
    st.title("Perutean Armada Udara Karhutla")
    st.markdown(
        "Satu armada udara pemadam kebakaran hutan dan lahan (helikopter *water-bombing* atau pesawat OMC) "
        f"berangkat dari **Depot** di {cfg['depot']}. Armada itu harus memilih **provinsi mana** yang didatangi "
        "**dan dalam urutan apa**, lalu kembali ke Depot sebelum **Batas waktu misi** habis. "
        "Semakin lambat sebuah provinsi didatangi, semakin kecil kerusakan yang masih bisa dicegah (**Prize**), "
        "karena api terus meluas.")
    c = st.columns(4)
    c[0].metric("Depot", cfg["depot"], help=term("Depot"), border=True)
    c[1].metric("Node (provinsi)", "38", help=term("Node"), border=True)
    c[2].metric("Batas waktu misi (jam)", fmt(cfg["time_limit_hours"], "g"), help=term("Batas waktu misi"),
                border=True)
    c[3].metric("Kecepatan (km/jam)", fmt(cfg["speed_kmh"], "g"), border=True,
                help=f"Jarak = Haversine × {fmt(cfg['detour_factor'], 'g')} (memutar).")
    st.caption(f"Setiap Kunjungan menghabiskan waktu tinggal {fmt(cfg['dwell_hours'], 'g')} jam. " + term("Kunjungan"))

    _risk_section(cfg)
    _decay_section(cfg)
    _manual_route_section()

    st.header("4. Kenapa butuh algoritma pencarian?")
    st.markdown(
        "Algoritma tidak hanya mengurutkan seperti TSP, tetapi juga **memilih** node mana yang muat. "
        "Jumlah urutan yang mungkin adalah (n−1)!:")
    sizes = (6, 10, 15, 25, 38)
    st.dataframe(pd.DataFrame({"n (termasuk Depot)": sizes,
                               "jumlah urutan": [fmt(float(math.factorial(n - 1)), ".3g") for n in sizes]}),
                 hide_index=True, height=rows_height(len(sizes)))
    st.markdown(
        "Untuk n=6, semua urutan masih bisa dicoba (**Exact**). Untuk n besar tidak mungkin, sehingga proyek ini "
        "membandingkan tiga metode *local search*/metaheuristik (**HC**, **SA**, **GA**) dengan **Greedy** sebagai "
        "baseline. Lihat cara kerjanya di halaman **Coba sendiri**.")
