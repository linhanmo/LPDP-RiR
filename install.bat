@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ========================================================
echo        LPDP-RiR Auto Installer (Safe Mode)
echo ========================================================
echo.

:: 1. Get current directory
set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

echo [INFO] Project Path: "%PROJECT_DIR%"
echo.
echo [CHECK] 1. Path check passed.
echo.
echo Press any key to check for Conda...
pause

:: 2. Check Conda
echo.
echo [INFO] Checking for Conda...
where conda >nul 2>nul
if %errorlevel% neq 0 goto :CondaNotFound

echo [INFO] Conda found!
echo [INFO] Checking version...
call conda --version
echo.
echo Press any key to start installation...
pause
goto :CreateEnv

:CondaNotFound
echo.
echo ========================================================
echo [CRITICAL ERROR] Conda is NOT found in your PATH!
echo ========================================================
echo.
echo Windows cannot find the 'conda' command.
echo.
echo Solution:
echo    Please open "Anaconda Prompt" from Start Menu,
echo    then drag this file into it and run.
echo.
echo Press any key to exit...
pause
exit /b 1

:CreateEnv
:: 3. Create Conda Environment
set "ENV_DIR=%PROJECT_DIR%\env"
echo.
echo [INFO] Target Environment: "%ENV_DIR%"

if exist "%ENV_DIR%\python.exe" goto :EnvExists

echo [INFO] Creating environment (Python 3.11)...
echo        Please wait...
    
call conda create --prefix "%ENV_DIR%" python=3.11 -y
if %errorlevel% neq 0 goto :CreateFailed

echo [INFO] Environment created.
goto :InstallDeps

:EnvExists
echo [INFO] Environment exists. Skipping creation.
goto :InstallDeps

:CreateFailed
echo.
echo [ERROR] Failed to create environment.
echo Press any key to exit...
pause
exit /b 1

:InstallDeps
:: 4. Install Dependencies
echo.
echo [INFO] Installing dependencies...

:: 4.1 Install Mayavi
echo [INFO] Installing Mayavi...
call conda install --prefix "%ENV_DIR%" -c conda-forge mayavi -y

:: 4.2 Install pip requirements
if not exist "%PROJECT_DIR%\requirements.txt" goto :Finish

echo [INFO] Installing pip dependencies...
"%ENV_DIR%\python.exe" -m pip install --upgrade pip -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
if %errorlevel% neq 0 goto :PipFailed

"%ENV_DIR%\python.exe" -m pip install -r "%PROJECT_DIR%\requirements.txt" -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
if %errorlevel% neq 0 goto :PipFailed

goto :Finish

:PipFailed
echo.
echo [ERROR] Pip installation failed.
echo Press any key to exit...
pause
exit /b 1

:Finish
echo.
echo ========================================================
echo        Installation Complete!
echo ========================================================
echo.
pause
