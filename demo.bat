@echo off
setlocal EnableExtensions
title NFSU Library Chatbot - Full Demo
cd /d "%~dp0"

echo ============================================
echo  NFSU Library Chatbot - full local demo
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python not found on PATH.
  pause
  exit /b 1
)

if not exist "backend\.venv" (
  echo [1/4] Creating venv...
  python -m venv backend\.venv
)
if exist "backend\.venv\Scripts\activate.bat" (
  call "backend\.venv\Scripts\activate.bat"
)
python -c "import fastapi, uvicorn, httpx, pydantic_settings" 2>nul
if errorlevel 1 (
  echo [2/4] Installing requirements (first run only)...
  python -m pip install -q -r backend\requirements.txt
) else (
  echo [2/4] Dependencies OK.
)

if not exist "backend\.env" (
  copy /Y "backend\.env.example" "backend\.env" >nul
  echo [3/4] Created backend\.env - add LLM_API_TOKEN=hf_... for AI answers
) else (
  echo [3/4] Using existing backend\.env
)

netstat -ano | findstr ":8000.*LISTENING" >nul 2>&1
if not errorlevel 1 (
  echo [4/4] Backend already running
  goto :wait
)

echo [4/4] Starting backend (minimized window)...
start "NFSU-Backend" /min cmd /k "cd /d "%~dp0backend" && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

:wait
echo       Waiting for API health...
set /a _tries=0
:healthloop
set /a _tries+=1
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/v1/health' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } } catch {}; exit 1" >nul 2>&1
if not errorlevel 1 goto :ready
if %_tries% geq 60 (
  echo [ERROR] Backend did not become healthy in 60s.
  echo         Check the minimized NFSU-Backend window for errors.
  pause
  exit /b 1
)
timeout /t 1 /nobreak >nul
goto :healthloop

:ready
echo.
echo ============================================
echo  Ready.
echo  Demo : http://127.0.0.1:8000/demo
echo  API  : http://127.0.0.1:8000/api/v1/health
echo.
echo  Try in the red chat bubble:
echo   - Find books on forensic DNA analysis
echo   - Show books by Pipara
echo   - Library timing and rules
echo   - ISBN 9789364556255
echo.
echo  Close this window or run stop.bat to stop.
echo ============================================
echo.
start "" "http://127.0.0.1:8000/demo"

echo Press any key to stop...
pause >nul
call "%~dp0stop.bat"
