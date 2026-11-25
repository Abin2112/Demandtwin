param([ValidateSet('online_retail','off_india','twin2k')][string]$Dataset = 'online_retail')
. "$PSScriptRoot/common.ps1"
Invoke-DemandTwinPython (Join-Path $PSScriptRoot 'download_datasets.py') $Dataset
