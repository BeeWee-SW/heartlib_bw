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
rem           webapp\setup_windows.cmd cu124 "C:\Path\to\python.exe"
rem                                               (interpreter picked by hand)
rem ---------------------------------------------------------------------------

cd /d "%~dp0.."
echo.
echo   HeartMuLa Studio - Einrichtung
echo   Verzeichnis: %CD%
echo.

rem -- 0. neutralise pip redirection -------------------------------------------
rem A machine-wide PIP_TARGET (common alongside ComfyUI / embedded-Python
rem setups) makes pip write every package into that folder instead of the
rem virtual environment. pip still exits 0, so the install looks successful
rem while nothing is importable. These are cleared for this process only -
rem setlocal keeps the user's environment untouched.
set "PIP_TARGET="
set "PIP_USER="
set "PIP_PREFIX="
set "PYTHONPATH="
set "PYTHONHOME="

rem The same setting can also live in pip.ini, where clearing an environment
rem variable does not reach it. That is checked once the venv exists, below.

rem -- 1. find a usable interpreter -------------------------------------------
rem numpy 2.0.2 ships wheels only up to Python 3.12; anything newer would try
rem to compile from source and fail without a C compiler.
rem
rem The py launcher is not assumed to exist: it is missing on machines where
rem Python came from the Store, from winget, or from the 3.14 install manager.
rem So the known install layouts are probed directly as well. An explicit path
rem given as the second argument always wins.
set "PYEXE="

if not "%~2"=="" (
    if exist "%~2" (
        set "PYEXE=%~2"
    ) else (
        echo   [FEHLER] Angegebener Python-Pfad existiert nicht: %~2
        goto :fail
    )
)

if not defined PYEXE call :findpy 3.12 312
if not defined PYEXE call :findpy 3.11 311
if not defined PYEXE call :findpy 3.10 310

if not defined PYEXE (
    echo   [FEHLER] Keine passende Python-Version gefunden.
    echo.
    echo   Benoetigt wird Python 3.10, 3.11 oder 3.12.
    echo   Python 3.13 und 3.14 funktionieren NICHT: fuer numpy 2.0.2 gibt es
    echo   dort keine fertigen Pakete, und ohne C-Compiler bricht die
    echo   Installation ab.
    echo.
    echo   Gesucht wurde nach dem py-Launcher und unter:
    echo     %LocalAppData%\Programs\Python\Python312\python.exe
    echo     %LocalAppData%\Python\pythoncore-3.12-64\python.exe
    echo     %ProgramFiles%\Python312\python.exe
    echo     C:\Python312\python.exe
    echo   ^(sowie den gleichen Pfaden fuer 3.11 und 3.10^)
    echo.
    echo   Installieren Sie Python 3.12 von:
    echo     https://www.python.org/downloads/release/python-3129/
    echo   Standardauswahl genuegt - eine PATH-Aenderung ist NICHT noetig.
    echo.
    echo   Liegt Python bei Ihnen woanders, geben Sie den Pfad direkt an:
    echo     webapp\setup_windows.cmd cu124 "C:\Pfad\zu\python.exe"
    echo.
    goto :fail
)

echo   [1/5] Python gefunden:
echo         !PYEXE!
"!PYEXE!" -VV
if errorlevel 1 (
    echo   [FEHLER] Dieser Interpreter laesst sich nicht ausfuehren.
    goto :fail
)

rem -- 2. virtual environment --------------------------------------------------
if exist ".venv\Scripts\python.exe" (
    echo   [2/5] Vorhandene .venv wird weiterverwendet
) else (
    echo   [2/5] Lege virtuelle Umgebung .venv an ...
    "!PYEXE!" -m venv .venv
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

rem A `target` in pip.ini would redirect installs past the venv just like
rem PIP_TARGET does, and no environment variable can override it. Detect it and
rem take the config file out of the loop for this run.
set "PIPCFG="
"%VPY%" -m pip config list > "%TEMP%\heartmula_pipcfg.txt" 2>nul
if exist "%TEMP%\heartmula_pipcfg.txt" (
    findstr /i "target" "%TEMP%\heartmula_pipcfg.txt" >nul 2>&1
    if not errorlevel 1 set "PIPCFG=1"
    del "%TEMP%\heartmula_pipcfg.txt" >nul 2>&1
)
if defined PIPCFG (
    echo.
    echo   [Hinweis] Ihre pip-Konfiguration enthaelt ein Zielverzeichnis
    echo             ^(target^). Es wuerde die Pakete an der virtuellen
    echo             Umgebung vorbeischreiben und wird fuer diesen Lauf
    echo             ignoriert. Ein Proxy oder eigener Paket-Index aus
    echo             derselben Datei gilt dann ebenfalls nicht.
    echo.
    set "PIP_CONFIG_FILE=nul"
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
echo   [5/6] Installiere die Web-Schicht ...
"%VPY%" -m pip install -r webapp\requirements.txt
if errorlevel 1 (
    echo   [FEHLER] Installation der Web-Schicht fehlgeschlagen.
    goto :fail
)

rem -- 6. verify ---------------------------------------------------------------
rem pip can exit 0 and still leave a package unimportable (wrong environment,
rem a partially written install, a stale cache). Reporting success without
rem checking would push that failure to first start, as a raw traceback.
echo   [6/6] Pruefe Installation ...
"%VPY%" -c "import fastapi, uvicorn, pydantic" >nul 2>&1
if errorlevel 1 (
    echo.
    echo   [FEHLER] Die Web-Schicht ist nicht importierbar, obwohl pip
    echo            keinen Fehler gemeldet hat. Der echte Fehler lautet:
    echo.
    rem Re-run without suppression: hiding this is what made the problem
    rem undiagnosable in the first place.
    "%VPY%" -c "import fastapi, uvicorn, pydantic"
    echo.
    echo            Nachinstallieren und die Ausgabe vollstaendig lesen:
    echo                .venv\Scripts\python.exe -m pip install -r webapp\requirements.txt
    goto :fail
)
"%VPY%" -c "import heartlib" >nul 2>&1
if errorlevel 1 (
    echo.
    echo   [FEHLER] heartlib ist nicht importierbar. Der echte Fehler lautet:
    echo.
    "%VPY%" -c "import heartlib"
    echo.
    echo            Nachinstallieren und die Ausgabe vollstaendig lesen:
    echo                .venv\Scripts\python.exe -m pip install -e .
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
rem  :findpy <dotted> <compact>   e.g.  call :findpy 3.12 312
rem  Sets PYEXE to a full python.exe path, or leaves it undefined.
:findpy
if defined PYEXE exit /b 0

rem The launcher knows best when it is there. Its answer is written to a file
rem rather than captured with for/f, which is fragile around nested quotes.
del "%TEMP%\heartmula_py.txt" >nul 2>&1
py -%1 -c "import sys;open(r'%TEMP%\heartmula_py.txt','w').write(sys.executable)" >nul 2>&1
if exist "%TEMP%\heartmula_py.txt" (
    set /p PYEXE=<"%TEMP%\heartmula_py.txt"
    del "%TEMP%\heartmula_py.txt" >nul 2>&1
)
if defined PYEXE exit /b 0

call :trypath "%LocalAppData%\Programs\Python\Python%2\python.exe"
call :trypath "%LocalAppData%\Python\pythoncore-%1-64\python.exe"
call :trypath "%ProgramFiles%\Python%2\python.exe"
call :trypath "%ProgramFiles(x86)%\Python%2-32\python.exe"
call :trypath "C:\Python%2\python.exe"
exit /b 0

:trypath
if defined PYEXE exit /b 0
if exist "%~1" set "PYEXE=%~1"
exit /b 0

:fail
echo.
pause
exit /b 1
