param([Parameter(Mandatory=$true)][string]$Archive)
. "$PSScriptRoot\common.ps1"
Assert-Windows
Set-Location $ProjectRoot
Invoke-Checked $Python @('-m','backend.app.maintenance','restore','--archive',(Resolve-Path $Archive).Path)
Invoke-Checked $Python @('-m','alembic','-c','backend\alembic.ini','upgrade','head')
