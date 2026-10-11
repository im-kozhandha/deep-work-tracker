@echo off
setlocal
cd /d "%~dp0"

rem Usage: setupdev.bat [--seed]   (--seed also loads seed_data.sql into deepwork.db)
set "VENV_PYTHON=env\Scripts\python.exe"

echo [1/5] Checking prerequisites...
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python was not found on PATH. Install Python 3.10 or newer.
    goto :fail
)
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
    echo ERROR: Python 3.10 or newer is required.
    goto :fail
)
where node >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js was not found on PATH. Install Node.js 18 or newer.
    goto :fail
)
where npm >nul 2>&1
if errorlevel 1 (
    echo ERROR: npm was not found on PATH.
    goto :fail
)
where java >nul 2>&1
if errorlevel 1 echo WARNING: Java was not found. It is only needed by generate_sdk.bat, not by the app.

echo [2/5] Setting up backend virtual environment...
if not exist "%VENV_PYTHON%" (
    python -m venv env
    if errorlevel 1 (
        echo ERROR: Could not create the virtual environment.
        goto :fail
    )
) else (
    echo Reusing existing virtual environment in env\
)

echo [3/5] Installing backend dependencies...
"%VENV_PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: pip install failed.
    goto :fail
)

echo [4/5] Applying database migrations...
"%VENV_PYTHON%" -m alembic upgrade head
if errorlevel 1 (
    echo ERROR: alembic upgrade head failed.
    goto :fail
)
if /i "%~1"=="--seed" (
    echo Loading seed_data.sql...
    "%VENV_PYTHON%" -c "import sqlite3; c=sqlite3.connect('deepwork.db'); c.executescript(open('seed_data.sql', encoding='utf-8').read()); c.close()"
    if errorlevel 1 (
        echo ERROR: Loading seed data failed.
        goto :fail
    )
)

echo [5/5] Installing frontend dependencies...
pushd frontend
call npm install
if errorlevel 1 (
    popd
    echo ERROR: npm install failed.
    goto :fail
)
popd

echo.
echo Setup complete. Start the application with runapplication.bat
set "EXIT_CODE=0"
goto :finish

:fail
echo.
echo Setup FAILED. Fix the error above and run setupdev.bat again.
set "EXIT_CODE=1"

:finish
echo %cmdcmdline% | find /i "/c" >nul && pause
exit /b %EXIT_CODE%