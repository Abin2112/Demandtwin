param([int]$Port = 8000)
. "$PSScriptRoot/common.ps1"
Push-Location $DemandTwinRoot
try {
    Set-DemandTwinPythonPath
    Invoke-DemandTwinPython -m alembic -c backend/alembic.ini upgrade head
    Invoke-DemandTwinPython -m uvicorn app.main:app --host 127.0.0.1 --port $Port
} finally { Pop-Location }
