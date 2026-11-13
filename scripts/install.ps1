. "$PSScriptRoot\common.ps1"
Assert-Windows
Set-Location $ProjectRoot
if ([Environment]::OSVersion.Version.Major -lt 10) { throw 'Windows 10/11 required; verify the OS supported by your installed CorelDRAW and Nikon versions.' }
if (!(Get-Command py -ErrorAction SilentlyContinue)) { throw 'Install 64-bit Python 3.12 from python.org, including the Python launcher, then rerun.' }
Invoke-Checked 'py' @('-3.12','-c','import struct; assert struct.calcsize(chr(80))==8')
if (!(Get-Command node -ErrorAction SilentlyContinue)) { throw 'Install Node.js 22 LTS or newer from nodejs.org, then rerun.' }
Invoke-Checked 'node' @('-e','if(Number(process.versions.node.split(String.fromCharCode(46))[0])<22)process.exit(1)')
New-Item -ItemType Directory -Force -Path $DataRoot | Out-Null
$Identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
Invoke-Checked 'icacls.exe' @($DataRoot,'/inheritance:r','/grant:r',"${Identity}:(OI)(CI)F",'SYSTEM:(OI)(CI)F')
Invoke-Checked 'py' @('-3.12','-m','venv','.venv')
Invoke-Checked $Python @('-m','pip','install','--upgrade','pip')
Invoke-Checked $Python @('-m','pip','install','-r','backend\requirements.txt')
Invoke-Checked $Python @('-m','backend.app.maintenance','init')
Invoke-Checked $Python @('-m','alembic','-c','backend\alembic.ini','upgrade','head')
Push-Location frontend
try {
    if (Test-Path package-lock.json) { Invoke-Checked 'npm.cmd' @('ci') } else { Invoke-Checked 'npm.cmd' @('install') }
    Invoke-Checked 'npm.cmd' @('run','typecheck')
    Invoke-Checked 'npm.cmd' @('run','build')
} finally { Pop-Location }
Invoke-Checked $Python @('-m','pytest','tests','-q')
Invoke-Checked $Python @('windows-agent\diagnostics\check.py')
$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'ID Card Studio.lnk'))
$Shortcut.TargetPath = Join-Path $ProjectRoot 'Start ID Card Studio.bat'
$Shortcut.WorkingDirectory = $ProjectRoot
$Shortcut.WindowStyle = 7
$Shortcut.Save()
Write-Host 'Installation complete. Launch Start ID Card Studio.bat. Run diagnose.ps1 -CorelTest for the optional interactive CorelDRAW test.'
