# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · Dos formas de instalarlo, el mismo programa.

**El caso real.** El consultor trabaja con la laptop que le da su empresa y
entra a clientes que no dejan instalar nada. Son dos mundos distintos y el
producto tiene que servir en los dos:

  ESCRITORIO   el instalador de siempre, en la máquina del analista. El
               programa y la persona están en la misma computadora.
  SERVIDOR     una VM del cliente (o un contenedor). El programa corre
               ahí y la persona entra por el navegador, sin instalar nada.

**Por qué no alcanza con «que ande en los dos».** Hay funciones que
dependen de que el proceso y la persona compartan la máquina, y en
servidor no significan lo mismo:

- `origenes.buscar()` recorre una carpeta **de la máquina que corre el
  proceso**. En la laptop eso es «buscá mis Excel»; en una VM compartida
  es un explorador del disco del servidor, escrito en un cuadro de texto.
  No es una función degradada: es otra función, y peligrosa.
- La pestaña Herramientas detecta Power BI Desktop, DAX Studio y Tabular
  Editor instalados. En el servidor no hay ninguno, y decir «no
  detectada» sobre la máquina equivocada hace dudar del resto.
- El overlay F9 escucha el teclado de la máquina. En un servidor no hay
  teclado que escuchar.

Este módulo responde UNA pregunta —¿el proceso corre en la máquina de
quien lo está usando?— y el resto del programa la consulta en vez de
adivinar cada uno por su cuenta.

**Cómo se decide.** Lo dice el instalador: el paquete de escritorio
exporta `MVDAX_MODO=escritorio` y la imagen de contenedor
`MVDAX_MODO=servidor`. La deducción es solo la red de contención para
cuando ninguno de los dos lo hizo, y ante la duda cae en SERVIDOR: si se
equivoca hacia ahí, se esconde una función y el mensaje dice cómo
prenderla; si se equivocara hacia escritorio, un servidor compartido
quedaría con su disco a la vista.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

MODO_ESCRITORIO = "escritorio"
MODO_SERVIDOR = "servidor"

#: La variable que fija el modo. La escribe el instalador, no el usuario.
VARIABLE = "MVDAX_MODO"

#: Señales de que esto es un contenedor. Ninguna es infalible sola; juntas
#: cubren Docker, Podman y Kubernetes, que es donde va a correr de verdad.
_MARCAS_CONTENEDOR = ("/.dockerenv", "/run/.containerenv")
_VARIABLES_CONTENEDOR = ("KUBERNETES_SERVICE_HOST", "MVDAX_CONTENEDOR")


def _en_contenedor() -> bool:
    if any(Path(m).exists() for m in _MARCAS_CONTENEDOR):
        return True
    return any(os.environ.get(v) for v in _VARIABLES_CONTENEDOR)


def _hay_escritorio_grafico() -> bool:
    """¿Esta máquina tiene una sesión gráfica donde alguien está sentado?

    En Windows y macOS, sí por definición: son las plataformas del
    instalador. En Linux, solo si hay un servidor gráfico — una VM sin
    `DISPLAY` es exactamente el caso que este módulo tiene que reconocer.
    """
    if sys.platform.startswith(("win", "darwin")):
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def modo() -> str:
    """`escritorio` o `servidor`. Lo declarado manda; lo deducido acompaña."""
    pedido = os.environ.get(VARIABLE, "").strip().lower()
    if pedido in (MODO_ESCRITORIO, MODO_SERVIDOR):
        return pedido
    if _en_contenedor():
        return MODO_SERVIDOR
    return MODO_ESCRITORIO if _hay_escritorio_grafico() else MODO_SERVIDOR


def es_servidor() -> bool:
    return modo() == MODO_SERVIDOR


def es_escritorio() -> bool:
    return modo() == MODO_ESCRITORIO


#: Lo que cambia entre un modo y el otro, en un solo lugar.
#:
#: `True` = la función tiene sentido en ese modo. Está escrito como datos y
#: no como `if` desparramados a propósito: cuando alguien agregue una
#: función que toque el disco o el teclado de la máquina, el lugar donde
#: decidirlo tiene que ser evidente, y hay un test que recorre esta tabla.
FUNCIONES_LOCALES: dict[str, str] = {
    # clave → por qué depende de la máquina de quien lo usa
    "buscar_archivos": "recorre una carpeta del disco de esta máquina",
    "detectar_herramientas": "busca programas instalados en esta máquina",
    "overlay": "escucha el teclado de esta máquina",
    "abrir_en_powerbi": "lanza Power BI Desktop de esta máquina",
}


def permite(funcion: str) -> bool:
    """¿Esta función tiene sentido en el modo actual?

    Lo que no está en `FUNCIONES_LOCALES` no depende de la máquina y anda
    igual en los dos modos — que es la mayor parte del producto: leer un
    dataset, corregir el modelo, escribir DAX, armar el tablero, exportar
    el `.pbit` y verificarlo.
    """
    return funcion not in FUNCIONES_LOCALES or es_escritorio()
