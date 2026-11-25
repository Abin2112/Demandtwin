param([ValidateRange(1024,65535)][int]$ApiPort = 8000, [ValidateRange(1024,65535)][int]$WebPort = 3000, [switch]$Development)
. "$PSScriptRoot/common.ps1"
$DemandTwinBackend = $null
Push-Location $DemandTwinRoot
try {
    if ($ApiPort -eq $WebPort) { throw 'The API and frontend need different ports.' }
    if (-not (Test-Path -LiteralPath $DemandTwinPython) -or -not (Test-Path -LiteralPath 'frontend/node_modules/next/package.json')) {
        throw 'Dependencies are missing. Run scripts/setup.ps1 first.'
    }
    foreach ($DemandTwinPort in @($ApiPort, $WebPort)) {
        $DemandTwinListener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $DemandTwinPort)
        try { $DemandTwinListener.Start() }
        catch { throw "Port $DemandTwinPort is already in use. Close that app or choose different -ApiPort and -WebPort values." }
        finally { $DemandTwinListener.Stop() }
    }
    Set-DemandTwinPythonPath
    Invoke-DemandTwinPython scripts/configure_local.py
    Invoke-DemandTwinPython -m alembic -c backend/alembic.ini upgrade head
    Invoke-DemandTwinPython scripts/doctor.py
    $env:API_ORIGIN = "http://127.0.0.1:$ApiPort"
    if (-not $Development) {
        $DemandTwinBuild = Join-Path $DemandTwinRoot 'frontend/.next/BUILD_ID'
        $DemandTwinOriginFile = Join-Path $DemandTwinRoot 'frontend/.next/demandtwin-api-origin'
        $DemandTwinSources = @(Get-ChildItem frontend/app,frontend/components,frontend/lib -Recurse -File) +
            @(Get-Item frontend/next.config.ts,frontend/package-lock.json,frontend/postcss.config.mjs,frontend/tsconfig.json)
        $DemandTwinNewest = $DemandTwinSources |
            Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
        $DemandTwinNeedsBuild = -not (Test-Path -LiteralPath $DemandTwinBuild) -or
            -not (Test-Path -LiteralPath $DemandTwinOriginFile)
        if (-not $DemandTwinNeedsBuild) {
            $DemandTwinNeedsBuild = $DemandTwinNewest.LastWriteTimeUtc -gt (Get-Item -LiteralPath $DemandTwinBuild).LastWriteTimeUtc -or
                (Get-Content -Raw -LiteralPath $DemandTwinOriginFile).Trim() -ne $env:API_ORIGIN
        }
        if ($DemandTwinNeedsBuild) {
            Invoke-DemandTwinNpm run build
            [IO.File]::WriteAllText($DemandTwinOriginFile, $env:API_ORIGIN)
        }
    }
    $DemandTwinLogs = Join-Path $DemandTwinRoot 'data/runtime'
    $DemandTwinBackend = Start-Process -FilePath $DemandTwinPython -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port',"$ApiPort" -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $DemandTwinLogs 'api-out.log') -RedirectStandardError (Join-Path $DemandTwinLogs 'api-error.log')
    $DemandTwinReady = $false
    for ($try = 0; $try -lt 40; $try++) {
        if ($DemandTwinBackend.HasExited) { break }
        try {
            $check = Invoke-RestMethod "$env:API_ORIGIN/api/v1/health" -TimeoutSec 2
            if ($check.status -eq 'ok') { $DemandTwinReady = $true; break }
        } catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $DemandTwinReady) { throw "API startup failed. See $DemandTwinLogs/api-error.log." }
    Write-Host "DemandTwin  http://127.0.0.1:$WebPort"
    Write-Host "API docs    $env:API_ORIGIN/docs"
    & "$PSScriptRoot/start_frontend.ps1" -Port $WebPort -Development:$Development
} finally {
    if ($DemandTwinBackend -and -not $DemandTwinBackend.HasExited) { Stop-Process -Id $DemandTwinBackend.Id }
    Pop-Location
}
