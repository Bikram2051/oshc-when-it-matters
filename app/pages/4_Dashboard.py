"""Dashboard page. Skeleton. See plan section 6."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st  # noqa: E402

st.set_page_config(page_title="Dashboard", layout="centered")
st.title("Dashboard")
st.caption("Page id: dashboard. Not yet implemented. See the architecture plan.")
