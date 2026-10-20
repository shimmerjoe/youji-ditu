@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0..\.."
echo 正在启动游记地图，关闭此窗口即可停止预览。
start "" "http://localhost:8765/"
python -X utf8 -m http.server 8765 --bind 127.0.0.1 --directory site
pause
