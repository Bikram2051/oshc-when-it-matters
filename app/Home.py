"""NextBest prototype entry page. Run: streamlit run app/Home.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402

st.set_page_config(page_title="NextBest | OSHC When It Matters", page_icon="+", layout="centered")
st.title("NextBest")
st.caption("OSHC When It Matters | Team D5 university prototype | English demo")
st.write("Learn a useful idea, check the policy source, and explore a synthetic bill.")
st.info("This prototype explains general information and what a document shows. "
        "It cannot determine what your policy will pay or assess symptoms. "
        "Use synthetic bills only. In an emergency call 000.")

st.subheader("Learn before you need it")
st.write("Journey Coach offers three short lessons with practice questions and source links.")
if st.button("Start Journey Coach", key="home_coach"):
    st.switch_page("pages/1_Journey_Coach.py")

st.subheader("Read the policy source")
st.write("Navigator finds topic matches in the saved Medibank guide and shows the original pages.")
if st.button("Open Navigator", key="home_navigator"):
    st.switch_page("pages/2_Navigator.py")

st.subheader("Understand a bill")
st.write("Bill Explainer reads synthetic examples, keeps missing amounts unknown, "
         "and offers explicitly selected MBS reference comparisons.")
if st.button("Try Bill Explainer", key="home_bill"):
    st.switch_page("pages/3_Bill_Explainer.py")
