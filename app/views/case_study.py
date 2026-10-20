"""Page 4: the case-study route (n = 38, 2026), the decay ablation, and the sensitivity sweep."""
import streamlit as st

from app import charts
from app.core import COLORS, config, fmt, instance, rows_height, saved_route, styled, table, term
from app.views.problem import positions

ROUTE_COLUMNS = {"order": "urutan", "province": "provinsi", "status": "status", "risk": "Risiko",
                 "leg_km": "jarak leg (km)", "arrival_h": "tiba (jam)", "departure_h": "berangkat (jam)", "prize": "Prize"}


def _route_from_order(inst, column):
    """Route detail of the ablation order in `column` (position_decay / position_static), scored with decay."""
    o = table("decay_ablation_order").dropna(subset=[column]).sort_values(column)
    return inst.evaluate([inst.names.index(p) for p in o.province], details=True)


def render():
    cs = config()["analysis"]["case_study"]; n, scenario = int(cs["n"]), str(cs["scenario"])
    inst = instance(n, scenario)
    st.title("Studi kasus & ablasi decay")

    r = saved_route(f"best_route_{scenario}_n{n}")
    st.subheader(f"Rute terbaik: {r['algorithm']} seed {r['seed']}, Skenario tahun {scenario}, n = {n}")
    c = st.columns(4)
    c[0].metric("Fitness", fmt(r["fitness"], ".3f"), help=term("Fitness"), border=True)
    c[1].metric("Kunjungan", f"{len(r['route'])} dari {n - 1}", help=term("Kunjungan"), border=True)
    c[2].metric("Waktu misi (jam)", f"{fmt(r['mission_time_h'], '.1f')} / {fmt(inst.time_limit, 'g')}",
                help=term("Batas waktu misi"), border=True)
    c[3].metric("Jarak terbang", f"{fmt(r['distance_km'], ',.0f')} km", border=True)
    st.plotly_chart(charts.route_map(positions(), inst.names[inst.depot], [("", r["route"], r["skipped"])],
                                     COLORS[r["algorithm"]], height=480), width="stretch")
    st.caption("Arahkan kursor ke titik untuk melihat waktu tiba, Risiko, dan Prize.")
    with st.expander("Tabel rute lengkap"):
        t = table("case_study_route").rename(columns=ROUTE_COLUMNS)
        st.dataframe(styled(t, {"Risiko": ".3f", "ops": ".2f", "jarak leg (km)": ",.0f", "tiba (jam)": ".2f",
                                "berangkat (jam)": ".2f", "Prize": ".3f"}),
                     hide_index=True, width="stretch", height=rows_height(len(t)))

    st.header("Ablasi decay: bagaimana jika decay diabaikan?")
    st.markdown(
        "Rute direncanakan dengan **g0 = 0** (seolah Prize tidak meluruh), lalu dinilai dengan decay sebenarnya. "
        "Selisihnya adalah Prize yang hilang karena perencana tidak tahu bahwa api terus meluas.")
    with_decay = _route_from_order(inst, "position_decay"); static = _route_from_order(inst, "position_static")
    a, b = st.columns(2, gap="large")
    for col, d, label, color in ((a, with_decay, "Direncanakan dengan decay", COLORS["SA"]),
                                 (b, static, "Direncanakan tanpa decay (g0 = 0)", "#555")):
        col.plotly_chart(charts.route_map(positions(), inst.names[inst.depot], [("", d["route"], d["skipped"])], color,
                                          title=f"{label}<br>Fitness sebenarnya {fmt(d['fitness'], '.3f')}", height=380),
                         width="stretch")

    o = table("decay_ablation_order"); ops = o[o.ops > 0].sort_values("position_decay")
    left, right = st.columns([3, 2], gap="large")
    left.plotly_chart(charts.dumbbell(ops.province.tolist(), ops.position_decay, ops.position_static,
                                      "dengan decay", "tanpa decay", "Urutan kunjungan (1 = pertama)",
                                      "Provinsi ber-data operasional dikunjungi jauh lebih awal", height=400),
                      width="stretch")
    seeds = table("decay_ablation_seeds")
    right.plotly_chart(charts.bars(seeds.algorithm, seeds.prize_lost_mean_pct, [COLORS[x] for x in seeds.algorithm],
                                   [f"{fmt(v, '.1f')}%" for v in seeds.prize_lost_mean_pct], "Prize hilang rata-rata (%)",
                                   "Prize yang hilang jika decay diabaikan<br>rata-rata 30 seed"), width="stretch")

    st.header("Sensitivitas parameter")
    st.caption("Satu parameter diubah, yang lain tetap di nilai default (n = 38, Skenario tahun 2026, 30 seed).")
    s = table("sensitivity")
    a, b = st.columns(2, gap="large")
    a.plotly_chart(charts.lines(s[s.parameter == "time_limit_hours"], "value", "mean", "algorithm",
                                "Batas waktu misi (jam)", "Fitness rata-rata", "Batas waktu misi"), width="stretch")
    b.plotly_chart(charts.lines(s[s.parameter == "decay_g0"], "value", "mean", "algorithm", "g0 (per jam)",
                                "Fitness rata-rata", "Laju peluruhan g0"), width="stretch")
