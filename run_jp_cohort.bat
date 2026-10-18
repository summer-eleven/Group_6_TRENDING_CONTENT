@echo off
cd /d "C:\Users\VICTUS\Downloads\Group_6_TRENDING_CONTENT\Group_6_TRENDING_CONTENT"
if not exist logs mkdir logs
uv run python -m src.ingestion.run_daily_cohort --region JP --target-new 1000 --max-channels 400 --max-per-channel 10 --discovery-max-requests 450 --apply >> logs\JP_cohort.log 2>&1
exit /b %ERRORLEVEL%
