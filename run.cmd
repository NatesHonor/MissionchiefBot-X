@echo off
setlocal
set "PROJECT_ROOT=%~dp0"
set "PYTHON_EXE=%PROJECT_ROOT%.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo MissionChief Bot setup is missing.
    echo Follow the setup instructions in README.md first.
    exit /b 1
)

pushd "%PROJECT_ROOT%"
"%PYTHON_EXE%" "%PROJECT_ROOT%Main.py" %*
set "EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %EXIT_CODE%
