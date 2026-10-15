"""Navigator: fixed service handoffs and browsing of the verified public policy guide."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from oshc.navigator_ui import render

st.set_page_config(page_title="Navigator | NextBest", page_icon=":material/menu_book:", layout="wide")
render()
