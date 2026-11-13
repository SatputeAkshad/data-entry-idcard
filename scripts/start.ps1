. "$PSScriptRoot\common.ps1"
Assert-Windows
if (!(Test-Path $Python)) { throw 'Run scripts\install.ps1 first.' }
if (!(Test-Path (Join-Path $ProjectRoot 'frontend\out\index.html'))) { throw 'Frontend build missing. Run install.ps1.' }
$PythonW = Join-Path $ProjectRoot '.venv\Scripts\pythonw.exe'
Start-Process -FilePath $PythonW -ArgumentList @('"'+(Join-Path $PSScriptRoot 'launcher.py')+'"') -WorkingDirectory $ProjectRoot
