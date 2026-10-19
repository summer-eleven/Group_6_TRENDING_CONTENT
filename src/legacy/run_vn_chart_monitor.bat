@echo off
setlocal
cd /d "%~dp0"
if not exist "logs" mkdir "logs"

echo. >> logs\vn_chart_monitor.log
echo ============================================ >> logs\vn_chart_monitor.log
echo [%date% %time%] Starting VN Chart Monitor >> logs\vn_chart_monitor.log

REM Do not call API if local MinIO or SQL is not ready.
powershell -NoProfile -Command "if ((Test-NetConnection localhost -Port 9000 -InformationLevel Quiet) -and (Test-NetConnection localhost -Port 1433 -InformationLevel Quiet)) { exit 0 } else { exit 1 }" >nul 2>&1
if errorlevel 1 (
    echo [%date% %time%] SKIPPED: SQL Server or MinIO unavailable >> logs\vn_chart_monitor.log
    exit /b 1
)

uv run python -m src.ingestion.youtube_chart_monitor capture --region VN --max-pages 10 --apply >> logs\vn_chart_monitor.log 2>&1
set "EXIT_CODE=%ERRORLEVEL%"
echo [%date% %time%] Exit code: %EXIT_CODE% >> logs\vn_chart_monitor.log
exit /b %EXIT_CODE%
