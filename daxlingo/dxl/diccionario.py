# © 2026 Martín Viera. Todos los derechos reservados.

"""Por qué cada medida está escrita así.

Un tablero se entrega con cincuenta medidas y sin una línea que explique
por qué una usa `DIVIDE` y otra `/`, o por qué el denominador de un share
lleva `REMOVEFILTERS`. El que lo hereda tiene dos opciones: leer el DAX de
todas, o tocar y ver qué se rompe. Las dos son caras.

Este módulo arma un DICCIONARIO DE MEDIDAS: una fila por medida con su
fórmula y la razón de cada decisión que hay adentro. La razón no se
inventa ni se pide a una IA — se lee del propio DAX, patrón por patrón,
así que nunca contradice lo que el archivo hace de verdad.

Va como tabla desconectada al modelo (igual que `_Lectura`) para poder
mostrarla en una página del tablero: el diccionario viaja DENTRO del
.pbit, no en un documento aparte que se pierde.
"""
from __future__ import annotations

import re

from .catalogo import Catalogo
from .i18n import IDIOMA_DEFECTO, t as traducir

TABLA = "_Diccionario"
COL_MEDIDA = "Medida"
COL_CARPETA = "Carpeta"
COL_FORMATO = "Formato"
COL_DAX = "Fórmula"
COL_PORQUE = "Por qué está escrita así"


# Cada patrón es una decisión de diseño reconocible en el DAX, con la
# clave i18n que la explica. El orden importa: se listan de lo más
# específico a lo más general, porque `CALCULATE` aparece adentro de casi
# todo y explicarlo primero taparía lo que de verdad distingue a la
# medida.
_PATRONES: tuple[tuple[str, re.Pattern], ...] = (
    ("dic_ventana", re.compile(
        r"\bDATEADD\s*\([^,]*,\s*1\s*,\s*YEAR", re.IGNORECASE)),
    ("dic_guardia", re.compile(
        r"\bDiasHoy\b.*\bDiasAntes\b", re.IGNORECASE | re.DOTALL)),
    ("dic_aa", re.compile(r"\bSAMEPERIODLASTYEAR\s*\(", re.IGNORECASE)),
    ("dic_ytd", re.compile(r"\bTOTALYTD\s*\(", re.IGNORECASE)),
    ("dic_qtd", re.compile(r"\bTOTALQTD\s*\(", re.IGNORECASE)),
    ("dic_entre", re.compile(r"\bDATESBETWEEN\s*\(", re.IGNORECASE)),
    ("dic_quita", re.compile(
        r"\b(REMOVEFILTERS|ALL)\s*\(", re.IGNORECASE)),
    ("dic_visible", re.compile(r"\bALLSELECTED\s*\(", re.IGNORECASE)),
    ("dic_salvo", re.compile(r"\bALLEXCEPT\s*\(", re.IGNORECASE)),
    ("dic_keep", re.compile(r"\bKEEPFILTERS\s*\(", re.IGNORECASE)),
    ("dic_promedio_x", re.compile(
        r"\bAVERAGEX\s*\(\s*VALUES\s*\(", re.IGNORECASE)),
    ("dic_ranking", re.compile(r"\bRANKX\s*\(", re.IGNORECASE)),
    ("dic_distintos", re.compile(r"\bDISTINCTCOUNT\s*\(", re.IGNORECASE)),
    ("dic_division", re.compile(r"\bDIVIDE\s*\(", re.IGNORECASE)),
    ("dic_filas", re.compile(r"\bCOUNTROWS\s*\(", re.IGNORECASE)),
    ("dic_texto", re.compile(r"\bSWITCH\s*\(|\bFORMAT\s*\(", re.IGNORECASE)),
    ("dic_condicion", re.compile(r"\bCALCULATE\s*\(", re.IGNORECASE)),
    ("dic_suma", re.compile(r"\bSUM\s*\(", re.IGNORECASE)),
)

# Cuántas razones se listan por medida. Con más de tres la celda deja de
# leerse y el diccionario pasa a ser otro muro de texto — que es
# exactamente lo que viene a resolver.
MAX_RAZONES = 3


def porque(expresion: str, idioma: str = IDIOMA_DEFECTO) -> str:
    """Las decisiones de diseño que se leen en ese DAX, en una frase."""
    razones = []
    for clave, patron in _PATRONES:
        if patron.search(expresion or ""):
            razones.append(traducir(clave, idioma))
        if len(razones) == MAX_RAZONES:
            break
    if not razones:
        return traducir("dic_directa", idioma)
    return " ".join(razones)


def filas(cat: Catalogo, idioma: str = IDIOMA_DEFECTO) -> list[list]:
    """Una fila por medida: nombre, carpeta, formato, DAX y el porqué.

    Las medidas de color del semáforo no entran: son plomería del formato
    condicional, no lecturas de negocio, y sumarían quince filas que
    dicen todas lo mismo.
    """
    salida = []
    for m in sorted(cat.medidas(), key=lambda x: x["nombre"]):
        nombre = m["nombre"]
        if nombre.lower().startswith("color "):
            continue
        expr = " ".join((m.get("expresion") or "").split())
        salida.append([
            nombre,
            m.get("carpeta") or "—",
            m.get("formato") or "—",
            expr,
            porque(m.get("expresion") or "", idioma),
        ])
    return salida


def agregar(modelo: dict, idioma: str = IDIOMA_DEFECTO) -> dict:
    """Mete el diccionario en el modelo como tabla desconectada."""
    from . import dataset

    cat = Catalogo.desde_modelo(modelo)
    tablas = modelo.setdefault("model", {}).setdefault("tables", [])
    if any(t.get("name") == TABLA for t in tablas):
        return modelo
    datos = filas(cat, idioma)
    if not datos:
        return modelo
    columnas = [COL_MEDIDA, COL_CARPETA, COL_FORMATO, COL_DAX, COL_PORQUE]
    tabla = {
        "name": TABLA,
        "columns": [{"name": c, "dataType": "string", "sourceColumn": c,
                     "summarizeBy": "none"} for c in columnas],
        "partitions": [{
            "name": TABLA, "mode": "import",
            "source": {"type": "m",
                       "expression": dataset.m_embebido(columnas, datos)},
        }],
    }
    tablas.append(tabla)
    return modelo
