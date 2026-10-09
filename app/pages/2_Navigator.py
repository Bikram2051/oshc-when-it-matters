"""Navigator: offline browsing of the verified public policy guide."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402
from oshc.navigator_ui import render  # noqa: E402

st.set_page_config(page_title="Navigator | NextBest", page_icon="+", layout="wide")
render()
