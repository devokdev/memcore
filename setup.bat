@echo off
setlocal

echo ========================================================
echo         🧠 MemCore One-Click Setup for Windows         
echo ========================================================
echo.

:: 1. Check Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python 3.10+ was not found in your PATH!
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)

echo [1/3] Installing MemCore and dependencies...
python -m pip install -e .
if %errorlevel% neq 0 (
    echo [ERROR] Installation failed.
    pause
    exit /b 1
)

echo.
echo [2/3] Activating global Antigravity & MCP plugin...
python -m memcore.cli init

echo.
echo ========================================================
echo  ✨ SUCCESS! MemCore is installed and ready to use!   
echo ========================================================
echo.
echo In any project folder, simply open terminal and run:
echo    memcore init
echo.
pause
