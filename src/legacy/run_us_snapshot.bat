@echo off

cd /d "%~dp0"

if not exist logs mkdir logs

echo. >> logs\us_snapshot.log
echo ================================================== >> logs\us_snapshot.log
echo [%date% %time%] Starting US snapshot >> logs\us_snapshot.log

uv run python -m src.ingestion.youtube_snapshot_crawler --region US >> logs\us_snapshot.log 2>&1

set "EXIT_CODE=%ERRORLEVEL%"

echo [%date% %time%] Exit code: %EXIT_CODE% >> logs\us_snapshot.log

exit /b %EXIT_CODE%