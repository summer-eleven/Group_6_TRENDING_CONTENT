@echo off
setlocal
cd /d "%~dp0"
if not exist logs mkdir logs
echo [%date% %time%] START JP Cohort (%*) >> logs\JP_cohort.log
uv run python -m src.ingestion.run_daily_cohort_jp --target-new 1000 --max-channels 200 --max-per-channel 10 --discovery-max-requests 250 --details-max-requests 30 --apply >> logs\JP_cohort.log 2>&1
set EXIT_CODE=%ERRORLEVEL%

:: Automatically update JP cohort registry after collecting new batch
echo [%date% %time%] Updating JP cohort registry >> logs\JP_cohort.log
uv run python -m src.processing.build_cohort_registry_jp >> logs\JP_cohort.log 2>&1

echo [%date% %time%] END JP Cohort exit=%EXIT_CODE% >> logs\JP_cohort.log
exit /b %EXIT_CODE%