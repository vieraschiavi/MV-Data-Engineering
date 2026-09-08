# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · Por qué se movieron los números.

El resto del programa audita la ESTRUCTURA: si el DAX está bien, si el
modelo cierra, si el tablero se lee. Este módulo hace la otra pregunta, la
que hace un analista senior cuando le muestran el informe: **por qué
crecimos menos que el mercado**.

Y la responde con aritmética exacta, no con adjetivos. La descomposición
que usa es la clásica de participación de mercado, y su gracia es que es
una **identidad**: las partes suman exactamente el total, así que se puede
verificar.

    r − g  =  Σᵢ wᵢ (rᵢ − gᵢ)   +   Σᵢ (wᵢ − mᵢ) gᵢ
              ─────────────────       ─────────────────
                 DESEMPEÑO                 MEZCLA

donde `r` es cuánto creció lo propio, `g` cuánto creció el mercado, `wᵢ` el
peso del segmento *i* en lo propio al principio, `mᵢ` su peso en el
mercado, `rᵢ` y `gᵢ` los crecimientos de ese segmento.

Las dos mitades dicen cosas distintas, y confundirlas es el error habitual:

  · **Desempeño** es perder donde competís. Vendiste menos que el mercado
    EN LOS MISMOS segmentos. Se arregla vendiendo mejor ahí.
  · **Mezcla** es estar parado en el lugar equivocado. Cada segmento tuyo
    puede haber crecido igual que el mercado, y aun así perdés share
    porque estás pesado en los que crecen poco. Se arregla cambiando el
    portafolio, no el esfuerzo comercial.

Un informe que dice «bajamos 0,9 pp» y no separa esas dos cosas manda a
apretar a la fuerza de ventas cuando quizá el problema es el portafolio.

Y sobre el valor contra el volumen: si crecés en unidades más que en
dinero, bajaste el precio. Eso también se separa, con otra identidad
exacta (`ΔValor = ΔUnidades × P₀ + Precio₁ × ΔUnidades` reordenado como
efecto volumen + efecto precio).

**Nada de esto se estima.** Todo sale de las filas que el archivo trae
adentro. Si el archivo no tiene datos, o no tiene con qué separar lo
propio del mercado, este módulo devuelve `None` y el informe lo dice: una
explicación inventada sobre por qué cae el share es peor que ninguna.
"""
from __future__ import annotations

import base64
import json
import re
import zlib

from .catalogo import Catalogo, _norm
from .i18n import IDIOMA_DEFECTO, t as traducir

# Marcas de la columna que dice QUIÉN vende. Se reusa el criterio del
# módulo de períodos: fuerte le gana a débil.
from .periodos import _CORPORACION_DEBIL, _CORPORACION_FUERTE

# Nombres de columna de valor y de volumen.
_VALOR = ("venta", "ventas", "importe", "monto", "facturacion", "revenue",
          "sales", "receita", "usd", "valor", "ingreso", "neto")
_VOLUMEN = ("unidad", "unidades", "units", "cantidad", "volumen", "volume",
            "qty", "quantidade", "cajas", "pack")

# Cuántos miembros se muestran por dimensión. Más de esto no se lee, y los
# de abajo aportan decimales.
MAX_MIEMBROS = 10

# Cardinalidad máxima de una columna para servir como dimensión de
# análisis. Descomponer por una columna con 800 valores distintos no
# explica nada: da 800 contribuciones de 0,001 pp.
MAX_CARDINALIDAD = 40


def _es(nombre: str, marcas) -> bool:
    n = _norm(nombre)
    return any(p in n for p in marcas)


def _num(valor) -> float | None:
    """Un número, o `None` si esa celda no lo es. Nunca 0 por las dudas:
    tratar un dato ilegible como cero mueve todos los totales."""
    if valor is None:
        return None
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return float(valor)
    texto = str(valor).strip().replace(" ", "")
    if not texto:
        return None
    if "," in texto and "." not in texto:
        texto = texto.replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


# ==========================================================================
# De dónde salen las filas
# ==========================================================================
def filas_embebidas(expresion) -> list[list] | None:
    """Las filas que viajan adentro de una consulta M, o `None`."""
    texto = "\n".join(expresion) if isinstance(expresion, list) \
        else str(expresion or "")
    marca = "Binary.FromText ("
    if marca not in texto or "Binary.Decompress" not in texto:
        return None
    try:
        trozo = texto[texto.index(marca) + len(marca):
                      texto.index(", BinaryEncoding")]
        b64 = "".join(re.findall(r'"([^"]*)"', trozo))
        return json.loads(zlib.decompress(base64.b64decode(b64), -15)
                          .decode("utf-8"))
    except Exception:      # noqa: BLE001 — sin datos se sigue sin datos
        return None


def tablas_con_datos(cargado: dict) -> dict[str, dict]:
    """`{nombre: {"columnas": [...], "filas": [[...]]}}` con TODO lo que se
    pueda leer: la materia prima de un dataset crudo y, si no, las filas
    empotradas dentro de las consultas del modelo."""
    salida: dict[str, dict] = {}
    for t in (cargado.get("dataset_meta") or {}).get("tablas", []):
        if t.get("datos"):
            salida[t["nombre"]] = {
                "columnas": [c["nombre"] for c in t["columnas"]],
                "filas": t["datos"]}
    modelo = cargado.get("modelo") or {}
    for t in modelo.get("model", {}).get("tables", []):
        if t.get("name") in salida:
            continue
        for p in t.get("partitions", []):
            filas = filas_embebidas(p.get("source", {}).get("expression"))
            if filas:
                salida[t["name"]] = {
                    "columnas": [c["name"] for c in t.get("columns", [])],
                    "filas": filas}
                break
    return salida


# ==========================================================================
# Qué es qué en este modelo
# ==========================================================================
def _columna(columnas: list[str], marcas) -> str | None:
    for c in columnas:
        if _es(c, marcas):
            return c
    return None


def _col_fecha(datos: dict) -> str | None:
    """La columna que tiene fechas de verdad, mirando los valores."""
    for i, c in enumerate(datos["columnas"]):
        muestra = [f[i] for f in datos["filas"][:50] if i < len(f)]
        utiles = [str(v).strip() for v in muestra if str(v).strip()]
        if utiles and all(re.match(r"^\d{4}-\d{2}", v) for v in utiles):
            return c
    return None


def _propia(valores: list[str], cat: Catalogo) -> str | None:
    """Cuál de las corporaciones es la del informe.

    La que el modelo NOMBRA en sus medidas: si alguien escribió «Ventas
    Adium USD», ya dijo de qué lado está parado. Sin esa pista no se
    adivina por tamaño —la más grande puede ser la competencia— y se
    devuelve `None`.
    """
    elegida = cat.anotaciones.get("MVDAX_EmpresaPropia", "")
    if elegida:
        real = next((v for v in valores if _norm(v) == _norm(elegida)), None)
        if real is not None:
            return real
    nombres = " ".join(_norm(m["nombre"]) for m in cat.medidas())
    candidatas = [v for v in valores if _norm(v) and _norm(v) in nombres]
    if len(set(candidatas)) == 1:
        return candidatas[0]
    return None


def _contexto(cargado: dict) -> dict | None:
    """La tabla de hechos que sirve para este análisis y qué hay en ella."""
    modelo = cargado.get("modelo") or {}
    cat = Catalogo.desde_modelo(modelo) if modelo.get("model") else None
    if cat is None:
        return None
    datos = tablas_con_datos(cargado)
    mejor = None
    for nombre, d in datos.items():
        cols = d["columnas"]
        fecha = _col_fecha(d)
        valor = _columna(cols, _VALOR)
        if not fecha or not valor:
            continue
        corp = _columna(cols, _CORPORACION_FUERTE) or \
            _columna(cols, _CORPORACION_DEBIL)
        if not corp:
            continue
        # Entre varias, la que más filas tenga: es la de hechos.
        if mejor is None or len(d["filas"]) > len(mejor["datos"]["filas"]):
            mejor = {"tabla": nombre, "datos": d, "fecha": fecha,
                     "valor": valor, "corporacion": corp,
                     "volumen": _columna(cols, _VOLUMEN)}
    if mejor is None:
        return None
    mejor["cat"] = cat
    mejor["todas"] = datos
    return mejor


def _dimensiones(ctx: dict) -> dict[str, dict[str, str]]:
    """Por qué se puede descomponer: cada dimensión y, por cada clave del
    hecho, a qué miembro pertenece.

    Sale de las columnas del propio hecho y de las tablas relacionadas —
    un `ProductoID` no explica nada, pero el área terapéutica de ese
    producto sí.

    Quedan afuera dos cosas que parecen dimensiones y no lo son:

      · **El calendario.** El tiempo es el EJE de esta comparación, no una
        explicación de ella. «Perdiste share por culpa de marzo» no es una
        causa: marzo es cuándo, no por qué. Y un `DiaSemanaNumero` sobre
        datos mensuales directamente no significa nada.
      · **La propia columna de corporación.** Descomponer el share por
        quién vende es circular: da la respuesta metida en la pregunta.
    """
    cat, datos = ctx["cat"], ctx["datos"]
    idx = {c: i for i, c in enumerate(datos["columnas"])}
    dims: dict[str, dict[str, str]] = {}
    cal = cat.tabla_fechas()
    tabla_cal = _norm(cal["nombre"]) if cal else None

    # 1 · Columnas de texto del propio hecho.
    for c, i in idx.items():
        if c in (ctx["fecha"], ctx["valor"], ctx["volumen"],
                 ctx["corporacion"]):
            continue
        valores = [str(f[i]) for f in datos["filas"] if i < len(f)]
        distintos = set(valores)
        if 2 <= len(distintos) <= MAX_CARDINALIDAD:
            dims[c] = {v: v for v in distintos}

    # 2 · Columnas de las dimensiones relacionadas, mapeadas por la clave.
    for r in cat.relaciones:
        if _norm(r["desde_tabla"]) != _norm(ctx["tabla"]):
            continue
        if tabla_cal and _norm(r["hacia_tabla"]) == tabla_cal:
            continue                      # el tiempo es el eje, no la causa
        dim = ctx["todas"].get(r["hacia_tabla"])
        if not dim or r["desde_col"] not in idx:
            continue
        dcols = {c: i for i, c in enumerate(dim["columnas"])}
        if r["hacia_col"] not in dcols:
            continue
        k = dcols[r["hacia_col"]]
        for c, i in dcols.items():
            if c == r["hacia_col"]:
                continue
            if _es(c, _CORPORACION_FUERTE) or _es(c, _CORPORACION_DEBIL):
                continue                  # circular: es el numerador mismo
            mapa = {str(f[k]): str(f[i]) for f in dim["filas"]
                    if k < len(f) and i < len(f)}
            distintos = set(mapa.values())
            if 2 <= len(distintos) <= MAX_CARDINALIDAD:
                dims[f"{r['hacia_tabla']}[{c}]"] = mapa
    return dims


# ==========================================================================
# La descomposición
# ==========================================================================
def _periodos(fechas: list[str]) -> tuple[str, str, list[str]] | None:
    """Los dos períodos comparables: el último año con datos contra el
    anterior, RECORTADO a los meses que los dos tienen.

    Comparar un 2026 que llega a junio contra un 2025 completo da una
    caída del 47 % que no existe. El recorte no es un ajuste: es la única
    comparación que significa algo.
    """
    meses = sorted({f[:7] for f in fechas if len(f) >= 7})
    if not meses:
        return None
    años = sorted({m[:4] for m in meses})
    if len(años) < 2:
        return None
    actual, previo = años[-1], años[-2]
    comunes = sorted({m[5:7] for m in meses if m[:4] == actual}
                     & {m[5:7] for m in meses if m[:4] == previo})
    if not comunes:
        return None
    return actual, previo, comunes


def _sumar(ctx: dict, mapa: dict[str, str] | None,
           col_clave: str | None) -> dict:
    """Suma valor y volumen por (año, propio/mercado, miembro)."""
    datos = ctx["datos"]
    idx = {c: i for i, c in enumerate(datos["columnas"])}
    i_f, i_v = idx[ctx["fecha"]], idx[ctx["valor"]]
    i_c = idx[ctx["corporacion"]]
    i_u = idx.get(ctx["volumen"]) if ctx["volumen"] else None
    i_k = idx.get(col_clave) if col_clave else None
    acum: dict = {}
    for f in datos["filas"]:
        if max(i_f, i_v, i_c) >= len(f):
            continue
        fecha = str(f[i_f])
        if len(fecha) < 7 or fecha[5:7] not in ctx["meses"]:
            continue
        año = fecha[:4]
        if año not in (ctx["actual"], ctx["previo"]):
            continue
        valor = _num(f[i_v])
        if valor is None:
            continue
        unid = _num(f[i_u]) if i_u is not None and i_u < len(f) else None
        miembro = "—"
        if mapa is not None:
            crudo = str(f[i_k]) if i_k is not None and i_k < len(f) else ""
            miembro = mapa.get(crudo, crudo or "—")
        propio = str(f[i_c]) == ctx["propia"]
        clave = (año, propio, miembro)
        a = acum.setdefault(clave, [0.0, 0.0])
        a[0] += valor
        a[1] += unid or 0.0
    return acum


def _descomponer(ctx: dict, nombre: str, mapa: dict[str, str],
                 col_clave: str | None) -> dict | None:
    """La identidad de arriba, calculada para una dimensión."""
    acum = _sumar(ctx, mapa, col_clave)
    miembros = sorted({k[2] for k in acum})
    a, p = ctx["actual"], ctx["previo"]

    def v(año, propio, m):
        return acum.get((año, propio, m), [0.0, 0.0])[0]

    o0 = sum(v(p, True, m) for m in miembros)
    o1 = sum(v(a, True, m) for m in miembros)
    m0 = sum(v(p, True, m) + v(p, False, m) for m in miembros)
    m1 = sum(v(a, True, m) + v(a, False, m) for m in miembros)
    if not o0 or not m0 or not m1:
        return None

    r, g = o1 / o0 - 1, m1 / m0 - 1
    desempeno = mezcla = 0.0
    detalle = []
    for mi in miembros:
        oi0, oi1 = v(p, True, mi), v(a, True, mi)
        mi0 = oi0 + v(p, False, mi)
        mi1 = oi1 + v(a, False, mi)
        if not mi0:
            continue
        w = oi0 / o0                      # peso del segmento en lo propio
        cuota = mi0 / m0                  # peso del segmento en el mercado
        ri = (oi1 / oi0 - 1) if oi0 else 0.0
        gi = mi1 / mi0 - 1
        d = w * (ri - gi)
        z = (w - cuota) * gi
        desempeno += d
        mezcla += z
        detalle.append({
            "miembro": mi, "peso": w, "peso_mercado": cuota,
            "crec_propio": ri, "crec_mercado": gi,
            "desempeno": d, "mezcla": z, "total": d + z,
            "valor_propio": oi1, "valor_mercado": mi1,
            "share": (oi1 / mi1) if mi1 else 0.0,
            "share_previo": (oi0 / mi0) if mi0 else 0.0})
    detalle.sort(key=lambda x: x["total"])
    # ¿Compartimos segmento con la competencia en este corte? Si en cada
    # miembro estamos solos nosotros o solo ellos, «desempeño» da cero por
    # construcción y toda la explicación es mezcla. Hay que decirlo: un
    # «desempeño 0,00» presentado como hallazgo sería engañoso.
    compite = any(0.0 < (m["valor_propio"] / m["valor_mercado"]) < 0.999
                  for m in detalle if m["valor_mercado"])
    return {
        "dimension": nombre, "miembros": detalle, "compite": compite,
        "crec_propio": r, "crec_mercado": g, "brecha": r - g,
        "desempeno": desempeno, "mezcla": mezcla,
        # La identidad tiene que cerrar. Si no cierra, algo está mal en
        # los datos y hay que decirlo, no publicarlo igual.
        "residuo": (r - g) - (desempeno + mezcla)}


def explicar(cargado: dict, idioma: str = IDIOMA_DEFECTO) -> dict | None:
    """Por qué lo propio creció distinto que el mercado.

    Devuelve `None` cuando el archivo no da para responderlo: sin filas,
    sin fechas de dos años comparables, o sin una columna que separe lo
    propio de la competencia. Ahí el informe lo dice — inventar una
    explicación sobre por qué cae el share es peor que no darla.
    """
    ctx = _contexto(cargado)
    if ctx is None:
        return None
    datos = ctx["datos"]
    idx = {c: i for i, c in enumerate(datos["columnas"])}
    fechas = [str(f[idx[ctx["fecha"]]]) for f in datos["filas"]
              if idx[ctx["fecha"]] < len(f)]
    per = _periodos(fechas)
    if per is None:
        return None
    ctx["actual"], ctx["previo"], ctx["meses"] = per

    corps = sorted({str(f[idx[ctx["corporacion"]]]) for f in datos["filas"]
                    if idx[ctx["corporacion"]] < len(f)})
    if len(corps) < 2:
        return None
    propia = _propia(corps, ctx["cat"])
    if propia is None:
        return {"sin_propia": True, "corporaciones": corps,
                "columna": ctx["corporacion"]}
    ctx["propia"] = propia

    total = _descomponer(ctx, "", {"—": "—"}, None)
    if total is None:
        return None

    # Valor y volumen: si crecés más en unidades que en dinero, bajaste el
    # precio. Es la explicación de abajo de todo.
    acum = _sumar(ctx, None, None)
    a, p = ctx["actual"], ctx["previo"]
    precio = None
    if ctx["volumen"]:
        v0, u0 = acum.get((p, True, "—"), [0.0, 0.0])
        v1, u1 = acum.get((a, True, "—"), [0.0, 0.0])
        if u0 and u1:
            p0, p1 = v0 / u0, v1 / u1
            ef_vol = (u1 - u0) * p0
            ef_pre = (p1 - p0) * u1
            precio = {"precio_previo": p0, "precio_actual": p1,
                      "var_precio": p1 / p0 - 1 if p0 else 0.0,
                      "unidades_previo": u0, "unidades_actual": u1,
                      "var_unidades": u1 / u0 - 1,
                      "efecto_volumen": ef_vol, "efecto_precio": ef_pre,
                      "delta_valor": v1 - v0,
                      "residuo": (v1 - v0) - (ef_vol + ef_pre)}

    dims = _dimensiones(ctx)
    por_dim = []
    for nombre, mapa in dims.items():
        col = nombre if "[" not in nombre else None
        if col is None:
            # Dimensión relacionada: la clave está en el hecho.
            rel = next((r for r in ctx["cat"].relaciones
                        if _norm(r["desde_tabla"]) == _norm(ctx["tabla"])
                        and nombre.startswith(f"{r['hacia_tabla']}[")), None)
            if rel is None:
                continue
            col = rel["desde_col"]
        d = _descomponer(ctx, nombre, mapa, col)
        if d and len(d["miembros"]) > 1:
            por_dim.append(d)
    # Fuera las que dicen exactamente lo mismo. En un catálogo donde cada
    # producto tiene su molécula y su nombre propio, «por producto», «por
    # molécula» y «por código» dan las tres la MISMA descomposición: tres
    # copias del mismo gráfico no explican tres veces más.
    vistas: set[tuple] = set()
    unicas = []
    for d in por_dim:
        huella = tuple(sorted(round(m["total"], 9) for m in d["miembros"]))
        if huella in vistas:
            continue
        vistas.add(huella)
        unicas.append(d)

    # Y el orden: primero las que miden COMPETENCIA de verdad. Una
    # dimensión donde cada miembro pertenece a una sola corporación —cada
    # producto es de uno solo— tiene desempeño CERO por construcción: ahí
    # no competimos cara a cara, y lo único que puede medir es mezcla.
    # Sirve, pero explica menos que un corte donde estamos los dos.
    def peso(d):
        return (0 if d["compite"] else 1,
                -sum(abs(m["total"]) for m in d["miembros"]))
    unicas.sort(key=peso)
    por_dim = unicas

    o0 = sum(x[0] for k, x in acum.items() if k[0] == p and k[1])
    o1 = sum(x[0] for k, x in acum.items() if k[0] == a and k[1])
    m0 = sum(x[0] for k, x in acum.items() if k[0] == p)
    m1 = sum(x[0] for k, x in acum.items() if k[0] == a)
    return {
        "tabla": ctx["tabla"], "columna_corporacion": ctx["corporacion"],
        "propia": propia, "competidores": [c for c in corps if c != propia],
        "actual": a, "previo": p, "meses": len(ctx["meses"]),
        "columna_valor": ctx["valor"], "columna_volumen": ctx["volumen"],
        "propio_previo": o0, "propio_actual": o1,
        "mercado_previo": m0, "mercado_actual": m1,
        "share_previo": o0 / m0 if m0 else 0.0,
        "share_actual": o1 / m1 if m1 else 0.0,
        "delta_pp": ((o1 / m1 if m1 else 0) - (o0 / m0 if m0 else 0)) * 100,
        "crec_propio": total["crec_propio"],
        "crec_mercado": total["crec_mercado"],
        "brecha": total["brecha"],
        "precio": precio,
        "dimensiones": por_dim[:4],
        "idioma": idioma,
    }


# ==========================================================================
# Las oportunidades — qué haría con esto un analista
# ==========================================================================
def oportunidades(exp: dict, idioma: str = IDIOMA_DEFECTO) -> list[dict]:
    """Lo accionable que sale de la descomposición, ordenado por tamaño.

    Cada una lleva CUÁNTO vale en puntos porcentuales de share: sin la
    cifra al lado, una recomendación es una opinión.
    """
    if not exp or exp.get("sin_propia"):
        return []
    salida: list[dict] = []
    pp = exp["delta_pp"]

    # 1 · Precio: crecer en unidades y no en dinero es haber bajado precio.
    pr = exp.get("precio")
    if pr and abs(pr["var_precio"]) > 0.005:
        salida.append({
            "peso": abs(pr["efecto_precio"]),
            "tipo": "precio",
            "titulo": traducir("an_op_precio_t", idioma),
            "texto": traducir("an_op_precio", idioma).format(
                var=pr["var_precio"] * 100,
                unidades=pr["var_unidades"] * 100,
                efecto=pr["efecto_precio"])})

    for d in exp["dimensiones"][:2]:
        peores = [m for m in d["miembros"] if m["total"] < 0][:3]
        mejores = [m for m in reversed(d["miembros"])
                   if m["total"] > 0][:2]
        for m in peores:
            # Perder DONDE competís no es lo mismo que estar mal parado.
            clave = ("an_op_desempeno" if abs(m["desempeno"]) >= abs(m["mezcla"])
                     else "an_op_mezcla")
            salida.append({
                "peso": abs(m["total"]) * 100,
                "tipo": "desempeno" if clave.endswith("desempeno") else "mezcla",
                "titulo": f'{d["dimension"] or "—"} · {m["miembro"]}',
                "texto": traducir(clave, idioma).format(
                    miembro=m["miembro"], dim=d["dimension"],
                    propio=m["crec_propio"] * 100,
                    mercado=m["crec_mercado"] * 100,
                    pp=m["total"] * 100, peso=m["peso"] * 100)})
        for m in mejores:
            salida.append({
                "peso": abs(m["total"]) * 100,
                "tipo": "fuerte",
                "titulo": f'{d["dimension"] or "—"} · {m["miembro"]}',
                "texto": traducir("an_op_fuerte", idioma).format(
                    miembro=m["miembro"], propio=m["crec_propio"] * 100,
                    mercado=m["crec_mercado"] * 100, pp=m["total"] * 100)})
    salida.sort(key=lambda x: -x["peso"])
    del pp
    return salida
