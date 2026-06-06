#!/usr/bin/env python3
"""
MLB Edge v2.4 -- Distribution Builder

Output:
    MLB_Edge_v2.4_sfx.bat  -- Windows: double-click, extracts + runs
    MLB_Edge_v2.4.py       -- Any OS: double-click, extracts + runs
"""
import base64, io, os, sys, zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
MLB_EDGE_DIR = SCRIPT_DIR
OUTPUT_DIR = PROJECT_ROOT


def build_zip_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(MLB_EDGE_DIR):
            dirs[:] = [d for d in dirs if d not in
                       {"__pycache__", ".arena", ".git", "data", "output"}]
            for fname in files:
                if fname.endswith((".pyc", ".DS_Store")):
                    continue
                if fname == os.path.basename(__file__):
                    continue
                fpath = Path(root) / fname
                rel = fpath.relative_to(MLB_EDGE_DIR)
                rel_str = str(rel).replace("\\", "/")
                if "data/cache/" in rel_str or "output/" in rel_str:
                    continue
                zf.write(fpath, f"mlb_edge/{rel_str}")
        for name in ["START.bat", "README.md", "START.command"]:
            p = PROJECT_ROOT / name
            if p.exists():
                zf.write(p, name)
    return buf.getvalue()


# ================================================================
# Self-extracting .bat (Windows) -- certutil + PowerShell unzip
# ================================================================

SFX_BAT_HEADER = r"""
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

:: Step 1: find PS1_MARKER line, extract ONLY the next line (PS1 base64)
:: for loop overwrites SKIP; final = boundary line number
for /f "tokens=1 delims=:" %%a in ('findstr /n /c:"===PS1_MARKER_a7f3===" "%~f0"') do set /a SKIP=%%a
:: Read just the first line that comes after the marker
more +%SKIP% "%~f0" | findstr /r "^[A-Za-z0-9+/=]" > "%TEMP%\_ps1_b64.txt"
set "PS1=%TEMP%\_mlb_extract.ps1"
certutil -decode "%TEMP%\_ps1_b64.txt" "%PS1%" >nul 2>&1
del "%TEMP%\_ps1_b64.txt" 2>nul

:: Step 2: run PS1
if exist "%PS1%" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%" "%~f0" "%DEST%" "===PAYLOAD_MARKER_b9d2==="
    del "%PS1%" 2>nul
)
if exist "%DEST%\mlb_edge\launcher.py" goto :run

:: Fallback: certutil direct
echo.
echo   Primary extraction failed. Trying fallback...
for /f "tokens=1 delims=:" %%a in ('findstr /n /c:"===PAYLOAD_MARKER_b9d2===" "%~f0"') do set /a SKIP=%%a
more +%SKIP% "%~f0" > "%DEST%\payload.b64"
certutil -decode "%DEST%\payload.b64" "%DEST%\payload.zip" >nul 2>&1
if exist "%DEST%\payload.zip" (
    powershell -NoProfile -Command "Expand-Archive -LiteralPath '%DEST%\payload.zip' -DestinationPath '%DEST%' -Force" >nul 2>&1
    del "%DEST%\payload.zip" 2>nul
)
del "%DEST%\payload.b64" 2>nul

if not exist "%DEST%\mlb_edge\launcher.py" (
    echo.
    echo   Extraction failed. Make sure you downloaded this file.
    echo   Try: right-click this file ^> Properties ^> Unblock.
    pause
    exit /b 1
)

:run
set P=
where python >nul 2>&1 && set P=python
if not defined P where python3 >nul 2>&1 && set P=python3
if not defined P where py >nul 2>&1 && set P=py
if not defined P (
    echo Python not found. Install from: https://www.python.org/downloads/
    start "" "https://www.python.org/downloads/"
    pause
    exit /b 1
)
%P% -c "import requests, bs4" >nul 2>&1 || (
    echo Installing required packages...
    %P% -m pip install requests beautifulsoup4 --user -q 2>nul || %P% -m pip install requests beautifulsoup4 -q 2>nul
)

cd /d "%DEST%\mlb_edge"
echo.
echo   ============================================================
echo     MLB Edge v2.4 -- Starting...
echo   ============================================================
echo.
%P% launcher.py
if errorlevel 1 (echo Failed. Try running again. & pause)
exit /b 0

===PS1_MARKER_a7f3===
JABzAGUAbABmACAAPQAgAFsASQBPAC4ARgBpAGwAZQBdADoAOgBSAGUAYQBkAEEAbABsAFQAZQB4AHQAKAAkAGEAcgBnAHMAWwAwAF0AKQAKACQAbQAgAD0AIAAkAGEAcgBnAHMAWwAyAF0ACgAkAHAAIAA9ACAAJABzAGUAbABmAC4ATABhAHMAdABJAG4AZABlAHgATwBmACgAJABtACkAIAArACAAJABtAC4ATABlAG4AZwB0AGgACgAkAGIANgA0ACAAPQAgACQAcwBlAGwAZgAuAFMAdQBiAHMAdAByAGkAbgBnACgAJABwACkACgAkAGMAbABlAGEAbgAgAD0AIAAnACcACgBmAG8AcgAgACgAJABpACAAPQAgADAAOwAgACQAaQAgAC0AbAB0ACAAJABiADYANAAuAEwAZQBuAGcAdABoADsAIAAkAGkAKwArACkAIAB7AAoAIAAgACAAIAAkAGMAIAA9ACAAJABiADYANABbACQAaQBdAAoAIAAgACAAIABpAGYAIAAoACgAJABjACAALQBnAGUAIAAnAEEAJwAgAC0AYQBuAGQAIAAkAGMAIAAtAGwAZQAgACcAWgAnACkAIAAtAG8AcgAgACgAJABjACAALQBnAGUAIAAnAGEAJwAgAC0AYQBuAGQAIAAkAGMAIAAtAGwAZQAgACcAegAnACkAIAAtAG8AcgAKACAAIAAgACAAIAAgACAAIAAoACQAYwAgAC0AZwBlACAAJwAwACcAIAAtAGEAbgBkACAAJABjACAALQBsAGUAIAAnADkAJwApACAALQBvAHIAIAAkAGMAIAAtAGUAcQAgACcAKwAnACAALQBvAHIAIAAkAGMAIAAtAGUAcQAgACcALwAnACAALQBvAHIAIAAkAGMAIAAtAGUAcQAgACcAPQAnACkAIAB7AAoAIAAgACAAIAAgACAAIAAgACQAYwBsAGUAYQBuACAAKwA9ACAAJABjAAoAIAAgACAAIAB9AAoAfQAKACQAYgA2ADQAIAA9ACAAJABjAGwAZQBhAG4ACgAkAHAAYQBkACAAPQAgACQAYgA2ADQALgBMAGUAbgBnAHQAaAAgACUAIAA0AAoAaQBmACAAKAAkAHAAYQBkACkAIAB7ACAAJABiADYANAAgACsAPQAgACcAPQAnACAAKgAgACgANAAgAC0AIAAkAHAAYQBkACkAIAB9AAoAJABiAHkAdABlAHMAIAA9ACAAWwBDAG8AbgB2AGUAcgB0AF0AOgA6AEYAcgBvAG0AQgBhAHMAZQA2ADQAUwB0AHIAaQBuAGcAKAAkAGIANgA0ACkACgAkAGQAZQBzAHQAIAA9ACAAJABhAHIAZwBzAFsAMQBdAAoAaQBmACAAKAAtAG4AbwB0ACAAKABUAGUAcwB0AC0AUABhAHQAaAAgACQAZABlAHMAdAApACkAIAB7ACAATgBlAHcALQBJAHQAZQBtACAALQBJAHQAZQBtAFQAeQBwAGUAIABEAGkAcgBlAGMAdABvAHIAeQAgAC0AUABhAHQAaAAgACQAZABlAHMAdAAgAC0ARgBvAHIAYwBlACAAfAAgAE8AdQB0AC0ATgB1AGwAbAAgAH0ACgAkAHoAaQBwACAAPQAgAEoAbwBpAG4ALQBQAGEAdABoACAAJABkAGUAcwB0ACAAJwBwAGEAeQBsAG8AYQBkAC4AegBpAHAAJwAKAFsASQBPAC4ARgBpAGwAZQBdADoAOgBXAHIAaQB0AGUAQQBsAGwAQgB5AHQAZQBzACgAJAB6AGkAcAAsACAAJABiAHkAdABlAHMAKQAKAEUAeABwAGEAbgBkAC0AQQByAGMAaABpAHYAZQAgAC0ATABpAHQAZQByAGEAbABQAGEAdABoACAAJAB6AGkAcAAgAC0ARABlAHMAdABpAG4AYQB0AGkAbwBuAFAAYQB0AGgAIAAkAGQAZQBzAHQAIAAtAEYAbwByAGMAZQAKAFIAZQBtAG8AdgBlAC0ASQB0AGUAbQAgACQAegBpAHAAIAAtAEYAbwByAGMAZQAKAA==
===PAYLOAD_MARKER_b9d2===
"""
def build_sfx_bat(zip_bytes: bytes, output_path: Path):
    proj_b64 = base64.b64encode(zip_bytes).decode("ascii")
    # Split into 64-char lines for clean base64
    lines = [proj_b64[i:i+64] for i in range(0, len(proj_b64), 64)]

    with open(output_path, "w", encoding="ascii", newline="\r\n") as f:
        f.write(SFX_BAT_HEADER)
        for line in lines:
            f.write(line + "\r\n")

    mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  SFX Batch: {output_path.name} ({mb:.1f} MB) -- Windows double-click")


# ================================================================
# Single .py bootstrap (cross-platform)
# ================================================================

BOOTSTRAP_HEADER = """#!/usr/bin/env python3
\"\"\"MLB Edge v2.4 -- Single-File Distribution. Double-click to run.\"\"\"
import base64, os, sys, zipfile, io, subprocess
from pathlib import Path

_PAYLOAD_B64 = \"\"\"
{payload}
\"\"\"

DEST = Path.home() / ".mlb_edge"

def _extract():
    if (DEST / "mlb_edge" / "launcher.py").exists():
        return
    print("\\n  MLB Edge v2.4 -- First Run Setup")
    print("  Extracting... this only happens once.\\n")
    b64 = "".join(_PAYLOAD_B64.split()).strip()
    pad = len(b64) % 4
    if pad: b64 += "=" * (4 - pad)
    try:
        zip_bytes = base64.b64decode(b64)
    except Exception as e:
        print(f"  ERROR: {e}. File may be corrupted. Re-download.")
        input("  Press Enter to exit...")
        sys.exit(1)
    DEST.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        zf.extractall(DEST)
    print("  Ready!\\n")

def _install_deps():
    try: import requests, bs4  # noqa: F401
    except ImportError:
        print("  Installing packages (one-time)...")
        subprocess.run([sys.executable, "-m", "pip", "install",
                        "requests", "beautifulsoup4", "--user", "-q"], check=False)

def main():
    _extract()
    _install_deps()
    launcher = DEST / "mlb_edge" / "launcher.py"
    if not launcher.exists():
        print("  Extraction failed. Re-download the file.")
        input("  Press Enter to exit...")
        sys.exit(1)
    os.chdir(str(launcher.parent))
    with open(launcher) as f: exec(f.read())

if __name__ == "__main__":
    main()
"""


def build_single_py(zip_bytes: bytes, output_path: Path):
    b64 = base64.b64encode(zip_bytes).decode("ascii")
    chunks = [b64[i:i+1000] for i in range(0, len(b64), 1000)]
    content = BOOTSTRAP_HEADER.replace("{payload}", "\n".join(chunks))
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  Bootstrap .py: {output_path.name} ({mb:.1f} MB) -- any OS double-click")


# ================================================================
# Verify
# ================================================================

def verify(filepath: Path, extract_fn) -> tuple:
    raw = filepath.read_text(encoding="utf-8", errors="replace")
    b64 = extract_fn(raw).strip()
    b64 = "".join(b64.split())
    pad = len(b64) % 4
    if pad: b64 += "=" * (4 - pad)
    zip_bytes = base64.b64decode(b64)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
    ok = all(r in names for r in ["mlb_edge/launcher.py", "mlb_edge/run.py", "START.bat"])
    return ok, len(names)


def main():
    print()
    print("=" * 60)
    print("  MLB Edge v2.4 -- Distribution Builder")
    print("=" * 60)
    print()
    print("  Building project zip...")

    zip_bytes = build_zip_bytes()
    print(f"  Project zip: {len(zip_bytes) / 1024:.0f} KB")

    bat_path = OUTPUT_DIR / "MLB_Edge_v2.4_sfx.bat"
    build_sfx_bat(zip_bytes, bat_path)

    py_path = OUTPUT_DIR / "MLB_Edge_v2.4.py"
    build_single_py(zip_bytes, py_path)

    print()
    print("  Verifying...")

    def extract_bat(raw):
        m = "===PAYLOAD_MARKER_b9d2==="
        i = raw.rfind(m)
        return raw[i + len(m):] if i > 0 else ""

    def extract_py(raw):
        s = '_PAYLOAD_B64 = """'
        i = raw.find(s)
        if i < 0: return ""
        i += len(s)
        e = raw.find('"""', i)
        return raw[i:e] if e > 0 else ""

    for path, fn, label in [(bat_path, extract_bat, "SFX .bat"),
                             (py_path, extract_py, ".py")]:
        ok, count = verify(path, fn)
        print(f"  [{'OK' if ok else 'FAIL'}] {label}: {count} files")

    print()
    print("  Share these files:")
    print(f"    Windows  -> {bat_path.name}")
    print(f"    Mac/Lin  -> {py_path.name}")
    print()
    print("  Both are single files. No unzipping. Double-click to run.")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
