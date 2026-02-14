@echo off
echo 安装依赖...
pip install -r requirements.txt

echo.
echo 启动零漫画下载器（Fluent UI版）...
python gui_downloader_fluent.py

pause
