@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo   任务 #2 快速判断卡
echo ========================================
echo.
python task2\judge.py
echo.
pause
