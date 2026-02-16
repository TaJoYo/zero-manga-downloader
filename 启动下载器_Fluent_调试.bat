@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo 启动零漫画下载器（调试模式）...
python gui_downloader_fluent.py
echo.
echo 程序已退出，按任意键关闭窗口。
pause >nul
