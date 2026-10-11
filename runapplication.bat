@echo off
setlocal
cd /d "%~dp0"

set "VENV_PYTHON=env\Scripts\python.exe"
set "BACKEND_HOST=127.0.0.1"
set "BACKEND_PORT=8000"
set "BACKEND_URL=http://%BACKEND_HOST%:%BACKEND_PORT%"
set "FRONTEND_URL=http://localhost:5173"
set "HEALTH_RETRIES=30"
set /a ATTEMPT=0

if not exist "%VENV_PYTHON%" (
    echo ERROR: Virtual environment not found. Run setupdev.bat first.
    goto :fail
)
if not exist "frontend\node_modules" (
    echo ERROR: Frontend dependencies not found. Run setupdev.bat first.
    goto :fail
)

echo Applying database migrations...
"%VENV_PYTHON%" -m alembic upgrade head
if errorlevel 1 (
    echo ERROR: alembic upgrade head failed.
    goto :fail
)

echo Starting backend on %BACKEND_URL% in a new window...
start "Deep Work Backend" cmd /k env\Scripts\python.exe -m uvicorn backend.main:app --host %BACKEND_HOST% --port %BACKEND_PORT%

echo Starting frontend on %FRONTEND_URL% in a new window...
start "Deep Work Frontend" /D frontend cmd /k npm start

echo Waiting for the backend to answer...
:wait_backend
curl -s -f -o NUL "%BACKEND_URL%/openapi.json"
if not errorlevel 1 goto :ready
set /a ATTEMPT+=1
if %ATTEMPT% GEQ %HEALTH_RETRIES% (
    echo WARNING: The backend did not answer in time. Check the "Deep Work Backend" window.
    goto :finish_ok
)
ping -n 2 127.0.0.1 >nul
goto :wait_backend

:ready
echo Backend is up. API docs: %BACKEND_URL%/docs
ping -n 4 127.0.0.1 >nul
start "" "%FRONTEND_URL%"

:finish_ok
echo.
echo Both services are running in their own windows. Close those windows (or press Ctrl+C in them) to stop.
set "EXIT_CODE=0"
goto :finish

:fail
echo.
echo Could not start the application.
set "EXIT_CODE=1"

:finish
echo %cmdcmdline% | find /i "/c" >nul && pause
exit /b %EXIT_CODE%