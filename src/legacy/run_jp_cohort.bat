@echo off
cd /d "C:\Users\VICTUS\Downloads\Group_6_TRENDING_CONTENT\Group_6_TRENDING_CONTENT"
if not exist logs mkdir logs
uv run python -m src.ingestion.rolling_cohort --region JP --target-new 1000 --sync-due >> logs\JP_cohort.log 2>&1
exit /b %ERRORLEVEL%
