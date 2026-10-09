"""Synthetic Bill Explainer, backed by the offline extraction and reference modules."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st
from oshc.billexplainer.ui import render

st.set_page_config(page_title="Bill Explainer | NextBest", page_icon="+", layout="wide")
render()
