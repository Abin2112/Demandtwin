param([switch]$SkipBrowser)
. "$PSScriptRoot/common.ps1"
Push-Location $DemandTwinRoot
try {
    Invoke-DemandTwinPython -m pytest -q
    Invoke-DemandTwinNpm run typecheck
    Invoke-DemandTwinNpm run build
    if (-not $SkipBrowser) {
        if (-not $env:PLAYWRIGHT_CHROMIUM_EXECUTABLE) {
            $DemandTwinChrome = Join-Path $env:ProgramFiles 'Google/Chrome/Application/chrome.exe'
            if (Test-Path -LiteralPath $DemandTwinChrome) {
                $env:PLAYWRIGHT_CHROMIUM_EXECUTABLE = $DemandTwinChrome
            }
        }
        Invoke-DemandTwinNpm test
    }
} finally { Pop-Location }
