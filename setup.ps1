# OSHC When It Matters :: setup (Windows PowerShell)
$ErrorActionPreference = "Stop"
Write-Host "OSHC When It Matters :: setup"
python -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "Python environment creation failed." }
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip installation failed. Resolve the error above before continuing." }
python -m pip install -e ".[dev]"
if ($LASTEXITCODE -ne 0) { throw "Project dependency installation failed. Resolve the error above before starting the app." }
if (-Not (Test-Path .env)) { Copy-Item .env.example .env }
python scripts/bootstrap_sources.py
if ($LASTEXITCODE -ne 0) { throw "Source restoration failed. Follow the restore guidance before running source integration tests." }
Write-Host "Running tests..."
$previousOffline = $env:OSHC_OFFLINE
$previousLive = $env:OSHC_ENABLE_LIVE
try {
    $env:OSHC_OFFLINE = "1"
    $env:OSHC_ENABLE_LIVE = "0"
    python -m pytest
    if ($LASTEXITCODE -ne 0) { throw "Tests failed." }
}
finally {
    $env:OSHC_OFFLINE = $previousOffline
    $env:OSHC_ENABLE_LIVE = $previousLive
}
Write-Host ""
Write-Host "Done. Activate with: .\.venv\Scripts\Activate.ps1"
Write-Host "Run the app with:   streamlit run app/Home.py"
