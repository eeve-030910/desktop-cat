@echo off
cd /d "%~dp0"
echo Building Release version ...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_windows.ps1" -Channel Release
if errorlevel 1 (
    echo Build failed. Read the error above.
    pause
    exit /b 1
)
echo Done: dist\DesktopCat-v0.4.5.exe
explorer.exe "%~dp0dist"
pause
