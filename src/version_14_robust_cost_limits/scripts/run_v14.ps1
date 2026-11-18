param(
 [Parameter(Mandatory=$true)][string]$Development,
 [Parameter(Mandatory=$true)][string]$Test,
 [Parameter(Mandatory=$true)][string]$DevProvenance,
 [Parameter(Mandatory=$true)][string]$TestProvenance,
 [Parameter(Mandatory=$true)][string]$RunId,
 [string]$LockFrom="",
 [int]$Repeats=7,
 [int]$Bootstrap=2000
)
$ErrorActionPreference="Stop"
$py="code/cost_limits_v14.py"
$args=@("--development",$Development,"--test",$Test,"--run-id",$RunId,
 "--development-provenance",$DevProvenance,"--test-provenance",$TestProvenance,
 "--repeats",$Repeats,"--bootstrap",$Bootstrap)
if ($LockFrom -ne "") {
 $args+=@("--lock-from",$LockFrom)
} else {
 python $py --stage profile --development $Development --run-id $RunId --repeats $Repeats --bootstrap $Bootstrap
 if ($LASTEXITCODE -ne 0) {throw "Profile failed"}
 python $py --stage select --development $Development --run-id $RunId --repeats $Repeats --bootstrap $Bootstrap
 if ($LASTEXITCODE -ne 0) {throw "Rule selection failed"}
}
foreach($stage in @("preflight","scan","report")) {
 python $py --stage $stage @args
 if ($LASTEXITCODE -ne 0) {throw "Stage $stage failed"}
}
