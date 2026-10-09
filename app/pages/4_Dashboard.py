"""Presenter evidence dashboard."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402
from oshc.dashboard_ui import render  # noqa: E402

st.set_page_config(page_title="Prototype evidence", layout="wide")
render()
