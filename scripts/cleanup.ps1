. "$PSScriptRoot\common.ps1"
Assert-Windows
Set-Location $ProjectRoot
Invoke-Checked $Python @('-m','backend.app.maintenance','cleanup')
