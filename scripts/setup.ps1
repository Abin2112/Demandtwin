param([switch]$Research)
. "$PSScriptRoot/common.ps1"
Push-Location $DemandTwinRoot
try {
    if (-not (Test-Path -LiteralPath $DemandTwinPython)) {
        & python -m venv --without-pip .venv
        if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment.' }
    }
    $requirements = if ($Research) { 'backend/requirements-research.txt' } else { 'backend/requirements.txt' }
    & python -m pip --python $DemandTwinPython install -r $requirements
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    Invoke-DemandTwinNpm ci --no-audit --no-fund
    Set-DemandTwinPythonPath
    Invoke-DemandTwinPython scripts/configure_local.py
    Invoke-DemandTwinPython -m alembic -c backend/alembic.ini upgrade head
    Invoke-DemandTwinPython scripts/doctor.py
    Write-Host 'Setup complete. Run scripts/start_all.ps1 to open the local app.'
} finally { Pop-Location }
