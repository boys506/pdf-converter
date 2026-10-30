@echo off
chcp 65001 >nul
cd /d "%~dp0"
set TMPDIR=%~dp0.tmp
set TEMP=%~dp0.tmp
set TMP=%~dp0.tmp
if not exist ".tmp" mkdir ".tmp"

rem 使用 onedir（文件夹版）：启动不需要解压到系统临时目录，兼容性更好
".venv\Scripts\pyinstaller.exe" --noconfirm --clean --onedir --windowed ^
  --name "PDF转换工坊" --icon icon.ico --paths src ^
  --workpath build --distpath dist src\main.py

echo.
echo 打包完成：dist\PDF转换工坊\PDF转换工坊.exe
pause
