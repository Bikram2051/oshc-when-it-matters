"""Navigator page. Skeleton. See plan section 6."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st  # noqa: E402

st.set_page_config(page_title="Navigator", layout="centered")
st.title("Navigator")
st.caption("Page id: navigator. Not yet implemented. See the architecture plan.")
