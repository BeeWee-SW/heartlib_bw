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
set "VPY=%CD%\.venv\Scripts\python.exe"

if not exist "%VPY%" (
    echo.
    echo   [FEHLER] Keine virtuelle Umgebung gefunden.
    echo            Bitte zuerst einrichten:
    echo                webapp\setup_windows.cmd
    echo.
    pause
    exit /b 1
)

rem A missing or broken web layer is the one failure that would otherwise
rem produce a bare traceback before the app can explain itself.
"%VPY%" -c "import fastapi, uvicorn" >nul 2>&1
if errorlevel 1 goto :diagnose

echo.
echo   Starte HeartMuLa Studio ... zum Beenden Strg+C druecken.
echo.
"%VPY%" -m webapp.main --open %*

if errorlevel 1 (
    echo.
    echo   Der Server wurde mit einem Fehler beendet.
    pause
)
exit /b 0

rem ---------------------------------------------------------------------------
:diagnose
echo.
echo   [FEHLER] fastapi/uvicorn lassen sich in der .venv nicht importieren.
echo.
echo   ---------------- Diagnose ----------------
echo   Interpreter:
"%VPY%" -c "import sys;print('   ', sys.executable);print('   ', sys.version)"
echo.
echo   Tatsaechlicher Importfehler ^(nicht unterdrueckt^):
"%VPY%" -c "import uvicorn"
echo.
echo   Gefundene Pakete:
"%VPY%" -m pip list --disable-pip-version-check 2>nul | findstr /i "fastapi uvicorn pydantic starlette"
echo   ------------------------------------------
echo.
echo   Naechster Schritt - Ausgabe dieses Befehls vollstaendig lesen:
echo       .venv\Scripts\python.exe -m pip install -r webapp\requirements.txt
echo.
echo   Bleibt es dabei, virtuelle Umgebung neu aufbauen:
echo       rmdir /s /q .venv
echo       webapp\setup_windows.cmd
echo.
pause
exit /b 1
