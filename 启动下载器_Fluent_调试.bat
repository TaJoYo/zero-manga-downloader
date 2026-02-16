@echo off
setlocal
cd /d "%~dp0"

echo Starting Zero Manga Downloader (Debug mode)...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python was not found in PATH.
    echo Please install Python and run install_requirements.bat first.
    pause
    exit /b 1
)

python "%~dp0gui_downloader_fluent.py"

echo.
echo Program exited with code %errorlevel%.
echo Press any key to close this window.
pause >nul
