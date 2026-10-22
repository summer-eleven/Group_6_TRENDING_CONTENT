@echo off
cd /d "C:\Users\VICTUS\Downloads\Group_6_TRENDING_CONTENT\Group_6_TRENDING_CONTENT"
if not exist logs mkdir logs
echo [%date% %time%] Starting JP Daily Cohort >> logs\JP_cohort.log
uv run python -m src.ingestion.run_daily_cohort_jp --target-new 2000 --max-channels 400 --max-per-channel 10 --discovery-max-requests 450 --details-max-requests 60 --apply >> logs\JP_cohort.log 2>&1
echo [%date% %time%] Exit code: %ERRORLEVEL% >> logs\JP_cohort.log
exit /b %ERRORLEVEL%