"""Student landing page; general education with links to the four learning tools."""
import streamlit as st

MODULES = (
    ("Learn the essentials", "Journey Coach", "pages/1_Journey_Coach.py", "home_coach",
     "school", "Three short lessons. Practise what you learn and check the original source."),
    ("Find it in the guide", "Navigator", "pages/2_Navigator.py", "home_navigator",
     "menu_book", "Explore prepared topics, read the source passages, and open the full page."),
    ("Understand the numbers", "Bill Explainer", "pages/3_Bill_Explainer.py", "home_bill",
     "receipt_long", "Explore a synthetic bill and compare its charges with published MBS references."),
    ("Ask in your own words", "Ask NextBest", "pages/4_Ask.py", "home_ask",
     "forum", "Ask general OSHC questions in a guarded chat, with passages and page references."),
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
        st.badge("Offline demonstration", icon=":material/wifi_off:")

    st.space("small")
    with st.container(border=True):
        intro, action = st.columns([3, 1], vertical_alignment="center")
        with intro:
            st.subheader("Have a question of your own?")
            st.markdown("Ask NextBest checks each message before finding relevant passages in the saved guide.")
        with action:
            if st.button("Start a chat", icon=":material/arrow_forward:", type="primary",
                         width="stretch", key="home_start_chat"):
                st.switch_page("pages/4_Ask.py")

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
            "Free-form generated policy answers remain disabled pending the safety evaluation."
        )
    st.divider()
    footer, evidence = st.columns([3, 1], vertical_alignment="center")
    footer.caption("Team D5 · Swinburne University of Technology · Industry context: Medibank")
    if evidence.button("View project evidence", key="home_dashboard", width="stretch"):
        st.switch_page("pages/5_Dashboard.py")
