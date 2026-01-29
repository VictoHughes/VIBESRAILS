@echo off
REM VibesRails v2.0 - Complete Installation Script (Windows)
REM Install VibesRails v2.0 + setup your project with templates

setlocal enabledelayedexpansion

echo ================================================
echo   VibesRails v2.0 Complete Installer
echo   15 guards + Senior Mode + AI integration
echo ================================================
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
set "WHEEL_FILE=%SCRIPT_DIR%vibesrails-2.0.0-py3-none-any.whl"
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

REM Step 1: Install VibesRails v2
echo [1/3] Installing VibesRails v2.0...
python -m pip install "%WHEEL_FILE%[all]" --force-reinstall
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

if exist "%TEMPLATES_DIR%" (
    copy /Y "%TEMPLATES_DIR%\vibesrails.yaml" "%PROJECT_DIR%\" >nul 2>&1
    if not errorlevel 1 echo   [OK] vibesrails.yaml

    copy /Y "%TEMPLATES_DIR%\CLAUDE.md" "%PROJECT_DIR%\" >nul 2>&1
    if not errorlevel 1 echo   [OK] CLAUDE.md

    if not exist "%PROJECT_DIR%\.claude" mkdir "%PROJECT_DIR%\.claude"
    copy /Y "%TEMPLATES_DIR%\.claude\hooks.json" "%PROJECT_DIR%\.claude\" >nul 2>&1
    if not errorlevel 1 echo   [OK] .claude\hooks.json
) else (
    echo Templates not found, running vibesrails --setup...
    cd /d "%PROJECT_DIR%"
    vibesrails --setup --force 2>nul
)

echo.

REM Step 3: Install git hook
echo [3/3] Installing git pre-commit hook...
cd /d "%PROJECT_DIR%"
vibesrails --hook 2>nul

echo.
echo ================================================
echo   Installation Complete!
echo ================================================
echo.

echo Files installed:
if exist "%PROJECT_DIR%\vibesrails.yaml" echo   - vibesrails.yaml
if exist "%PROJECT_DIR%\CLAUDE.md" echo   - CLAUDE.md
if exist "%PROJECT_DIR%\.claude\hooks.json" echo   - .claude\hooks.json
if exist "%PROJECT_DIR%\.git\hooks\pre-commit" echo   - .git\hooks\pre-commit
echo.

echo v2.0 Features:
echo   - 15 security ^& quality guards
echo   - Senior Mode with architecture mapping
echo   - AI coding safety (hallucination, bypass, lazy code)
echo   - Performance, complexity ^& dependency audits
echo   - Type safety ^& API design guards
echo   - Community pattern packs
echo.

echo CLI Commands:
echo   vibesrails --all          Scan entire project
echo   vibesrails --senior       Run Senior Mode analysis
echo   vibesrails --show         Show configured patterns
echo   vibesrails --watch        Live scanning mode
echo   vibesrails --learn        AI pattern discovery
echo   vibesrails --fix          Auto-fix issues
echo   vibesrails --audit        Dependency audit
echo   vibesrails --upgrade      Upgrade advisor
echo   vibesrails --stats        View scan statistics
echo.

echo Happy safe coding!
pause
