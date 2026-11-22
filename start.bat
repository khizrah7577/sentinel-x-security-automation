@echo off
setlocal EnableExtensions
cd /d D:\CyberSecurity_FYP

echo ============================================
echo  SENTINEL X — Docker Start
echo ============================================

where docker >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Docker not found on PATH.
  echo         Install/start Docker Desktop, then re-run start.bat
  echo         Dev fallback without Docker: start-dev.bat
  exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Docker Engine is not running.
  echo         Start Docker Desktop and wait until it is ready.
  exit /b 1
)

if not exist ".env" (
  if exist ".env.docker.example" (
    echo [WARN] .env missing — copying from .env.docker.example
    copy /Y .env.docker.example .env >nul
  ) else if exist ".env.example" (
    copy /Y .env.example .env >nul
  )
)

if not exist "data\pcaps" mkdir data\pcaps
if not exist "data\secrets" mkdir data\secrets
if not exist "data\uploads" mkdir data\uploads
if not exist "data\backups" mkdir data\backups
if not exist "data\database\postgres" mkdir data\database\postgres
if not exist "logs" mkdir logs
if not exist "reports" mkdir reports
if not exist "ml\saved_models" mkdir ml\saved_models
if not exist "ml\datasets" mkdir ml\datasets

echo [1/3] Freeing host ports 8000/8080 if old non-Docker processes hold them...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":8000 .*LISTENING"') do (
  for /f "tokens=1" %%I in ('docker ps -q --filter "publish=8000" 2^>nul') do goto :skip8000
  echo       Stopping non-Docker PID %%P on :8000
  taskkill /F /PID %%P >nul 2>&1
)
:skip8000

echo [2/3] Building and starting Compose stack...
docker compose up -d --build
if errorlevel 1 (
  echo [ERROR] docker compose up failed. Run status.bat and logs.bat
  exit /b 1
)

echo [3/3] Waiting for health...
timeout /t 8 /nobreak >nul
docker compose ps
echo.
curl -fsS http://127.0.0.1:8080/health 2>nul && echo. || echo [WARN] nginx /health not ready yet — wait and retry.
curl -fsS http://127.0.0.1:8000/health 2>nul && echo. || echo [WARN] backend :8000 not ready yet.

echo.
echo ----------------------------------------
echo  App (nginx):  http://127.0.0.1:8080
echo  API direct:   http://127.0.0.1:8000/docs
echo  Health:       http://127.0.0.1:8080/health
echo  Login:        admin@localhost / ChangeMeAdmin123!
echo ----------------------------------------
echo  Data on D:    D:\CyberSecurity_FYP\data\
echo  Volumes NEVER deleted by this script.
echo  Cloud prep:   see docs\ORACLE_CLOUD_GUIDE.md
echo ----------------------------------------
endlocal
