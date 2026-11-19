# Software smoke test on SYNTHETIC data only (about 1 minute). Run from the package root:
#   powershell -ExecutionPolicy Bypass -File .\scripts\smoke_v15_1.ps1
param([string]$Python = "python")
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONIOENCODING = "utf-8"
function Py([string[]]$A) { Write-Host ">> $Python $($A -join ' ')"; & $Python @A; if ($LASTEXITCODE -ne 0) { throw "Step failed" } }
Py @("-m", "unittest", "discover", "-s", "tests", "-v")
Py @("code/make_synthetic.py", "--output", "data/smoke_dev.npz", "--n", "8", "--prefix", "DEV", "--seed", "12")
Py @("code/make_synthetic.py", "--output", "data/smoke_dm.npz", "--n", "6", "--prefix", "DMT", "--seed", "34")
Py @("code/make_synthetic.py", "--output", "data/smoke_3gpp.npz", "--n", "6", "--prefix", "GPT", "--seed", "56")
$c = @("code/run_experiment.py", "--development", "data/smoke_dev.npz", "--ks", "4,6,8", "--beam-counts", "3", "--repeats", "2",
       "--bootstrap", "100", "--smoke", "--limit", "6", "--min-cell-groups", "1", "--out-root", "outputs_smoke")
if (Test-Path "outputs_smoke") { Remove-Item "outputs_smoke" -Recurse -Force }
Py ($c + @("--stage", "develop", "--run-id", "SM_DM"))
Py ($c + @("--stage", "lock", "--run-id", "SM_DM"))
Py ($c + @("--stage", "test", "--run-id", "SM_DM", "--test", "data/smoke_dm.npz"))
Py ($c + @("--stage", "test", "--run-id", "SM_3G", "--test", "data/smoke_3gpp.npz", "--lock-from", "outputs_smoke/SM_DM/CP03_locked_cells.json"))
Py @("code/run_experiment.py", "--stage", "combine", "--run-id", "SM_FINAL", "--combine-runs", "SM_DM,SM_3G", "--out-root", "outputs_smoke")
Write-Host "SMOKE OK (status SMOKE_ONLY is expected)."
