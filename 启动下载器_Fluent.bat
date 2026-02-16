@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE="
where python >nul 2>nul
if %errorlevel%==0 (
    for /f "delims=" %%P in ('where python') do (
        set "PYTHON_EXE=%%P"
        goto :found_python
    )
)

goto :try_pyw

:found_python
set "PYTHONW_EXE=%PYTHON_EXE:python.exe=pythonw.exe%"
if exist "%PYTHONW_EXE%" (
    start "" "%PYTHONW_EXE%" "%~dp0gui_downloader_fluent.py"
    exit /b 0
)

:try_pyw
where pyw >nul 2>nul
if %errorlevel%==0 (
    start "" pyw -3 "%~dp0gui_downloader_fluent.py"
    exit /b 0
)

echo Could not find pythonw or pyw.
echo Please install Python and run install_requirements.bat first.
pause
