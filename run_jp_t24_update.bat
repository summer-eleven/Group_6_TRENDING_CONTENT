@echo off
cd /d "C:\Users\VICTUS\Downloads\Group_6_TRENDING_CONTENT\Group_6_TRENDING_CONTENT"
if not exist logs mkdir logs
echo [%date% %time%] Starting JP T24 update >> logs\JP_t24_update.log

:: Find all PENDING_T24 manifests and update them
for /d %%D in (data\raw\rolling_cohorts\JP\JP_*) do (
    if exist "%%D\manifest.json" (
        findstr /c:"PENDING_T24" "%%D\manifest.json" >nul 2>&1
        if not errorlevel 1 (
            echo [%date% %time%] Updating T24 for %%D >> logs\JP_t24_update.log
            uv run python -m src.ingestion.rolling_cohort update --manifest "%%D\manifest.json" >> logs\JP_t24_update.log 2>&1
        )
    )
)

echo [%date% %time%] T24 update complete >> logs\JP_t24_update.log
exit /b 0