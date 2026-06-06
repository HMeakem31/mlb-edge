@echo off
:: MLB Edge v2.4 — One-click Windows Task Scheduler setup
:: Run this once. It creates a daily 11 AM task that runs even if you're logged out.
:: Requires Administrator (right-click → Run as Administrator).

title MLB Edge Auto-Scheduler Setup
cd /d "%~dp0"

:: Find Python
set P=
where python >nul 2>&1 && set P=python
if not defined P where python3 >nul 2>&1 && set P=python3
if not defined P where py >nul 2>&1 && set P=py
if not defined P (
    echo Python not found. Install from python.org first.
    pause
    exit /b 1
)

set "SCRIPT_DIR=%~dp0"
set "RUN_PATH=%SCRIPT_DIR%run.py"
set "SCORE_PATH=%SCRIPT_DIR%score_yesterday.py"

:: Task 1: Daily pipeline at 11:00 AM
schtasks /create /tn "MLB_Edge_Daily_Run" ^
    /tr "%P% \"%RUN_PATH%\"" ^
    /sc daily /st 11:00 ^
    /rl highest ^
    /f ^
    /np >nul 2>&1

if %errorlevel% neq 0 (
    echo FAILED to create daily task. Did you run as Administrator?
    pause
    exit /b 1
)

:: Task 2: Score yesterday at 7:00 AM
schtasks /create /tn "MLB_Edge_Score_Yesterday" ^
    /tr "%P% \"%SCORE_PATH%\"" ^
    /sc daily /st 07:00 ^
    /rl highest ^
    /f ^
    /np >nul 2>&1

echo ============================================================
echo   MLB Edge Auto-Scheduler Setup Complete
echo ============================================================
echo.
echo   Daily pipeline:   11:00 AM  every day
echo   Score yesterday:  7:00 AM  every day
echo.
echo   To check:  Open Task Scheduler, look for:
echo     - MLB_Edge_Daily_Run
echo     - MLB_Edge_Score_Yesterday
echo.
echo   To remove:  Delete those tasks in Task Scheduler.
echo.
pause
