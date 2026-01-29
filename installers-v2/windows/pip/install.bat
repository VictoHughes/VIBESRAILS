@echo off
REM VibesRails v2.0 - pip installer for Windows
echo ================================================
echo   VibesRails v2.0 Installer (pip)
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

echo Installing vibesrails v2.0 with all extras...
pip install "vibesrails[all]>=2.0.0"

if errorlevel 1 (
    echo.
    echo ERROR: Installation failed
    echo Try: pip install --user "vibesrails[all]>=2.0.0"
    exit /b 1
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
echo   - Performance, complexity ^& dependency audits
echo   - Type safety ^& API design guards
echo   - Community pattern packs
echo.
echo CLI Commands:
echo   vibesrails --all          Scan entire project
echo   vibesrails --setup        Setup new project
echo   vibesrails --senior       Run Senior Mode analysis
echo   vibesrails --show         Show configured patterns
echo   vibesrails --watch        Live scanning mode
echo   vibesrails --learn        AI pattern discovery
echo   vibesrails --fix          Auto-fix issues
echo   vibesrails --audit        Dependency audit
echo   vibesrails --upgrade      Upgrade advisor
echo.
echo Next steps:
echo   cd your-project
echo   vibesrails --setup
echo.
pause
