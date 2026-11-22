@echo off
setlocal
echo Checking services...

curl -s http://127.0.0.1:8000/health >nul 2>&1
if errorlevel 1 (
  powershell -NoProfile -Command "try { (Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health).Content; exit 0 } catch { Write-Host '[FAIL] Backend health unreachable'; exit 1 }"
) else (
  curl -s http://127.0.0.1:8000/health
  echo.
)

powershell -NoProfile -Command "try { $r=Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5173; Write-Host '[OK] Frontend HTTP' $r.StatusCode } catch { Write-Host '[WARN] Frontend not reachable yet' }"

docker ps --filter name=cybersecurity_fyp_db --format "[DB] {{.Names}} {{.Status}}" 2>nul
endlocal
