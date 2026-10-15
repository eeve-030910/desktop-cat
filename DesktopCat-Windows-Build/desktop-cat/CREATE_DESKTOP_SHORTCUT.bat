@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0create_desktop_shortcut.ps1"
if errorlevel 1 (
    echo Shortcut creation failed. Build the EXE first using BUILD_EXE.bat.
    pause
    exit /b 1
)
pause
