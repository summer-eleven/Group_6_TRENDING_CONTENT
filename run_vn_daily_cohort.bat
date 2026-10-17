
@echo off
setlocal

cd /d "%~dp0"

if not exist "logs" mkdir "logs"

echo. >> logs\vn_daily_cohort.log
echo ============================================ >> logs\vn_daily_cohort.log
echo [%date% %time%] Starting VN Daily Cohort >> logs\vn_daily_cohort.log

REM Check MinIO and SQL Server before collecting data
powershell -NoProfile -Command "if ((Test-NetConnection localhost -Port 9000 -InformationLevel Quiet) -and (Test-NetConnection localhost -Port 1433 -InformationLevel Quiet)) { exit 0 } else { exit 1 }" >nul 2>&1

if errorlevel 1 (
    echo [%date% %time%] SKIPPED: MinIO or SQL Server is unavailable >> logs\vn_daily_cohort.log
    exit /b 1
)

REM Daily discovery, snapshot T0, and sync


uv run python -m src.ingestion.run_daily_cohort --region VN --target-new 2000 --max-channels 600 --max-per-channel 10 --discovery-max-requests 650 --details-max-requests 60 --apply >> logs\vn_daily_cohort.log 2>&1

set "EXIT_CODE=%ERRORLEVEL%"

echo [%date% %time%] Exit code: %EXIT_CODE% >> logs\vn_daily_cohort.log

exit /b %EXIT_CODE%
