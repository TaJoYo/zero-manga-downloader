@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

where pyw >nul 2>nul
if %errorlevel%==0 (
    start "" pyw -3 gui_downloader_fluent.py
    exit /b 0
)

where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw gui_downloader_fluent.py
    exit /b 0
)

echo 未找到 pyw/pythonw，无法无控制台启动。
echo 请确认已安装 Python，并先运行 install_requirements.bat。
pause
