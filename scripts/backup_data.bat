@echo off
setlocal EnableExtensions
cd /d D:\CyberSecurity_FYP

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set STAMP=%%I
set DEST=D:\CyberSecurity_FYP\data\backups\backup_%STAMP%
mkdir "%DEST%" 2>nul

echo Backing up application data to %DEST%
echo [1/3] Copying secrets metadata folder structure (encrypted blobs)...
xcopy /E /I /Y "data\secrets" "%DEST%\secrets" >nul 2>&1

echo [2/3] Exporting Postgres dump via Docker (if running)...
docker exec cybersecurity_fyp_db pg_dump -U cybersec cybersecurity_fyp > "%DEST%\postgres_dump.sql" 2>nul
if errorlevel 1 (
  echo [WARN] pg_dump skipped — ensure container cybersecurity_fyp_db is running.
) else (
  echo       postgres_dump.sql written
)

echo [3/3] Copying model metrics and dataset manifests...
xcopy /E /I /Y "ml\saved_models\*_metrics.json" "%DEST%\model_metrics\" >nul 2>&1
copy /Y "docs\PROGRESS.md" "%DEST%\PROGRESS.md" >nul 2>&1

echo.
echo Backup complete: %DEST%
echo Note: large PCAP binaries are not copied by default to save space.
echo       Copy data\pcaps manually if needed.
endlocal
