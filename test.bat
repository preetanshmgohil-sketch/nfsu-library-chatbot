@echo off
setlocal EnableExtensions
title NFSU Library Chatbot - Tests
cd /d "%~dp0backend"

echo ============================================
echo  NFSU Library Chatbot - test suite
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python not found.
  pause
  exit /b 1
)

if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"

python -c "import fastapi, uvicorn, httpx, pydantic_settings" 2>nul
if errorlevel 1 (
  echo Installing requirements for tests...
  python -m pip install -q -r requirements.txt
)

echo [1/3] Query parser unit tests
python tests\test_query_parser.py
if errorlevel 1 goto :fail

echo.
echo [2/3] Security guardrail unit tests
python tests\test_guardrails.py
if errorlevel 1 goto :fail

echo.
echo [3/3] Live integration smoke (needs server on :8000)
curl -s -o nul -w "  health -> %%{http_code}\n" http://127.0.0.1:8000/api/v1/health 2>nul
if errorlevel 1 (
  echo   Server not running on :8000 - start it with start.bat, then re-run test.bat
  echo   (unit tests above already passed)
  goto :done
)
python tests\smoke_matrix.py
if errorlevel 1 goto :fail

:done
echo.
echo ============================================
echo  ALL TESTS PASSED
echo ============================================
pause
exit /b 0

:fail
echo.
echo ============================================
echo  TESTS FAILED - see output above
echo ============================================
pause
exit /b 1
