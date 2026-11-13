. "$PSScriptRoot\common.ps1"
Assert-Windows
if (Test-Path (Join-Path $DataRoot 'runtime.lock')) {
    New-Item -ItemType File -Force -Path (Join-Path $DataRoot 'shutdown.request') | Out-Null
    $Deadline = (Get-Date).AddSeconds(200)
    while ((Test-Path (Join-Path $DataRoot 'runtime.lock')) -and (Get-Date) -lt $Deadline) { Start-Sleep -Seconds 1 }
    if (Test-Path (Join-Path $DataRoot 'runtime.lock')) { throw 'Shutdown did not finish. Inspect logs and Task Manager; do not restore while processes are running.' }
}
Write-Host 'ID Card Studio stopped. CorelDRAW remains open.'
