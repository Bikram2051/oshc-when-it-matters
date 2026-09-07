# OSHC When It Matters :: setup (Windows PowerShell)
$ErrorActionPreference = "Stop"
Write-Host "OSHC When It Matters :: setup"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
if (-Not (Test-Path .env)) { Copy-Item .env.example .env }
Write-Host "Running tests..."
pytest
Write-Host ""
Write-Host "Done. Activate with: .\.venv\Scripts\Activate.ps1"
Write-Host "Run the app with:   streamlit run app/Home.py"
