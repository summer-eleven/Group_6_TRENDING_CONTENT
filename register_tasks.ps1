<#
 register_tasks.ps1 - Tao task Windows Task Scheduler cho MOT nuoc bat ky (phuong an A).

   "YouTube <REGION> Chart Monitor" : moi 1 gio -> run_chart.bat <REGION>
   "YouTube <REGION> Daily Cohort"  : 1 lan/ngay -> run_rolling.bat <REGION> [TargetNew]

 Vi du (PowerShell, tai thu muc goc project):
   .\scripts\register_tasks.ps1 -Region US -ChartOnly        # luc chua co rolling_cohort.py
   .\scripts\register_tasks.ps1 -Region KR -DailyAt "07:30" -TargetNew 1000
   .\scripts\register_tasks.ps1 -Region JP -ChartOnly -MinuteOffset 10   # lech phut de cac nuoc khong goi cung luc
   .\scripts\register_tasks.ps1 -Region US -Unregister       # go 2 task cua US

 Cau hinh giong huong dan GUI trong tai lieu:
   - Chay khi user dang dang nhap (de debug; khong can luu mat khau Windows)
   - Bo "Start only if idle"; bat "Wake the computer to run this task" (khong danh thuc may da SHUTDOWN)
   - Bo lo lich: chay som nhat co the sau khi bo lo (StartWhenAvailable)
   - Neu task dang chay: KHONG khoi dong ban thu hai (IgnoreNew)
   - Retry khi loi: 3 lan, cach 5 phut
 Sau khi tao: taskschd.msc -> chuot phai task -> Run -> Last Run Result phai la 0x0
 va logs\<REGION>_chart.log co "Exit code: 0".
#>
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z]{2}$')]
    [string]$Region,
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$DailyAt = "07:00",
    [ValidateRange(1, 50000)][int]$TargetNew = 1000,
    [ValidateRange(0, 59)][int]$MinuteOffset = 0,
    [switch]$ChartOnly,
    [switch]$Unregister
)

$ErrorActionPreference = "Stop"
$Region = $Region.ToUpper()

$cohortName = "YouTube $Region Daily Cohort"
$chartName  = "YouTube $Region Chart Monitor"

if ($Unregister) {
    foreach ($n in @($cohortName, $chartName)) {
        Unregister-ScheduledTask -TaskName $n -Confirm:$false -ErrorAction SilentlyContinue
        Write-Host "Removed (if existed): $n"
    }
    return
}

$chartBat  = Join-Path $ProjectRoot "run_chart.bat"
$cohortBat = Join-Path $ProjectRoot "run_rolling.bat"
if (-not (Test-Path $chartBat)) { throw "Khong thay $chartBat" }
if (-not $ChartOnly -and -not (Test-Path $cohortBat)) { throw "Khong thay $cohortBat" }

$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive -RunLevel Limited

function New-Settings([int]$LimitMinutes) {
    New-ScheduledTaskSettingsSet `
        -StartWhenAvailable `
        -WakeToRun `
        -MultipleInstances IgnoreNew `
        -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5) `
        -ExecutionTimeLimit (New-TimeSpan -Minutes $LimitMinutes)
}

# ---- Chart monitor: Daily luc 00:<offset>, lap moi 1 gio trong 1 ngay (= phu kin 24h, lap lai moi ngay)
$start = "00:{0:00}" -f $MinuteOffset
$chartTrigger = New-ScheduledTaskTrigger -Daily -At $start
$chartTrigger.Repetition = (New-ScheduledTaskTrigger -Once -At $start `
        -RepetitionInterval (New-TimeSpan -Hours 1) `
        -RepetitionDuration (New-TimeSpan -Days 1)).Repetition

Register-ScheduledTask -TaskName $chartName -Force `
    -Action (New-ScheduledTaskAction -Execute $chartBat -Argument $Region -WorkingDirectory $ProjectRoot) `
    -Trigger $chartTrigger -Settings (New-Settings 30) -Principal $principal `
    -Description "Hourly YouTube mostPopular chart monitor ($Region)" | Out-Null
Write-Host "Registered: $chartName"

# ---- Daily cohort
if (-not $ChartOnly) {
    Register-ScheduledTask -TaskName $cohortName -Force `
        -Action (New-ScheduledTaskAction -Execute $cohortBat -Argument "$Region $TargetNew" -WorkingDirectory $ProjectRoot) `
        -Trigger (New-ScheduledTaskTrigger -Daily -At $DailyAt) `
        -Settings (New-Settings 240) -Principal $principal `
        -Description "Daily rolling cohort T0 + T+24h ($Region)" | Out-Null
    Write-Host "Registered: $cohortName"
}

Get-ScheduledTask -TaskName "YouTube $Region*" | Format-Table TaskName, State -AutoSize
