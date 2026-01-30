@echo off
REM VibesRails - Windows Installer (self-contained)
REM Usage: install.bat C:\path\to\project

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "TARGET=%~1"
if "%TARGET%"=="" set "TARGET=%CD%"

echo === VibesRails Installer ===
echo Target: %TARGET%

REM 1. Install vibesrails via pip
echo.
echo [1/4] Installing vibesrails...
pip install vibesrails

REM 2. Copy config files
echo.
echo [2/4] Copying configuration files...

copy /Y "%SCRIPT_DIR%vibesrails.yaml" "%TARGET%\vibesrails.yaml"
echo   -^> vibesrails.yaml

copy /Y "%SCRIPT_DIR%CLAUDE.md" "%TARGET%\CLAUDE.md"
echo   -^> CLAUDE.md

if not exist "%TARGET%\.claude" mkdir "%TARGET%\.claude"
copy /Y "%SCRIPT_DIR%.claude\hooks.json" "%TARGET%\.claude\hooks.json"
echo   -^> .claude\hooks.json

REM 3. Install git pre-commit hook
echo.
echo [3/4] Installing git pre-commit hook...
if exist "%TARGET%\.git" (
    if not exist "%TARGET%\.git\hooks" mkdir "%TARGET%\.git\hooks"
    (
        echo #!/usr/bin/env bash
        echo # vibesrails pre-commit hook
        echo if command -v vibesrails ^&^>/dev/null; then
        echo     vibesrails
        echo     if [ $? -ne 0 ]; then
        echo         echo "vibesrails: issues found. Fix before committing."
        echo         exit 1
        echo     fi
        echo fi
    ) > "%TARGET%\.git\hooks\pre-commit"
    echo   -^> .git\hooks\pre-commit
) else (
    echo   (no .git directory found, skipping hook^)
)

REM 4. Install AI self-protection hook
echo.
echo [4/4] Installing AI self-protection hook...
if not exist "%USERPROFILE%\.claude\hooks" mkdir "%USERPROFILE%\.claude\hooks"
copy /Y "%SCRIPT_DIR%ptuh.py" "%USERPROFILE%\.claude\hooks\ptuh.py"
echo   -^> ~/.claude/hooks/ptuh.py

python3 -c "import json,os;p=os.path.join(os.path.expanduser('~'),'.claude','settings.json');s=json.load(open(p)) if os.path.exists(p) else {};h=s.setdefault('hooks',{});t=h.setdefault('PreToolUse',[]);e={'type':'command','command':'python3 ~/.claude/hooks/ptuh.py'};t.append(e) if not any(x.get('command','')==e['command'] for x in t) else None;open(p,'w').write(json.dumps(s,indent=2))"
echo   -^> ~/.claude/settings.json (hook registered)

echo.
echo === Done! ===
echo Commands:
echo   vibesrails --all    # Scan project
echo   vibesrails --setup  # Reconfigure (interactive)
echo   vibesrails --show   # Show patterns

endlocal
