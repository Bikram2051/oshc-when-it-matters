"""Journey Coach page. Skeleton. See plan section 6."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st  # noqa: E402

st.set_page_config(page_title="Journey Coach", layout="centered")
st.title("Journey Coach")
st.caption("Page id: coach. Not yet implemented. See the architecture plan.")
