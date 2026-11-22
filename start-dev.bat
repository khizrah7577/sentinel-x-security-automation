@echo off
setlocal EnableExtensions
cd /d D:\CyberSecurity_FYP

echo ============================================
echo  CyberSecurity_FYP — Local Development Start
echo ============================================

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Virtual environment missing.
  echo         Run: scripts\setup_venv.bat
  exit /b 1
)

if not exist ".env" (
  echo [WARN] .env missing — copying from .env.example
  copy /Y .env.example .env >nul
)

if not exist "logs" mkdir logs
if not exist "data\pcaps" mkdir data\pcaps
if not exist "data\database" mkdir data\database
if not exist "data\backups" mkdir data\backups

echo [1/4] Starting PostgreSQL via Docker Compose...
where docker-compose >nul 2>&1
if errorlevel 1 (
  echo [WARN] docker-compose not found on PATH.
) else (
  docker-compose up -d
  if errorlevel 1 (
    echo [WARN] Docker Compose failed. Start Docker Desktop, then re-run start.bat.
  ) else (
    echo       Waiting for database health...
    timeout /t 5 /nobreak >nul
  )
)

echo [2/4] Starting backend API on http://127.0.0.1:8000 ...
start "CyberSecurity_FYP Backend" cmd /k "cd /d D:\CyberSecurity_FYP\backend && set PYTHONPATH=D:\CyberSecurity_FYP\backend && D:\CyberSecurity_FYP\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

timeout /t 3 /nobreak >nul

echo [3/4] Starting frontend on http://127.0.0.1:5173 ...
if exist "frontend\package.json" (
  if exist "D:\node\npm.cmd" (
    start "CyberSecurity_FYP Frontend" cmd /k "cd /d D:\CyberSecurity_FYP\frontend && D:\node\npm.cmd run dev -- --host 127.0.0.1 --port 5173"
  ) else (
    start "CyberSecurity_FYP Frontend" cmd /k "cd /d D:\CyberSecurity_FYP\frontend && npm run dev -- --host 127.0.0.1 --port 5173"
  )
) else (
  echo [ERROR] frontend\package.json missing
)

echo [4/4] Running health check...
timeout /t 4 /nobreak >nul
call scripts\healthcheck.bat

echo.
echo ----------------------------------------
echo  Frontend:  http://127.0.0.1:5173
echo  API docs:  http://127.0.0.1:8000/docs
echo  Health:    http://127.0.0.1:8000/health
echo  Login:     admin@localhost / ChangeMeAdmin123!
echo ----------------------------------------
echo  Stop DB containers with stop.bat
echo  Close Backend/Frontend console windows to stop apps
echo  Data persists under D:\CyberSecurity_FYP\data\
echo ----------------------------------------
endlocal
