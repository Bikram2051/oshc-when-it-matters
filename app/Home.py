"""NextBest entry point. Run: streamlit run app/Home.py."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Server-side .env/secrets supply credentials; values are never rendered.
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
# Normal operation uses guarded Haiku. Tests/research can explicitly select the
# preserved source-only mode without calling a provider.
os.environ.setdefault("OSHC_OFFLINE", "0")
os.environ.setdefault("OSHC_ENABLE_LIVE", "1")
os.environ.setdefault("OSHC_MODEL", "claude-haiku-4-5-20251001")

import streamlit as st

from oshc.home_ui import render

st.set_page_config(
    page_title="NextBest | OSHC When It Matters",
    page_icon=":material/health_and_safety:",
    layout="wide",
)

page = st.navigation([
    st.Page(render, title="Home", icon=":material/home:", default=True),
    st.Page("views/1_Journey_Coach.py", title="Journey Coach", icon=":material/school:"),
    st.Page("views/2_Navigator.py", title="Navigator", icon=":material/menu_book:"),
    st.Page("views/3_Bill_Explainer.py", title="Bill Explainer", icon=":material/receipt_long:"),
    st.Page("views/4_Ask.py", title="Ask NextBest", icon=":material/forum:"),
    st.Page("views/5_Dashboard.py", title="Project dashboard", icon=":material/dashboard:"),
], position="top")
page.run()
