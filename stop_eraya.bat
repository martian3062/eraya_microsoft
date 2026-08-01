@echo off
setlocal

rem Stop the ERAYA local origin and public tunnel.

set "PORT=8022"
title ERAYA - stop

for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:":%PORT% .*LISTENING"') do taskkill /F /PID %%p >nul 2>&1
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*daphne*' -and $_.CommandLine -like '*-p %PORT%*' -and $_.CommandLine -like '*eraya.asgi*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1
taskkill /F /IM cloudflared.exe >nul 2>&1

echo   ERAYA stopped (origin + Cloudflare Tunnel).
ping -n 4 127.0.0.1 >nul
