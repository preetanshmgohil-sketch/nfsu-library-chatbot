@echo off
title NFSU Library Chatbot - Stop
echo Stopping NFSU chatbot servers on ports 8000 and 8080...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000.*LISTENING"') do (
  echo   killing PID %%p on :8000
  taskkill /PID %%p /F >nul 2>nul
)
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8080.*LISTENING"') do (
  echo   killing PID %%p on :8080
  taskkill /PID %%p /F >nul 2>nul
)
echo Done.
