@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul || (echo Python n est pas installe. Voir MODE_EMPLOI.md, option B. & pause & exit /b 1)
py -3 -m pip install --quiet --user -r requirements.txt
start "" pyw -3 -m capture_ecran
