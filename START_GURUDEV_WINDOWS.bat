@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel%==0 (set "PY=py -3") else (set "PY=python")
if not exist ".venv\Scripts\python.exe" (
  %PY% -m venv .venv
  if errorlevel 1 (
    echo Python 3.10 or newer is needed. Install Python before running locally.
    pause
    exit /b 1
  )
)
call .venv\Scripts\activate.bat
python -m pip install -e .
if errorlevel 1 (
  echo Installation failed; do not assume the application is running.
  pause
  exit /b 1
)
start "" http://127.0.0.1:8502
python -m gurudev_ai.companion.server
pause
