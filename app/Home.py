"""OSHC When It Matters. Entry page.

Run: streamlit run app/Home.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

st.set_page_config(page_title="OSHC When It Matters", page_icon="+", layout="centered")

st.title("OSHC When It Matters")
st.caption("Team D5 prototype. Synthetic and public sample documents only.")

st.info(
    "This is a university prototype. It explains general OSHC rules and what a "
    "document shows. It cannot tell you what your own policy will pay, and it "
    "does not assess symptoms. In an emergency call 000."
)

st.markdown(
    """
Three moments, three pages:

- **Journey Coach** puts the words in front of you before they matter.
- **Navigator** explains what a GP, pharmacy, urgent care and emergency each do and cost.
- **Bill Explainer** reads a bill and explains what OSHC covers, what it does not, and how to claim.
"""
)

lang = st.selectbox("Language / भाषा", ["English", "हिन्दी (Hindi)"], index=0)
st.session_state["lang"] = "hi" if lang.startswith("ह") else "en"
