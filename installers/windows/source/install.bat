@echo off
REM vibesrails - Source installer for Windows
setlocal enabledelayedexpansion

echo === VibesRails source installer ===
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Download from: https://python.org
    exit /b 1
)

REM Check git
git --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: git is not installed or not in PATH
    echo Download from: https://git-scm.com
    exit /b 1
)

set "INSTALL_PATH=%USERPROFILE%\.vibesrails"

REM Clone or update
if exist "%INSTALL_PATH%" (
    echo Updating existing installation at %INSTALL_PATH%...
    cd /d "%INSTALL_PATH%"
    git pull
) else (
    echo Cloning to %INSTALL_PATH%...
    git clone https://github.com/VictoHughes/VIBESRAILS.git "%INSTALL_PATH%"
    if errorlevel 1 (
        echo ERROR: Clone failed
        exit /b 1
    )
)

echo.
echo Installing in development mode...
pip install -e "%INSTALL_PATH%"

if errorlevel 1 (
    echo.
    echo ERROR: Installation failed
    exit /b 1
)

echo.
vibesrails --version 2>nul
if errorlevel 1 (
    echo vibesrails installed (run: python -m vibesrails --version)
)

echo.
echo === Installation complete ===
echo.
echo Next steps:
echo   cd your-project
echo   vibesrails --setup
echo.
pause
