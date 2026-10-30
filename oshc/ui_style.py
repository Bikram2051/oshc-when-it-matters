"""Shared presentation helpers: one stylesheet, a lead paragraph and the safety line.

Colours and fonts come from .streamlit/config.toml. This file only adds what the
theme cannot express: the sidebar brand and team credits, the journey line,
readable measure, caption contrast, visible keyboard focus and reduced motion.
"""
from __future__ import annotations

from html import escape

import streamlit as st

from oshc.care_navigation import HEALTHDIRECT_NUMBER

_CSS = """
<style>
:root {
  --nb-ink: #111111;
  --nb-muted: #4D4D4D;
  --nb-brand: #D50032;
  --nb-line: #D6D6D6;
  --nb-field: #8C8C8C;
  --nb-alert-bg: #FBE8EC;
}
p.nb-lead { font-size: 1.15rem; line-height: 1.55; color: var(--nb-ink); margin: 0; max-width: 38rem; }
/* Streamlit fades captions with opacity; that fails contrast. Use a solid muted ink. */
[data-testid="stCaptionContainer"] { opacity: 1 !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: var(--nb-muted) !important; }
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li { line-height: 1.6; }
/* Guide passages and answers keep their line breaks but read in the body face. */
[data-testid="stText"] { font-family: inherit; white-space: pre-wrap; line-height: 1.55; }

/* Home: a larger, tighter headline with a deliberate line break. */
h1.nb-hero { font-size: 2.75rem; line-height: 1.12; font-weight: 700; color: var(--nb-ink);
  margin: 0 0 0.75rem; padding: 0; letter-spacing: -0.01em; }

/* Home: the journey line. Each stop is a dot on one continuous route. */
.st-key-journey { gap: 0 !important; margin-top: 0.5rem; }
[class*="st-key-stop_"] { position: relative; padding: 0 0 1.5rem 2.4rem; gap: 0.15rem !important; }
[class*="st-key-stop_"]::before {
  content: ""; position: absolute; left: 0.3rem; top: 0.15rem; width: 1.1rem; height: 1.1rem;
  border-radius: 50%; background: #FFFFFF; border: 3px solid var(--nb-brand); box-sizing: border-box;
}
[class*="st-key-stop_"]::after {
  content: ""; position: absolute; left: calc(0.85rem - 1.5px); top: 1.35rem; bottom: 0.1rem;
  width: 3px; background: var(--nb-line);
}
.st-key-stop_last::after { display: none; }
p.nb-moment { color: var(--nb-brand); font-weight: 700; font-size: 0.95rem; margin: 0; }
[class*="st-key-stop_"] [data-testid="stPageLink"] a { padding: 0; min-height: 0; }
[class*="st-key-stop_"] [data-testid="stPageLink"] a span,
[class*="st-key-stop_"] [data-testid="stPageLink"] a div,
[class*="st-key-stop_"] [data-testid="stPageLink"] a p {
  white-space: normal !important; overflow: visible !important; text-overflow: clip !important;
}
[class*="st-key-stop_"] [data-testid="stPageLink"] a p,
[class*="st-key-stop_"] [data-testid="stPageLink"] a span {
  font-size: 1.2rem; font-weight: 700; color: var(--nb-ink);
  text-decoration: underline; text-underline-offset: 4px; text-decoration-thickness: 1px;
}
[class*="st-key-stop_"] [data-testid="stPageLink"] a:hover p,
[class*="st-key-stop_"] [data-testid="stPageLink"] a:hover span { color: var(--nb-brand); text-decoration-thickness: 2px; }
[class*="st-key-stop_"] [data-testid="stPageLink"] a:hover { background: transparent; }

/* Partner paths are long; let them wrap on a phone instead of running off the edge. */
.st-key-partner_links a { overflow-wrap: anywhere; }
.st-key-partner_links li { margin-bottom: 0.5rem; }

/* Emergency information: the only tinted panel in the app, so it stands apart from
   red buttons and links. */
p.nb-safety { background: var(--nb-alert-bg); border-left: 5px solid var(--nb-brand);
  border-radius: 0 0.25rem 0.25rem 0; padding: 0.75rem 1rem; margin: 0; max-width: 40rem; color: var(--nb-ink); }

/* Form fields: a 3:1 outline so each field can be found without relying on its fill. */
[data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div,
[data-testid="stChatInput"] > div { border-color: var(--nb-field) !important; }

/* Sidebar: logo, then the team, then the menu. */
[data-testid="stSidebarHeader"] { height: auto; padding-top: 1.5rem; padding-bottom: 0.25rem; align-items: flex-start; }
img[data-testid="stSidebarLogo"] { height: 2.75rem; max-width: 100%; object-fit: contain; object-position: left center; }
[data-testid="stSidebarContent"] { display: flex; flex-direction: column; }
[data-testid="stSidebarHeader"] { order: 0; }
[data-testid="stSidebarUserContent"] { order: 1; padding-top: 0.25rem; padding-bottom: 0.5rem; }
[data-testid="stSidebarNav"] { order: 2; }
[data-testid="stSidebarNavSeparator"] { display: none; }
.nb-team { margin: 0; padding: 0 0 1rem; border-bottom: 1px solid var(--nb-line); }
.nb-team p { margin: 0 0 0.6rem; font-size: 0.8rem; font-weight: 700; letter-spacing: 0.06em;
  text-transform: uppercase; color: var(--nb-muted); }
.nb-team ul { list-style: none; margin: 0; padding: 0; }
.nb-team li { margin: 0 0 0.55rem; line-height: 1.3; }
.nb-team li:last-child { margin-bottom: 0; }
.nb-team strong { display: block; font-size: 0.95rem; color: var(--nb-ink); }
.nb-team span { display: block; font-size: 0.85rem; color: var(--nb-muted); }
/* The page you are on: bold, with a red bar. */
[data-testid="stSidebarNavLink"] { border-left: 4px solid transparent; border-radius: 0 0.25rem 0.25rem 0; }
[data-testid="stSidebarNavLink"][aria-current="page"] { border-left-color: var(--nb-brand); }
[data-testid="stSidebarNavLink"][aria-current="page"] span { font-weight: 700; color: var(--nb-ink); }

a:focus-visible, button:focus-visible, [role="tab"]:focus-visible, [role="radio"]:focus-visible,
input:focus-visible, textarea:focus-visible, summary:focus-visible {
  outline: 3px solid var(--nb-brand) !important; outline-offset: 2px;
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; scroll-behavior: auto !important; }
}
/* With the sidebar closed, the red OSHC badge stands in for the logo. */
img[data-testid="stHeaderLogo"] { height: 2rem; object-fit: contain; object-position: left center; }
@media (max-width: 640px) {
  h1.nb-hero { font-size: 2.1rem; }
}
</style>
"""


def apply() -> None:
    """Inject the shared stylesheet. Style-only HTML takes no space on the page."""
    st.html(_CSS)


def hero(first: str, second: str) -> None:
    """The Home headline: one h1, broken where the meaning breaks."""
    st.html(f"<h1 class='nb-hero'>{escape(first)}<br>{escape(second)}</h1>")


def lead(text: str) -> None:
    """The one sentence under a page title that says what the page is for."""
    st.html(f"<p class='nb-lead'>{escape(text)}</p>")


# Who built this, with the project roles the team agreed on 31 October 2026.
TEAM = (
    ("Bikram Bhattarai", "Team lead"),
    ("Md Minhaj Rahman", "Learning design and analytics"),
    ("Aayush Khade", "AI and safety engineer"),
)


def team_credits() -> None:
    """Names and roles, shown in the sidebar directly under the logo."""
    rows = "".join(f"<li><strong>{escape(name)}</strong><span>{escape(role)}</span></li>"
                   for name, role in TEAM)
    st.html(f"<div class='nb-team'><p>Team D5 · Swinburne</p><ul>{rows}</ul></div>")


def safety_line() -> None:
    """Emergency and health-advice numbers, shown the same way everywhere."""
    st.html(f"<p class='nb-safety'>In an emergency, call <strong>000</strong>. For health advice "
            f"at any hour, call healthdirect on "
            f"<strong>{HEALTHDIRECT_NUMBER.replace(' ', '&nbsp;')}</strong>.</p>")
