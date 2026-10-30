@echo off
chcp 936 >nul
cd /d "%~dp0"
setlocal

rem ============================================================
rem  PDF 转换工坊 - 推送到 GitHub
rem  用法: push_github.bat <GitHub用户名> [仓库名] [提交名字] [提交邮箱]
rem  例:   push_github.bat zhangsan pdf-converter "张三" zhangsan@example.com
rem  前提: 已先在 https://github.com/new 建好空仓库（不要勾选 README）
rem  说明: 脚本会自动查找 git，不需要把 git 加到系统 PATH
rem ============================================================

if "%~1"=="" goto USAGE

set "GHUSER=%~1"
set "REPO=%~2"
if "%REPO%"=="" set "REPO=pdf-converter"

rem ---------- 查找 git ----------
set "GIT="
for /f "delims=" %%i in ('where git 2^>nul') do if not defined GIT set "GIT=%%i"
if defined GIT goto GOTGIT

if exist "%ProgramFiles%\Git\cmd\git.exe" set "GIT=%ProgramFiles%\Git\cmd\git.exe"
if defined GIT goto GOTGIT
if exist "%ProgramFiles(x86)%\Git\cmd\git.exe" set "GIT=%ProgramFiles(x86)%\Git\cmd\git.exe"
if defined GIT goto GOTGIT
if exist "%LOCALAPPDATA%\Programs\Git\cmd\git.exe" set "GIT=%LOCALAPPDATA%\Programs\Git\cmd\git.exe"
if defined GIT goto GOTGIT

for /d %%d in ("%USERPROFILE%\.workbuddy-ai\binaries\PortableGit\versions\*") do if not defined GIT if exist "%%d\cmd\git.exe" set "GIT=%%d\cmd\git.exe"
if defined GIT goto GOTGIT

if exist "D:\workbuddy\WorkBuddyAI\resources\vendor\PortableGit\cmd\git.exe" set "GIT=D:\workbuddy\WorkBuddyAI\resources\vendor\PortableGit\cmd\git.exe"
if defined GIT goto GOTGIT

for /d %%d in ("%USERPROFILE%\.workbuddy-ai\binaries\PortableGit\versions\*") do if not defined GIT if exist "%%d\mingw64\bin\git.exe" set "GIT=%%d\mingw64\bin\git.exe"
if defined GIT goto GOTGIT
goto NOGIT

:GOTGIT
echo.
echo git: %GIT%

if exist ".git" goto HASGIT
"%GIT%" init -b main
:HASGIT

if not "%~3"=="" "%GIT%" config --local user.name "%~3"
if not "%~4"=="" "%GIT%" config --local user.email "%~4"

set "GN="
set "GE="
"%GIT%" config user.name > .gitname.tmp 2>nul
set /p GN=<.gitname.tmp
"%GIT%" config user.email > .gitmail.tmp 2>nul
set /p GE=<.gitmail.tmp
del .gitname.tmp .gitmail.tmp >nul 2>nul

if not defined GN goto NOIDENT
if not defined GE goto NOIDENT

echo 目标仓库: https://github.com/%GHUSER%/%REPO%
echo 提交作者: %GN% ^<%GE%^>
echo.

"%GIT%" add -A
"%GIT%" diff --cached --quiet
if not errorlevel 1 goto NOCHANGE
"%GIT%" commit -m "feat: PDF converter - batch convert images / office / text to PDF"
if errorlevel 1 goto COMMITFAIL
goto AFTERCOMMIT
:NOCHANGE
echo 没有新的改动需要提交。
:AFTERCOMMIT

"%GIT%" remote remove origin >nul 2>nul
"%GIT%" remote add origin https://github.com/%GHUSER%/%REPO%.git
"%GIT%" branch -M main

echo.
echo 正在推送。若提示登录：用户名填 GitHub 用户名，密码填 Personal Access Token。
echo.
"%GIT%" push -u origin main
if errorlevel 1 goto PUSHFAIL

echo.
echo [成功] 打开 https://github.com/%GHUSER%/%REPO% 查看
echo.
pause
exit /b 0

:PUSHFAIL
echo.
echo [失败] 检查：仓库是否已创建、用户名与仓库名是否写错、Token 是否有 repo 权限。
echo.
pause
exit /b 1

:COMMITFAIL
echo.
echo [失败] 提交没有成功，请检查上面的 git 报错。
echo.
pause
exit /b 1

:NOGIT
echo.
echo [找不到 git] 这台机器上没有安装 Git，也没有找到可用的便携版。
echo.
echo 请安装 Git for Windows: https://git-scm.com/download/win
echo 安装后重新运行本脚本即可。
echo.
pause
exit /b 1

:NOIDENT
echo.
echo [缺少身份信息] 请补上提交作者，两种方式任选其一：
echo.
echo   方式一（只对当前仓库生效）:
echo     push_github.bat %GHUSER% %REPO% "你的名字" "你的邮箱@example.com"
echo.
echo   方式二（全局设置）:
echo     git config --global user.name "你的名字"
echo     git config --global user.email "你的邮箱@example.com"
echo.
pause
exit /b 1

:USAGE
echo.
echo PDF 转换工坊 - 推送到 GitHub
echo.
echo 用法: push_github.bat ^<GitHub用户名^> [仓库名] [提交名字] [提交邮箱]
echo.
echo 例子: push_github.bat zhangsan pdf-converter "张三" zhangsan@example.com
echo.
echo 步骤:
echo   1. 先到 https://github.com/new 建一个空仓库（不要勾选 README / .gitignore / license）
echo   2. 再运行上面的命令
echo.
pause
exit /b 1
