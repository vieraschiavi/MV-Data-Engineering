# Instalador de Windows · MV Data Engineering

Dos formas de correr el programa en Windows. La diferencia práctica es **qué
necesita la máquina donde se instala**.

| | Portable (`MV_DataEngineering.bat`) | Instalador (`MV_DataEngineering_Setup.exe`) |
|---|---|---|
| Python en la máquina | **Hace falta** 3.11+ en el PATH | No hace falta: va adentro |
| Internet la primera vez | **Hace falta** (baja ~500 MB de dependencias) | No hace falta |
| Permisos de administrador | No | No |
| Primera ejecución | Varios minutos | Inmediata |
| Accesos directos | No | Menú Inicio y escritorio |
| Para qué sirve | Probar rápido desde el ZIP del repo | Entregarle el producto a alguien |

El instalador existe porque la versión portable falla justo donde más duele:
en la PC de un cliente sin Python, sin permisos, o en una empresa que filtra
PyPI. Ahí el `.bat` muestra una pared de texto de pip y no abre.

## Cómo se construye

Se construye **en Windows**. En Linux no se puede: el runtime embebido de
python.org es un `.zip` de binarios de Windows e Inno Setup no corre ahí.

```powershell
powershell -ExecutionPolicy Bypass -File packaging\preparar_runtime.ps1
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" packaging\MVDataEngineering.iss
```

Queda en `dist_instalador\MV_DataEngineering_Setup.exe`.

En la práctica no hace falta hacerlo a mano: el workflow
`.github/workflows/instalador-mvde.yml` lo construye en un runner de Windows en
cada push que toque el producto, **y lo prueba instalándolo** — comprueba los
accesos directos, arranca el programa, le pide una página por HTTP, verifica
que escuche sólo en localhost y lo desinstala. El `.exe` queda como artefacto
de la corrida.

Ese workflow no es ceremonia. Estas cosas no fallan al compilar: fallan
instalándose bien y no abriendo en la máquina del cliente, que es donde no hay
nadie para diagnosticarlo.

## Las piezas

| Archivo | Qué es |
|---|---|
| `preparar_runtime.ps1` | Baja Python 3.11 embebido, le instala las dependencias adentro y arma `dist_app/` |
| `MVDataEngineering.iss` | Script de Inno Setup: empaqueta `dist_app/`, crea accesos directos, desinstala |
| `lanzador.py` | Arranca el motor y abre el navegador. Lo usan las **tres** formas de correr el programa |
| `mvde.ico` | Icono (6 tamaños, de 16 a 256 px) |

## Por qué el lanzador es uno solo

`lanzador.py` lo usan el `.bat` portable, el `run.sh` de Linux/macOS y los
accesos directos de la versión instalada. Tres caminos, un solo arranque: lo
que se arregla una vez queda arreglado en los tres.

Hace tres cosas que el arranque directo de Streamlit no hacía:

1. **Pide un puerto libre al sistema** en vez de usar el 8501 fijo. Con el
   puerto fijo, tener MV Data Governance abierto hacía que este no levantara —
   o, peor, que el navegador abriera la otra app y pareciera que éste está roto.
2. **Espera a que el servidor conteste** antes de abrir el navegador. Abrirlo
   antes muestra "no se puede acceder a este sitio" durante los segundos que
   Streamlit tarda, y la gente cierra la pestaña.
3. **Registra todo en un archivo** y avisa los errores con un cuadro de
   diálogo. Los accesos directos usan `pythonw.exe`, que no abre consola: sin
   esto, un fallo de arranque es un doble clic que no hace nada.

El log vive en `%LOCALAPPDATA%\MV Data Engineering\lanzador.log`. Es lo primero
que hay que pedir cuando alguien dice que no abre.

## Escucha sólo en localhost

El programa se ata a `127.0.0.1`, no a `0.0.0.0`. Con el default de Streamlit
la app queda accesible desde toda la red local y la consola imprime una
"External URL" con la IP pública de quien la corre. Para un programa de
escritorio eso no es una función.

El despliegue en servidor **no** se ve afectado: el `Dockerfile` pasa
`--server.address=0.0.0.0` en el `CMD`, y la línea de comandos le gana al
archivo de configuración. El default es el seguro; abrirse es explícito, y el
workflow lo verifica con `Get-NetTCPConnection` sobre la instalación real.
