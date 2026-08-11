@echo off
rem ---------------------------------------------------------------------------
rem  HeartMuLa Studio - Windows launcher
rem
rem  Runs the app from the .venv created by setup_windows.cmd. Any arguments
rem  are passed straight through, e.g.:
rem      webapp\start_windows.cmd --port 8080
rem      webapp\start_windows.cmd --lazy_load
rem ---------------------------------------------------------------------------

cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo   [FEHLER] Keine virtuelle Umgebung gefunden.
    echo            Bitte zuerst einrichten:
    echo                webapp\setup_windows.cmd
    echo.
    pause
    exit /b 1
)

echo.
echo   Starte HeartMuLa Studio ... zum Beenden Strg+C druecken.
echo.
".venv\Scripts\python.exe" -m webapp.main --open %*

if errorlevel 1 (
    echo.
    echo   Der Server wurde mit einem Fehler beendet.
    pause
)
exit /b 0
