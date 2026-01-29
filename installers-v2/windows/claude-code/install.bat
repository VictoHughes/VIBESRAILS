@echo off
REM VibesRails v2.0 - Claude Code integration installer for Windows
setlocal enabledelayedexpansion

echo ================================================
echo   VibesRails v2.0 + Claude Code Installer
echo   15 guards + Senior Mode + AI integration
echo ================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Download Python 3.10+ from: https://python.org
    exit /b 1
)

REM Get project path from args or use current directory
if "%~1"=="" (
    set "PROJECT_PATH=%CD%"
) else (
    set "PROJECT_PATH=%~1"
)

if not exist "%PROJECT_PATH%" (
    echo ERROR: Path does not exist: %PROJECT_PATH%
    exit /b 1
)

REM Step 1: Install vibesrails v2 if not present
vibesrails --version >nul 2>&1
if errorlevel 1 (
    echo [1/4] Installing vibesrails v2.0...
    pip install "vibesrails[all]>=2.0.0"
    if errorlevel 1 (
        echo ERROR: vibesrails installation failed
        exit /b 1
    )
) else (
    echo [1/4] vibesrails already installed
)

echo.
vibesrails --version
echo.

REM Step 2: Change to project directory
cd /d "%PROJECT_PATH%"
echo [2/4] Setting up project: %PROJECT_PATH%
echo.

REM Check if git repo
if not exist ".git" (
    echo WARNING: Not a git repository. Initializing...
    git init
)

REM Step 3: Run smart setup
echo [3/4] Running vibesrails --setup...
vibesrails --setup --force

echo.

REM Step 4: Install git hook
echo [4/4] Installing git pre-commit hook...
vibesrails --hook 2>nul
echo.

echo ================================================
echo   Installation complete!
echo ================================================
echo.
echo Files created:
if exist "vibesrails.yaml" echo   vibesrails.yaml
if exist "CLAUDE.md" echo   CLAUDE.md
if exist ".claude\hooks.json" echo   .claude\hooks.json
if exist ".git\hooks\pre-commit" echo   .git\hooks\pre-commit

echo.
echo v2.0 Features available:
echo   - 15 security ^& quality guards
echo   - Senior Mode with architecture mapping
echo   - AI coding safety (hallucination, bypass, lazy code detection)
echo   - Performance, complexity ^& dependency audits
echo   - Community pattern packs
echo.
echo Claude Code will now:
echo   - Scan code on every commit
echo   - Run Senior Mode during AI sessions
echo   - Show active plan on session start
echo   - Auto-save state before compaction
echo.
echo CLI Commands:
echo   vibesrails --all          Full project scan
echo   vibesrails --senior       Senior Mode analysis
echo   vibesrails --audit        Dependency audit
echo   vibesrails --upgrade      Upgrade advisor
echo.
pause
