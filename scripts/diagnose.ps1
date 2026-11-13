param([switch]$CorelTest)
. "$PSScriptRoot\common.ps1"
Assert-Windows
Set-Location $ProjectRoot
$Arguments = @('windows-agent\diagnostics\check.py')
if ($CorelTest) {
    if (Test-Path (Join-Path $DataRoot 'runtime.lock')) { throw 'Stop ID Card Studio before the interactive CorelDRAW diagnostic to avoid concurrent automation.' }
    $Arguments += '--corel-test'
}
Invoke-Checked $Python $Arguments
