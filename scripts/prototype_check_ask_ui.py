"""Compatibility entry point for the current guarded chat development checks.

The 13 October retrieval-only checkpoint is preserved in ask_ui_check.json and
Git history. Its scores do not measure the later chat scope boundary. Use this
command or prototype_check_student_chat.py with a fresh --out path for today's
development smoke checks; neither command runs held-out evaluation.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.prototype_check_student_chat import main

if __name__ == "__main__":
    main()
