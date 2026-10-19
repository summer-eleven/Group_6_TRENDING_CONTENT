
@echo off
setlocal

cd /d "%~dp0"

if not exist "logs" mkdir "logs"

echo. >> logs\vn_cohort_t24.log
echo ============================================ >> logs\vn_cohort_t24.log
echo [%date% %time%] Starting VN T24 check >> logs\vn_cohort_t24.log

REM Check MinIO and SQL Server before processing
powershell -NoProfile -Command "if ((Test-NetConnection localhost -Port 9000 -InformationLevel Quiet) -and (Test-NetConnection localhost -Port 1433 -InformationLevel Quiet)) { exit 0 } else { exit 1 }" >nul 2>&1

if errorlevel 1 (
    echo [%date% %time%] SKIPPED: MinIO or SQL Server is unavailable >> logs\vn_cohort_t24.log
    exit /b 1
)

REM Process only batches that have reached T+24h
uv run python -m src.ingestion.run_due_cohorts --region VN >> logs\vn_cohort_t24.log 2>&1

set "EXIT_CODE=%ERRORLEVEL%"

echo [%date% %time%] Exit code: %EXIT_CODE% >> logs\vn_cohort_t24.log

exit /b %EXIT_CODE%
