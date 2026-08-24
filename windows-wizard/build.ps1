$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$Python = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } elseif (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { throw "Python 3 non trovato" }

if (-not (Test-Path ".venv-build\Scripts\python.exe")) {
    & $Python -3 -m venv .venv-build 2>$null
    if ($LASTEXITCODE -ne 0) { & $Python -m venv .venv-build }
}

$Py = ".\.venv-build\Scripts\python.exe"
& $Py -m pip install --upgrade pip
& $Py -m pip install -r requirements.txt pyinstaller

& $Py -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name StreamStackSetupWizard `
    --collect-all customtkinter `
    --hidden-import app `
    --hidden-import remote `
    --hidden-import launcher `
    --hidden-import demo_launcher `
    local_ready.py

Write-Host ""
Write-Host "Build completata: $PSScriptRoot\dist\StreamStackSetupWizard.exe" -ForegroundColor Green
