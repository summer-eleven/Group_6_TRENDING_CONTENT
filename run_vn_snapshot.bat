@echo off

cd /d "%~dp0"

if not exist logs mkdir logs

echo. >> logs\vn_snapshot.log
echo ================================================== >> logs\vn_snapshot.log
echo [%date% %time%] Starting VN snapshot >> logs\vn_snapshot.log

uv run python -m src.ingestion.youtube_snapshot_crawler --region VN >> logs\vn_snapshot.log 2>&1

set "EXIT_CODE=%ERRORLEVEL%"

echo [%date% %time%] Exit code: %EXIT_CODE% >> logs\vn_snapshot.log

exit /b %EXIT_CODE%