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
  echo [1/4] Creating backend\.venv ...
  python -m venv backend\.venv
  if errorlevel 1 (
    echo [ERROR] Could not create venv.
    pause
    exit /b 1
  )
)
call "backend\.venv\Scripts\activate.bat"
if errorlevel 1 (
  echo [ERROR] Could not activate backend\.venv
  pause
  exit /b 1
)

echo [2/4] Checking dependencies...
python -c "import fastapi, uvicorn, httpx, pydantic_settings" 2>nul
if errorlevel 1 (
  echo       Installing backend\requirements.txt ...
  python -m pip install -q -r backend\requirements.txt
  if errorlevel 1 (
    echo [ERROR] pip install failed.
    pause
    exit /b 1
  )
) else (
  echo       Dependencies OK.
)

if not exist "backend\.env" (
  if exist "backend\.env.example" (
    copy /Y "backend\.env.example" "backend\.env" >nul
    echo [3/4] Created backend\.env
  ) else (
    echo [3/4] No .env.example found - continuing without .env
  )
) else (
  echo [3/4] Using existing backend\.env
)

netstat -ano | findstr ":8000.*LISTENING" >nul 2>&1
if not errorlevel 1 (
  echo [4/4] Backend already running
  goto :wait
)

echo [4/4] Starting backend...
start "NFSU-Backend" /min cmd /k "cd /d "%~dp0backend" && call ".venv\Scripts\activate.bat" && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

:wait
echo       Waiting for API health (up to 60s)...
set /a _tries=0
:healthloop
set /a _tries+=1
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/v1/health' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } } catch {}; exit 1" >nul 2>&1
if not errorlevel 1 goto :ready
if %_tries% geq 60 (
  echo.
  echo [ERROR] Backend did not become healthy in 60 seconds.
  echo         Open the minimized NFSU-Backend window to see errors.
  echo.
  pause
  exit /b 1
)
timeout /t 1 /nobreak >nul
goto :healthloop

:ready
echo.
echo ============================================
echo  READY
echo.
echo  Demo: http://127.0.0.1:8000/demo
echo.
echo  Try in the red chat bubble:
echo   - Find books on forensic DNA analysis
echo   - Show books by Pipara
echo   - Library timing and rules
echo   - ISBN 9789364556255
echo.
echo  Browser should open automatically.
echo  Close this window or run stop.bat to stop.
echo ============================================
echo.
start "" "http://127.0.0.1:8000/demo"
echo Browser opened (or use the URL above).
echo.
pause
call "%~dp0stop.bat"
