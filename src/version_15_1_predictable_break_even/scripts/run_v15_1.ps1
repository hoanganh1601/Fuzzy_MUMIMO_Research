# V15.1 official run: development -> lock -> DeepMIMO test -> 3GPP test (same lock) -> combine.
# Run from the package root:
#   powershell -ExecutionPolicy Bypass -File .\scripts\run_v15_1.ps1 `
#     -Development data\dev.npz -DevProvenance data\dev.npz.provenance.json `
#     -TestDM data\dm_test.npz -TestDMProvenance data\dm_test.npz.provenance.json `
#     -Test3GPP data\gpp_test.npz -Test3GPPProvenance data\gpp_test.npz.provenance.json -Tag V151
# Rerun the identical command to resume after an interruption. Do not change any option between runs.
param(
  [Parameter(Mandatory=$true)][string]$Development,
  [Parameter(Mandatory=$true)][string]$DevProvenance,
  [string]$TestDM = "", [string]$TestDMProvenance = "",
  [string]$Test3GPP = "", [string]$Test3GPPProvenance = "",
  [string]$Tag = "V151",
  [string]$Python = "python",
  [switch]$StopAfterLock
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONIOENCODING = "utf-8"
$env:OMP_NUM_THREADS = "1"; $env:OPENBLAS_NUM_THREADS = "1"; $env:MKL_NUM_THREADS = "1"
$out = "outputs"
$dm = "${Tag}_DM"; $g3 = "${Tag}_3GPP"

function Py([string[]]$A) {
  Write-Host ">> $Python $($A -join ' ')"
  & $Python @A
  if ($LASTEXITCODE -ne 0) { throw "Step failed (exit $LASTEXITCODE)" }
}
$common = @("code/run_experiment.py", "--development", $Development, "--dev-provenance", $DevProvenance, "--out-root", $out)

Write-Host "=== 0. Unit tests ==="
Py @("-m", "unittest", "discover", "-s", "tests")
Write-Host "=== 1. Preflight (development only): early_ratio distribution ==="
Py ($common + @("--stage", "preflight", "--run-id", $dm))
Write-Host "=== 2. Development + lock (run id $dm) ==="
Py ($common + @("--stage", "develop", "--run-id", $dm))
if (-not (Test-Path "$out/$dm/CP03_locked_cells.json")) { Py ($common + @("--stage", "lock", "--run-id", $dm)) }
else { Write-Host "Lock already exists - not retrained." }
if ($StopAfterLock) { Write-Host "Stopped after lock as requested."; exit 0 }

$runs = @()
if ($TestDM -ne "") {
  Write-Host "=== 3. DeepMIMO test ==="
  Py ($common + @("--stage", "test", "--run-id", $dm, "--test", $TestDM, "--test-provenance", $TestDMProvenance))
  Py ($common + @("--stage", "report", "--run-id", $dm)); $runs += $dm
}
if ($Test3GPP -ne "") {
  Write-Host "=== 4. 3GPP test with the SAME frozen lock ==="
  Py ($common + @("--stage", "test", "--run-id", $g3, "--test", $Test3GPP, "--test-provenance", $Test3GPPProvenance,
                  "--lock-from", "$out/$dm/CP03_locked_cells.json"))
  Py ($common + @("--stage", "report", "--run-id", $g3)); $runs += $g3
}
if ($runs.Count -ge 2) {
  Write-Host "=== 5. Combined decision ==="
  Py @("code/run_experiment.py", "--stage", "combine", "--run-id", "${Tag}_FINAL", "--combine-runs", ($runs -join ","), "--out-root", $out)
}

$res = "KET_QUA_$Tag"
if (Test-Path $res) { Remove-Item $res -Recurse -Force }
New-Item -ItemType Directory $res | Out-Null
Get-ChildItem $out -Directory -Filter "${Tag}_*" | ForEach-Object {
  $d = Join-Path $res $_.Name; New-Item -ItemType Directory $d | Out-Null
  Copy-Item (Join-Path $_.FullName "CP*") $d
}
Compress-Archive -Path "$res/*" -DestinationPath "$res.zip" -Force
Write-Host "DONE. Send back $res.zip"
