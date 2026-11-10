# Run manuscript Section V (A-D) end to end on Windows PowerShell.
# Usage (from this folder):
#   powershell -ExecutionPolicy Bypass -File .\CHAY_TOAN_BO.ps1 -Dev "D:\data\deepmimo_v10.npz" -Tag V11
# Optional independent test sets (protocol is locked before they are read):
#   -TestDM "D:\data\deepmimo_new.npz" -TestDMProv "D:\data\deepmimo_new_provenance.json"
#   -Test3GPP "D:\data\sionna_3gpp.npz" -Test3GPPProv "D:\data\sionna_provenance.json"
# Rerun the same command with the same -Tag to resume after an interruption.
param(
  [Parameter(Mandatory = $true)][string]$Dev,
  [string]$Tag = "V11",
  [string]$DevLabel = "DeepMIMO v10 development set",
  [string]$TestDM = "", [string]$TestDMProv = "",
  [string]$Test3GPP = "", [string]$Test3GPPProv = "",
  [string]$Python = "python",
  [int]$Repeats = 5, [int]$Bootstrap = 2000
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$env:PYTHONIOENCODING = "utf-8"
$out = "outputs"

function Invoke-Py([string[]]$PyArgs) {
  Write-Host ">> $Python $($PyArgs -join ' ')"
  & $Python @PyArgs
  if ($LASTEXITCODE -ne 0) { throw "Step failed (exit $LASTEXITCODE): $($PyArgs -join ' ')" }
}

Write-Host "=== [1/3] Environment check ==="
Invoke-Py @("code/check_env.py", "--data", $Dev)

Write-Host "=== [2/3] Lock independent-test protocols (before any test data are read) ==="
$testArgs = @()
$pairs = @(@("${Tag}_DM", $TestDM, $TestDMProv), @("${Tag}_3GPP", $Test3GPP, $Test3GPPProv))
foreach ($p in $pairs) {
  if ($p[1] -ne "") {
    if ($p[2] -eq "") { throw "Missing provenance JSON for $($p[1])" }
    if (-not (Test-Path "$out/$($p[0])/CP00_locked_protocol.json")) {
      Invoke-Py @("code/independent_validation.py", "--stage", "lock", "--run-id", $p[0], "--out-root", $out,
                  "--repeats", "$Repeats", "--bootstrap", "$Bootstrap")
    }
    $testArgs += @("--test", $p[0], $p[1], $p[2])
  }
}

Write-Host "=== [3/3] Sections A, B, C (and D if test sets given) ==="
$runArgs = @("code/run_manuscript.py", "--tag", $Tag, "--dev", $Dev, "--dev-label", $DevLabel, "--out-root", $out,
             "--repeats", "$Repeats", "--bootstrap", "$Bootstrap") + $testArgs
if ($testArgs.Count -eq 0) { $runArgs += @("--skip", "D") }
Invoke-Py $runArgs

# Collect the small result files to send back (task checkpoints are left in place).
$res = "KET_QUA_$Tag"
if (Test-Path $res) { Remove-Item $res -Recurse -Force }
New-Item -ItemType Directory $res | Out-Null
Copy-Item "ENV_CHECK.json", "$out/${Tag}_MANUSCRIPT_TABLES.md", "$out/${Tag}_manuscript_results.json" $res
Get-ChildItem $out -Directory -Filter "${Tag}_*" | ForEach-Object {
  $d = Join-Path $res $_.Name; New-Item -ItemType Directory $d | Out-Null
  Copy-Item (Join-Path $_.FullName "CP0*") $d
}
Compress-Archive -Path "$res/*" -DestinationPath "$res.zip" -Force
Write-Host ""
Write-Host "DONE. Tables: $out/${Tag}_MANUSCRIPT_TABLES.md"
Write-Host "Send back: $res.zip"
