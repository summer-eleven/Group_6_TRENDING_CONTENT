
@echo off
setlocal

cd /d "%~dp0"

if not exist "logs" mkdir "logs"

echo. >> logs\vn_daily_cohort.log
echo ============================================ >> logs\vn_daily_cohort.log
echo [%date% %time%] Starting VN Daily Cohort >> logs\vn_daily_cohort.log


REM Wait for MinIO and SQL Server before collecting data
set /a RETRIES=0

:WAIT_FOR_SERVICES

powershell -NoProfile -Command "if ((Test-NetConnection localhost -Port 9000 -InformationLevel Quiet) -and (Test-NetConnection localhost -Port 1433 -InformationLevel Quiet)) { exit 0 } else { exit 1 }" >nul 2>&1

if not errorlevel 1 goto SERVICES_READY

set /a RETRIES+=1

if %RETRIES% GEQ 10 (
    echo [%date% %time%] FAILED: MinIO or SQL Server unavailable after 10 checks >> logs\vn_daily_cohort.log
    exit /b 1
)

echo [%date% %time%] WAITING: Services unavailable. Retry %RETRIES%/10 in 60 seconds >> logs\vn_daily_cohort.log

powershell -NoProfile -Command "Start-Sleep -Seconds 60" >nul 2>&1

goto WAIT_FOR_SERVICES

:SERVICES_READY

echo [%date% %time%] SERVICES READY: MinIO and SQL Server ports reachable >> logs\vn_daily_cohort.log

REM Daily discovery, snapshot T0, and sync


uv run python -m src.ingestion.run_daily_cohort --region VN --target-new 2000 --max-channels 600 --max-per-channel 10 --discovery-max-requests 650 --details-max-requests 60 --apply >> logs\vn_daily_cohort.log 2>&1

set "EXIT_CODE=%ERRORLEVEL%"

echo [%date% %time%] Exit code: %EXIT_CODE% >> logs\vn_daily_cohort.log

exit /b %EXIT_CODE%
