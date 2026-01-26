@echo off
REM vibesrails - pip installer for Windows
echo === VibesRails pip installer ===
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Download from: https://python.org
    exit /b 1
)

echo Installing vibesrails...
pip install vibesrails

if errorlevel 1 (
    echo.
    echo ERROR: Installation failed
    echo Try: pip install --user vibesrails
    exit /b 1
)

echo.
echo === Installation complete ===
echo.
echo Next steps:
echo   cd your-project
echo   vibesrails --setup
echo.
pause
