@echo off
setlocal EnableExtensions
cd /d D:\CyberSecurity_FYP

echo ============================================
echo  SENTINEL X — Restore
echo ============================================
echo This will overwrite the CURRENT database contents.
echo Volumes/files outside the dump are not auto-deleted.
echo.

if "%~1"=="" (
  echo Usage: restore.bat D:\CyberSecurity_FYP\data\backups\TIMESTAMP
  echo.
  echo Available backups:
  dir /b /ad D:\CyberSecurity_FYP\data\backups 2>nul
  exit /b 1
)

set "BDIR=%~1"
if not exist "%BDIR%\db.sql" (
  echo [ERROR] Missing %BDIR%\db.sql
  exit /b 1
)

echo Target backup: %BDIR%
set /p CONFIRM=Type YES to restore database: 
if /I not "%CONFIRM%"=="YES" (
  echo Cancelled. No changes made.
  exit /b 0
)

where docker >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Docker required.
  exit /b 1
)

echo Restoring database...
type "%BDIR%\db.sql" | docker compose exec -T postgres psql -U cybersec -d cybersecurity_fyp
if errorlevel 1 (
  type "%BDIR%\db.sql" | docker exec -i cybersecurity_fyp_db psql -U cybersec -d cybersecurity_fyp
)

if exist "%BDIR%\ml" (
  echo Restoring ML models...
  xcopy /E /I /Y "%BDIR%\ml\*" "D:\CyberSecurity_FYP\ml\saved_models\" >nul
)
if exist "%BDIR%\reports" (
  xcopy /E /I /Y "%BDIR%\reports\*" "D:\CyberSecurity_FYP\reports\" >nul
)
if exist "%BDIR%\secrets" (
  xcopy /E /I /Y "%BDIR%\secrets\*" "D:\CyberSecurity_FYP\data\secrets\" >nul
)

echo Restore finished. Run restart.bat if services were mid-write.
endlocal
