# © 2026 Martín Viera. Todos los derechos reservados.
#
# Arma la carpeta que el instalador empaqueta: el producto + un Python 3.11
# embebido con TODAS las dependencias ya instaladas adentro.
#
# La gracia es que la máquina donde se instala no necesita Python, ni internet,
# ni permisos de administrador. Todo el trabajo lento —bajar medio giga de
# wheels— pasa acá, una vez, en el runner, y no en la PC de cada persona.
#
# Corre en Windows (runner de GitHub o una máquina propia). En Linux no: el
# runtime embebido de python.org es un .zip de binarios de Windows.
#
#   powershell -ExecutionPolicy Bypass -File packaging\preparar_runtime.ps1

param(
  [string]$VersionPython = "3.11.9"
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"          # sin esto Invoke-WebRequest es MUCHO más lento

$raiz    = Split-Path -Parent $PSScriptRoot
$destino = Join-Path $raiz "dist_app"
$runtime = Join-Path $destino "runtime"

Write-Host "== Limpiando staging anterior"
if (Test-Path $destino) { Remove-Item $destino -Recurse -Force }
New-Item -ItemType Directory -Path $destino | Out-Null

# ---------------------------------------------------------------------------
# 1. El producto. Se copia lo que el programa NECESITA para correr, no el repo
#    entero: los tests, los videos, la landing y el material de venta no tienen
#    por qué viajar dentro del instalador ni sumar peso a la descarga.
# ---------------------------------------------------------------------------
Write-Host "== Copiando el producto"
foreach ($d in @("mvde", "app", "docs", "packaging", ".streamlit")) {
  $origen = Join-Path $raiz $d
  if (Test-Path $origen) {
    Copy-Item $origen -Destination (Join-Path $destino $d) -Recurse -Force
  }
}
foreach ($f in @("README.md", "requirements.txt")) {
  $origen = Join-Path $raiz $f
  if (Test-Path $origen) { Copy-Item $origen -Destination $destino -Force }
}
# `datos/` vacía: el programa escribe ahí y si no existe falla al primer uso.
New-Item -ItemType Directory -Path (Join-Path $destino "datos") -Force | Out-Null

# Los __pycache__ de la máquina que construye no sirven en la que instala, y
# sólo suman archivos al instalador.
Get-ChildItem $destino -Recurse -Directory -Filter "__pycache__" |
  Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# ---------------------------------------------------------------------------
# 2. El intérprete embebido.
# ---------------------------------------------------------------------------
Write-Host "== Bajando Python $VersionPython embebido"
$zip = Join-Path $env:TEMP "python-$VersionPython-embed-amd64.zip"
Invoke-WebRequest "https://www.python.org/ftp/python/$VersionPython/python-$VersionPython-embed-amd64.zip" -OutFile $zip
Expand-Archive $zip -DestinationPath $runtime -Force
Remove-Item $zip

# Sin descomentar `import site`, pip instala pero NADA se importa: el runtime
# embebido arranca con el sistema de paquetes apagado y `import streamlit`
# falla con un ModuleNotFoundError que no dice por qué.
$pth = Get-ChildItem $runtime -Filter "python*._pth" | Select-Object -First 1
(Get-Content $pth.FullName) -replace '^#\s*import site', 'import site' | Set-Content $pth.FullName

Write-Host "== Instalando pip y las dependencias dentro del runtime"
$getpip = Join-Path $env:TEMP "get-pip.py"
Invoke-WebRequest "https://bootstrap.pypa.io/get-pip.py" -OutFile $getpip
& "$runtime\python.exe" $getpip --no-warn-script-location
Remove-Item $getpip
& "$runtime\python.exe" -m pip install --no-warn-script-location --disable-pip-version-check `
  -r (Join-Path $raiz "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "pip falló instalando las dependencias" }

# ---------------------------------------------------------------------------
# 3. Comprobar que el runtime se sostiene solo ANTES de empaquetarlo.
#    Un instalador que se construye bien y no arranca es peor que uno que no
#    se construye: el error aparece en la máquina del cliente.
# ---------------------------------------------------------------------------
Write-Host "== Comprobando el runtime"
& "$runtime\python.exe" -c @"
import sys, streamlit, pandas, duckdb, sklearn, matplotlib
print('python    ', sys.version.split()[0])
print('streamlit ', streamlit.__version__)
print('pandas    ', pandas.__version__)
print('duckdb    ', duckdb.__version__)
"@
if ($LASTEXITCODE -ne 0) { throw "el runtime embebido no puede importar sus dependencias" }

# El motor del producto tiene que importarse con ESE intérprete, no con el del
# sistema: es la diferencia entre "las dependencias están" y "el programa anda".
& "$runtime\python.exe" -c "import sys; sys.path.insert(0, r'$destino'); import mvde; print('mvde        OK ·', len(mvde.ETAPAS), 'etapas')"
if ($LASTEXITCODE -ne 0) { throw "el runtime no puede importar el motor mvde" }

if (-not (Test-Path "$runtime\pythonw.exe")) { throw "falta pythonw.exe: los accesos directos abrirían una consola" }

$mb = [math]::Round((Get-ChildItem $destino -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB, 1)
Write-Host "== Listo: $destino ($mb MB)"
