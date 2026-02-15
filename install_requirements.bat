@echo off
chcp 65001 >nul
echo 正在安装依赖包...
echo.
pip install -r requirements.txt
echo.
echo 依赖安装完成！
pause
