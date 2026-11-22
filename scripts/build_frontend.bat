@echo off
setlocal
cd /d D:\CyberSecurity_FYP\frontend
if exist "D:\node\npm.cmd" (
  D:\node\npm.cmd run build
) else (
  npm run build
)
echo Production build output: D:\CyberSecurity_FYP\frontend\dist
endlocal
