"""Ask a question: guardrailed, retrieval-only search over the verified guide."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from oshc.ask_ui import render

st.set_page_config(page_title="Ask NextBest | NextBest", page_icon=":material/forum:", layout="centered")
render()
