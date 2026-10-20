@echo off
setlocal
cd /d "%~dp0..\.."
set "TRAVEL_FETCH_SOURCE=1"
call npm run build
set "TRAVEL_FETCH_SOURCE="
if errorlevel 1 (
  echo.
  echo 生成失败。请确认网络可用、已安装 Python，并已安装 Pillow 依赖。
  echo 可尝试运行：python -m pip install pillow
  pause
  exit /b 1
)
echo.
echo 来源图片补抓并重新生成完成。
pause
