@echo off
setlocal
cd /d D:\CyberSecurity_FYP
set PIP_CACHE_DIR=D:\CyberSecurity_FYP\data\cache\pip
mkdir "%PIP_CACHE_DIR%" 2>nul

set PY312=C:\Users\PC\AppData\Local\Programs\Python\Python312\python.exe
if not exist "%PY312%" (
  echo Python 3.12 not found at %PY312%
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment with Python 3.12...
  "%PY312%" -m venv .venv
)

echo Installing backend requirements...
".venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
".venv\Scripts\python.exe" -m pip install -r backend\requirements.txt
echo Done.
endlocal
