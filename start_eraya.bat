@echo off
setlocal

rem ERAYA - start the local origin and Cloudflare Tunnel for eraya.online.
rem Double-click this file, or run it from PowerShell/cmd.

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "PYTHON=%BACKEND%\.venv\Scripts\python.exe"
set "CLOUDFLARED=cloudflared.exe"
set "CF_CONFIG=%USERPROFILE%\.cloudflared\config.yml"
set "PORT=8022"

title ERAYA - Cloudflare server
cd /d "%BACKEND%"

if not exist "%PYTHON%" (
  echo Missing Python venv: %PYTHON%
  echo Create/install the backend venv first.
  ping -n 9 127.0.0.1 >nul
  exit /b 1
)

where.exe "%CLOUDFLARED%" >nul 2>&1
if errorlevel 1 (
  echo Missing cloudflared on PATH.
  echo Install cloudflared, then run this again.
  ping -n 9 127.0.0.1 >nul
  exit /b 1
)

if not exist "%CF_CONFIG%" (
  echo Missing Cloudflare tunnel config: %CF_CONFIG%
  echo Restore %%USERPROFILE%%\.cloudflared\config.yml for eraya.online.
  ping -n 9 127.0.0.1 >nul
  exit /b 1
)

set "DJANGO_SETTINGS_MODULE=eraya.settings.vm"
set "PYTHONUNBUFFERED=1"

rem Stop stale local origin/tunnel processes before starting cleanly.
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:":%PORT% .*LISTENING"') do taskkill /F /PID %%p >nul 2>&1
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*daphne*' -and $_.CommandLine -like '*-p %PORT%*' -and $_.CommandLine -like '*eraya.asgi*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1
taskkill /F /IM cloudflared.exe >nul 2>&1

echo.
echo   ERAYA starting...
echo   ------------------------------------------------
echo   Public : https://eraya.online
echo   Local  : http://127.0.0.1:%PORT%/
echo   Tunnel : %CF_CONFIG%
echo   ------------------------------------------------
echo.

echo   Checking Django...
"%PYTHON%" manage.py check || goto :fail

echo   Collecting static files...
"%PYTHON%" manage.py collectstatic --noinput > "%ROOT%eraya-collectstatic.log" 2>&1
if errorlevel 1 goto :static_fail

echo   Starting Daphne origin...
start "" /min "%PYTHON%" -m daphne -b 127.0.0.1 -p %PORT% eraya.asgi:application

ping -n 7 127.0.0.1 >nul
curl.exe -fsS "http://127.0.0.1:%PORT%/" >nul
if errorlevel 1 goto :origin_fail

echo   Starting Cloudflare Tunnel...
start "" /min "%CLOUDFLARED%" --config "%CF_CONFIG%" tunnel run

ping -n 7 127.0.0.1 >nul
tasklist /FI "IMAGENAME eq cloudflared.exe" | find /I "cloudflared.exe" >nul
if errorlevel 1 goto :tunnel_fail

echo.
echo   ERAYA is running.
echo   Public : https://eraya.online
echo   Local  : http://127.0.0.1:%PORT%/
echo.
echo   To stop everything, run stop_eraya.bat
ping -n 7 127.0.0.1 >nul
exit /b 0

:static_fail
echo collectstatic failed. See %ROOT%eraya-collectstatic.log
ping -n 11 127.0.0.1 >nul
exit /b 1

:origin_fail
echo Daphne started but the local origin did not answer on %PORT%.
ping -n 11 127.0.0.1 >nul
exit /b 1

:tunnel_fail
echo cloudflared did not stay running. Check the tunnel config and Cloudflare credentials.
ping -n 11 127.0.0.1 >nul
exit /b 1

:fail
echo Django check failed.
ping -n 11 127.0.0.1 >nul
exit /b 1
