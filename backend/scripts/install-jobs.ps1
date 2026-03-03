[CmdletBinding()]
param(
    [string]$TaskPrefix = 'PatitasBigotes',
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Split-Path -Parent $scriptDir
$runnerPath = Join-Path $scriptDir 'run-job.ps1'

if (-not (Test-Path $runnerPath)) {
    throw "Runner script not found: $runnerPath"
}

function Register-PatitasTask {
    param(
        [string]$Name,
        [string]$JobKey,
        [TimeSpan]$Interval,
        [datetime]$StartAt,
        [string]$Description
    )

    $taskName = "${TaskPrefix}_$Name"
    $arg = "-NoProfile -ExecutionPolicy Bypass -File `"$runnerPath`" -Job $JobKey"
    $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arg -WorkingDirectory $backendDir
    $trigger = New-ScheduledTaskTrigger -Once -At $StartAt -RepetitionInterval $Interval -RepetitionDuration (New-TimeSpan -Days 3650)
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

    $existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($existing -and -not $Force) {
        Write-Host "Skipping existing task (use -Force to replace): $taskName"
        return
    }
    if ($existing) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    }

    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description $Description | Out-Null
    Write-Host "Registered: $taskName"
}

$now = Get-Date
$today = $now.Date

Register-PatitasTask -Name 'WebhookReprocess' -JobKey 'webhook_reprocess' -Interval (New-TimeSpan -Minutes 10) -StartAt ($today.AddMinutes(1)) -Description 'Reprocess failed webhook events every 10 minutes'
Register-PatitasTask -Name 'PaymentsReconcile' -JobKey 'payments_reconcile' -Interval (New-TimeSpan -Hours 4) -StartAt ($today.AddMinutes(2)) -Description 'Reconcile recent pending MP payments every 4 hours'
Register-PatitasTask -Name 'ExpireStockReservations' -JobKey 'expire_stock_reservations' -Interval (New-TimeSpan -Minutes 15) -StartAt ($today.AddMinutes(3)) -Description 'Expire stock reservations every 15 minutes'
Register-PatitasTask -Name 'PruneAuthActionTokens' -JobKey 'prune_auth_action_tokens' -Interval (New-TimeSpan -Days 1) -StartAt ($today.AddHours(3).AddMinutes(20)) -Description 'Prune old auth action tokens daily'
Register-PatitasTask -Name 'PruneAuthLoginThrottles' -JobKey 'prune_auth_login_throttles' -Interval (New-TimeSpan -Days 1) -StartAt ($today.AddHours(3).AddMinutes(35)) -Description 'Prune old auth login throttles daily'

Get-ScheduledTask | Where-Object { $_.TaskName -like "${TaskPrefix}_*" } | Select-Object TaskName, State | Sort-Object TaskName
