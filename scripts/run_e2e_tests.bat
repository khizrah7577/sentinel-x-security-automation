@echo off
cd /d D:\CyberSecurity_FYP
D:\CyberSecurity_FYP\.venv\Scripts\python.exe scripts\e2e_integration_test.py
echo.
D:\CyberSecurity_FYP\.venv\Scripts\python.exe -m pytest backend\tests -q
exit /b %ERRORLEVEL%
