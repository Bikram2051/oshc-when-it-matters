param([string]$Python = "python")
$ErrorActionPreference = "Stop"
$packageRoot = $PSScriptRoot
$manifest = Get-Content -LiteralPath (Join-Path $packageRoot "package_manifest.json") -Raw | ConvertFrom-Json
$runtimeRoot = Join-Path (Split-Path $packageRoot -Parent) ("NextBest-env-" + $manifest.source_commit.Substring(0, 12))
$runtimePython = Join-Path $runtimeRoot "Scripts\python.exe"

$env:OSHC_OFFLINE = "1"
$env:OSHC_ENABLE_LIVE = "0"
$env:OSHC_MODEL = "claude-haiku-4-5-20251001"

if (-not (Test-Path -LiteralPath $runtimePython -PathType Leaf)) {
    if (Test-Path -LiteralPath $runtimeRoot) {
        throw "A partial runtime folder exists: $runtimeRoot. Keep it and inspect the setup error."
    }
    $actual = & $Python -I -c "import platform; print('|'.join((platform.python_version(), platform.system(), platform.machine())))"
    if ($LASTEXITCODE -ne 0) { throw "Could not inspect the selected Python." }
    $expected = "$($manifest.environment.python)|$($manifest.environment.system)|$($manifest.environment.machine)"
    if ($actual -ne $expected) { throw "This package requires $expected. Selected Python reports $actual." }
    & $Python -I -m venv $runtimeRoot
    if ($LASTEXITCODE -ne 0) { throw "Could not create the demo environment." }
    & $runtimePython -I -m pip --isolated install --no-index --no-deps --require-hashes --find-links (Join-Path $packageRoot "wheelhouse") -r (Join-Path $packageRoot "requirements.lock")
    if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
}

& $runtimePython -I -B (Join-Path $packageRoot "verify_demo.py") --integrity-only
if ($LASTEXITCODE -ne 0) { throw "Package verification failed." }

Push-Location $packageRoot
try {
    & $runtimePython -I -B -m streamlit run app/Home.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false
    if ($LASTEXITCODE -ne 0) { throw "Streamlit stopped with an error." }
}
finally {
    Pop-Location
}
