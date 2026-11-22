@echo off
setlocal EnableExtensions
cd /d D:\CyberSecurity_FYP
echo SENTINEL X — Restart
call stop.bat
timeout /t 3 /nobreak >nul
call start.bat
endlocal
