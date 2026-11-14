param(
  [Parameter(Mandatory=$true)][string]$Development,
  [Parameter(Mandatory=$true)][string]$Test,
  [Parameter(Mandatory=$true)][string]$DevelopmentProvenance,
  [Parameter(Mandatory=$true)][string]$TestProvenance,
  [Parameter(Mandatory=$true)][string]$RunId,
  [int]$Repeats=7,
  [int]$Bootstrap=2000,
  [switch]$SkipDevelopment
)
$ErrorActionPreference='Stop'
$cmd=@('code/cost_aware_v13.py','--dev-dataset',$Development,'--test-dataset',$Test,
       '--dev-provenance',$DevelopmentProvenance,'--test-provenance',$TestProvenance,
       '--run-id',$RunId,'--repeats',"$Repeats",'--bootstrap',"$Bootstrap")
if (-not $SkipDevelopment) {
  & python @cmd --stage develop
  if ($LASTEXITCODE -ne 0) { throw 'Development stage failed' }
}
foreach ($s in @('preflight','scan','report')) {
  & python @cmd --stage $s
  if ($LASTEXITCODE -ne 0) { throw "Stage $s failed" }
}
Write-Host "Outputs in outputs/$RunId. To resume, rerun with -SkipDevelopment."
