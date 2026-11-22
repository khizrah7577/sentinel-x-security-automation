@echo off
REM Production-style local API (no --reload). Still binds to localhost by default.
setlocal
cd /d D:\CyberSecurity_FYP\backend
set PYTHONPATH=D:\CyberSecurity_FYP\backend
set APP_ENV=production
set APP_DEBUG=false
D:\CyberSecurity_FYP\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 --log-level info
endlocal
