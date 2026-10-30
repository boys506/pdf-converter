@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    echo 未找到 .venv 虚拟环境，正在创建...
    python -m venv .venv
    .venv\Scripts\python.exe -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
)
start "" ".venv\Scripts\pythonw.exe" "src\main.py"
