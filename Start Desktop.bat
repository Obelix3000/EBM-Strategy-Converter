@echo off
title EBM Strategy Desktop
cd /d "%~dp0"

echo.
echo  =========================================
echo   EBM Strategy Desktop
echo  =========================================
echo.

:: ── 1. Python pruefen ───────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [FEHLER] Python nicht gefunden.
    echo Bitte Python installieren: https://www.python.org/downloads/
    pause & exit /b 1
)

:: ── 2. Virtuelles Environment anlegen (nur beim Erststart) ───────────────────
if not exist ".venv\Scripts\activate.bat" (
    echo [Setup] Erststart erkannt - erstelle virtuelle Umgebung...
    python -m venv .venv
    if errorlevel 1 (
        echo [FEHLER] Konnte .venv nicht erstellen.
        pause & exit /b 1
    )
    echo [Setup] Umgebung erstellt.
    echo.
)

:: ── 3. Umgebung aktivieren ───────────────────────────────────────────────────
call .venv\Scripts\activate.bat

:: ── 4. Requirements installieren / aktuell halten ────────────────────────────
echo [Setup] Pruefe Abhaengigkeiten...
pip install -r requirements.txt --quiet --disable-pip-version-check
if errorlevel 1 (
    echo [FEHLER] Requirements konnten nicht installiert werden.
    pause & exit /b 1
)
echo [Setup] Abhaengigkeiten OK.
echo.

:: ── 5. App starten ───────────────────────────────────────────────────────────
echo [Start] Desktop-App wird gestartet...
echo.
python desktop_app.py

pause
