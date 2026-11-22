@echo off
setlocal EnableExtensions
cd /d D:\CyberSecurity_FYP

echo ============================================
echo  SENTINEL X — Status
echo ============================================

where docker >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Docker not found.
  exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Docker Engine not running.
  exit /b 1
)

echo --- Compose services ---
docker compose ps
echo.
echo --- Health ---
curl -fsS http://127.0.0.1:8080/health 2>nul || echo nginx:8080 DOWN
curl -fsS http://127.0.0.1:8000/health 2>nul || echo backend:8000 DOWN
echo.
echo --- Disk (D:) ---
powershell -NoProfile -Command "Get-PSDrive D | Select-Object Used,Free | Format-List"
endlocal
