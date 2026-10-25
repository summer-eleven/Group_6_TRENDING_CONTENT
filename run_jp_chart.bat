@echo off
setlocal
cd /d "%~dp0"
if not exist logs mkdir logs
echo [%date% %time%] START JP Chart (%*) >> logs\JP_chart_monitor.log
uv run python -m src.ingestion.youtube_chart_monitor capture --region JP --max-pages 10 --apply >> logs\JP_chart_monitor.log 2>&1
set EXIT_CODE=%ERRORLEVEL%
echo [%date% %time%] END JP Chart exit=%EXIT_CODE% >> logs\JP_chart_monitor.log
exit /b %EXIT_CODE%