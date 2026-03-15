@echo off
setlocal
cd /d "%~dp0"

:: ========================================================
::    LPDP-RiR Portable Launcher
:: ========================================================

:: 1. Get Project Path
set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

:: 2. Define Environment Paths
set "ENV_DIR=%PROJECT_DIR%\env"
set "ENV_PYTHON=%ENV_DIR%\python.exe"
set "MAIN_SCRIPT=%PROJECT_DIR%\application\main.py"

:: 3. Check if Environment Exists
if not exist "%ENV_PYTHON%" (
    echo.
    echo [ERROR] Virtual environment not found!
    echo.
    echo If this is the source computer:
    echo    Run 'install.bat' first to create the environment.
    echo.
    echo If this is a target computer (copied version):
    echo    Please ensure you copied the 'env' folder along with the project.
    echo.
    echo Press any key to exit...
    pause
    exit /b 1
)

:: 4. Simulate Conda Activation (Critical for Portability)
::    This allows the app to find DLLs (torch, mayavi, etc.) 
::    even if Conda is not installed on this machine.
set "PATH=%ENV_DIR%;%ENV_DIR%\Library\bin;%ENV_DIR%\Scripts;%ENV_DIR%\Library\usr\bin;%ENV_DIR%\Library\mingw-w64\bin;%PATH%"

:: 5. Set PYTHONPATH to project root
set "PYTHONPATH=%PROJECT_DIR%"

:: 6. Run Application
echo.
echo ========================================================
echo        Starting LPDP-RiR System...
echo ========================================================
echo.
echo [INFO] Project: "%PROJECT_DIR%"
echo [INFO] Python:  Portable Mode
echo.

"%ENV_PYTHON%" "%MAIN_SCRIPT%"

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application crashed or closed with error.
    pause
)
