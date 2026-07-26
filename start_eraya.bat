@echo off
REM ─────────────────────────────────────────────────────────────
REM  ERAYA — start the site + public tunnel on this laptop.
REM  Runs at logon via Task Scheduler (task: "ERAYA Autostart"),
REM  or double-click this file any time.
REM
REM  Public : https://disarray-malformed-visor.ngrok-free.dev
REM  Local  : http://localhost:8022/
REM ─────────────────────────────────────────────────────────────
title ERAYA - server + tunnel
cd /d "%~dp0backend"

set DJANGO_SETTINGS_MODULE=eraya.settings.development
set PYTHONUNBUFFERED=1

REM --- stop anything already listening, so restarts are clean ---
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:"LISTENING.*:8022"') do taskkill /F /PID %%p >nul 2>&1
taskkill /F /IM ngrok.exe >nul 2>&1

echo.
echo   ERAYA starting...
echo   ------------------------------------------------
echo   Public : https://disarray-malformed-visor.ngrok-free.dev
echo   Local  : http://localhost:8022/
echo   ------------------------------------------------
echo.

REM --- backend (hidden) ---
start "" /min ".venv\Scripts\python.exe" -m daphne -b 0.0.0.0 -p 8022 eraya.asgi:application

REM --- give Django a moment, then open the tunnel ---
timeout /t 8 /nobreak >nul
start "" /min "%~dp0tools\ngrok\ngrok.exe" http --url=disarray-malformed-visor.ngrok-free.dev 8022

echo   Both started. This window can be closed - they keep running.
echo   To stop everything, run stop_eraya.bat
timeout /t 6 /nobreak >nul
