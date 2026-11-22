@echo off
setlocal EnableExtensions
cd /d D:\CyberSecurity_FYP

echo ============================================
echo  CyberSecurity_FYP — Stop
echo ============================================

echo [1/2] Stopping Docker Compose PostgreSQL (data volume kept on D:)...
docker-compose down 2>nul
if errorlevel 1 (
  echo [WARN] Docker Compose not available or already stopped.
) else (
  echo       Database container stopped. Volume data retained.
)

echo [2/2] Attempting to free ports 8000 and 5173...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":8000 .*LISTENING"') do (
  echo Killing PID %%P on port 8000
  taskkill /F /PID %%P >nul 2>&1
)
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":5173 .*LISTENING"') do (
  echo Killing PID %%P on port 5173
  taskkill /F /PID %%P >nul 2>&1
)

echo.
echo Persistent data remains at:
echo   D:\CyberSecurity_FYP\data\
echo   D:\CyberSecurity_FYP\ml\saved_models\
echo   D:\CyberSecurity_FYP\logs\
endlocal
