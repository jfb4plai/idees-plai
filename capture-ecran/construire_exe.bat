@echo off
chcp 65001 >nul
cd /d "%~dp0"
py -3 -m pip install --user -r requirements-dev.txt
py -3 -m PyInstaller --noconfirm --onefile --windowed --name "Capture-ecran-PLAI" --collect-submodules PIL capture_ecran\__main__.py
echo.
echo Termine : dist\Capture-ecran-PLAI.exe
pause
