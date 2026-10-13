@echo off
setlocal EnableExtensions
title NFSU Library Chatbot - Backend
cd /d "%~dp0backend"

echo ============================================
echo  NFSU Library Chatbot - start backend
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python not found on PATH. Install Python 3.10+ and retry.
  pause
  exit /b 1
)
python --version
echo.

if not exist ".venv" (
  echo [1/3] Creating virtual environment in backend\.venv ...
  python -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Could not create venv.
    pause
    exit /b 1
  )
)
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
  echo [ERROR] Could not activate backend\.venv
  pause
  exit /b 1
)

echo [2/3] Checking dependencies...
python -c "import fastapi, uvicorn, httpx, pydantic_settings" 2>nul
if errorlevel 1 (
  echo       Installing backend\requirements.txt ...
  python -m pip install -q -r requirements.txt
  if errorlevel 1 (
    echo [ERROR] pip install failed. Check network and retry.
    pause
    exit /b 1
  )
)
echo       Dependencies OK.
echo.

if not exist ".env" (
  echo [3/3] Creating backend\.env from example...
  if exist ".env.example" (
    copy /Y ".env.example" ".env" >nul
    echo       Add LLM_API_TOKEN=hf_... in backend\.env for AI answers
  ) else (
    echo       [WARN] .env.example not found
  )
) else (
  echo [3/3] Using existing backend\.env
)
echo.

echo ============================================
echo  Starting API on http://127.0.0.1:8000
echo  Demo  : http://127.0.0.1:8000/demo
echo  Health: http://127.0.0.1:8000/api/v1/health
echo  Stop  : close this window or run stop.bat
echo ============================================
echo.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
