[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('webhook_reprocess','payments_reconcile','expire_stock_reservations','prune_auth_action_tokens','prune_auth_login_throttles')]
    [string]$Job,
    [string]$PythonExe = ''
)

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Split-Path -Parent $scriptDir

if ([string]::IsNullOrWhiteSpace($PythonExe)) {
    $venvPython = Join-Path $backendDir '.venv\Scripts\python.exe'
    if (Test-Path $venvPython) {
        $PythonExe = $venvPython
    }
    else {
        $PythonExe = 'python'
    }
}

switch ($Job) {
    'webhook_reprocess' {
        $jobArgs = @(
            '-m', 'source.jobs.reprocess_failed_webhooks_job',
            '--once',
            '--batch-size', '25',
            '--max-attempts', '4',
            '--base-delay-minutes', '30',
            '--max-delay-minutes', '720'
        )
    }
    'payments_reconcile' {
        $jobArgs = @(
            '-m', 'source.jobs.reconcile_pending_payments_job',
            '--once',
            '--batch-size', '50',
            '--max-age-hours', '24',
            '--min-age-minutes', '15'
        )
    }
    'expire_stock_reservations' {
        $jobArgs = @(
            '-m', 'source.jobs.expire_stock_reservations_job',
            '--once',
            '--batch-limit', '200',
            '--max-batches', '20'
        )
    }
    'prune_auth_action_tokens' {
        $jobArgs = @(
            '-m', 'source.jobs.prune_auth_action_tokens_job',
            '--once',
            '--older-than-days', '7',
            '--batch-size', '500'
        )
    }
    'prune_auth_login_throttles' {
        $jobArgs = @(
            '-m', 'source.jobs.prune_auth_login_throttles_job',
            '--once',
            '--older-than-days', '14',
            '--batch-size', '1000'
        )
    }
    default {
        throw "Unsupported job: $Job"
    }
}

Write-Host "Running job '$Job' with: $PythonExe $($jobArgs -join ' ')"
Push-Location $backendDir
try {
    & $PythonExe @jobArgs
    $exitCode = $LASTEXITCODE
    if ($null -ne $exitCode -and $exitCode -ne 0) {
        exit $exitCode
    }
}
finally {
    Pop-Location
}
