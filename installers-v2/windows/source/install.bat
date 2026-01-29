@echo off
REM VibesRails v2.0 - Source installer for Windows
setlocal enabledelayedexpansion

echo ================================================
echo   VibesRails v2.0 Installer (source)
echo   YAML-driven security + code quality scanner
echo ================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Download Python 3.10+ from: https://python.org
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
    git checkout v2.0 2>nul || git checkout main
) else (
    echo Cloning to %INSTALL_PATH%...
    git clone https://github.com/VictoHughes/VIBESRAILS.git "%INSTALL_PATH%"
    if errorlevel 1 (
        echo ERROR: Clone failed
        exit /b 1
    )
    cd /d "%INSTALL_PATH%"
    git checkout v2.0 2>nul || git checkout main
)

echo.
echo Installing vibesrails v2.0 from source with all extras...
pip install -e ".[all]"

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
echo ================================================
echo   Installation complete!
echo ================================================
echo.
echo v2.0 Features:
echo   - 15 security ^& quality guards
echo   - Senior Mode (AI coding safety)
echo   - Architecture mapping
echo   - Community pattern packs
echo.
echo Next steps:
echo   cd your-project
echo   vibesrails --setup
echo.
pause
