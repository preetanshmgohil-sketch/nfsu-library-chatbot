@echo off
setlocal EnableExtensions
title NFSU Library Chatbot - Backend
cd /d "%~dp0"

echo ============================================
echo  NFSU Library Chatbot - start backend
echo ============================================
echo.

REM --- Python check ---
where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python not found on PATH. Install Python 3.10+ and retry.
  pause
  exit /b 1
)
python --version
echo.

REM --- Dependencies ---
if not exist ".venv" (
  echo [1/3] Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Could not create venv.
    pause
    exit /b 1
  )
)
call ".venv\Scripts\activate.bat" 2>nul
if errorlevel 1 (
  echo [WARN] venv activate failed, using system Python.
)

echo [2/3] Checking dependencies...
python -c "import fastapi, uvicorn, httpx, pydantic_settings" 2>nul
if errorlevel 1 (
  echo       Installing requirements...
  python -m pip install -q -r requirements.txt
  if errorlevel 1 (
    echo [ERROR] pip install failed. Check network and retry.
    pause
    exit /b 1
  )
)
echo       Dependencies OK.
echo.

REM --- Local .env (create from example if missing) ---
if not exist ".env" (
  echo [3/3] Creating .env from example...
  copy /Y ".env.example" ".env" >nul
  echo       Edit backend\.env to add your Hugging Face token (LLM_API_TOKEN=hf_...)
) else (
  echo [3/3] Using existing backend\.env
)
echo.

echo ============================================
echo  Starting API on http://127.0.0.1:8000
echo  Health : http://127.0.0.1:8000/api/v1/health
echo  Config : http://127.0.0.1:8000/api/v1/config
echo  Stop   : close this window or run stop.bat
echo ============================================
echo.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
