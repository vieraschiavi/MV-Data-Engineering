@echo off
rem ============================================================
rem  MV Data Engineering - version PORTABLE para Windows (.bat)
rem
rem  ES: Doble clic. Crea el entorno la primera vez y abre el programa.
rem  EN: Double-click. Creates the environment on first run and opens it.
rem  PT: Duplo clique. Cria o ambiente na primeira vez e abre o programa.
rem
rem  Esta version necesita Python 3.11+ instalado y bajar las dependencias
rem  la primera vez. Si eso no sirve -sin internet, sin permisos, PyPI
rem  filtrado por la empresa- usa el INSTALADOR, que lleva todo adentro:
rem  MV_DataEngineering_Setup.exe (ver packaging\LEEME.md).
rem ============================================================
setlocal EnableExtensions
cd /d "%~dp0"
title MV Data Engineering
if not exist ".mvde_tmp" mkdir ".mvde_tmp" >nul 2>nul
set "TEMP=%cd%\.mvde_tmp"
set "TMP=%cd%\.mvde_tmp"
set "LOGINSTALL=%cd%\.mvde_tmp\instalacion.log"

rem --- Buscar Python -------------------------------------------------------
rem  Se prueba `py` PRIMERO. El `python` del PATH puede ser el stub de la
rem  Microsoft Store: responde a `--version` sin ser un Python, y lo unico
rem  que hace al ejecutarlo es abrir la tienda. El lanzador `py` nunca es el
rem  stub, y `py -3.11` prefiere la version con la que se prueba el producto.
set "PYCMD="
py -3.11 -c "import sys" >nul 2>nul && set "PYCMD=py -3.11"
if not defined PYCMD py -3 -c "import sys" >nul 2>nul && set "PYCMD=py -3"
if not defined PYCMD python -c "import sys" >nul 2>nul && set "PYCMD=python"
if not defined PYCMD (
  echo.
  echo  [ES] No se encontro Python 3.11 o superior.
  echo       Instalalo desde https://www.python.org/downloads/ y marca
  echo       "Add python.exe to PATH" durante la instalacion.
  echo       O usa el instalador MV_DataEngineering_Setup.exe, que no lo necesita.
  echo.
  echo  [EN] Python 3.11+ not found. Install it from python.org ticking
  echo       "Add python.exe to PATH", or use MV_DataEngineering_Setup.exe.
  echo.
  pause & exit /b 1
)

rem --- Comprobar la version ------------------------------------------------
rem  Con 3.10 o menos el programa importa y despues revienta en medio de una
rem  corrida con un error que no menciona la version. Mejor cortar aca.
%PYCMD% -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
if errorlevel 1 (
  echo  [ES] Se encontro Python, pero es anterior a 3.11. Actualizalo.
  echo  [EN] Python found, but older than 3.11. Please upgrade.
  %PYCMD% --version
  pause & exit /b 1
)

rem --- Entorno -------------------------------------------------------------
if not exist ".venv\Scripts\python.exe" (
  echo.
  echo  [ES] Primera ejecucion: preparando el entorno. Puede tardar varios
  echo       minutos y necesita internet. Solo pasa esta vez.
  echo  [EN] First run: preparing the environment. This can take several
  echo       minutes and needs internet. Only happens once.
  echo.
  %PYCMD% -m venv .venv
  if errorlevel 1 (echo  No se pudo crear el entorno. & pause & exit /b 1)
  rem  La salida completa va a un archivo: si pip falla, el motivo real esta
  rem  ahi y se puede mandar. En pantalla solo la ultima linea, que es la que
  rem  dice que paso.
  ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt > "%LOGINSTALL%" 2>&1
  if errorlevel 1 (
    echo.
    echo  [ES] Fallo la instalacion de dependencias. Detalle en:
    echo       %LOGINSTALL%
    echo  [EN] Dependency installation failed. Details in the file above.
    echo.
    powershell -NoProfile -Command "Get-Content '%LOGINSTALL%' -Tail 15" 2>nul
    rmdir /s /q .venv >nul 2>nul
    pause & exit /b 1
  )
  echo  [ES] Entorno listo.  [EN] Environment ready.
)

rem --- Arrancar ------------------------------------------------------------
rem  Se usa el MISMO lanzador que la version instalada: elige un puerto libre
rem  (no el 8501, que chocaba con los otros programas de la casa), espera a
rem  que el motor conteste y recien ahi abre el navegador.
".venv\Scripts\python.exe" "packaging\lanzador.py"
if errorlevel 1 pause
