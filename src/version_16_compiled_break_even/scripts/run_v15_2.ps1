# V15.2 official run in three phases (run from any folder; paths relative to the package root).
#   Phase develop : unit tests -> development preflight -> develop -> lock
#   Phase select  : build sealed test sets AFTER the lock (covariate stratification of pools, or given files)
#                   -> test-preflight for both sources (no runtime measured)
#   Phase test    : runtime test DeepMIMO + 3GPP (same lock) -> report -> combine -> KET_QUA_<Tag>.zip
# Example:
#   powershell -ExecutionPolicy Bypass -File .\scripts\run_v15_2.ps1 -Phase develop -Development data\dev.npz -DevProvenance data\dev.npz.provenance.json -Tag V152
#   powershell -ExecutionPolicy Bypass -File .\scripts\run_v15_2.ps1 -Phase select  -Development data\dev.npz -DevProvenance data\dev.npz.provenance.json -Tag V152 `
#       -PoolDM data\dm_pool.npz -PoolDMProvenance data\dm_pool.npz.provenance.json -Pool3GPP data\gpp_pool.npz -Pool3GPPProvenance data\gpp_pool.npz.provenance.json
#   powershell -ExecutionPolicy Bypass -File .\scripts\run_v15_2.ps1 -Phase test    -Development data\dev.npz -DevProvenance data\dev.npz.provenance.json -Tag V152
# Rerun the identical command to resume. Never change options between phases.
param(
  [Parameter(Mandatory=$true)][ValidateSet("develop","select","test")][string]$Phase,
  [Parameter(Mandatory=$true)][string]$Development,
  [Parameter(Mandatory=$true)][string]$DevProvenance,
  [string]$Tag = "V152",
  [string]$PoolDM = "", [string]$PoolDMProvenance = "",
  [string]$Pool3GPP = "", [string]$Pool3GPPProvenance = "",
  [string]$TestDM = "", [string]$TestDMProvenance = "",
  [string]$Test3GPP = "", [string]$Test3GPPProvenance = "",
  [int]$RegionGroups = 15, [int]$OutsideGroups = 15,
  [string]$Python = "python"
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONIOENCODING = "utf-8"
$env:OMP_NUM_THREADS = "1"; $env:OPENBLAS_NUM_THREADS = "1"; $env:MKL_NUM_THREADS = "1"
$out = "outputs"; $dm = "${Tag}_DM"; $g3 = "${Tag}_3GPP"; $lock = "$out/$dm/CP03_locked_cells.json"
$dmFile = "data/${Tag}_dm_test.npz"; $g3File = "data/${Tag}_3gpp_test.npz"

function Py([string[]]$A) {
  Write-Host ">> $Python $($A -join ' ')"
  & $Python @A
  if ($LASTEXITCODE -ne 0) { throw "Step failed (exit $LASTEXITCODE)" }
}
$common = @("code/run_experiment.py", "--development", $Development, "--dev-provenance", $DevProvenance, "--out-root", $out)

if ($Phase -eq "develop") {
  Py @("-m", "unittest", "discover", "-s", "tests")
  Py ($common + @("--stage", "preflight", "--run-id", $dm))
  Py ($common + @("--stage", "develop", "--run-id", $dm))
  if (-not (Test-Path $lock)) { Py ($common + @("--stage", "lock", "--run-id", $dm)) } else { Write-Host "Lock exists - not retrained." }
  Write-Host "PHASE develop DONE. Lock: $lock  -> now prepare/seal test pools, then run -Phase select."
  exit 0
}

if (-not (Test-Path $lock)) { throw "No lock found ($lock). Run -Phase develop first." }

if ($Phase -eq "select") {
  foreach ($s in @(@("DM", $PoolDM, $PoolDMProvenance, $TestDM, $TestDMProvenance, $dmFile, $dm, ""),
                   @("3GPP", $Pool3GPP, $Pool3GPPProvenance, $Test3GPP, $Test3GPPProvenance, $g3File, $g3, $lock))) {
    $name, $pool, $poolProv, $test, $testProv, $target, $rid, $lockFrom = $s
    if ($pool -ne "") {
      Py @("code/stratify_test_pool.py", "--pool", $pool, "--pool-provenance", $poolProv, "--manifest", "$out/$dm/CP00_manifest.json",
           "--lock", $lock, "--region-groups", "$RegionGroups", "--outside-groups", "$OutsideGroups", "--output", $target)
    } elseif ($test -ne "") {
      Copy-Item $test $target -Force; Copy-Item $testProv "$target.provenance.json" -Force
    } else { Write-Host "No $name pool/test given - skipped."; continue }
    $a = $common + @("--stage", "test-preflight", "--run-id", $rid, "--test", $target)
    if ($lockFrom -ne "") { $a += @("--lock-from", $lockFrom) }
    Py $a
  }
  Write-Host "PHASE select DONE. If a source was REJECTED, build a new sealed pool with more cell-edge drops and rerun -Phase select."
  exit 0
}

# Phase test
$runs = @()
foreach ($s in @(@($dmFile, $dm, ""), @($g3File, $g3, $lock))) {
  $target, $rid, $lockFrom = $s
  if (-not (Test-Path $target)) { continue }
  $a = $common + @("--stage", "test", "--run-id", $rid, "--test", $target, "--test-provenance", "$target.provenance.json")
  if ($lockFrom -ne "") { $a += @("--lock-from", $lockFrom) }
  Py $a
  Py ($common + @("--stage", "report", "--run-id", $rid)); $runs += $rid
}
if ($runs.Count -ge 2) { Py @("code/run_experiment.py", "--stage", "combine", "--run-id", "${Tag}_FINAL", "--combine-runs", ($runs -join ","), "--out-root", $out) }
$res = "KET_QUA_$Tag"
if (Test-Path $res) { Remove-Item $res -Recurse -Force }
New-Item -ItemType Directory $res | Out-Null
Get-ChildItem $out -Directory -Filter "${Tag}_*" | ForEach-Object {
  $d = Join-Path $res $_.Name; New-Item -ItemType Directory $d | Out-Null
  Copy-Item (Join-Path $_.FullName "CP*") $d
  if (Test-Path (Join-Path $_.FullName "TEST_SELECTION_LOG.csv")) { Copy-Item (Join-Path $_.FullName "TEST_SELECTION_LOG.csv") $d }
}
Compress-Archive -Path "$res/*" -DestinationPath "$res.zip" -Force
Write-Host "DONE. Send back $res.zip"
