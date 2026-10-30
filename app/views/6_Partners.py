"""For partners: how to link NextBest from existing channels, and how a pilot is measured."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from oshc.partner_ui import render

st.set_page_config(page_title="For partners | NextBest", page_icon=":material/handshake:", layout="centered")
render()
