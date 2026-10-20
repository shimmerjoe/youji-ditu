@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0..\.."
echo ============================================================
echo  旅游攻略 - 手机访问 / PWA 安装
echo ------------------------------------------------------------
echo  1) 确保手机和电脑连同一个 WiFi
echo  2) 在电脑命令行运行: ipconfig  查看本机 IPv4 地址
echo  3) 手机浏览器打开:  http://你的电脑IP:8000/index.html
echo  4) 局域网 HTTP 可浏览；完整 PWA 安装与离线缓存需 HTTPS 或本机 localhost
echo ------------------------------------------------------------
echo  本机回环测试: http://127.0.0.1:8000/index.html
echo  关闭本窗口即停止服务。
echo ============================================================
python -X utf8 -m http.server 8000 --bind 0.0.0.0 --directory site
pause
