@echo off
setlocal EnableExtensions
cd /d D:\CyberSecurity_FYP

echo ============================================
echo  SENTINEL X — Logs (Ctrl+C to stop)
echo  Usage: logs.bat [service]
echo  Services: nginx backend frontend postgres
echo ============================================

where docker >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Docker not found.
  exit /b 1
)

if "%~1"=="" (
  docker compose logs -f --tail=100
) else (
  docker compose logs -f --tail=100 %~1
)
endlocal
