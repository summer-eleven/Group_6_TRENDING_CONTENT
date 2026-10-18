@echo off
cd /d "C:\Users\VICTUS\Downloads\Group_6_TRENDING_CONTENT\Group_6_TRENDING_CONTENT"
if not exist logs mkdir logs
uv run python -m src.ingestion.youtube_chart_monitor capture --region JP --max-pages 10 --apply >> logs\JP_chart.log 2>&1
exit /b %ERRORLEVEL%
