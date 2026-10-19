@echo off
cd /d "C:\Users\hp\OneDrive\Documents\GitHub\Group_6_TRENDING_CONTENT"
if not exist logs mkdir logs
uv run python -m src.ingestion.run_due_cohorts --region US >> logs\us_rolling.log 2>&1
uv run python -m src.ingestion.run_daily_cohort --region US --target-new 1000 --max-channels 400 --max-per-channel 10 --discovery-max-requests 450 --apply >> logs\us_rolling.log 2>&1
exit /b %ERRORLEVEL%
