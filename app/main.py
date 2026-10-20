"""Entry point: streamlit run app/main.py (from the repo root)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.views import case_study, firms, playground, problem, results  # noqa: E402

st.set_page_config(page_title="Perutean Armada Udara Karhutla", page_icon=":material/local_fire_department:",
                   layout="wide")
# Readable line length on wide screens and even spacing between sections.
st.html("""<style>
.block-container {max-width: 1240px; padding-top: 2.5rem; padding-bottom: 4rem;}
h1 {padding-bottom: .25rem;}
h2 {padding-top: 1.75rem;}
h3 {padding-top: 1rem;}
[data-testid="stMetric"] {padding: .6rem .9rem;}
[data-testid="stMetricLabel"] p {font-size: .9rem;}
[data-testid="stPlotlyChart"] {margin-top: .25rem;}
</style>""")

pages = [
    st.Page(problem.render, title="Masalahnya", icon=":material/map:", url_path="masalah", default=True),
    st.Page(playground.render, title="Coba sendiri", icon=":material/play_circle:", url_path="coba-sendiri"),
    st.Page(results.render, title="Hasil perbandingan", icon=":material/bar_chart:", url_path="hasil"),
    st.Page(case_study.render, title="Studi kasus & ablasi decay", icon=":material/route:", url_path="studi-kasus"),
    st.Page(firms.render, title="Klaster hotspot FIRMS", icon=":material/satellite_alt:", url_path="firms"),
]
st.sidebar.markdown("**Perutean Armada Udara Karhutla**  \nHC vs SA vs GA · Kelompok 8")
st.navigation(pages).run()
st.sidebar.caption("Istilah mengikuti GLOSSARY.md. Arahkan kursor ke ikon tanda tanya untuk definisinya.")
