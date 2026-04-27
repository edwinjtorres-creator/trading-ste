param(
    [string]$Path = "tests"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$py = if (Test-Path ".venv/Scripts/python.exe") {
    ".venv/Scripts/python.exe"
} else {
    "python"
}

Write-Host "Running fast pytest on: $Path"
& $py -m pytest -q -n auto --dist worksteal $Path
