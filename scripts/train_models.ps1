param([ValidateSet('all','retail','sandbox')][string]$Track = 'all')
. "$PSScriptRoot/common.ps1"
if ($Track -ne 'sandbox') { Invoke-DemandTwinPython (Join-Path $PSScriptRoot 'preprocess_all.py') }
Invoke-DemandTwinPython (Join-Path $PSScriptRoot 'train_all.py') --track $Track
