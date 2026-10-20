"""Entry point: streamlit run app/main.py (from the repo root)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.views import case_study, firms, playground, problem, results  # noqa: E402

st.set_page_config(page_title="Perutean Armada Udara Karhutla", page_icon="🔥", layout="wide")

pages = [
    st.Page(problem.render, title="1. Masalahnya", icon="🗺️", url_path="masalah", default=True),
    st.Page(playground.render, title="2. Coba sendiri", icon="▶️", url_path="coba-sendiri"),
    st.Page(results.render, title="3. Hasil perbandingan", icon="📊", url_path="hasil"),
    st.Page(case_study.render, title="4. Studi kasus & ablasi decay", icon="🔍", url_path="studi-kasus"),
    st.Page(firms.render, title="5. Klaster hotspot FIRMS", icon="🛰️", url_path="firms"),
]
st.sidebar.markdown("**Perutean Armada Udara Karhutla**  \nHC vs SA vs GA · Kelompok 8")
st.navigation(pages).run()
st.sidebar.caption("Istilah mengikuti GLOSSARY.md. Arahkan kursor ke ikon ⓘ untuk definisinya.")
