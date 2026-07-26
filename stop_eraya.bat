@echo off
REM Stop the ERAYA site + public tunnel.
title ERAYA - stop
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:"LISTENING.*:8022"') do taskkill /F /PID %%p >nul 2>&1
taskkill /F /IM ngrok.exe >nul 2>&1
echo   ERAYA stopped (site + tunnel).
timeout /t 3 /nobreak >nul
