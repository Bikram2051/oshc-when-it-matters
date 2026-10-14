"""NextBest prototype entry page. Run: streamlit run app/Home.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402

st.set_page_config(page_title="NextBest | OSHC When It Matters", page_icon="+", layout="wide")

MODULES = (
    ("Journey Coach", "pages/1_Journey_Coach.py", "home_coach", "Learn before you need it",
     "Three short lessons with practice questions, each one linked to the page of the "
     "guide it came from."),
    ("Navigator", "pages/2_Navigator.py", "home_navigator", "Read the policy source",
     "Six prepared topics, the exact column excerpt, and the original PDF page beside it."),
    ("Bill Explainer", "pages/3_Bill_Explainer.py", "home_bill", "Understand a bill",
     "Reads a synthetic invoice, leaves missing amounts unknown, and compares line items "
     "against the published MBS schedule."),
    ("Ask a question", "pages/4_Ask.py", "home_ask", "Ask in your own words",
     "Your question, matched against the saved guide. Shows you the passage and the page, "
     "and refuses anything it should not answer."),
)


def main():
    st.title("NextBest")
    st.caption("OSHC When It Matters | Team D5 university prototype | English demo")
    st.write(
        "International students arrive holding a policy they did not choose and cannot read. "
        "NextBest explains the general rules, shows what a document actually says, and "
        "decodes a bill, without ever guessing at what one person is covered for."
    )
    st.info(
        "This prototype explains general information and what a document shows. It cannot "
        "determine what your policy will pay or assess symptoms. Use synthetic bills only. "
        "In an emergency call 000."
    )

    st.subheader("Four ways in")
    for row in (MODULES[:2], MODULES[2:]):
        for column, (name, page, key, heading, blurb) in zip(st.columns(2), row):
            with column.container(border=True):
                st.markdown(f"#### {name}")
                st.caption(heading)
                st.write(blurb)
                if st.button(f"Open {name}", key=key, width="stretch"):
                    st.switch_page(page)

    with st.expander("What this prototype will not do, and why"):
        st.markdown(
            "- **It will not tell you what your own policy pays.** That is personal "
            "financial product advice. Every page routes a question like that to Medibank.\n"
            "- **It will not assess symptoms.** There is no code path from a symptom to a "
            "service in this repository.\n"
            "- **It will not write its own answers.** Ask a question returns passages from "
            "the guide as published. The module that would compose prose stays switched "
            "off until it passes a measured refusal-recall threshold.\n"
            "- **It will not read a real bill.** Bill Explainer takes synthetic invoices only."
        )
        st.caption(
            "Engineering evidence for each module, and the six evaluations that are still "
            "outstanding, are listed on the Prototype evidence page."
        )

    if st.button("Open the prototype evidence page", key="home_dashboard"):
        st.switch_page("pages/5_Dashboard.py")


main()
