"""Ask a question: guardrailed, retrieval-only search over the verified guide."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402
from oshc.ask_ui import render  # noqa: E402

st.set_page_config(page_title="Ask a question | NextBest", page_icon="+", layout="wide")
render()
