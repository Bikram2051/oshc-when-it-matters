"""Journey Coach: fixed lessons and session-only practice."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from oshc.coach_ui import render

st.set_page_config(page_title="Journey Coach | NextBest", page_icon=":material/school:", layout="wide")
render()
