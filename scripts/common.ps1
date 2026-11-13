$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path $PSScriptRoot -Parent
$Python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$DataRoot = if ($env:IDCS_DATA_DIR) { $env:IDCS_DATA_DIR } else { Join-Path $env:LOCALAPPDATA 'IDCardStudio' }
function Assert-Windows { if ($env:OS -ne 'Windows_NT') { throw 'Run this script on Windows.' } }
function Invoke-Checked { param([string]$Executable,[string[]]$Arguments) & $Executable @Arguments; if ($LASTEXITCODE -ne 0) { throw "$Executable failed with exit code $LASTEXITCODE" } }
