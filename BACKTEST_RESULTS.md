@echo off
setlocal enabledelayedexpansion
title MLB Edge v2.4
cd /d "%~dp0"
set "DEST=%TEMP%\mlb_edge"

if exist "%DEST%\mlb_edge\launcher.py" goto :run

echo.
echo   MLB Edge v2.4 -- First Run Setup
echo   ============================================================
echo   Extracting... this only happens once.
echo.

:: Step 1: Write the PowerShell extractor (base64, decoded by certutil)
set "PS1=%TEMP%\_mlb_extract.ps1"
for /f "tokens=1 delims=:" %%a in ('findstr /n "PS1_MARKER" "%~f0"') do set /a PSLINE=%%a+1
more +%PSLINE% "%~f0" > "%TEMP%\_ps1_b64.txt"
certutil -decode "%TEMP%\_ps1_b64.txt" "%PS1%" >nul 2>&1
del "%TEMP%\_ps1_b64.txt" 2>nul

:: Step 2: Run it
if exist "%PS1%" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%" "%~f0" "%DEST%"
    del "%PS1%" 2>nul
)
if exist "%DEST%\mlb_edge\launcher.py" goto :run

:: Fallback: certutil decodes the project zip directly
echo.
echo   Primary extraction failed. Trying fallback...
set "SKIP=0"
for /f "tokens=1 delims=:" %%a in ('findstr /n "PAYLOAD_MARKER" "%~f0"') do set "SKIP=%%a"
if %SKIP% gtr 0 (
    more +%SKIP% "%~f0" > "%DEST%\payload.b64"
    certutil -decode "%DEST%\payload.b64" "%DEST%\payload.zip" >nul 2>&1
    if exist "%DEST%\payload.zip" (
        powershell -NoProfile -Command "Expand-Archive -LiteralPath '%DEST%\payload.zip' -DestinationPath '%DEST%' -Force" >nul 2>&1
        del "%DEST%\payload.zip" 2>nul
    )
    del "%DEST%\payload.b64" 2>nul
)

if not exist "%DEST%\mlb_edge\launcher.py" (
    echo.
    echo   Extraction failed. Make sure you downloaded this file
    echo   (not opened from inside a zip preview).
    echo   Try: right-click this file ^> Properties ^> Unblock.
    pause
    exit /b 1
)

:run
:: Find Python
set P=
where python >nul 2>&1 && set P=python
if not defined P where python3 >nul 2>&1 && set P=python3
if not defined P where py >nul 2>&1 && set P=py
if not defined P (
    echo.
    echo   Python not found. Install from: https://www.python.org/downloads/
    echo   Then double-click this file again.
    start "" "https://www.python.org/downloads/"
    pause
    exit /b 1
)
%P% -c "import requests, bs4" >nul 2>&1 || (
    echo Installing required packages (one-time)...
    %P% -m pip install requests beautifulsoup4 --user -q 2>nul || %P% -m pip install requests beautifulsoup4 -q 2>nul
)

cd /d "%DEST%\mlb_edge"
echo.
echo   ============================================================
echo     MLB Edge v2.4 -- Starting...
echo   ============================================================
echo.
%P% launcher.py
if errorlevel 1 (echo Something went wrong. Try again. & pause)
exit /b 0

---PS1_MARKER---
JABzAGUAbABmACAAPQAgAFsASQBPAC4ARgBpAGwAZQBdADoAOgBSAGUAYQBkAEEAbABsAFQAZQB4AHQAKAAkAGEAcgBnAHMAWwAwAF0AKQAKACQAbQBhAHIAawBlAHIAIAA9ACAAJwBfAF8AUABBAFkATABPAEEARABfAF8AJwAKACQAcAAgAD0AIAAkAHMAZQBsAGYALgBMAGEAcwB0AEkAbgBkAGUAeABPAGYAKAAkAG0AYQByAGsAZQByACkAIAArACAAJABtAGEAcgBrAGUAcgAuAEwAZQBuAGcAdABoAAoAJABiADYANAAgAD0AIAAkAHMAZQBsAGYALgBTAHUAYgBzAHQAcgBpAG4AZwAoACQAcAApAAoAJABjAGwAZQBhAG4AIAA9ACAAJwAnAAoAZgBvAHIAIAAoACQAaQAgAD0AIAAwADsAIAAkAGkAIAAtAGwAdAAgACQAYgA2ADQALgBMAGUAbgBnAHQAaAA7ACAAJABpACsAKwApACAAewAKACAAIAAgACAAJABjACAAPQAgACQAYgA2ADQAWwAkAGkAXQAKACAAIAAgACAAaQBmACAAKAAoACQAYwAgAC0AZwBlACAAJwBBACcAIAAtAGEAbgBkACAAJABjACAALQBsAGUAIAAnAFoAJwApACAALQBvAHIAIAAoACQAYwAgAC0AZwBlACAAJwBhACcAIAAtAGEAbgBkACAAJABjACAALQBsAGUAIAAnAHoAJwApACAALQBvAHIACgAgACAAIAAgACAAIAAgACAAKAAkAGMAIAAtAGcAZQAgACcAMAAnACAALQBhAG4AZAAgACQAYwAgAC0AbABlACAAJwA5ACcAKQAgAC0AbwByACAAJABjACAALQBlAHEAIAAnACsAJwAgAC0AbwByACAAJABjACAALQBlAHEAIAAnAC8AJwAgAC0AbwByACAAJABjACAALQBlAHEAIAAnAD0AJwApACAAewAKACAAIAAgACAAIAAgACAAIAAkAGMAbABlAGEAbgAgACsAPQAgACQAYwAKACAAIAAgACAAfQAKAH0ACgAkAGIANgA0ACAAPQAgACQAYwBsAGUAYQBuAAoAJABwAGEAZAAgAD0AIAAkAGIANgA0AC4ATABlAG4AZwB0AGgAIAAlACAANAAKAGkAZgAgACgAJABwAGEAZAApACAAewAgACQAYgA2ADQAIAArAD0AIAAnAD0AJwAgACoAIAAoADQAIAAtACAAJABwAGEAZAApACAAfQAKACQAYgB5AHQAZQBzACAAPQAgAFsAQwBvAG4AdgBlAHIAdABdADoAOgBGAHIAbwBtAEIAYQBzAGUANgA0AFMAdAByAGkAbgBnACgAJABiADYANAApAAoAJABkAGUAcwB0ACAAPQAgACQAYQByAGcAcwBbADEAXQAKAGkAZgAgACgALQBuAG8AdAAgACgAVABlAHMAdAAtAFAAYQB0AGgAIAAkAGQAZQBzAHQAKQApACAAewAgAE4AZQB3AC0ASQB0AGUAbQAgAC0ASQB0AGUAbQBUAHkAcABlACAARABpAHIAZQBjAHQAbwByAHkAIAAtAFAAYQB0AGgAIAAkAGQAZQBzAHQAIAAtAEYAbwByAGMAZQAgAHwAIABPAHUAdAAtAE4AdQBsAGwAIAB9AAoAJAB6AGkAcAAgAD0AIABKAG8AaQBuAC0AUABhAHQAaAAgACQAZABlAHMAdAAgACcAcABhAHkAbABvAGEAZAAuAHoAaQBwACcACgBbAEkATwAuAEYAaQBsAGUAXQA6ADoAVwByAGkAdABlAEEAbABsAEIAeQB0AGUAcwAoACQAegBpAHAALAAgACQAYgB5AHQAZQBzACkACgBFAHgAcABhAG4AZAAtAEEAcgBjAGgAaQB2AGUAIAAtAEwAaQB0AGUAcgBhAGwAUABhAHQAaAAgACQAegBpAHAAIAAtAEQAZQBzAHQAaQBuAGEAdABpAG8AbgBQAGEAdABoACAAJABkAGUAcwB0ACAALQBGAG8AcgBjAGUACgBSAGUAbQBvAHYAZQAtAEkAdABlAG0AIAAkAHoAaQBwACAALQBGAG8AcgBjAGUACgA=
---PAYLOAD_MARKER---
