$ErrorActionPreference = 'Stop'
$DemandTwinRoot = Split-Path -Parent $PSScriptRoot
$DemandTwinPython = Join-Path $DemandTwinRoot '.venv/Scripts/python.exe'
function Invoke-DemandTwinPython {
    & $DemandTwinPython @args
    if ($LASTEXITCODE -ne 0) { throw "DemandTwin Python exited with code $LASTEXITCODE." }
}
function Invoke-DemandTwinNpm {
    & npm.cmd --prefix (Join-Path $DemandTwinRoot 'frontend') @args
    if ($LASTEXITCODE -ne 0) { throw "npm exited with code $LASTEXITCODE." }
}
function Set-DemandTwinPythonPath {
    $env:PYTHONPATH = (Join-Path $DemandTwinRoot 'backend') + [IO.Path]::PathSeparator + (Join-Path $DemandTwinRoot 'ml-engine')
}
