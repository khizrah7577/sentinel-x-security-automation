@echo off
setlocal EnableExtensions
cd /d D:\CyberSecurity_FYP

echo ============================================
echo  SENTINEL X — Backup (to D:\...\data\backups)
echo ============================================

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%I"
set "BDIR=D:\CyberSecurity_FYP\data\backups\%STAMP%"
mkdir "%BDIR%" 2>nul
mkdir "%BDIR%\ml" 2>nul
mkdir "%BDIR%\reports" 2>nul
mkdir "%BDIR%\secrets" 2>nul

where docker >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Docker required for DB dump.
  exit /b 1
)

echo [1/3] PostgreSQL dump...
docker compose exec -T postgres pg_dump -U cybersec cybersecurity_fyp > "%BDIR%\db.sql"
if errorlevel 1 (
  echo [WARN] pg_dump via compose failed — trying container name...
  docker exec -i cybersecurity_fyp_db pg_dump -U cybersec cybersecurity_fyp > "%BDIR%\db.sql"
)

echo [2/3] Copying models / reports / secrets (not large PCAPs)...
if exist "D:\CyberSecurity_FYP\ml\saved_models\*" xcopy /E /I /Y "D:\CyberSecurity_FYP\ml\saved_models\*" "%BDIR%\ml\" >nul
if exist "D:\CyberSecurity_FYP\reports\*" xcopy /E /I /Y "D:\CyberSecurity_FYP\reports\*" "%BDIR%\reports\" >nul
if exist "D:\CyberSecurity_FYP\data\secrets\*" xcopy /E /I /Y "D:\CyberSecurity_FYP\data\secrets\*" "%BDIR%\secrets\" >nul

echo [3/3] Writing manifest...
echo SENTINEL X backup %STAMP%> "%BDIR%\MANIFEST.txt"
echo Path: %BDIR%>> "%BDIR%\MANIFEST.txt"

echo.
echo Backup complete:
echo   %BDIR%
echo PCAPs under data\pcaps are NOT copied automatically.
endlocal
