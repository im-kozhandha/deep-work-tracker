@echo off
setlocal
cd /d "%~dp0"

rem Requires the backend to be running (runapplication.bat). Override the address with DEEPWORK_API_URL.
if "%DEEPWORK_API_URL%"=="" set "DEEPWORK_API_URL=http://localhost:8000"
set "VENV_PYTHON=env\Scripts\python.exe"
set "SDK_DIR=deepwork_sdk"

if not exist "%VENV_PYTHON%" (
    echo ERROR: Virtual environment not found. Run setupdev.bat first.
    goto :fail
)
where java >nul 2>&1
if errorlevel 1 (
    echo ERROR: Java 11 or newer is required by OpenAPI Generator. Install a JRE and retry.
    goto :fail
)

where openapi-generator-cli >nul 2>&1
if errorlevel 1 (
    echo Installing OpenAPI Generator CLI globally...
    call npm install -g @openapitools/openapi-generator-cli
    if errorlevel 1 (
        echo ERROR: Could not install @openapitools/openapi-generator-cli.
        goto :fail
    )
)

echo Checking %DEEPWORK_API_URL%/openapi.json ...
curl -s -f -o NUL "%DEEPWORK_API_URL%/openapi.json"
if errorlevel 1 (
    echo ERROR: The backend is not reachable. Start it with runapplication.bat first.
    goto :fail
)

if exist "%SDK_DIR%" rmdir /s /q "%SDK_DIR%"

echo Generating the Python SDK into %SDK_DIR%\ ...
call openapi-generator-cli generate -i "%DEEPWORK_API_URL%/openapi.json" -g python -o "%SDK_DIR%" "--additional-properties=packageName=deepwork_sdk,projectName=deepwork-sdk"
if errorlevel 1 (
    echo ERROR: SDK generation failed.
    goto :fail
)

echo Installing the SDK into the virtual environment...
"%VENV_PYTHON%" -m pip install -e "%SDK_DIR%"
if errorlevel 1 (
    echo ERROR: Installing the generated SDK failed.
    goto :fail
)

echo Running the SDK smoke test...
"%VENV_PYTHON%" sdk_smoke_test.py
if errorlevel 1 (
    echo ERROR: The SDK smoke test failed.
    goto :fail
)

echo.
echo SDK generated, installed and verified.
set "EXIT_CODE=0"
goto :finish

:fail
echo.
echo SDK step FAILED.
set "EXIT_CODE=1"

:finish
echo %cmdcmdline% | find /i "/c" >nul && pause
exit /b %EXIT_CODE%