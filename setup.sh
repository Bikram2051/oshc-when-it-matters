#!/usr/bin/env bash
set -euo pipefail
echo "OSHC When It Matters :: setup"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
[ -f .env ] || cp .env.example .env
echo "Running tests..."
pytest
echo
echo "Done. Activate with: source .venv/bin/activate"
echo "Run the app with:   streamlit run app/Home.py"
