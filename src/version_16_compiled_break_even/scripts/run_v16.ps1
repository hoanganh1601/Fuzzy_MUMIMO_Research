# V16 extension of the frozen V15.2 study (run from any folder; paths relative to the package root).
# Phases:
#   check            : build compiled solver, selftest, unit tests, check that the V15.2 lock is reusable on this machine
#   transfer         : ONLY if 'check' reports a machine-only difference: transfer the lock (policy map unchanged)
#   compiled         : compiled CARD/EARLY/ROUTED on the V15.2 development set and both V15.2 test sets
#   model            : analytical break-even model, fitted on development, validated on both test sets (Python and compiled)
#   natural-protocol : freeze the natural-prevalence protocol (needs -NaturalPool), BEFORE sampling
#   natural          : sample -> V15.2 test with the frozen lock -> compiled run -> endpoints N1-N4 -> KET_QUA_V16.zip
# Example:
#   powershell -ExecutionPolicy Bypass -File .\scripts\run_v16.ps1 -Phase check -Development data\dev.npz -DevProvenance data\dev.npz.provenance.json
param(
  [Parameter(Mandatory=$true)][ValidateSet("check","transfer","compiled","model","natural-protocol","natural")][string]$Phase,
  [Parameter(Mandatory=$true)][string]$Development,
  [Parameter(Mandatory=$true)][string]$DevProvenance,
  [string]$Tag = "V152",
  [string]$NaturalPool = "", [string]$NaturalPoolProvenance = "", [int]$NaturalGroups = 100,
  [string]$Python = "python"
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONIOENCODING = "utf-8"
$env:OMP_NUM_THREADS = "1"; $env:OPENBLAS_NUM_THREADS = "1"; $env:MKL_NUM_THREADS = "1"
$out = "outputs"; $dm = "${Tag}_DM"; $g3 = "${Tag}_3GPP"
$origManifest = "$out/$dm/CP00_manifest.json"; $origLock = "$out/$dm/CP03_locked_cells.json"
$tRun = "V16_T"; $tManifest = "$out/$tRun/CP00_manifest.json"; $tLock = "$out/$tRun/CP03T_transferred_lock.json"
if (Test-Path $tLock) { $Manifest = $tManifest; $Lock = $tLock; $LockRun = $tRun; Write-Host "Using TRANSFERRED lock $tLock" }
else { $Manifest = $origManifest; $Lock = $origLock; $LockRun = $dm }
$dmTest = "data/${Tag}_dm_test.npz"; $g3Test = "data/${Tag}_3gpp_test.npz"

function Py([string[]]$A) {
  Write-Host ">> $Python $($A -join ' ')"
  & $Python @A
  if ($LASTEXITCODE -ne 0) { throw "Step failed (exit $LASTEXITCODE)" }
}

switch ($Phase) {
  "check" {
    Py @("code/native_search.py", "--build", "--selftest")
    Py @("-m", "unittest", "discover", "-s", "tests")
    Write-Host ">> lock compatibility check"
    & $Python code/lock_transfer.py --stage check --manifest $origManifest --lock $origLock --development $Development
    if ($LASTEXITCODE -eq 0) { Write-Host "OK: the V15.2 lock is reusable as is." }
    else { Write-Host "The lock differs from this machine. If ONLY 'machine' differs, run -Phase transfer. Otherwise stop and report." }
  }
  "transfer" {
    Py @("code/lock_transfer.py", "--stage", "transfer", "--manifest", $origManifest, "--lock", $origLock, "--development", $Development,
         "--dev-provenance", $DevProvenance, "--new-run-id", $tRun, "--out-root", $out)
  }
  "compiled" {
    Py @("code/compiled_benchmark.py", "--data", $Development, "--manifest", $Manifest, "--lock", $Lock, "--run-id", "C16_DEV", "--out-root", $out)   # no --python-run: CP06 belongs to the test sets, not to development
    Py @("code/compiled_benchmark.py", "--data", $dmTest, "--manifest", $Manifest, "--lock", $Lock, "--run-id", "C16_DM", "--out-root", $out, "--python-run", "$out/$dm")
    Py @("code/compiled_benchmark.py", "--data", $g3Test, "--manifest", $Manifest, "--lock", $Lock, "--run-id", "C16_3GPP", "--out-root", $out, "--python-run", "$out/$g3")
  }
  "model" {
    Py @("code/breakeven_model.py", "--manifest", $Manifest, "--run-id", "M16_PY", "--out-root", $out,
         "--fit", $Development, "$out/${dm}:development", "--validate", "DM", $dmTest, "$out/${dm}:test", "--validate", "3GPP", $g3Test, "$out/${g3}:test")
    Py @("code/breakeven_model.py", "--manifest", $Manifest, "--run-id", "M16_C", "--out-root", $out,
         "--fit", $Development, "$out/C16_DEV", "--validate", "DM", $dmTest, "$out/C16_DM", "--validate", "3GPP", $g3Test, "$out/C16_3GPP")
  }
  "natural-protocol" {
    if ($NaturalPool -eq "") { throw "Give -NaturalPool (sealed pool, uniform user drops, never measured)" }
    Py @("code/natural_prevalence.py", "--stage", "protocol", "--run-id", "NP16", "--out-root", $out, "--manifest", $Manifest, "--lock", $Lock,
         "--pool", $NaturalPool, "--n-groups", "$NaturalGroups")
    Write-Host "Protocol frozen: $out/NP16/NP00_natural_protocol.json. Now run -Phase natural with the same -NaturalPool."
  }
  "natural" {
    if ($NaturalPool -eq "") { throw "Give -NaturalPool" }
    $sample = "data/V16_natural_sample.npz"; $nrun = "V16_NAT"
    Py @("code/natural_prevalence.py", "--stage", "sample", "--run-id", "NP16", "--out-root", $out, "--pool", $NaturalPool,
         "--pool-provenance", $NaturalPoolProvenance, "--output", $sample)
    $c = @("code/run_experiment.py", "--development", $Development, "--dev-provenance", $DevProvenance, "--out-root", $out, "--run-id", $nrun, "--lock-from", $Lock)
    Py ($c + @("--stage", "test-preflight", "--test", $sample))
    Py ($c + @("--stage", "test", "--test", $sample, "--test-provenance", "$sample.provenance.json", "--allow-small-region"))
    Py ($c + @("--stage", "report"))
    Py @("code/compiled_benchmark.py", "--data", $sample, "--manifest", $Manifest, "--lock", $Lock, "--run-id", "C16_NAT", "--out-root", $out, "--python-run", "$out/$nrun")
    Py @("code/natural_prevalence.py", "--stage", "analyze", "--run-id", "NP16", "--out-root", $out, "--v152-run", "$out/$nrun", "--compiled-run", "$out/C16_NAT")
    $res = "KET_QUA_V16"
    if (Test-Path $res) { Remove-Item $res -Recurse -Force }
    New-Item -ItemType Directory $res | Out-Null
    foreach ($d in @("C16_DEV","C16_DM","C16_3GPP","C16_NAT","M16_PY","M16_C","NP16",$nrun,$tRun)) {
      if (Test-Path "$out/$d") { $t = Join-Path $res $d; New-Item -ItemType Directory $t | Out-Null
        Get-ChildItem "$out/$d" -File | Where-Object { $_.Name -match '^(C[CMP]|NP|CP)' } | Copy-Item -Destination $t }
    }
    Compress-Archive -Path "$res/*" -DestinationPath "$res.zip" -Force
    Write-Host "DONE. Send back $res.zip"
  }
}
