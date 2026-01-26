@echo off
REM VibesRails - Complete Installation Script (Windows)
REM Install VibesRails + setup your project with templates

setlocal enabledelayedexpansion

echo ================================
echo VibesRails Complete Installer
echo ================================
echo.

REM Check Python version
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ from python.org
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python %PYTHON_VERSION%

REM Get script directory
set "SCRIPT_DIR=%~dp0"
set "WHEEL_FILE=%SCRIPT_DIR%vibesrails-1.3.0-py3-none-any.whl"
set "TEMPLATES_DIR=%SCRIPT_DIR%claude-code"

REM Check wheel exists
if not exist "%WHEEL_FILE%" (
    echo ERROR: vibesrails wheel not found
    exit /b 1
)

REM Get target directory
if "%~1"=="" (
    echo.
    echo Usage: INSTALL.bat C:\path\to\your\project
    echo.
    echo Or run from your project directory:
    echo   cd your-project
    echo   "C:\path\to\INSTALL.bat" .
    echo.
    exit /b 1
)

set "PROJECT_DIR=%~f1"

if not exist "%PROJECT_DIR%" (
    echo ERROR: Directory not found: %1
    exit /b 1
)

echo [OK] Target project: %PROJECT_DIR%
echo.

REM Step 1: Install VibesRails
echo [1/3] Installing VibesRails...
python -m pip install "%WHEEL_FILE%" --force-reinstall --no-deps
python -m pip install pyyaml semgrep

REM Verify
vibesrails --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: vibesrails not found after installation
    echo Try: python -m vibesrails --version
    exit /b 1
)

for /f "tokens=*" %%i in ('vibesrails --version 2^>^&1') do set VIBES_VERSION=%%i
echo [OK] VibesRails installed: %VIBES_VERSION%
echo.

REM Step 2: Copy templates
echo [2/3] Copying configuration files...

REM Check if git repo
if not exist "%PROJECT_DIR%\.git" (
    echo WARNING: Not a git repository. Initializing...
    cd /d "%PROJECT_DIR%"
    git init
)

copy /Y "%TEMPLATES_DIR%\vibesrails.yaml" "%PROJECT_DIR%\" >nul
echo   [OK] vibesrails.yaml

copy /Y "%TEMPLATES_DIR%\CLAUDE.md" "%PROJECT_DIR%\" >nul
echo   [OK] CLAUDE.md

if not exist "%PROJECT_DIR%\.claude" mkdir "%PROJECT_DIR%\.claude"
copy /Y "%TEMPLATES_DIR%\.claude\hooks.json" "%PROJECT_DIR%\.claude\" >nul
echo   [OK] .claude\hooks.json

echo.

REM Step 3: Install git hook
echo [3/3] Installing git pre-commit hook...
cd /d "%PROJECT_DIR%"
vibesrails --hook

echo.
echo ================================
echo Installation Complete! 🚀
echo ================================
echo.

echo Files installed:
echo   • vibesrails.yaml - Security patterns
echo   • CLAUDE.md - Claude Code instructions
echo   • .claude\hooks.json - Automation hooks
echo   • .git\hooks\pre-commit - Git hook
echo.

echo Test the installation:
echo   cd %PROJECT_DIR%
echo   vibesrails --all
echo.

echo Try these commands:
echo   vibesrails --show       # Show configured patterns
echo   vibesrails --watch      # Live scanning mode
echo   vibesrails --learn      # AI pattern discovery
echo   vibesrails --stats      # View scan statistics
echo.

echo Happy safe coding! 🛤️
pause
