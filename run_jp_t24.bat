@echo off
setlocal
cd /d "%~dp0"
if not exist logs mkdir logs
echo [%date% %time%] START JP T24 (%*) >> logs\JP_t24.log
uv run python -m src.ingestion.run_due_cohorts --region JP %* >> logs\JP_t24.log 2>&1
set EXIT_CODE=%ERRORLEVEL%
echo [%date% %time%] END JP T24 exit=%EXIT_CODE% >> logs\JP_t24.log
exit /b %EXIT_CODE%