@echo off
setlocal
cd /d "%~dp0..\.."
call npm run build
if errorlevel 1 (
  echo.
  echo 生成失败。请确认已安装 Node.js、Python，并运行 npm ci 及 python -m pip install -r tools\requirements-build.txt。
  pause
  exit /b 1
)
echo.
echo 网页已重新生成。
pause
