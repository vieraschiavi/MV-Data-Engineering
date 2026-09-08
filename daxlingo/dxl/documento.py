# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · Un documento, tres formatos.

**Por qué existe.** Lo que este programa hace con un dataset hay que poder
mostrárselo a tres personas distintas: al que va a mantener el modelo, al
que firma, y al que lo audita seis meses después. Los tres piden el mismo
contenido en formatos distintos — la pantalla, el adjunto de un mail, el
PDF que se archiva.

**Cómo.** Se arma UNA vez una lista de bloques (`Doc`) y de ahí salen los
tres. Escribir el HTML y después «convertirlo» a Word sería garantizar que
diverjan: el día que alguien toque una tabla en el HTML, el Word queda
viejo y nadie se entera.

**Sin dependencias, a propósito.** `requirements.txt` dice que el motor
corre con la stdlib, y eso no es una preferencia estética: es lo que
permite que el `.exe` empaquetado pese lo que pesa y que el motor se pueda
testear sin instalar nada. Así que el `.docx` se escribe como lo que es
—un zip con XML de OOXML adentro— y el `.pdf` como lo que es —texto con
un índice de objetos al final—. Ninguno de los dos es un formato mágico
que necesite una librería; necesitan que uno los respete.

Lo que este módulo NO hace, y conviene decirlo: tipografía fina. El PDF
usa Helvetica de las 14 fuentes base (sin incrustar nada) y parte las
líneas midiendo con la tabla de anchos estándar. Alcanza de sobra para un
informe de texto y tablas; no es una herramienta de maquetación.
"""
from __future__ import annotations

import zipfile
from datetime import datetime, timezone
from html import escape as _esc
from io import BytesIO

# ==========================================================================
# El documento: una lista de bloques y nada más
# ==========================================================================
# ("h1"|"h2"|"h3", texto)
# ("p", texto)
# ("nota", clase, titulo, texto)      clase: info | ok | warn | dang
# ("lista", [texto, ...])
# ("tabla", [encabezados], [[celda, ...], ...])
# ("codigo", texto)
# ("kv", [(clave, valor), ...])
# ("salto",)                          corte de página en Word y PDF
Doc = list[tuple]

_CLASES = ("info", "ok", "warn", "dang")


def ahora() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# ==========================================================================
# HTML
# ==========================================================================
_CSS = """
:root{--navy:#12203c;--navy2:#1f4e79;--green:#7dc242;--amber:#f2b441;
--red:#d64550;--line:#dfe4ee;--mut:#5a6a85;--card:#fff}
*{box-sizing:border-box}
body{margin:0;background:#f5f7fb;color:var(--navy);
font:15px/1.62 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
header{background:var(--navy);color:#fff;padding:26px 20px}
header .in{max-width:1080px;margin:0 auto}
header h1{margin:0 0 4px;font-size:24px}
header p{margin:0;opacity:.82;font-size:14px}
.wrap{max-width:1080px;margin:0 auto;padding:24px 20px 80px}
section{background:var(--card);border:1px solid var(--line);border-radius:14px;
padding:22px 24px;margin-bottom:18px}
h2{margin:0 0 10px;font-size:20px;color:var(--navy);display:flex;
align-items:center;gap:11px}
h2 .n{background:var(--navy2);color:#fff;min-width:31px;height:31px;padding:0 7px;
border-radius:9px;display:inline-flex;align-items:center;justify-content:center;
font-size:14px;flex:none}
h3{margin:20px 0 8px;font-size:15.6px;color:var(--navy2);
border-bottom:2px solid #eef3fc;padding-bottom:4px}
p{margin:0 0 10px}
table{width:100%;border-collapse:collapse;font-size:13.6px;margin:10px 0 14px}
th{background:var(--navy);color:#fff;text-align:left;padding:9px 11px;
font-weight:600;font-size:12.8px}
td{padding:8px 11px;border-bottom:1px solid var(--line);vertical-align:top}
tr:nth-child(even) td{background:#fafbfe}
ul{margin:6px 0 12px;padding-left:22px}
li{margin:3px 0}
pre{background:#0f1b31;color:#e3ecfa;padding:13px 15px;border-radius:10px;
overflow-x:auto;font-size:12.9px;margin:0 0 12px;border-left:4px solid var(--green)}
.box{padding:12px 15px;border-radius:10px;margin:12px 0;font-size:14.2px;
border-left:4px solid}
.box b{display:block;margin-bottom:2px}
.info{background:#eef3fc;border-color:var(--navy2)}
.ok{background:#f2f8e9;border-color:var(--green)}
.warn{background:#fdf6e6;border-color:var(--amber)}
.dang{background:#fdecea;border-color:var(--red)}
dl.kv{display:grid;grid-template-columns:minmax(140px,auto) 1fr;gap:5px 16px;
margin:8px 0 14px;font-size:14px}
dl.kv dt{color:var(--mut)}
dl.kv dd{margin:0;font-weight:600}
footer{max-width:1080px;margin:0 auto;padding:0 20px 40px;
color:var(--mut);font-size:12.6px}
@media print{
  body{background:#fff}
  section{break-inside:avoid;border:none;padding:0 0 14px;border-radius:0}
  header{background:#fff;color:var(--navy);padding:0 0 16px}
  .salto{break-before:page}
}
"""


def a_html(doc: Doc, titulo: str, subtitulo: str = "",
           pie: str = "") -> str:
    """El documento como una página autocontenida — sin red, sin CDN."""
    partes: list[str] = []
    abierta = False
    for b in doc:
        tipo = b[0]
        if tipo == "h1":
            if abierta:
                partes.append("</section>")
            partes.append(f'<section><h2>{_esc(str(b[1]))}</h2>')
            abierta = True
        elif tipo == "h2":
            if abierta:
                partes.append("</section>")
            n = str(b[2]) if len(b) > 2 else ""
            marca = f'<span class="n">{_esc(n)}</span>' if n else ""
            partes.append(f'<section><h2>{marca}{_esc(str(b[1]))}</h2>')
            abierta = True
        elif tipo == "h3":
            partes.append(f"<h3>{_esc(str(b[1]))}</h3>")
        elif tipo == "p":
            partes.append(f"<p>{_esc(str(b[1]))}</p>")
        elif tipo == "nota":
            clase = b[1] if b[1] in _CLASES else "info"
            partes.append(f'<div class="box {clase}"><b>{_esc(str(b[2]))}</b>'
                          f"{_esc(str(b[3]))}</div>")
        elif tipo == "lista":
            filas = "".join(f"<li>{_esc(str(x))}</li>" for x in b[1])
            partes.append(f"<ul>{filas}</ul>")
        elif tipo == "tabla":
            th = "".join(f"<th>{_esc(str(h))}</th>" for h in b[1])
            cuerpo = "".join(
                "<tr>" + "".join(f"<td>{_esc(str(c))}</td>" for c in fila)
                + "</tr>" for fila in b[2])
            partes.append(f"<table><thead><tr>{th}</tr></thead>"
                          f"<tbody>{cuerpo}</tbody></table>")
        elif tipo == "codigo":
            partes.append(f"<pre>{_esc(str(b[1]))}</pre>")
        elif tipo == "kv":
            filas = "".join(f"<dt>{_esc(str(k))}</dt><dd>{_esc(str(v))}</dd>"
                            for k, v in b[1])
            partes.append(f'<dl class="kv">{filas}</dl>')
        elif tipo == "salto":
            partes.append('<div class="salto"></div>')
    if abierta:
        partes.append("</section>")
    return (
        '<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{_esc(titulo)}</title><style>{_CSS}</style></head><body>"
        f'<header><div class="in"><h1>{_esc(titulo)}</h1>'
        f"<p>{_esc(subtitulo)}</p></div></header>"
        f'<div class="wrap">{"".join(partes)}</div>'
        f"<footer>{_esc(pie)}</footer></body></html>")


# ==========================================================================
# Word (.docx) — OOXML a mano
# ==========================================================================
_CT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""

_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

_DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

_W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def _estilo(ident: str, nombre: str, tam: int, negrita: bool,
            color: str, antes: int = 0, defecto: bool = False) -> str:
    b = "<w:b/>" if negrita else ""
    # Un estilo tiene que estar marcado como el predeterminado del
    # documento. Sin eso, un párrafo sin `pStyle` —el salto de página, por
    # ejemplo— no resuelve contra ningún estilo: `python-docx` devolvía
    # `None` al pedirlo, y Word cae en su propio Normal, que no es el
    # nuestro.
    marca = ' w:default="1"' if defecto else ""
    return (f'<w:style w:type="paragraph" w:styleId="{ident}"{marca}>'
            f'<w:name w:val="{nombre}"/>'
            f'<w:pPr><w:spacing w:before="{antes}" w:after="120"/></w:pPr>'
            f'<w:rPr>{b}<w:color w:val="{color}"/>'
            f'<w:sz w:val="{tam * 2}"/></w:rPr></w:style>')


_ESTILOS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    f"<w:styles {_W}>"
    '<w:docDefaults><w:rPrDefault><w:rPr>'
    '<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="21"/>'
    "</w:rPr></w:rPrDefault></w:docDefaults>"
    + _estilo("Titulo", "Title", 20, True, "12203C")
    + _estilo("Encab1", "heading 1", 15, True, "1F4E79", 240)
    + _estilo("Encab2", "heading 2", 12, True, "1F4E79", 200)
    + _estilo("Normal", "Normal", 10, False, "12203C", defecto=True)
    + _estilo("Codigo", "Code", 9, False, "12203C")
    + "</w:styles>")


def _xml(texto) -> str:
    return _esc(str(texto), quote=False)


def _parrafo(texto, estilo="Normal", negrita=False) -> str:
    b = "<w:b/>" if negrita else ""
    rpr = f"<w:rPr>{b}</w:rPr>" if b else ""
    return (f'<w:p><w:pPr><w:pStyle w:val="{estilo}"/></w:pPr>'
            f'<w:r>{rpr}<w:t xml:space="preserve">{_xml(texto)}</w:t>'
            "</w:r></w:p>")


def _celda(texto, encabezado=False) -> str:
    sombra = ('<w:shd w:val="clear" w:fill="12203C"/>' if encabezado else "")
    color = '<w:color w:val="FFFFFF"/>' if encabezado else ""
    b = "<w:b/>" if encabezado else ""
    return (f"<w:tc><w:tcPr>{sombra}</w:tcPr>"
            f'<w:p><w:pPr><w:pStyle w:val="Normal"/></w:pPr>'
            f"<w:r><w:rPr>{b}{color}</w:rPr>"
            f'<w:t xml:space="preserve">{_xml(texto)}</w:t></w:r></w:p></w:tc>')


# Ancho útil de una A4 con los márgenes de `sectPr`, en twips:
# 11906 de hoja menos 1134 de cada lado.
_ANCHO_TABLA = 9638


def _tabla_docx(encabezados, filas) -> str:
    borde = ('<w:tblBorders>' + "".join(
        f'<w:{x} w:val="single" w:sz="4" w:color="DFE4EE"/>'
        for x in ("top", "left", "bottom", "right", "insideH", "insideV"))
        + "</w:tblBorders>")
    # `tblGrid` NO es decorativo: el esquema de OOXML lo exige como hijo de
    # `tbl`. Sin él la tabla se escribe igual y el archivo abre, pero
    # cualquier lector que valide el esquema lo rechaza — lo encontró
    # `python-docx` al abrir el primer .docx que salió de acá.
    columnas = max(len(encabezados), 1)
    grid = ("<w:tblGrid>"
            + f'<w:gridCol w:w="{_ANCHO_TABLA // columnas}"/>' * columnas
            + "</w:tblGrid>")
    cabecera = "<w:tr>" + "".join(_celda(h, True) for h in encabezados) + "</w:tr>"
    cuerpo = "".join(
        "<w:tr>" + "".join(_celda(c) for c in fila) + "</w:tr>" for fila in filas)
    return (f'<w:tbl><w:tblPr><w:tblW w:w="5000" w:type="pct"/>{borde}'
            f"</w:tblPr>{grid}{cabecera}{cuerpo}</w:tbl>"
            + _parrafo(""))          # Word necesita un párrafo tras la tabla


def a_docx(doc: Doc, titulo: str, subtitulo: str = "") -> bytes:
    """El mismo documento como `.docx` de verdad, sin librerías."""
    cuerpo = [_parrafo(titulo, "Titulo")]
    if subtitulo:
        cuerpo.append(_parrafo(subtitulo))
    for b in doc:
        tipo = b[0]
        if tipo in ("h1", "h2"):
            n = f"{b[2]}. " if tipo == "h2" and len(b) > 2 and b[2] else ""
            cuerpo.append(_parrafo(f"{n}{b[1]}", "Encab1"))
        elif tipo == "h3":
            cuerpo.append(_parrafo(b[1], "Encab2"))
        elif tipo == "p":
            cuerpo.append(_parrafo(b[1]))
        elif tipo == "nota":
            cuerpo.append(_parrafo(f"{b[2]}: {b[3]}"))
        elif tipo == "lista":
            cuerpo.extend(_parrafo(f"• {x}") for x in b[1])
        elif tipo == "tabla":
            cuerpo.append(_tabla_docx(b[1], b[2]))
        elif tipo == "codigo":
            cuerpo.extend(_parrafo(linea, "Codigo")
                          for linea in str(b[1]).splitlines() or [""])
        elif tipo == "kv":
            cuerpo.append(_tabla_docx(["", ""], [[k, v] for k, v in b[1]]))
        elif tipo == "salto":
            cuerpo.append('<w:p><w:pPr><w:pStyle w:val="Normal"/></w:pPr>'
                          '<w:r><w:br w:type="page"/></w:r></w:p>')

    documento = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 f"<w:document {_W}><w:body>{''.join(cuerpo)}"
                 '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
                 '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" '
                 'w:left="1134"/></w:sectPr></w:body></w:document>')

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CT)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("word/_rels/document.xml.rels", _DOC_RELS)
        z.writestr("word/styles.xml", _ESTILOS)
        z.writestr("word/document.xml", documento)
    return buffer.getvalue()


# ==========================================================================
# PDF — las 14 fuentes base, sin incrustar nada
# ==========================================================================
# Anchos de Helvetica en milésimas de em, para los caracteres imprimibles
# de ASCII. Se usan para partir las líneas: sin medir, un renglón largo se
# sale de la hoja y el PDF queda ilegible justo donde más texto hay.
_ANCHO = (
    "278 278 355 556 556 889 667 191 333 333 389 584 278 333 278 278 "
    "556 556 556 556 556 556 556 556 556 556 278 278 584 584 584 556 "
    "1015 667 667 722 722 667 611 778 722 278 500 667 556 833 722 778 "
    "667 778 722 667 611 722 667 944 667 667 611 278 278 278 469 556 "
    "333 556 556 500 556 556 278 556 556 222 222 500 222 833 556 556 "
    "556 556 333 500 278 556 500 722 500 500 500 334 260 334 584")
_ANCHOS = {chr(32 + i): int(v) for i, v in enumerate(_ANCHO.split())}
_ANCHO_OTRO = 556          # acentos y demás: se sobreestima, nunca desborda

A4 = (595.28, 841.89)
_MARGEN = 56.0


def _mide(texto: str, tam: float) -> float:
    return sum(_ANCHOS.get(c, _ANCHO_OTRO) for c in texto) * tam / 1000.0


def _partir(texto: str, tam: float, ancho: float) -> list[str]:
    """Parte en renglones que entran en `ancho`, sin cortar palabras."""
    lineas: list[str] = []
    for cruda in str(texto).split("\n"):
        actual = ""
        for palabra in cruda.split(" "):
            prueba = f"{actual} {palabra}".strip()
            if actual and _mide(prueba, tam) > ancho:
                lineas.append(actual)
                actual = palabra
            else:
                actual = prueba
        lineas.append(actual)
    return lineas or [""]


def _pdf_txt(texto: str) -> bytes:
    """A WinAnsi, que es lo que entienden las fuentes base."""
    crudo = str(texto).encode("cp1252", "replace")
    return (crudo.replace(b"\\", b"\\\\")
            .replace(b"(", b"\\(").replace(b")", b"\\)"))


class _Hoja:
    """Acumula las órdenes de dibujo de una página."""

    def __init__(self):
        self.ops: list[bytes] = []


def a_pdf(doc: Doc, titulo: str, subtitulo: str = "",
          pie: str = "") -> bytes:
    """El mismo documento como PDF, con Helvetica y sin dependencias."""
    ancho, alto = A4
    util = ancho - 2 * _MARGEN
    hojas: list[_Hoja] = []
    estado = {"y": 0.0}

    def nueva():
        hojas.append(_Hoja())
        estado["y"] = alto - _MARGEN

    def sitio(alto_necesario: float):
        if estado["y"] - alto_necesario < _MARGEN + 24:
            nueva()

    def linea(texto, tam=10.0, negrita=False, sangria=0.0,
              color=(0.07, 0.13, 0.24), interlineado=1.42):
        alto_linea = tam * interlineado
        for renglon in _partir(texto, tam, util - sangria):
            sitio(alto_linea)
            fuente = "F2" if negrita else "F1"
            hojas[-1].ops.append(
                b"BT " + f"{color[0]:.2f} {color[1]:.2f} {color[2]:.2f} rg "
                .encode("ascii")
                + f"/{fuente} {tam:.1f} Tf ".encode("ascii")
                + f"1 0 0 1 {_MARGEN + sangria:.1f} {estado['y']:.1f} Tm "
                .encode("ascii")
                + b"(" + _pdf_txt(renglon) + b") Tj ET\n")
            estado["y"] -= alto_linea

    def espacio(px=6.0):
        estado["y"] -= px

    nueva()
    linea(titulo, 17.0, True, color=(0.07, 0.13, 0.24))
    if subtitulo:
        linea(subtitulo, 9.5, color=(0.35, 0.42, 0.52))
    espacio(10)

    for b in doc:
        tipo = b[0]
        if tipo in ("h1", "h2"):
            espacio(10)
            sitio(40)
            n = f"{b[2]}. " if tipo == "h2" and len(b) > 2 and b[2] else ""
            linea(f"{n}{b[1]}", 13.0, True, color=(0.12, 0.31, 0.47))
            espacio(2)
        elif tipo == "h3":
            espacio(6)
            linea(b[1], 10.8, True, color=(0.12, 0.31, 0.47))
        elif tipo == "p":
            linea(b[1])
            espacio(3)
        elif tipo == "nota":
            linea(f"{b[2]}: {b[3]}", 9.8, sangria=10)
            espacio(3)
        elif tipo == "lista":
            for x in b[1]:
                linea(f"• {x}", 9.8, sangria=10)
            espacio(3)
        elif tipo == "kv":
            for k, v in b[1]:
                linea(f"{k}: {v}", 9.8, sangria=10)
            espacio(3)
        elif tipo == "codigo":
            for renglon in str(b[1]).splitlines() or [""]:
                linea(renglon, 8.6, sangria=10, color=(0.25, 0.3, 0.4))
            espacio(4)
        elif tipo == "tabla":
            # Una tabla en PDF sin motor de layout: cada fila va como
            # «encabezado: valor» en renglones. Es feo hacer columnas a
            # mano y queda peor que esto en cuanto una celda es larga.
            linea(" | ".join(str(h) for h in b[1]), 9.4, True,
                  color=(0.12, 0.31, 0.47))
            for fila in b[2]:
                for h, c in zip(b[1], fila):
                    if str(c).strip():
                        linea(f"{h}: {c}", 9.4, sangria=10)
                espacio(3)
            espacio(4)
        elif tipo == "salto":
            nueva()

    if pie:
        espacio(10)
        linea(pie, 8.4, color=(0.35, 0.42, 0.52))

    # ---- ensamblado del archivo ----
    objetos: list[bytes] = []

    def agregar(cuerpo: bytes) -> int:
        objetos.append(cuerpo)
        return len(objetos)

    # 1 catálogo · 2 páginas · 3 y 4 fuentes · después cada hoja y su flujo
    ids_hojas = [5 + 2 * i for i in range(len(hojas))]
    agregar(b"<< /Type /Catalog /Pages 2 0 R >>")
    agregar(("<< /Type /Pages /Count %d /Kids [%s] >>" % (
        len(hojas), " ".join(f"{i} 0 R" for i in ids_hojas))).encode("ascii"))
    agregar(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
            b"/Encoding /WinAnsiEncoding >>")
    agregar(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
            b"/Encoding /WinAnsiEncoding >>")
    for i, hoja in enumerate(hojas):
        flujo = b"".join(hoja.ops)
        agregar(("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.2f %.2f] "
                 "/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> "
                 "/Contents %d 0 R >>" % (ancho, alto, 6 + 2 * i)
                 ).encode("ascii"))
        agregar(b"<< /Length %d >>\nstream\n" % len(flujo) + flujo
                + b"\nendstream")

    salida = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    posiciones = []
    for numero, cuerpo in enumerate(objetos, 1):
        posiciones.append(len(salida))
        salida += b"%d 0 obj\n" % numero + cuerpo + b"\nendobj\n"
    inicio_xref = len(salida)
    salida += b"xref\n0 %d\n" % (len(objetos) + 1)
    salida += b"0000000000 65535 f \n"
    for p in posiciones:
        salida += b"%010d 00000 n \n" % p
    salida += (b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
               % (len(objetos) + 1, inicio_xref))
    return bytes(salida)
