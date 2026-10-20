"""Page 5: the Klaster hotspot FIRMS instances (phase 2, ADR-0001), shown from saved results only."""
import streamlit as st

from app import charts
from app.core import (ALGORITHMS, COLORS, ROOT, config, coords, fmt, readme_section, rows_height, saved_route,
                      styled, table, term)

HC_COLUMNS = {"neighbourhood_size": "tetangga per langkah", "budget": "Budget evaluasi",
              "budget_per_neighbourhood": "langkah penuh per budget", "hc_restarts_mean": "pendakian (rata-rata)",
              "hc_steps_mean": "langkah naik (rata-rata)"}


@st.cache_data
def hotspots():
    from src.firms import load_hotspots
    f = config()["firms"]
    h = load_hotspots(ROOT / f["snapshot"], f["confidence"], f["bboxes"])
    return h.lon.to_numpy(), h.lat.to_numpy()


def render():
    cfg = config(); f = cfg["firms"]
    st.title("Klaster hotspot NASA FIRMS (fase 2)")
    st.markdown(
        "Untuk menguji apakah peringkat algoritma tetap berlaku pada instance yang jauh lebih besar, titik panas "
        "satelit NASA FIRMS (VIIRS, 7 hari) dikelompokkan dengan k-means menjadi k **Klaster hotspot**. Hasil di "
        "halaman ini dibaca dari `results/` (satu run butuh 20–40 detik, terlalu lama untuk dijalankan langsung).",
        help=term("Klaster hotspot"))
    _route_section(cfg, f)

    st.subheader("Fitness rata-rata 30 seed")
    s = table("firms_summary")
    wide = s.pivot_table(index="k", columns="algorithm", values="mean")[list(ALGORITHMS)]
    wide.insert(0, "Best-known", s.groupby("k").best_known.first())
    wide = wide.reset_index()
    st.dataframe(styled(wide, {c: ".3f" for c in wide.columns if c != "k"})
                 .highlight_max(subset=list(ALGORITHMS), axis=1, color="#e3f1dc"),
                 hide_index=True, width="stretch", height=rows_height(len(wide)))

    st.subheader("Apakah peringkat dari instance provinsi tetap berlaku?")
    rank = table("firms_ranking"); rank.columns = ["instance", "peringkat (rata-rata Fitness, terbaik dulu; = berarti seri)"]
    st.dataframe(rank, hide_index=True, width="stretch", height=rows_height(len(rank)))

    st.subheader("Kenapa HC jatuh: biaya per langkah O(n²)")
    hc = table("firms_hc_cost")
    hc = hc[(hc.instance_family == "FIRMS") | (hc.n == 38)].copy()
    hc.insert(0, "instance", [f"FIRMS k = {n - 1}" if fam == "FIRMS" else f"provinsi {sc}, n = {n}"
                              for fam, sc, n in zip(hc.instance_family, hc.scenario, hc.n)])
    hc = hc[["instance", "neighbourhood_size", "budget", "budget_per_neighbourhood", "hc_restarts_mean",
             "hc_steps_mean"]].rename(columns=HC_COLUMNS)
    st.dataframe(styled(hc, {"tetangga per langkah": ",d", "Budget evaluasi": ",d", "langkah penuh per budget": ".1f",
                             "pendakian (rata-rata)": ".1f", "langkah naik (rata-rata)": ".1f"}),
                 hide_index=True, width="stretch", height=rows_height(len(hc)))
    st.markdown(readme_section("Instance Klaster hotspot FIRMS (fase 2)", start_marker="Catatan jujur",
                               end_marker="<!-- AUTO:firms-hc-cost"))


@st.fragment
def _route_section(cfg, f):
    """k picker, headline numbers and the route map; switching k reruns only this part."""
    a, b = st.columns([2, 3])
    k = a.radio("k (jumlah Klaster hotspot)", f["sizes"], index=f["sizes"].index(f["map_k"]), horizontal=True)
    show_bg = b.toggle("Tampilkan semua hotspot FIRMS", value=True)
    nodes = table(f"firms_clusters_k{k}")
    depot = coords().set_index("Provinsi").loc[cfg["depot"]]
    depot_name = str(depot.Ibukota)
    pos = {name: (lon, lat) for name, lon, lat in zip(nodes.name, nodes.lon, nodes.lat)}
    pos[depot_name] = (float(depot.lon), float(depot.lat))
    r = saved_route(f"best_route_firms_k{k}")
    c = st.columns(4)
    c[0].metric("Fitness rute terbaik", fmt(r["fitness"], ".3f"), help=term("Fitness"), border=True)
    c[1].metric("Klaster dikunjungi", f"{len(r['route'])} dari {k}", border=True)
    c[2].metric("Waktu misi (jam)", f"{fmt(r['mission_time_h'], '.1f')} / {fmt(r['time_limit_h'], 'g')}", border=True)
    c[3].metric("Algoritma · seed", f"{r['algorithm']} · {r['seed']}", border=True)
    st.plotly_chart(charts.route_map(pos, depot_name, [("", r["route"], r["skipped"])], COLORS[r["algorithm"]],
                                     title=f"Rute terbaik, k = {k}",
                                     background=hotspots() if show_bg else None, height=560), width="stretch")
    st.caption("Risiko klaster: " + term("Risiko klaster"))
