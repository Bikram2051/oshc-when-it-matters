"""Bill Explainer page. Skeleton. See plan section 6."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st  # noqa: E402

st.set_page_config(page_title="Bill Explainer", layout="centered")
st.title("Bill Explainer")
st.caption("Page id: explainer. Not yet implemented. See the architecture plan.")
