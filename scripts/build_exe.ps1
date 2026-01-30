param(
    [string]$Name = "E2-HUD-Designer"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Resolve-Path (Join-Path $scriptDir "..")
$mainPath = Join-Path $rootDir "main.py"

if (-not (Test-Path $mainPath)) {
    throw "main.py not found at $mainPath"
}

Push-Location $rootDir
try {
    python -m pip install --upgrade pyinstaller | Out-Null
    pyinstaller --noconfirm --onefile --windowed --name $Name $mainPath
    Write-Host "Build complete. Output in dist/$Name.exe"
}
finally {
    Pop-Location
}
