@echo off
cd /d "C:\Users\hp\OneDrive\Documents\GitHub\Group_6_TRENDING_CONTENT"
if not exist logs mkdir logs
uv run python -m src.ingestion.youtube_chart_monitor capture --region US --max-pages 10 --apply >> logs\us_chart.log 2>&1
exit /b %ERRORLEVEL%
