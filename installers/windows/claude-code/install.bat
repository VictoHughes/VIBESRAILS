@echo off
REM vibesrails - Claude Code integration installer for Windows
setlocal enabledelayedexpansion

echo === vibesrails + Claude Code installer ===
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Download from: https://python.org
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

REM Step 1: Install vibesrails if not present
vibesrails --version >nul 2>&1
if errorlevel 1 (
    echo Installing vibesrails...
    pip install vibesrails
    if errorlevel 1 (
        echo ERROR: vibesrails installation failed
        exit /b 1
    )
) else (
    echo vibesrails already installed
)

echo.
vibesrails --version
echo.

REM Step 2: Change to project directory
cd /d "%PROJECT_PATH%"
echo Setting up project: %PROJECT_PATH%
echo.

REM Check if git repo
if not exist ".git" (
    echo WARNING: Not a git repository. Initializing...
    git init
)

REM Step 3: Run smart setup
echo Running vibesrails --setup...
vibesrails --setup --force

echo.
echo === Installation complete ===
echo.
echo Files created:
if exist "vibesrails.yaml" echo   vibesrails.yaml
if exist "CLAUDE.md" echo   CLAUDE.md
if exist ".claude\hooks.json" echo   .claude\hooks.json
if exist ".git\hooks\pre-commit" echo   .git\hooks\pre-commit

echo.
echo Claude Code will now:
echo   - Scan code on every commit
echo   - Show active plan on session start
echo   - Auto-save state before compaction
echo.
echo Try: vibesrails --all
echo.
pause
