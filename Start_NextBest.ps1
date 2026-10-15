param(
    [string]$Python = "",
    [int]$Port = 8502
)
$ErrorActionPreference = "Stop"
if (-not $Python) {
    $localPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
    $activePython = if ($env:VIRTUAL_ENV) { Join-Path $env:VIRTUAL_ENV "Scripts\python.exe" } else { "" }
    $Python = if ($activePython -and (Test-Path -LiteralPath $activePython -PathType Leaf)) {
        $activePython
    } elseif (Test-Path -LiteralPath $localPython -PathType Leaf) {
        $localPython
    } else { "python" }
}

$env:OSHC_OFFLINE = "0"
$env:OSHC_ENABLE_LIVE = "1"
$env:OSHC_MODEL = "claude-haiku-4-5-20251001"
$env:PYTHONUTF8 = "1"

Push-Location $PSScriptRoot
try {
    & $Python -c "import streamlit, pymupdf, pydantic, rank_bm25, anthropic"
    if ($LASTEXITCODE -ne 0) {
        throw "Install the project runtime or pass -Python with the path to your existing project environment."
    }
    & $Python -m streamlit run app/Home.py --server.address 127.0.0.1 --server.port $Port --server.headless true --browser.gatherUsageStats false
    if ($LASTEXITCODE -ne 0) { throw "Streamlit stopped with an error." }
}
finally { Pop-Location }
