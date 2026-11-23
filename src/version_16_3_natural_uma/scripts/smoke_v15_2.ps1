# Software smoke test on SYNTHETIC data only (about 1-2 minutes). Run:  powershell -ExecutionPolicy Bypass -File .\scripts\smoke_v15_2.ps1
param([string]$Python = "python")
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONIOENCODING = "utf-8"
function Py([string[]]$A) { Write-Host ">> $Python $($A -join ' ')"; & $Python @A; if ($LASTEXITCODE -ne 0) { throw "Step failed" } }
Py @("-m", "unittest", "discover", "-s", "tests", "-v")
Py @("code/make_synthetic.py", "--output", "data/smoke_dev.npz", "--n", "10", "--prefix", "DEV", "--seed", "12")
Py @("code/make_synthetic.py", "--output", "data/smoke_pool_dm.npz", "--n", "30", "--prefix", "DMP", "--seed", "34", "--prior-use", "never_seen")
Py @("code/make_synthetic.py", "--output", "data/smoke_pool_3gpp.npz", "--n", "30", "--prefix", "GPP", "--seed", "56", "--prior-use", "never_seen")
$o = "outputs_smoke"
if (Test-Path $o) { Remove-Item $o -Recurse -Force }
$c = @("code/run_experiment.py", "--development", "data/smoke_dev.npz", "--ks", "4,6,8", "--beam-counts", "3", "--repeats", "2",
       "--bootstrap", "100", "--smoke", "--limit", "10", "--min-cell-groups", "1", "--out-root", $o)
Py ($c + @("--stage", "develop", "--run-id", "SM_DM"))
Py ($c + @("--stage", "lock", "--run-id", "SM_DM"))
foreach ($s in @(@("dm", "SM_DM", ""), @("3gpp", "SM_3G", "$o/SM_DM/CP03_locked_cells.json"))) {
  $n, $rid, $lf = $s
  Py @("code/stratify_test_pool.py", "--pool", "data/smoke_pool_$n.npz", "--pool-provenance", "data/smoke_pool_$n.npz.provenance.json",
       "--manifest", "$o/SM_DM/CP00_manifest.json", "--lock", "$o/SM_DM/CP03_locked_cells.json", "--region-groups", "4", "--outside-groups", "4",
       "--output", "data/smoke_test_$n.npz")
  $x = @("--run-id", $rid, "--test", "data/smoke_test_$n.npz"); if ($lf -ne "") { $x += @("--lock-from", $lf) }
  Py ($c + @("--stage", "test-preflight") + $x)
  Py ($c + @("--stage", "test") + $x)
}
Py @("code/run_experiment.py", "--stage", "combine", "--run-id", "SM_FINAL", "--combine-runs", "SM_DM,SM_3G", "--out-root", $o)
Write-Host "SMOKE OK (SMOKE_ONLY expected)."
