@echo off
setlocal
cd /d "%~dp0"
if not exist logs mkdir logs
echo [%date% %time%] START JP Cohort (%*) >> logs\JP_cohort.log
uv run python -m src.ingestion.run_daily_cohort --region JP %* >> logs\JP_cohort.log 2>&1
set EXIT_CODE=%ERRORLEVEL%
echo [%date% %time%] END JP Cohort exit=%EXIT_CODE% >> logs\JP_cohort.log
exit /b %EXIT_CODE%