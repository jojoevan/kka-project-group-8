"""Page 2: run the solvers live on a province instance and replay how the best route improves."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app import charts
from app.core import (ALGORITHM_NAMES, ALGORITHMS, COLORS, EXACT_MAX_NODES, SCENARIOS, SIZES, best_known, config,
                      experiment_budget, fmt, instance, run, term)
from app.views.problem import positions

BUDGETS = [1000, 2000, 5000, 10000, 20000, 50000]

HOW = {
    "Greedy": "Mulai dari Depot. Berulang kali pilih node yang **masih muat** dengan rasio "
              "Prize / (waktu terbang + waktu tinggal) terbesar, sampai tidak ada yang muat. Deterministik "
              "(seed tidak berpengaruh) dan hanya butuh 1 evaluasi Fitness.",
    "HC": "Mulai dari urutan acak. Setiap langkah mencoba **semua** tetangga (*swap*, *relocate*, dan "
          "*reverse*/2-opt) lalu pindah ke tetangga terbaik. Jika tidak ada tetangga yang lebih baik "
          "(*local optimum*), HC mulai lagi dari urutan acak baru (*restart*) selama Budget evaluasi masih ada.",
    "SA": "Mulai dari urutan acak. Setiap langkah mencoba **satu** tetangga acak. Tetangga yang lebih baik selalu "
          "diterima; yang lebih buruk diterima dengan peluang e^(Δ/T). Suhu T turun geometris dari T0 sampai "
          "sekitar 0,001·T0 saat budget habis, jadi di awal SA berani menjelajah dan di akhir makin selektif.",
    "GA": "Mulai dari 100 urutan acak (populasi). Setiap generasi: pilih induk lewat turnamen (3 kandidat), "
          "gabungkan dua induk dengan *Order Crossover*, mutasi 20% anak dengan satu move acak, dan simpan "
          "2 individu terbaik (elitisme). Setiap anak menghabiskan 1 evaluasi.",
    "Exact": "Mencoba semua kemungkinan urutan (dengan pemangkasan prefix yang tidak muat). Dijamin optimal, "
             "tetapi hanya mungkin untuk n kecil.",
}


def _form(cfg):
    with st.form("params"):
        a, b, c = st.columns(3)
        scenario = a.radio("Skenario tahun", SCENARIOS, index=1, horizontal=True, help=term("Skenario tahun"))
        n = a.select_slider("n (jumlah node, termasuk Depot)", SIZES, value=15, help=term("Instance"))
        algorithms = b.multiselect("Algoritma", [*ALGORITHMS, "Exact"], default=list(ALGORITHMS),
                                   help=f"Exact hanya untuk n = {EXACT_MAX_NODES}.")
        seed = b.number_input("Seed", 0, 999, 0, help="Mengatur urutan awal acak dan keacakan algoritma.")
        budget = c.select_slider("Budget evaluasi", BUDGETS, value=5000, help=term("Budget evaluasi"))
        g0 = c.slider("g0 (laju peluruhan)", 0.0, 0.05, float(cfg["decay_g0"]), 0.001, format="%.3f",
                      help="0 berarti Prize tidak meluruh.")
        t_max = c.slider("Batas waktu misi (jam)", 12, 120, int(cfg["time_limit_hours"]), 6,
                         help=term("Batas waktu misi"))
        submitted = st.form_submit_button("▶ Jalankan", type="primary")
    if "Exact" in algorithms and n > EXACT_MAX_NODES:
        algorithms = [x for x in algorithms if x != "Exact"]
        if submitted: st.warning(f"Exact dilewati: hanya dijalankan untuk n = {EXACT_MAX_NODES}.")
    return submitted, dict(scenario=scenario, n=n, algorithms=algorithms, seed=int(seed), budget=budget,
                           g0=g0, t_max=t_max)


def _states(inst, result):
    """Route states (label, route, skipped) of every improving best-so-far route."""
    out = []
    for evals, perm, fit in result["snapshots"]:
        d = inst.evaluate(perm, details=True)
        out.append((f"Rute terbaik setelah {fmt(evals, ',d')} evaluasi: Fitness {fmt(fit, '.3f')}",
                    d["route"], d["skipped"]))
    return out


def _diagnostics(alg, result, n):
    x = result["extra"]
    if alg == "HC":
        c = st.columns(3)
        c[0].metric("Tetangga per langkah", fmt(x["neighbourhood_size"], ",d"),
                    help="Ukuran neighbourhood penuh: O(n²). Satu langkah HC menghabiskan sebanyak ini evaluasi.")
        c[1].metric("Langkah naik", x["steps"])
        c[2].metric("Pendakian (start + restart)", x["restarts"])
        if x["restarts"] <= 1:
            st.warning("Budget habis sebelum pendakian pertama mencapai local optimum. Pada n besar, biaya per "
                       "langkah HC yang O(n²) menghabiskan budget.")
    elif alg == "SA":
        c = st.columns(3)
        c[0].metric("Suhu awal T0", fmt(x["T0"] or 0, ".4f"))
        c[1].metric("Suhu akhir", fmt(x["final_temperature"] or 0, ".2e"))
        c[2].metric("Acceptance rate", fmt(x["acceptance_rate"], ".3f"), help="Fraksi langkah yang diterima.")
        trace = x.get("temperature_trace") or []
        if trace:
            fig = go.Figure(go.Scatter(x=[e for e, _ in trace], y=[t for _, t in trace], mode="lines",
                                       line=dict(color=COLORS["SA"])))
            fig.update_xaxes(title="Evaluasi"); fig.update_yaxes(title="Suhu T", type="log")
            fig.update_layout(title="Jadwal pendinginan SA", height=280, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig, width="stretch")
    elif alg == "GA":
        c = st.columns(2)
        c[0].metric("Ukuran populasi", x["population"]); c[1].metric("Generasi", x["generations"])
    elif alg == "Exact":
        st.metric("Terbukti optimal", "ya" if x.get("optimal") else "tidak")


def render():
    cfg = config()
    st.title("▶️ Coba sendiri")
    st.markdown("Atur instance dan algoritma, lalu tekan **Jalankan**. Solver yang dipakai sama persis dengan "
                "eksperimen; halaman ini hanya merekam setiap kali rute terbaik membaik, supaya prosesnya bisa "
                "diputar ulang di peta.")
    submitted, p = _form(cfg)
    if submitted:
        if not p["algorithms"]:
            st.error("Pilih minimal satu algoritma."); return
        results = {}
        with st.status("Menjalankan solver…", expanded=False) as status:
            for alg in p["algorithms"]:
                status.update(label=f"Menjalankan {alg}…")
                results[alg] = run(alg, p["n"], p["scenario"], p["g0"], p["t_max"], p["budget"], p["seed"])
            status.update(label="Selesai", state="complete")
        st.session_state.playground = (p, results)
    if "playground" not in st.session_state:
        st.info("Belum ada hasil. Default yang disarankan untuk demo: n = 15, budget 5.000 (sekitar 1–2 detik)."); return
    p, results = st.session_state.playground
    inst = instance(p["n"], p["scenario"], p["g0"], p["t_max"])

    default = p["g0"] == cfg["decay_g0"] and p["t_max"] == cfg["time_limit_hours"]
    full = experiment_budget(p["n"])
    ref = best_known(p["scenario"], p["n"]) if default else None
    if p["budget"] < full:
        st.caption(f"⚠️ Budget {fmt(p['budget'], ',d')} lebih kecil dari budget eksperimen untuk n = {p['n']} "
                   f"({fmt(full, ',d')}). Hasil di sini bisa berbeda dari angka di laporan.")
    if not default:
        st.caption("⚠️ g0 atau Batas waktu misi berbeda dari config.yaml, jadi tidak ada Best-known dari eksperimen.")

    cols = st.columns(len(results))
    for col, (alg, r) in zip(cols, results.items()):
        d = r["best_route"]
        col.metric(alg, fmt(r["best_fitness"], ".3f"), help=f"{ALGORITHM_NAMES[alg]}. " + term("Fitness"),
                   delta=f"{fmt(100 * r['best_fitness'] / ref, '.1f')}% dari Best-known" if ref else None,
                   delta_color="off")
        col.caption(f"{len(d['route'])}/{p['n'] - 1} node dikunjungi · waktu misi {fmt(d['mission_time_h'], '.1f')} "
                    f"jam · {fmt(r['evals'], ',d')} evaluasi · {fmt(r['runtime'], '.2f')} dtk")
    if ref: st.caption(f"Best-known instance ini: {fmt(ref, '.3f')} ({term('Best-known')})")

    series = {}
    for alg, r in results.items():
        h = r["history"]
        x = [e for e, _ in h] + [r["evals"]]; y = [v for _, v in h] + [h[-1][1]]
        series[alg] = (x, y)
    st.plotly_chart(charts.convergence(series, "Kurva konvergensi: Fitness terbaik vs evaluasi yang dipakai"),
                    width="stretch")

    st.subheader("Cara kerja tiap algoritma")
    for tab, (alg, r) in zip(st.tabs(list(results)), results.items()):
        with tab:
            st.markdown(f"**{ALGORITHM_NAMES[alg]}.** {HOW[alg]}")
            _diagnostics(alg, r, p["n"])
            states = _states(inst, r)
            if len(states) > 1:
                st.caption(f"Rute terbaik membaik {len(states)} kali. Tekan **▶ Putar** atau geser slider untuk "
                           "melihat urutannya.")
            st.plotly_chart(charts.route_map(positions(), inst.names[inst.depot], states, COLORS[alg]),
                            width="stretch", key=f"map_{alg}")
            d = r["best_route"]
            left, right = st.columns([2, 1])
            left.dataframe(pd.DataFrame([{"urutan": k, "provinsi": v["province"], "tiba (jam)": round(v["arrival_h"], 2),
                                          "Risiko": round(v["risk"], 3), "Prize": round(v["prize"], 3)}
                                         for k, v in enumerate(d["route"], 1)]), hide_index=True)
            right.markdown("**Node dilewati**" + (":\n\n" + "\n".join(f"- {s['province']} (Risiko {fmt(s['risk'], '.2f')})"
                                                                      for s in d["skipped"]) if d["skipped"] else ": tidak ada"),
                           help=term("Node dilewati"))
