@echo off
REM Double-click this file (Windows) to build the example meta-analysis
REM and open it in your browser. Needs Python installed (python.org).
cd /d "%~dp0"
echo Building the example meta-analysis...
python build.py configs/example_finerenone_ckd.json
if errorlevel 1 (
  echo.
  echo Could not run. Is Python installed? Get it at https://www.python.org/downloads/
  echo During install on Windows, tick "Add Python to PATH".
  pause
  exit /b 1
)
echo.
echo Opening the result in your browser...
start "" "output\example_finerenone_ckd.html"
echo.
echo To make your own: copy a file in the configs\ folder, put your trial
echo numbers in, then run:  python build.py configs\your_file.json
pause
