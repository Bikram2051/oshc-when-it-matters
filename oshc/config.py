"""Paths and settings. No secrets in this file."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = ROOT / "corpus"        # gitignored, shared privately
DATA_DIR = ROOT / "data"
GOLD_DIR = DATA_DIR / "gold"
PROBE_DIR = DATA_DIR / "probes"
RULES_CSV = DATA_DIR / "rules" / "benefit_rules.csv"
CACHE_DIR = ROOT / "cache" / "llm"  # committed
EVENTS_DB = ROOT / "data" / "events.sqlite"

OFFLINE = os.getenv("OSHC_OFFLINE") == "1"
MODEL = os.getenv("OSHC_MODEL", "unset-model")

# Ship condition from the architecture plan. The conversational surface does
# not go in front of anyone below this.
REFUSAL_RECALL_FLOOR = 0.90

# Below this, the MBS matcher abstains and the line is marked
# "not an MBS item, check the PDS".
MBS_MATCH_FLOOR = 0.88

LANGUAGES = ("en", "hi")  # English, Hindi. Static strings only, no runtime translation.
