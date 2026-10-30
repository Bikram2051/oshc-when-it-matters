"""Shared presentation helpers: one stylesheet, a lead paragraph and the safety line.

Colours and fonts come from .streamlit/config.toml. This file only adds what the
theme cannot express: the journey line, readable measure, caption contrast,
visible keyboard focus and reduced motion.
"""
from __future__ import annotations

from html import escape

import streamlit as st

from oshc.care_navigation import HEALTHDIRECT_NUMBER

_CSS = """
<style>
:root {
  --nb-ink: #1F2A2E;
  --nb-muted: #475357;
  --nb-brand: #1E5B4F;
  --nb-line: #CBD5D1;
  --nb-alert: #B42318;
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

/* Emergency information: red is reserved for this. */
p.nb-safety { border-left: 4px solid var(--nb-alert); padding: 0.2rem 0 0.2rem 0.9rem; margin: 0; max-width: 40rem; }

a:focus-visible, button:focus-visible, [role="tab"]:focus-visible, [role="radio"]:focus-visible,
input:focus-visible, textarea:focus-visible, summary:focus-visible {
  outline: 3px solid var(--nb-brand) !important; outline-offset: 2px;
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; scroll-behavior: auto !important; }
}
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


def safety_line() -> None:
    """Emergency and health-advice numbers, shown the same way everywhere."""
    st.html(f"<p class='nb-safety'>In an emergency, call <strong>000</strong>. For health advice "
            f"at any hour, call healthdirect on "
            f"<strong>{HEALTHDIRECT_NUMBER.replace(' ', '&nbsp;')}</strong>.</p>")
