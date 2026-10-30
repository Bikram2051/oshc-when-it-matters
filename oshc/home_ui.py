"""Student landing page; general education with links to the four learning tools."""
import os
import streamlit as st

MODULES = (
    ("Learn the essentials", "Journey Coach", "views/1_Journey_Coach.py", "home_coach",
     "school", "Three short lessons, practice scenarios, and a checklist you can take away."),
    ("Find it in the guide", "Navigator", "views/2_Navigator.py", "home_navigator",
     "menu_book", "Explore prepared topics, read the source passages, and open the full page."),
    ("Understand the numbers", "Bill Explainer", "views/3_Bill_Explainer.py", "home_bill",
     "receipt_long", "Explore a synthetic bill and compare its charges with published MBS references."),
    ("Ask in your own words", "Ask NextBest", "views/4_Ask.py", "home_ask",
     "forum", "Ask in your own words. Every message is checked, and answers show their guide passages."),
)


def render():
    st.caption("NEXTBEST  /  OSHC WHEN IT MATTERS")
    st.title("A clearer next step.")
    st.markdown(
        "Understand your overseas student health cover, one useful idea at a time. "
        "Learn the terms, explore the guide, or ask a question when you need it."
    )
    with st.container(horizontal=True):
        st.badge("University prototype", icon=":material/science:")
        st.badge("Public sources + synthetic bills", icon=":material/verified_user:")
        live = os.getenv("OSHC_OFFLINE") == "0" and os.getenv("OSHC_ENABLE_LIVE") == "1"
        st.badge("Guarded Haiku chat" if live else "Verified source mode", icon=":material/verified_user:")

    st.space("small")
    with st.container(border=True):
        intro, action = st.columns([3, 1], vertical_alignment="center")
        with intro:
            st.subheader("Have a question of your own?")
            st.markdown("Ask NextBest checks each message before finding relevant passages in the saved guide.")
        with action:
            if st.button("Start a chat", icon=":material/arrow_forward:", type="primary",
                         width="stretch", key="home_start_chat"):
                st.switch_page("views/4_Ask.py")

    st.subheader("Choose where to start")
    for row in (MODULES[:2], MODULES[2:]):
        for column, (heading, name, page, key, icon, blurb) in zip(st.columns(2), row):
            with column.container(border=True):
                st.markdown(f":primary[:material/{icon}:]  **{name}**")
                st.subheader(heading)
                st.markdown(blurb)
                if st.button(f"Open {name}", key=key, icon=":material/arrow_forward:"):
                    st.switch_page(page)

    st.info(
        "General education only. NextBest cannot assess symptoms, decide your cover or "
        "confirm a claim payment. Use invented bills and avoid personal details. "
        "In an emergency call 000.", icon=":material/info:",
    )
    with st.expander("How the prototype keeps answers grounded"):
        st.markdown(
            "Each submitted chat message passes the safety boundary before source lookup. "
            "Responses show passages from a verified copy of the Medibank OSHC Member Guide. "
            "When a request needs personal advice, health assessment or unsupported information, "
            "the chat stops or asks for a clearer general question."
        )
        st.caption(
            "Chat stays in the current Streamlit session and can be cleared. "
            + ("Haiku checks the question, generates from retrieved evidence and reviews the answer before display. "
               if os.getenv("OSHC_OFFLINE") == "0" and os.getenv("OSHC_ENABLE_LIVE") == "1" else
               "In verified source mode, answers are fixed explanations bound to guide passages; no AI provider is called. ")
            + "Personal benefits and clinical advice remain outside scope."
        )
    st.divider()
    footer, evidence = st.columns([3, 1], vertical_alignment="center")
    footer.caption("Team D5 · Swinburne University of Technology · Industry context: Medibank")
    if evidence.button("View project evidence", key="home_dashboard", width="stretch"):
        st.switch_page("views/5_Dashboard.py")
