@echo off
setlocal
set "JOB_INTEL_APP=%~dp0app"
if not exist "%JOB_INTEL_APP%\start.py" set "JOB_INTEL_APP=%~dp0."
set "JOB_INTEL_PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%JOB_INTEL_PYTHON%" set "JOB_INTEL_PYTHON=%JOB_INTEL_APP%\.venv\Scripts\python.exe"
if not exist "%JOB_INTEL_PYTHON%" (
  echo Missing Python environment. See app\README.md or README.md for setup.
  pause
  exit /b 1
)
cd /d "%JOB_INTEL_APP%"
"%JOB_INTEL_PYTHON%" "%JOB_INTEL_APP%\start.py" --no-scrape %*
if errorlevel 1 pause
