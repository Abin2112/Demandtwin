param([int]$Port = 3000, [switch]$Development)
. "$PSScriptRoot/common.ps1"
$env:NEXT_TELEMETRY_DISABLED = '1'
Push-Location (Join-Path $DemandTwinRoot 'frontend')
try {
    if (-not $Development -and -not (Test-Path -LiteralPath '.next/BUILD_ID')) {
        Invoke-DemandTwinNpm run build
    }
    $DemandTwinMode = if ($Development) { 'dev' } else { 'start' }
    & node 'node_modules/next/dist/bin/next' $DemandTwinMode --hostname 127.0.0.1 --port $Port
    if ($LASTEXITCODE -ne 0) { throw "Next.js exited with code $LASTEXITCODE." }
} finally { Pop-Location }
