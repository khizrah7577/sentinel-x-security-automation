@echo off
setlocal EnableExtensions
cd /d D:\CyberSecurity_FYP

echo ============================================
echo  SENTINEL X — Update (rebuild images)
echo ============================================

where docker >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Docker not found.
  exit /b 1
)

echo Pulling base images (postgres/nginx) and rebuilding app images...
docker compose pull postgres nginx
docker compose build --pull
if errorlevel 1 (
  echo [ERROR] Build failed.
  exit /b 1
)

echo Recreating containers (named volumes / D: binds kept)...
docker compose up -d --remove-orphans
docker compose ps
echo.
echo Update complete. Health: http://127.0.0.1:8080/health
endlocal
