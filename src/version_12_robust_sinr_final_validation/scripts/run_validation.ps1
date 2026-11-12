param(
    [Parameter(Mandatory=$true)][ValidateSet('DeepMIMO','Sionna_3GPP')][string]$Source,
    [Parameter(Mandatory=$true)][string]$Dataset,
    [Parameter(Mandatory=$true)][string]$Provenance,
    [Parameter(Mandatory=$true)][string]$RunId,
    [string]$DevelopmentGroups = '',
    [int]$Repeats = 7,
    [int]$Bootstrap = 2000
)
$ErrorActionPreference='Stop'
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '..'))
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$common = @('--run-id',$RunId,'--source',$Source,'--repeats',$Repeats,'--bootstrap',$Bootstrap)
$withData = $common + @('--dataset',$Dataset,'--provenance',$Provenance)
if ($DevelopmentGroups -ne '') { $withData += @('--development-groups',$DevelopmentGroups) }
foreach ($stage in @('lock','preflight','scan','report')) {
    Write-Host "STAGE $stage"
    $argsForRun = if ($stage -eq 'lock') { @('--stage','lock') + $common } else { @('--stage',$stage) + $withData }
    & python 'code/final_runtime_validation.py' @argsForRun
    if ($LASTEXITCODE -ne 0) { throw "Pipeline aborted at $stage (exit $LASTEXITCODE)" }
}
