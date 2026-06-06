"""
MLB Edge v2.4 — Simple Launcher
Runs analysis directly, opens report in browser.
Zero complexity. Zero subprocess. Zero state management.
"""
import os
import sys
import time
import webbrowser
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
os.chdir(str(THIS_DIR))

# Install dependencies if needed
try:
    import requests, bs4  # noqa: F401
except ImportError:
    print("Installing required packages (one-time)...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install",
                    "requests", "beautifulsoup4", "--user", "-q"], check=False)
    print("Done.\n")

print("=" * 60)
print("  MLB Edge v2.4 — Running Analysis")
print("=" * 60)
print()
print("  This takes 45-90 seconds. Progress will appear below.")
print("  The report opens in your browser when done.")
print()

t0 = time.time()

# Run run.py in this process — no subprocess, no pipes, no deadlocks
try:
    import runpy
    runpy.run_path(str(THIS_DIR / "run.py"), run_name="__main__")
except SystemExit:
    pass  # run.py calls sys.exit() at the end — that's normal
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
    print()
    input("Press Enter to close...")
    sys.exit(1)

elapsed = time.time() - t0
print(f"\n  Analysis completed in {elapsed:.0f}s.")

# Open the report
output_dir = THIS_DIR / "output"
reports = sorted(output_dir.glob("mlb_edge_report*.html"),
                 key=lambda p: p.stat().st_mtime, reverse=True)

if reports:
    report_path = str(reports[0])
    webbrowser.open(f"file:///{report_path}")
    print(f"  Report opened: {reports[0].name}")
else:
    print("  WARNING: No report found. Check errors above.")

print()
input("Press Enter to close...")
