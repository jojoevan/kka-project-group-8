"""Page 4: the case-study route (n = 38, 2026), the decay ablation, and the sensitivity sweep."""
import plotly.graph_objects as go
import streamlit as st

from app import charts
from app.core import COLORS, config, fmt, instance, saved_route, table, term
from app.views.problem import positions


def _route_from_order(inst, column):
    """Route detail of the ablation order in `column` (position_decay / position_static), scored with decay."""
    o = table("decay_ablation_order").dropna(subset=[column]).sort_values(column)
    return inst.evaluate([inst.names.index(p) for p in o.province], details=True)


def render():
    cs = config()["analysis"]["case_study"]; n, scenario = int(cs["n"]), str(cs["scenario"])
    inst = instance(n, scenario)
    st.title("🔍 Studi kasus & ablasi decay")

    r = saved_route(f"best_route_{scenario}_n{n}")
    st.subheader(f"Rute terbaik: {r['algorithm']} seed {r['seed']}, Skenario tahun {scenario}, n = {n}")
    c = st.columns(4)
    c[0].metric("Fitness", fmt(r["fitness"], ".3f"), help=term("Fitness"))
    c[1].metric("Kunjungan", f"{len(r['route'])} dari {n - 1}", help=term("Kunjungan"))
    c[2].metric("Waktu misi", f"{fmt(r['mission_time_h'], '.1f')} / {fmt(inst.time_limit, 'g')} jam",
                help=term("Batas waktu misi"))
    c[3].metric("Jarak terbang", f"{fmt(r['distance_km'], ',.0f')} km")
    st.plotly_chart(charts.route_map(positions(), inst.names[inst.depot], [("", r["route"], r["skipped"])],
                                     COLORS[r["algorithm"]], title="Arahkan kursor ke titik untuk waktu tiba dan Prize"),
                    width="stretch")
    with st.expander("Tabel rute lengkap"):
        st.dataframe(table("case_study_route"), hide_index=True, width="stretch")

    st.header("Ablasi decay: bagaimana jika decay diabaikan?")
    st.markdown(
        "Rute direncanakan dengan **g0 = 0** (seolah Prize tidak meluruh), lalu dinilai dengan decay sebenarnya. "
        "Selisihnya adalah Prize yang hilang karena perencana tidak tahu bahwa api terus meluas.")
    with_decay = _route_from_order(inst, "position_decay"); static = _route_from_order(inst, "position_static")
    a, b = st.columns(2)
    for col, d, label, color in ((a, with_decay, "Direncanakan dengan decay", COLORS["SA"]),
                                 (b, static, "Direncanakan tanpa decay (g0 = 0)", "#555")):
        col.plotly_chart(charts.route_map(positions(), inst.names[inst.depot], [("", d["route"], d["skipped"])], color,
                                          title=f"{label}<br>Fitness sebenarnya {fmt(d['fitness'], '.3f')}", height=460),
                         width="stretch")

    o = table("decay_ablation_order"); ops = o[o.ops > 0].sort_values("position_decay")
    fig = go.Figure()
    for _, row in ops.iterrows():
        fig.add_scatter(x=["dengan decay", "tanpa decay"], y=[row.position_decay, row.position_static],
                        mode="lines+markers+text", name=row.province, text=[row.province, ""],
                        textposition="middle left")
    fig.update_yaxes(title="Urutan kunjungan", autorange="reversed")
    fig.update_layout(title="Provinsi ber-data operasional (decay lebih cepat) dikunjungi jauh lebih awal",
                      height=420, margin=dict(l=10, r=10, t=40, b=10), showlegend=False)
    left, right = st.columns([3, 2])
    left.plotly_chart(fig, width="stretch")
    seeds = table("decay_ablation_seeds")
    bar = go.Figure(go.Bar(x=seeds.algorithm, y=seeds.prize_lost_mean_pct, marker_color=[COLORS[x] for x in seeds.algorithm],
                           text=[f"{fmt(v, '.1f')}%" for v in seeds.prize_lost_mean_pct], textposition="outside"))
    bar.update_yaxes(title="Prize hilang rata-rata (%)")
    bar.update_layout(title="Prize yang hilang jika decay diabaikan (30 seed)", height=420,
                      margin=dict(l=10, r=10, t=40, b=10))
    right.plotly_chart(bar, width="stretch")

    st.header("Sensitivitas parameter")
    st.caption("Satu parameter diubah, yang lain tetap di nilai default. Kualitas = % dari Best-known pada nilai itu.")
    s = table("sensitivity")
    a, b = st.columns(2)
    a.plotly_chart(charts.lines(s[s.parameter == "time_limit_hours"], "value", "mean", "algorithm",
                                "Batas waktu misi (jam)", "Fitness rata-rata", "Batas waktu misi"), width="stretch")
    b.plotly_chart(charts.lines(s[s.parameter == "decay_g0"], "value", "mean", "algorithm", "g0",
                                "Fitness rata-rata", "Laju peluruhan g0"), width="stretch")
