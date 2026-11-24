# V16 extension of the frozen V15.2 study (run from any folder; paths relative to the package root).
# Phases:
#   check            : build compiled solver, selftest, unit tests, check that the V15.2 lock is reusable on this machine
#   transfer         : ONLY if 'check' reports a machine-only difference: transfer the lock (policy map unchanged)
#   compiled         : compiled CARD/EARLY/ROUTED on the V15.2 development set and both V15.2 test sets
#   model            : analytical break-even model, fitted on development, validated on both test sets (Python and compiled)
#   natural-protocol : freeze the natural-prevalence protocol (needs -NaturalPool), BEFORE sampling
#   natural          : sample -> V15.2 test with the frozen lock -> compiled run -> endpoints N1-N4 -> KET_QUA_V16.zip
#   natural2-spec     : V16.3 freeze the power-limited deployment (UMa ISD 500 m) BEFORE generating any channel
#   natural2-generate : generate the sealed UMa pool from the frozen spec with Sionna (-SionnaPython, -BsRows, -BsCols)
#   natural2-validate : check pool + provenance against the frozen spec (no early ratio is computed on the pool)
#   natural2-protocol : freeze the second natural protocol (sample size and seed come from the spec)
#   pmax-protocol     : V17 freeze the power-budget sweep (30/35/46/49 dBm) on the never-sampled halves of both natural pools
#   pmax-run          : CK1 -> 8 compiled runs (UMi, UMa x 4 budgets) with CK2 after each run (resumable)
#   pmax-analyze      : CK3 endpoints X1-X6 per deployment and budget -> KET_QUA_V17_PMAX.zip
#   natural2          : sample -> V15.2 test -> compiled -> N1-N4 -> comparison with NP16 -> KET_QUA_V16_NAT2.zip
# Example:
#   powershell -ExecutionPolicy Bypass -File .\scripts\run_v16.ps1 -Phase check -Development data\dev.npz -DevProvenance data\dev.npz.provenance.json
param(
  [Parameter(Mandatory=$true)][ValidateSet("check","transfer","compiled","model","natural-protocol","natural","natural2-spec","natural2-generate","natural2-validate","natural2-protocol","natural2","pmax-protocol","pmax-run","pmax-analyze")][string]$Phase,
  [Parameter(Mandatory=$true)][string]$Development,
  [Parameter(Mandatory=$true)][string]$DevProvenance,
  [string]$Tag = "V152",
  [string]$NaturalPool = "", [string]$NaturalPoolProvenance = "", [int]$NaturalGroups = 100,
  [string]$Python = "python",
  [string]$Pool2 = "data/nat2_pool.npz", [string]$Sample1 = "data/V16_natural_sample.npz", [string]$Sample2 = "data/V16_natural2_sample.npz", [int]$BsRows = 1, [int]$BsCols = 16, [string]$SionnaPython = ""
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

function Archive-OldCompiled([string]$Id) {
  # V16.2: runs started with an older compiled_benchmark version (strict 1e-7) cannot be resumed; keep them, but out of the way.
  $m = "$out/$Id/CC00_manifest.json"
  if (Test-Path $m) {
    $v = (Get-Content $m -Raw | ConvertFrom-Json).version
    if ($v -ne "V17-compiled") {
      $dst = "$out/${Id}_old_${v}_" + (Get-Date -Format "yyyyMMdd_HHmmss")
      Move-Item "$out/$Id" $dst
      Write-Host "Archived previous run $Id (version $v) to $dst"
    }
  }
}

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
    foreach ($id in @("C16_DEV","C16_DM","C16_3GPP")) { Archive-OldCompiled $id }
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
    Archive-OldCompiled "C16_NAT"
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
  "pmax-protocol" {
    if ($NaturalPool -eq "") { throw "Give -NaturalPool (UMi pool of NP16) and -NaturalPoolProvenance" }
    Py @("code/pmax_sweep.py", "--stage", "protocol", "--out-root", $out, "--manifest", $Manifest, "--lock", $Lock,
         "--umi-pool", $NaturalPool, "--umi-pool-provenance", $NaturalPoolProvenance, "--umi-sample", $Sample1,
         "--uma-pool", $Pool2, "--uma-pool-provenance", "$Pool2.provenance.json", "--uma-sample", $Sample2)
    Write-Host "Protocol frozen: $out/PX17/PX00_protocol.json. Now run -Phase pmax-run."
  }
  "pmax-run" {
    Py @("code/pmax_sweep.py", "--stage", "check", "--out-root", $out, "--manifest", $Manifest, "--lock", $Lock)
    foreach ($dep in @("umi","uma")) {
      foreach ($p in @("30","35","46","49")) {
        $id = "C17_$($dep.ToUpper())_P$p"
        Py @("code/compiled_benchmark.py", "--data", "data/V17_${dep}_complement.npz", "--manifest", $Manifest, "--lock", $Lock,
             "--run-id", $id, "--out-root", $out, "--pmax-dbm", $p)
        Py @("code/pmax_sweep.py", "--stage", "progress", "--out-root", $out)
      }
    }
  }
  "pmax-analyze" {
    Py @("code/pmax_sweep.py", "--stage", "progress", "--out-root", $out)
    Py @("code/pmax_sweep.py", "--stage", "analyze", "--out-root", $out)
    $res = "KET_QUA_V17_PMAX"
    if (Test-Path $res) { Remove-Item $res -Recurse -Force }
    New-Item -ItemType Directory $res | Out-Null
    $dirs = @("PX17") + @(foreach ($d in @("UMI","UMA")) { foreach ($p in @("30","35","46","49")) { "C17_${d}_P$p" } })
    foreach ($d in $dirs) {
      if (Test-Path "$out/$d") { $t = Join-Path $res $d; New-Item -ItemType Directory $t | Out-Null
        Get-ChildItem "$out/$d" -File | Where-Object { $_.Name -match '^(CC|PX)' } | Copy-Item -Destination $t }
    }
    Compress-Archive -Path "$res/*" -DestinationPath "$res.zip" -Force
    Write-Host "DONE. Send back $res.zip"
  }
  "natural2-spec" {
    Py @("code/scenario_spec.py", "--stage", "freeze", "--run-id", "NS2", "--out-root", $out)
    Write-Host "Deployment frozen: $out/NS2/NS00_scenario_spec.json. Generate the pool ONLY from this file (-Phase natural2-generate)."
  }
  "natural2-generate" {
    $sp = $(if ($SionnaPython -ne "") { $SionnaPython } else { $Python })
    Write-Host ">> $sp code/gen_sionna_uma.py"
    & $sp code/gen_sionna_uma.py --spec "$out/NS2/NS00_scenario_spec.json" --output $Pool2 --bs-rows $BsRows --bs-cols $BsCols
    if ($LASTEXITCODE -ne 0) { throw "Pool generation failed (adapt the ADAPT lines of gen_sionna_uma.py or use your own UMi generator, see the guide)" }
  }
  "natural2-validate" {
    Py @("code/scenario_spec.py", "--stage", "validate", "--run-id", "NS2", "--out-root", $out, "--pool", $Pool2, "--provenance", "$Pool2.provenance.json")
  }
  "natural2-protocol" {
    $spec = Get-Content "$out/NS2/NS00_scenario_spec.json" -Raw | ConvertFrom-Json
    Py @("code/natural_prevalence.py", "--stage", "protocol", "--run-id", "NP16B", "--out-root", $out, "--manifest", $Manifest, "--lock", $Lock,
         "--pool", $Pool2, "--n-groups", "$($spec.sample_groups)", "--seed", "$($spec.sample_seed)",
         "--scenario-spec", "$out/NS2/NS00_scenario_spec.json", "--pool-validation", "$out/NS2/NS01_pool_validation.json")
    Write-Host "Protocol frozen: $out/NP16B/NP00_natural_protocol.json. Now run -Phase natural2."
  }
  "natural2" {
    $sample = "data/V16_natural2_sample.npz"; $nrun = "V16_NAT2"
    Py @("code/natural_prevalence.py", "--stage", "sample", "--run-id", "NP16B", "--out-root", $out, "--pool", $Pool2,
         "--pool-provenance", "$Pool2.provenance.json", "--output", $sample)
    $c = @("code/run_experiment.py", "--development", $Development, "--dev-provenance", $DevProvenance, "--out-root", $out, "--run-id", $nrun, "--lock-from", $Lock)
    Py ($c + @("--stage", "test-preflight", "--test", $sample))
    Py ($c + @("--stage", "test", "--test", $sample, "--test-provenance", "$sample.provenance.json", "--allow-small-region"))
    Py ($c + @("--stage", "report"))
    Archive-OldCompiled "C16_NAT2"
    Py @("code/compiled_benchmark.py", "--data", $sample, "--manifest", $Manifest, "--lock", $Lock, "--run-id", "C16_NAT2", "--out-root", $out, "--python-run", "$out/$nrun")
    Py @("code/natural_prevalence.py", "--stage", "analyze", "--run-id", "NP16B", "--out-root", $out, "--v152-run", "$out/$nrun", "--compiled-run", "$out/C16_NAT2")
    if (Test-Path "$out/NP16/NP02_natural_decision.json") {
      Py @("code/natural_prevalence.py", "--stage", "compare", "--run-id", "NP16B", "--out-root", $out, "--compare-with", "$out/NP16")
    } else { Write-Host "NP16 not found: comparison with the UMi run skipped" }
    $res = "KET_QUA_V16_NAT2"
    if (Test-Path $res) { Remove-Item $res -Recurse -Force }
    New-Item -ItemType Directory $res | Out-Null
    foreach ($d in @("NS2","NP16B",$nrun,"C16_NAT2")) {
      if (Test-Path "$out/$d") { $t = Join-Path $res $d; New-Item -ItemType Directory $t | Out-Null
        Get-ChildItem "$out/$d" -File | Where-Object { $_.Name -match '^(C[CMP]|NP|CP|NS)' } | Copy-Item -Destination $t }
    }
    Copy-Item "$Pool2.provenance.json" (Join-Path $res "pool2.provenance.json")
    Compress-Archive -Path "$res/*" -DestinationPath "$res.zip" -Force
    Write-Host "DONE. Send back $res.zip"
  }
}
