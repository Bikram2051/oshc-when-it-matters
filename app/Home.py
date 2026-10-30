"""OSHC When It Matters entry point. Run: streamlit run app/Home.py."""
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
from oshc.ui_style import apply as apply_style

st.set_page_config(
    page_title="OSHC When It Matters",
    page_icon=":material/health_and_safety:",
    layout="centered",
)
apply_style()
st.logo(str(Path(__file__).parent / "static/brand/wordmark.svg"), size="small")

# Students see five places. Partners get one page of their own. The research evidence
# page stays reachable at /Dashboard for assessors but is not part of the product.
page = st.navigation([
    st.Page(render, title="Home", default=True),
    st.Page("views/1_Journey_Coach.py", title="Journey Coach"),
    st.Page("views/2_Navigator.py", title="Navigator"),
    st.Page("views/3_Bill_Explainer.py", title="Bill Explainer"),
    st.Page("views/4_Ask.py", title="Ask a question"),
    st.Page("views/6_Partners.py", title="For partners"),
    st.Page("views/5_Dashboard.py", title="Project evidence", visibility="hidden"),
], position="top")
page.run()
