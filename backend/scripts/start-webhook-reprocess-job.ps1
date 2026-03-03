[CmdletBinding()]
param(
    [switch]$Once,
    [int]$IntervalMinutes = 0,
    [int]$BatchSize = 0,
    [int]$MaxAttempts = 0,
    [int]$BaseDelayMinutes = 0,
    [int]$MaxDelayMinutes = 0
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Split-Path -Parent $scriptDir

$jobArgs = @("-m", "source.jobs.reprocess_failed_webhooks_job")
if ($Once) {
    $jobArgs += "--once"
}
if ($IntervalMinutes -gt 0) {
    $jobArgs += @("--interval-minutes", "$IntervalMinutes")
}
if ($BatchSize -gt 0) {
    $jobArgs += @("--batch-size", "$BatchSize")
}
if ($MaxAttempts -gt 0) {
    $jobArgs += @("--max-attempts", "$MaxAttempts")
}
if ($BaseDelayMinutes -gt 0) {
    $jobArgs += @("--base-delay-minutes", "$BaseDelayMinutes")
}
if ($MaxDelayMinutes -gt 0) {
    $jobArgs += @("--max-delay-minutes", "$MaxDelayMinutes")
}

Write-Host "Iniciando worker de reproceso de webhooks failed..."
Write-Host "Comando: python $($jobArgs -join ' ')"
Push-Location $backendDir
try {
    python @jobArgs
}
finally {
    Pop-Location
}
