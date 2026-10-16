"""Presenter evidence dashboard."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from oshc.dashboard_ui import render

st.set_page_config(page_title="Project dashboard | NextBest", page_icon=":material/dashboard:", layout="wide")
render()
