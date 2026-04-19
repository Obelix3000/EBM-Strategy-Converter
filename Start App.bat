@echo off
title EBM Strategy Software
echo.
echo  =========================================
echo   EBM Strategy Software wird gestartet...
echo  =========================================
echo.

:: Wechsle in das Projektverzeichnis (relativ zur .bat-Datei)
cd /d "%~dp0"

:: Pruefe ob das virtuelle Environment existiert
if not exist ".venv\Scripts\activate.bat" (
    echo FEHLER: Virtuelles Environment nicht gefunden!
    echo Bitte stelle sicher, dass .venv im Projektordner existiert.
    pause
    exit /b 1
)

:: Aktiviere das virtuelle Environment und starte Streamlit
call .venv\Scripts\activate.bat
echo Starte die App im Browser...
echo (Dieses Fenster kann minimiert werden)
echo.
streamlit run app.py

pause
