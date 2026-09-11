# © 2026 Martín Viera. Todos los derechos reservados.
"""Modo confidencial: el programa no puede sacar un dato de la red donde corre.

Para qué existe
---------------
Cuando el producto se usa en un proyecto de consultoría, los datos son del
CLIENTE y no pueden salir de su infraestructura — ni a la máquina del
consultor, ni a un proveedor de IA, ni a un bucket. El acuerdo suele
prohibirlo y la responsabilidad no es del que configuró mal: es del que
entregó una herramienta que podía.

«Está apagado por defecto» no alcanza para eso. Una clave de API exportada
sin pensar, un YAML copiado de otro proyecto con una fuente `url`, un
`kaggle` que quedó de una prueba: en los tres casos el dato sale y nadie se
entera hasta que alguien audita. Este módulo convierte el default seguro en
una PROHIBICIÓN: con el modo activo, cada punto de salida corta con una
excepción que nombra qué se intentó y hacia dónde.

Cómo se activa
--------------
Una variable de entorno, del lado del servidor, que el consultor no controla:

    MVDE_CONFIDENCIAL=1

Se lee del entorno en CADA llamada, no una vez al importar: así el estado no
depende del orden en que se cargaron los módulos, y un test puede encenderlo
y apagarlo sin reimportar nada.

Qué bloquea, exactamente
------------------------
Los lugares del motor por donde un dato puede cruzar el borde de la red:

  fuentes.py    fuentes `url`, fuentes `kaggle`, y rutas de nube
                (s3:// gs:// az:// abfs:// adl://)
  ia.py         cualquier consulta a un proveedor de IA, y el listado de
                modelos — que ya viaja con la clave

`reuniones.py` no aparece porque ya no manda nada a la red: transcribía audio
contra OpenAI o Groq y se le sacó esa capacidad — el `.vtt` que exporta Teams
ya viene transcripto, con hablantes y sin conexión.

Qué NO bloquea, y por qué
-------------------------
Las fuentes SQL y los archivos locales siguen andando: son la red del cliente
y el disco de su propia VM. Bloquearlas dejaría al producto sin poder leer
los datos que vino a procesar. El borde que se defiende es la SALIDA de la
infraestructura del cliente, no el acceso a lo que ya está adentro.

Esto no reemplaza al firewall
-----------------------------
Un contenedor sin salida a internet es una garantía más fuerte, y las dos se
usan juntas: ver `docs/DESPLIEGUE.md`. Pero el firewall lo administra otra
gente y cambia sin avisar; esta defensa viaja con el programa y se verifica
con un test que corre en cada build.
"""
from __future__ import annotations

import os

ENV = "MVDE_CONFIDENCIAL"

# Prefijos de almacenamiento que están fuera de la red del cliente por
# definición. `file://` no está: es disco local.
PREFIJOS_NUBE = ("s3://", "gs://", "gcs://", "az://", "abfs://", "abfss://", "adl://")

# Valores que cuentan como "encendido". Se acepta más de uno a propósito:
# quien configura una VM escribe `true` o `1` según la costumbre del equipo, y
# que el modo dependa de haber acertado la palabra exacta sería justo el tipo
# de fragilidad que este módulo existe para no tener.
_VERDADEROS = {"1", "true", "si", "sí", "yes", "on"}


class SalidaBloqueada(RuntimeError):
    """Se intentó sacar datos de la red del cliente con el modo activo."""


def activo() -> bool:
    """Si el modo confidencial está encendido en este entorno."""
    return os.environ.get(ENV, "").strip().lower() in _VERDADEROS


def exigir_local(que: str, destino: str = "") -> None:
    """Corta si el modo está activo. `que` es la acción en criollo y `destino`
    a dónde iba el dato — los dos aparecen en el mensaje, porque un error que
    dice sólo «bloqueado» obliga a leer el código para saber qué se frenó."""
    if not activo():
        return
    hacia = f" hacia «{destino}»" if destino else ""
    raise SalidaBloqueada(
        f"modo confidencial activo ({ENV}): se bloqueó {que}{hacia}. "
        "Los datos de este proyecto no pueden salir de la red donde corre el "
        "programa. Si esta salida es legítima, apagar el modo es una decisión "
        "del dueño de los datos, no del que corre el pipeline."
    )


def es_ruta_de_nube(ruta: str) -> bool:
    return str(ruta).lower().startswith(PREFIJOS_NUBE)


def estado() -> dict:
    """Para el manifiesto de entrega y la app: deja constancia de en qué modo
    corrió el pipeline. Una corrida confidencial que no lo diga por escrito no
    le sirve a nadie que tenga que auditarla después."""
    enc = activo()
    return {
        "activo": enc,
        "variable": ENV,
        "bloquea": ["fuentes url", "fuentes kaggle", "rutas de nube",
                    "proveedores de IA"] if enc else [],
        "nota": ("Esta corrida no pudo sacar datos de la red donde se ejecutó."
                 if enc else
                 "Modo confidencial APAGADO: el proyecto puede leer de internet y consultar "
                 "proveedores de IA si el YAML o el entorno lo declaran."),
    }
