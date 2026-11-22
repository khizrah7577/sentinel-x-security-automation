@echo off
setlocal EnableExtensions
cd /d D:\CyberSecurity_FYP

echo ============================================
echo  SENTINEL X — Docker Stop
echo ============================================

where docker >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Docker not found.
  exit /b 1
)

echo Stopping containers (volumes and D: data KEPT)...
docker compose down
if errorlevel 1 (
  echo [WARN] compose down reported an error — containers may already be stopped.
)

echo.
echo Persistent data remains at:
echo   D:\CyberSecurity_FYP\data\
echo   D:\CyberSecurity_FYP\ml\saved_models\
echo   D:\CyberSecurity_FYP\logs\
echo   D:\CyberSecurity_FYP\reports\
echo.
echo To also stop the old venv servers: stop-dev.bat
endlocal
