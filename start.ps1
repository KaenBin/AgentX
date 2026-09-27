param([int]$Port = 8010)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$appPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $appPython)) {
    throw 'Create the environment first: python -m venv .venv; then install requirements.txt.'
}
& $appPython -m uvicorn src.main:app --host 127.0.0.1 --port $Port
