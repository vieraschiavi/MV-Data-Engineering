@echo off
rem ============================================================
rem  MV Data Engineering - version portable para Windows (.bat)
rem  ES: Doble clic y listo: crea el entorno, instala las
rem      dependencias la primera vez y abre el programa.
rem  EN: Double-click and go: creates the environment, installs
rem      dependencies on first run and opens the program.
rem  PT: Duplo clique e pronto: cria o ambiente, instala as
rem      dependencias na primeira execucao e abre o programa.
rem ============================================================
setlocal EnableExtensions
cd /d "%~dp0"
title MV Data Engineering
if not exist ".mvde_tmp" mkdir ".mvde_tmp" >nul 2>nul
set "TEMP=%cd%\.mvde_tmp"
set "TMP=%cd%\.mvde_tmp"
set "PYCMD="
python --version >nul 2>nul
if not errorlevel 1 set "PYCMD=python"
if not defined PYCMD py -3 --version >nul 2>nul
if not defined PYCMD if not errorlevel 1 set "PYCMD=py -3"
if not defined PYCMD (
  echo [ES] No se encontro Python 3.11+. Instalalo desde python.org y marca "Add to PATH".
  echo [EN] Python 3.11+ not found. Install it from python.org and tick "Add to PATH".
  pause & exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo [ES] Primera ejecucion: creando entorno...  [EN] First run: creating environment...
  %PYCMD% -m venv .venv || (echo No se pudo crear el entorno & pause & exit /b 1)
  ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt || (echo Fallo la instalacion & pause & exit /b 1)
)
".venv\Scripts\python.exe" -m streamlit run app\app.py --server.headless true --browser.gatherUsageStats false --client.toolbarMode minimal
if errorlevel 1 pause
