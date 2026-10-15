"""Additional chat emergency routing; the measured baseline remains unchanged."""
import re

# Emergency routing precedes every other gate, including length and privacy.
# These patterns recognise descriptions of immediate danger, not diagnoses.
_DANGER = re.compile(
    r"\b(?:cannot|can not|can't|cant|unable to|struggling to)\s+(?:breathe|get (?:any )?air)\b|"
    r"\b(?:throat|tongue|airway)\b.{0,45}\b(?:swell\w*|clos\w*)\b|"
    r"\b(?:choking|gasping|unresponsive|collapsed)\b|"
    r"\b(?:blood|bleeding)\b.{0,65}\b(?:spurting|gushing|profusely|won't stop|will not stop|not stop|uncontroll\w*)\b|"
    r"\b(?:took|taken|swallowed|taking)\b.{0,35}\b(?:too many|large (?:amount|number)|handful|bottle|packet)\b.{0,25}\b(?:pills|tablets|medicine|medication)\b|"
    r"\b(?:end|ending|take|taking)\s+my\s+(?:own\s+)?life\b|"
    r"\b(?:hurt|harm|kill)\s+(?:myself|my self)\b|"
    r"\b(?:jump|jumping)\b.{0,35}\b(?:bridge|roof|building|train)\b|"
    r"\b(?:face|mouth)\b.{0,25}\bdroop\w*\b|"
    r"\b(?:suddenly|sudden)\b.{0,30}\b(?:cannot speak|can't speak|slurred speech)\b"
)


def immediate_danger(normalised_text: str) -> bool:
    return bool(_DANGER.search(normalised_text))
