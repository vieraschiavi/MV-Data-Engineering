# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · Corrector del REPORTE de un `.pbix`.

Qué se puede arreglar y qué no
------------------------------
El `DataModel` de un `.pbix` es un binario propietario (XPress9, el formato
de backup de Analysis Services) que no se puede leer desde afuera de Power
BI. Pero NO hace falta leerlo para arreglar el reporte: se copia byte a byte
tal como vino y se reescribe sólo `Report/Layout`, que es JSON.

O sea:

  · defectos del REPORTE (visuales duplicados, botones tapados) → se
    arreglan y sale un `.pbix` que Power BI abre, con el modelo intacto;
  · defectos del MODELO (medidas, relaciones, auto date/time) → no se puede
    desde acá. Hay que exportar `.pbit` desde Power BI Desktop.

Qué se toca y qué no
--------------------
Sólo lo que se puede justificar sin adivinar la intención de nadie:

  · RP01 · borrar una copia EXACTA de un visual en la misma página. Exacta
    quiere decir mismo tipo, campos, filtros de visual y título: si algo de
    eso difiere, no es una copia y no se toca.
  · RP02 · mover un visual que quedó tapado por otro, para que se pueda
    usar. No se borra nada: se corre a un lugar libre del lienzo.

Lo demás (consolidar páginas, sacar filtros repetidos, achicar páginas
densas) cambia lo que el usuario ve y lo decide una persona.

`SecurityBindings`
------------------
Es un blob DPAPI atado a la máquina y al usuario que guardó el archivo, no
una firma del reporte. Al reempaquetar se descarta: Power BI vuelve a pedir
las credenciales del origen la primera vez y sigue de largo. Dejarlo sería
peor — quedaría un binario que ya no corresponde a este archivo.
"""
from __future__ import annotations

import copy
import re
import json
import shutil
import zipfile
from pathlib import Path

from .i18n import IDIOMA_DEFECTO, t as traducir
from . import reporte

# Partes que no se copian al archivo nuevo.
#   SecurityBindings: ver arriba.
#   Report/Layout:    se reescribe con las correcciones.
NO_COPIAR = {"SecurityBindings", "Report/Layout"}

# Margen que se deja alrededor de un visual al buscarle lugar libre.
AIRE = 8


# Cualquier `<Override>` de SecurityBindings, sin depender de cómo esté
# escrito: el orden de los atributos y los espacios cambian entre versiones,
# y una comparación de cadena literal falla en silencio.
RE_SECURITY = re.compile(r"<Override\b[^>]*SecurityBindings[^>]*/?>",
                         re.IGNORECASE)


def _u16(texto: str) -> bytes:
    """`Report/Layout` viaja en UTF-16-LE sin BOM, como lo escribe Power BI."""
    return texto.encode("utf-16-le")


def _leer_parte(crudo: bytes) -> str:
    """Decodifica una parte del zip, sea UTF-8 o UTF-16-LE sin BOM.

    Se decide por el byte nulo: un texto UTF-8 no tiene ninguno, y un
    UTF-16-LE con contenido ASCII tiene uno cada dos. Dentro de un mismo
    `.pbix` conviven las dos codificaciones.
    """
    if crudo[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return crudo.decode("utf-16")
    if crudo[:3] == b"\xef\xbb\xbf":
        return crudo[3:].decode("utf-8")
    if b"\x00" in crudo[:512]:
        return crudo.decode("utf-16-le")
    return crudo.decode("utf-8")


def _rect(v: dict) -> tuple[float, float, float, float]:
    return (v.get("x") or 0, v.get("y") or 0,
            v.get("width") or 0, v.get("height") or 0)


def _chocan(a: tuple, b: tuple) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (ax + aw <= bx or bx + bw <= ax
                or ay + ah <= by or by + bh <= ay)


def _lugar_libre(ocupados: list[tuple], ancho: float, alto: float,
                 lienzo_w: float, lienzo_h: float) -> tuple[float, float] | None:
    """Primer hueco donde entra un visual de `ancho`×`alto`.

    Se barre de arriba a abajo y de izquierda a derecha en pasos chicos, y se
    prueban además los bordes de lo que ya está puesto: un tablero real casi
    nunca deja huecos alineados a una grilla redonda.
    """
    candidatos_x = {0.0}
    candidatos_y = {0.0}
    for x, y, w, h in ocupados:
        candidatos_x.update({x + w + AIRE, x})
        candidatos_y.update({y + h + AIRE, y})
    for y in sorted(candidatos_y):
        for x in sorted(candidatos_x):
            if x + ancho > lienzo_w or y + alto > lienzo_h:
                continue
            cand = (x, y, ancho, alto)
            if not any(_chocan(cand, o) for o in ocupados):
                return (x, y)
    return None


def _firma(vc: dict) -> tuple:
    """Identidad de un visual, para decidir si otro es una copia exacta."""
    cfg = reporte._json(vc.get("config"))
    sv = cfg.get("singleVisual") or {}
    campos = reporte.campos_de(sv) or reporte.campos_de(
        reporte._json(vc.get("query")))
    return (sv.get("visualType") or "?", tuple(sorted(campos)),
            reporte.filtros_de(vc), reporte.titulo_de(sv))


def corregir_layout(layout: dict,
                    idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[dict]]:
    """Aplica las correcciones seguras. Devuelve (layout nuevo, cambios).

    No muta el layout que recibe: quien llama tiene que poder comparar el
    antes con el después, y un arreglo que pisa el original no deja volver.
    """
    nuevo = copy.deepcopy(layout or {})
    cambios: list[dict] = []

    for sec in nuevo.get("sections", []) or []:
        pagina = (sec.get("displayName") or "?").strip()
        lienzo_w = sec.get("width") or 1280
        lienzo_h = sec.get("height") or 720
        vcs = sec.get("visualContainers") or []

        # --- RP01: copias exactas dentro de la misma página ---------------
        vistos: dict[tuple, int] = {}
        sobreviven = []
        for vc in vcs:
            f = _firma(vc)
            # Sin campos no se puede afirmar que dos visuales sean el mismo.
            if not f[1]:
                sobreviven.append(vc)
                continue
            if f in vistos:
                cambios.append({
                    "regla": "RP01", "pagina": pagina, "tipo": f[0],
                    "que": traducir("co_borrado", idioma).format(
                        tipo=f[0], pagina=pagina)})
                continue
            vistos[f] = 1
            sobreviven.append(vc)
        sec["visualContainers"] = sobreviven
        vcs = sobreviven

        # --- RP02: visuales tapados ---------------------------------------
        # Se mueve el de ARRIBA en el orden del layout sólo si es el más
        # chico; si no, el de abajo. Mover el grande reordenaría la página
        # entera, y la idea es tocar lo mínimo. Con eje z se mide qué
        # fracción del visual de ABAJO desaparece — un botón «Volver» chico
        # con z alto sobre la esquina de un slicer NO está tapado y no se
        # toca (moverlo sería romper una decisión de diseño deliberada).
        for i in range(len(vcs)):
            for j in range(i + 1, len(vcs)):
                a, b = vcs[i], vcs[j]
                ra, rb = _rect(a), _rect(b)
                if not ra[2] or not rb[2]:
                    continue
                da = {"x": ra[0], "y": ra[1], "w": ra[2], "h": ra[3]}
                db = {"x": rb[0], "y": rb[1], "w": rb[2], "h": rb[3]}
                za, zb = a.get("z"), b.get("z")
                if za is not None and zb is not None and za != zb:
                    abajo = db if za > zb else da
                    area = abajo["w"] * abajo["h"]
                    sol = (reporte._interseccion(da, db) / area) if area else 0
                else:
                    sol = reporte._solape(da, db)
                if sol <= reporte.SOLAPE_TAPA:
                    continue
                mover = a if ra[2] * ra[3] <= rb[2] * rb[3] else b
                rm = _rect(mover)
                ocupados = [_rect(v) for v in vcs if v is not mover]
                destino = _lugar_libre(ocupados, rm[2], rm[3],
                                       lienzo_w, lienzo_h)
                tipo = _firma(mover)[0]
                if destino is None:
                    cambios.append({
                        "regla": "RP02", "pagina": pagina, "tipo": tipo,
                        "que": traducir("co_sin_lugar", idioma).format(
                            tipo=tipo, pagina=pagina)})
                    continue
                mover["x"], mover["y"] = destino
                cambios.append({
                    "regla": "RP02", "pagina": pagina, "tipo": tipo,
                    "que": traducir("co_movido", idioma).format(
                        tipo=tipo, pagina=pagina,
                        x=f"{destino[0]:.0f}", y=f"{destino[1]:.0f}")})
    return nuevo, cambios


def exportar_pbix(origen: str | Path, layout: dict,
                  destino: str | Path) -> Path:
    """Escribe un `.pbix` nuevo: mismo modelo, reporte corregido.

    El `DataModel` se copia byte a byte sin mirarlo. No hace falta entenderlo
    para conservarlo, y es lo que permite devolver un archivo que Power BI
    abre con todas las medidas y relaciones intactas.
    """
    origen, destino = Path(origen), Path(destino)
    crudo = json.dumps(layout, ensure_ascii=False, separators=(",", ":"))

    with zipfile.ZipFile(origen) as z_in:
        nombres = z_in.namelist()
        if "Report/Layout" not in nombres:
            raise ValueError("El archivo no tiene Report/Layout: no es un .pbix.")
        with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z_out:
            for info in z_in.infolist():
                if info.filename in NO_COPIAR:
                    continue
                if info.filename == "[Content_Types].xml":
                    # La declaración de SecurityBindings tiene que irse con la
                    # parte: un Content_Types que anuncia algo que no está es
                    # de lo que Power BI rechaza como archivo corrupto.
                    #
                    # Y se devuelve en la MISMA codificación en que vino. En
                    # los .pbix reales esta parte es UTF-8 aunque
                    # `Report/Layout` sea UTF-16: asumir una sola para todo el
                    # paquete reventaba al abrirlo.
                    crudo_ct = z_in.read(info.filename)
                    era_16 = b"\x00" in crudo_ct[:512]
                    xml = _leer_parte(crudo_ct)
                    xml = RE_SECURITY.sub("", xml)
                    z_out.writestr(info,
                                   _u16(xml) if era_16 else xml.encode("utf-8"))
                    continue
                z_out.writestr(info, z_in.read(info.filename))
            # El layout va al final, con el mismo nombre de parte.
            z_out.writestr("Report/Layout", _u16(crudo))
    return destino


def corregir_archivo(origen: str | Path, destino: str | Path,
                     idioma: str = IDIOMA_DEFECTO) -> dict:
    """Lee un `.pbix`, aplica lo seguro y escribe el corregido."""
    from . import modelo as modmod

    origen, destino = Path(origen), Path(destino)
    cargado = modmod.cargar(origen)
    layout = cargado.get("layout")
    if not layout:
        shutil.copy2(origen, destino)
        return {"ok": False, "cambios": [],
                "error": traducir("co_sin_layout", idioma)}

    antes = reporte.analizar(layout)
    nuevo, cambios = corregir_layout(layout, idioma)
    despues = reporte.analizar(nuevo)
    exportar_pbix(origen, nuevo, destino)
    return {"ok": True, "cambios": cambios, "destino": str(destino),
            "hallazgos_antes": len(antes), "hallazgos_despues": len(despues)}
