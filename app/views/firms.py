"""Page 5: the Klaster hotspot FIRMS instances (phase 2, ADR-0001), shown from saved results only."""
import streamlit as st

from app import charts
from app.core import ALGORITHMS, COLORS, ROOT, config, coords, fmt, readme_section, saved_route, table, term


@st.cache_data
def hotspots():
    from src.firms import load_hotspots
    f = config()["firms"]
    h = load_hotspots(ROOT / f["snapshot"], f["confidence"], f["bboxes"])
    return h.lon.to_numpy(), h.lat.to_numpy()


def render():
    cfg = config(); f = cfg["firms"]
    st.title("🛰️ Klaster hotspot NASA FIRMS (fase 2)")
    st.markdown(
        "Untuk menguji apakah peringkat algoritma tetap berlaku pada instance yang jauh lebih besar, titik panas "
        "satelit NASA FIRMS (VIIRS, 7 hari) dikelompokkan dengan k-means menjadi k **Klaster hotspot**. Hasil di "
        "halaman ini dibaca dari `results/` (satu run butuh 20–40 detik, terlalu lama untuk dijalankan langsung).",
        help=term("Klaster hotspot"))
    k = st.radio("k (jumlah Klaster hotspot)", f["sizes"], index=f["sizes"].index(f["map_k"]), horizontal=True)

    nodes = table(f"firms_clusters_k{k}")
    depot = coords().set_index("Provinsi").loc[cfg["depot"]]
    depot_name = str(depot.Ibukota)
    pos = {name: (lon, lat) for name, lon, lat in zip(nodes.name, nodes.lon, nodes.lat)}
    pos[depot_name] = (float(depot.lon), float(depot.lat))
    r = saved_route(f"best_route_firms_k{k}")
    c = st.columns(4)
    c[0].metric("Fitness rute terbaik", fmt(r["fitness"], ".3f"), help=term("Fitness"))
    c[1].metric("Klaster dikunjungi", f"{len(r['route'])} dari {k}")
    c[2].metric("Waktu misi", f"{fmt(r['mission_time_h'], '.1f')} / {fmt(r['time_limit_h'], 'g')} jam")
    c[3].metric("Algoritma · seed", f"{r['algorithm']} · {r['seed']}")
    show_bg = st.toggle("Tampilkan semua hotspot FIRMS", value=True)
    st.plotly_chart(charts.route_map(pos, depot_name, [("", r["route"], r["skipped"])], COLORS[r["algorithm"]],
                                     title=f"Rute terbaik, k = {k}; Risiko klaster = Σ FRP → log1p → min-max",
                                     background=hotspots() if show_bg else None, height=600), width="stretch")
    st.caption("Ikon ⓘ: " + term("Risiko klaster"))

    st.subheader("Fitness rata-rata 30 seed")
    s = table("firms_summary")
    wide = s.pivot_table(index="k", columns="algorithm", values="mean")[list(ALGORITHMS)]
    wide.insert(0, "Best-known", s.groupby("k").best_known.first())
    st.dataframe(wide.reset_index().style.format({c: lambda v: fmt(v, ".3f") for c in wide.columns})
                 .highlight_max(subset=list(ALGORITHMS), axis=1, color="#d8f0d2"), hide_index=True, width="stretch")
    rank = table("firms_ranking"); rank.columns = ["instance", "peringkat (terbaik dulu; = berarti seri)"]
    st.dataframe(rank, hide_index=True, width="stretch")

    st.subheader("Kenapa HC jatuh: biaya per langkah O(n²)")
    hc = table("firms_hc_cost")
    st.dataframe(hc, hide_index=True, width="stretch")
    st.markdown(readme_section("Instance Klaster hotspot FIRMS (fase 2)", start_marker="Catatan jujur",
                               end_marker="<!-- AUTO:firms-hc-cost"))
