@echo off
setlocal enabledelayedexpansion
rem ---------------------------------------------------------------------------
rem  HeartMuLa Studio - Windows setup
rem
rem  Creates a .venv with a Python version that actually has wheels for this
rem  project's pinned dependencies, then installs everything into it.
rem  Your system PATH is never touched.
rem
rem  Usage:   webapp\setup_windows.cmd            (CUDA 12.4, the common case)
rem           webapp\setup_windows.cmd cu128      (other CUDA build)
rem           webapp\setup_windows.cmd cpu        (no GPU - UI only)
rem ---------------------------------------------------------------------------

cd /d "%~dp0.."
echo.
echo   HeartMuLa Studio - Einrichtung
echo   Verzeichnis: %CD%
echo.

rem -- 1. find a usable interpreter -------------------------------------------
rem numpy 2.0.2 ships wheels only up to Python 3.12; anything newer would try
rem to compile from source and fail without a C compiler.
set "PYCMD="
call :findpy 3.12
if not defined PYCMD call :findpy 3.11
if not defined PYCMD call :findpy 3.10

if not defined PYCMD (
    echo   [FEHLER] Keine passende Python-Version gefunden.
    echo.
    echo   Benoetigt wird Python 3.10, 3.11 oder 3.12.
    echo   Python 3.13 und 3.14 funktionieren NICHT: fuer numpy 2.0.2 gibt es
    echo   dort keine fertigen Pakete, und ohne C-Compiler bricht die
    echo   Installation ab.
    echo.
    echo   Installieren Sie Python 3.12 von:
    echo     https://www.python.org/downloads/release/python-3129/
    echo.
    echo   Beim Installer genuegt die Standardauswahl - eine PATH-Aenderung
    echo   ist NICHT noetig, dieses Skript findet die Version selbst.
    echo.
    goto :fail
)

echo   [1/5] Python gefunden:
%PYCMD% -VV

rem -- 2. virtual environment --------------------------------------------------
if exist ".venv\Scripts\python.exe" (
    echo   [2/5] Vorhandene .venv wird weiterverwendet
) else (
    echo   [2/5] Lege virtuelle Umgebung .venv an ...
    !PYCMD! -m venv .venv
    if errorlevel 1 (
        echo   [FEHLER] Anlegen der virtuellen Umgebung fehlgeschlagen.
        goto :fail
    )
)

set "VPY=%CD%\.venv\Scripts\python.exe"
if not exist "%VPY%" (
    echo   [FEHLER] %VPY% nicht gefunden.
    goto :fail
)

"%VPY%" -m pip install --upgrade pip --quiet
if errorlevel 1 echo   [Hinweis] pip liess sich nicht aktualisieren - weiter geht es trotzdem.

rem -- 3. PyTorch --------------------------------------------------------------
rem On Windows the PyPI torch wheels are CPU-only, so CUDA builds must come
rem from PyTorch's own index. Installing it first stops `pip install -e .`
rem from pulling the CPU variant.
set "CUDA=%~1"
if "%CUDA%"=="" set "CUDA=cu124"

where nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo.
    echo   [Hinweis] nvidia-smi nicht gefunden - vermutlich keine NVIDIA-GPU.
    echo             Die Oberflaeche laeuft trotzdem, aber Songs lassen sich
    echo             ohne CUDA-GPU nicht erzeugen.
    echo.
)

if /i "%CUDA%"=="cpu" (
    echo   [3/5] Installiere PyTorch ^(CPU-Variante^) ...
    "%VPY%" -m pip install torch torchaudio
) else (
    echo   [3/5] Installiere PyTorch mit CUDA ^(%CUDA%^) ...
    "%VPY%" -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/%CUDA%
)
if errorlevel 1 (
    echo.
    echo   [FEHLER] PyTorch konnte nicht installiert werden.
    echo            Passende CUDA-Variante pruefen unter:
    echo              https://pytorch.org/get-started/locally/
    echo            Dann erneut aufrufen, z. B.:
    echo              webapp\setup_windows.cmd cu128
    goto :fail
)

rem -- 4. the model library ----------------------------------------------------
echo   [4/5] Installiere heartlib ...
"%VPY%" -m pip install -e .
if errorlevel 1 (
    echo   [FEHLER] Installation von heartlib fehlgeschlagen.
    goto :fail
)

rem -- 5. the web layer --------------------------------------------------------
echo   [5/5] Installiere die Web-Schicht ...
"%VPY%" -m pip install -r webapp\requirements.txt
if errorlevel 1 (
    echo   [FEHLER] Installation der Web-Schicht fehlgeschlagen.
    goto :fail
)

echo.
echo   Fertig. Starten mit:
echo       webapp\start_windows.cmd
echo.
rem No percent signs in this line: cmd would eat them as variable references.
"%VPY%" -c "import torch;print('   PyTorch', torch.__version__, '| CUDA verfuegbar:', torch.cuda.is_available())" 2>nul
echo.
pause
exit /b 0

rem ---------------------------------------------------------------------------
:findpy
py -%1 -c "import sys" >nul 2>&1
if not errorlevel 1 set "PYCMD=py -%1"
exit /b 0

:fail
echo.
pause
exit /b 1
