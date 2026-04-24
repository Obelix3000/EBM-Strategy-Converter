@echo off
title EBM Strategy Software
cd /d "%~dp0"

echo.
echo  =========================================
echo   EBM Strategy Software
echo  =========================================
echo.

:: ── 1. Python prüfen ─────────────────────────────────────────────────────────
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

:: ── 5. Git-Updates prüfen ────────────────────────────────────────────────────
git --version >nul 2>&1
if errorlevel 1 goto :start_app

echo [Update] Pruefe auf Updates...
git fetch --quiet --timeout=5 2>nul
if errorlevel 1 (
    echo [Update] Kein Netzwerkzugang - Update-Check uebersprungen.
    echo.
    goto :start_app
)

:: Lokalen Stand mit Remote vergleichen
for /f %%i in ('git rev-parse HEAD 2^>nul') do set LOCAL=%%i
for /f %%i in ('git rev-parse @{u} 2^>nul') do set REMOTE=%%i

if "%LOCAL%"=="%REMOTE%" (
    echo [Update] Software ist aktuell.
) else (
    echo [Update] Neue Version verfuegbar - wird heruntergeladen...
    git pull --quiet
    if errorlevel 1 (
        echo [Update] Update fehlgeschlagen - starte mit vorhandener Version.
    ) else (
        echo [Update] Update abgeschlossen. Installiere neue Abhaengigkeiten...
        pip install -r requirements.txt --quiet --disable-pip-version-check
    )
)
echo.

:: ── 6. App starten ───────────────────────────────────────────────────────────
:start_app
echo [Start] Oeffne App im Browser...
echo        (Dieses Fenster kann minimiert werden)
echo.
streamlit run app.py

pause
