$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $pythonExe)) {
    Write-Error "MissionChief Bot setup is missing. Follow the setup instructions in README.md first."
    exit 1
}

Push-Location -LiteralPath $projectRoot
try {
    & $pythonExe (Join-Path $projectRoot "Main.py") @args
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
