$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command py -ErrorAction SilentlyContinue) -and -not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python 3 non trovato. Installalo da https://www.python.org/downloads/windows/ e abilita 'Add python.exe to PATH'." -ForegroundColor Red
    Read-Host "Premi Invio per uscire"
    exit 1
}

$Python = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    & $Python -3 -m venv .venv 2>$null
    if ($LASTEXITCODE -ne 0) { & $Python -m venv .venv }
}

& .\.venv\Scripts\python.exe -m pip install --disable-pip-version-check -q -r requirements.txt
& .\.venv\Scripts\python.exe local_ready.py
