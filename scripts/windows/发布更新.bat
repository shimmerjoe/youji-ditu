@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0..\.."
echo 本脚本只推送已审查并提交的 main，不自动暂存或提交。
git diff --quiet
if errorlevel 1 goto dirty
git diff --cached --quiet
if errorlevel 1 goto dirty
git push origin main
if errorlevel 1 (
  echo 推送失败，请查看上方错误。
  pause
  exit /b 1
)
echo 已推送。网站上线状态需检查 GitHub Actions 和 Pages 配置。
pause
exit /b 0
:dirty
echo 请先运行 npm run check，审查差异并选择性提交，再运行本脚本。
pause
exit /b 1
