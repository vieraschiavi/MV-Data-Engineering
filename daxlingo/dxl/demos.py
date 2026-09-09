# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · Registro de los datasets DEMO que el producto trae adentro.

Los CSV viven en `datos/demo/<clave>/` y los escribe
`datos/demo/generar_demos.py` con semilla fija; este módulo solo dice
cuáles existen, cómo se llaman en cada idioma, en qué orden cargar sus
tablas y en qué edición se ofrece cada uno. La app lee de acá — no de una
lista propia — para que un demo nuevo aparezca en pantalla con solo
registrarlo.

El ORDEN de `tablas` importa y no es cosmético: el motor infiere el modelo
recorriendo las tablas tal como llegan, y ante dos candidatas de igual
peso se queda con la primera. En `farma`, `Producto` va antes que `Medico`
para que la corporación que sale del denominador del share sea la del
producto (que es la que vende) y no la del médico.

`farma` es solo de la edición owner: es el demo con el que se muestra el
producto en una reunión, no el que se entrega con la licencia.
"""
from __future__ import annotations

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]      # daxlingo/

_CARPETA_DEMOS = Path("datos") / "demo"


def _archivos(carpeta: Path, tablas: tuple[str, ...]):
    def archivos() -> list[Path]:
        return [RAIZ / carpeta / f"{t}.csv" for t in tablas]
    return archivos


def _demo(clave: str, ediciones: tuple[str, ...],
          tablas: tuple[str, ...]) -> dict:
    carpeta = _CARPETA_DEMOS / clave
    return {
        "clave": clave,
        "titulo": f"demo_{clave}_titulo",
        "descripcion": f"demo_{clave}_desc",
        "ediciones": ediciones,
        "carpeta": carpeta,
        "tablas": tablas,
        "archivos": _archivos(carpeta, tablas),
    }


DEMOS: list[dict] = [
    _demo("ofertas", ("profesional", "demo", "owner"),
          ("Calendario", "Canal", "PuntoVenta", "Oferta", "Relevamiento")),
    _demo("relevamiento", ("profesional", "demo", "owner"),
          ("Calendario", "Cliente", "Pregunta", "Respuesta", "Objetivo")),
    _demo("farma", ("owner",),
          ("Fecha", "Producto", "Medico", "Visitas", "Recetas",
           "InteraccionDigital", "Mercado")),
]


def disponibles(edicion: str) -> list[dict]:
    """Los demos que se ofrecen en esta edición, en el orden del registro."""
    return [d for d in DEMOS if edicion in d["ediciones"]]


def por_clave(clave: str) -> dict:
    for d in DEMOS:
        if d["clave"] == clave:
            return d
    raise KeyError(clave)


def archivos_de(clave: str) -> list[Path]:
    """Las rutas absolutas de los CSV del demo, en el orden de carga."""
    return por_clave(clave)["archivos"]()
