#!/usr/bin/env python3
# © 2026 Martín Viera. Todos los derechos reservados.
"""
Lanzador de MV Data Engineering para la versión INSTALADA en Windows.

Lo arranca `pythonw.exe` del runtime embebido, sin ventana de consola. Eso
obliga a dos cosas que acá no son opcionales:

1. **Todo se registra en un archivo.** Sin consola, una excepción no la ve
   nadie: el programa "no abre" y no hay nada que mirar. El log vive en
   `%LOCALAPPDATA%\\MV Data Engineering\\lanzador.log` y es lo primero que hay
   que pedirle a alguien que reporta que no arranca.
2. **Los errores se muestran en una ventana.** Si el motor no levanta, sale un
   cuadro de diálogo de Windows con el motivo y la ruta del log, en vez de un
   silencio.

Y dos decisiones sobre el arranque:

- **Puerto libre de verdad, no 8501 fijo.** El 8501 es el default de Streamlit
  y lo usan los otros productos de la casa: con el puerto fijo, tener MV Data
  Governance abierto hacía que este no levantara, o —peor— que el navegador
  abriera la OTRA app y pareciera que este programa está roto. Se pide al
  sistema un puerto libre y se usa ese.
- **El navegador se abre recién cuando el servidor contesta.** Abrirlo antes
  muestra "no se puede acceder a este sitio" durante los segundos que Streamlit
  tarda en levantar, y la gente cierra la pestaña antes de que cargue.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
APP = RAIZ / "app" / "app.py"
ESPERA_MAX = 90.0          # segundos: la primera carga de pandas+sklearn es lenta en discos lentos
INTERVALO = 0.4


def _carpeta_log() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("TEMP") or str(Path.home())
    carpeta = Path(base) / "MV Data Engineering"
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


LOG = _carpeta_log() / "lanzador.log"


def registrar(msg: str) -> None:
    linea = f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {msg}"
    try:
        with LOG.open("a", encoding="utf-8") as f:
            f.write(linea + "\n")
    except OSError:
        pass                                   # un log que no se puede escribir no tumba el programa
    print(linea)                               # visible si alguien lo corre con python.exe


def avisar(titulo: str, texto: str) -> None:
    """Cuadro de diálogo de Windows. Sin consola es la única forma de que el
    usuario se entere de por qué no abrió."""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, texto, titulo, 0x10)   # MB_ICONERROR
    except Exception:
        pass


def puerto_libre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def esperar_servidor(url: str, proc: subprocess.Popen) -> bool:
    """True cuando el endpoint de salud contesta. Corta antes si el proceso
    murió: esperar 90 segundos a algo que ya no existe es tiempo regalado."""
    limite = time.monotonic() + ESPERA_MAX
    while time.monotonic() < limite:
        if proc.poll() is not None:
            registrar(f"el motor terminó solo con código {proc.returncode}")
            return False
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return True
        except (urllib.error.URLError, OSError, TimeoutError):
            pass
        time.sleep(INTERVALO)
    registrar(f"el motor no contestó en {ESPERA_MAX:.0f}s")
    return False


def main() -> int:
    registrar(f"--- arranque · raíz={RAIZ}")
    if not APP.exists():
        msg = f"No se encontró la aplicación en:\n{APP}\n\nLa instalación parece incompleta."
        registrar(msg.replace("\n", " "))
        avisar("MV Data Engineering", msg)
        return 2

    puerto = puerto_libre()
    url = f"http://127.0.0.1:{puerto}"
    registrar(f"puerto elegido: {puerto}")

    # `python.exe` del runtime, no `sys.executable`: este script lo corre
    # pythonw.exe, y Streamlit con pythonw pierde stdout y algunas de sus
    # comprobaciones de arranque se comportan distinto.
    py = Path(sys.executable).with_name("python.exe")
    if not py.exists():
        py = Path(sys.executable)

    cmd = [str(py), "-m", "streamlit", "run", str(APP),
           "--server.port", str(puerto),
           "--server.address", "127.0.0.1",     # nunca 0.0.0.0: esto es una app de escritorio
           "--server.headless", "true",         # el navegador lo abrimos nosotros, cuando ya contesta
           "--browser.gatherUsageStats", "false",
           "--client.toolbarMode", "minimal"]
    registrar("ejecutando: " + " ".join(cmd))

    creation = getattr(subprocess, "CREATE_NO_WINDOW", 0)       # sin ventanita negra al arrancar
    try:
        with LOG.open("a", encoding="utf-8") as salida:
            proc = subprocess.Popen(cmd, cwd=str(RAIZ), stdout=salida, stderr=salida,
                                    creationflags=creation)
    except OSError as e:
        msg = f"No se pudo arrancar el motor:\n{e}\n\nDetalle en:\n{LOG}"
        registrar(f"fallo al arrancar: {e}")
        avisar("MV Data Engineering", msg)
        return 3

    if not esperar_servidor(f"{url}/_stcore/health", proc):
        try:
            proc.terminate()
        except OSError:
            pass
        msg = ("El programa no llegó a abrir.\n\n"
               f"El detalle está en:\n{LOG}\n\n"
               "Si el problema sigue, mandá ese archivo.")
        avisar("MV Data Engineering", msg)
        return 4

    registrar(f"servidor listo, abriendo {url}")
    webbrowser.open(url)
    try:
        proc.wait()                            # el programa vive mientras viva el motor
    except KeyboardInterrupt:
        proc.terminate()
    registrar(f"--- cierre · código {proc.returncode}")
    return proc.returncode or 0


if __name__ == "__main__":
    sys.exit(main())
