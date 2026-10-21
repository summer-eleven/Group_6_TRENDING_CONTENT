@echo off
REM Cap nhat T24 cho cac batch US da den han. Mac dinh --dry-run.
REM Chay that:  run_us_t24.bat apply
cd /d "%~dp0"
if not exist logs mkdir logs
set LOG=logs\US_t24.log
echo ===== %date% %time% US T24 (mode=%1) ===== >> %LOG%
if /I "%1"=="apply" (
  uv run python -m src.ingestion.run_due_cohorts --region US >> %LOG% 2>&1
) else (
  uv run python -m src.ingestion.run_due_cohorts --region US --dry-run >> %LOG% 2>&1
)
echo exit code: %ERRORLEVEL% >> %LOG%
exit /b %ERRORLEVEL%
