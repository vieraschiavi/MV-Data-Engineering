# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · La matriz completa de comparativos de período.

Un informe gerencial no pregunta «cuánto vendimos»: pregunta **cuánto
vendimos comparado con qué**. Mes contra el mismo mes del año pasado,
trimestre contra trimestre, semestre contra semestre, YTD contra YTD del
año anterior — y todo eso en valor, en unidades, y en participación de
mercado propia y de cada competidor. Este módulo genera esas medidas
enteras, validadas contra el catálogo, listas para pegar.

Tres decisiones que separan una medida que anda de una que engaña:

**El eje, no la medida.** Una sola medida «año anterior» sirve para mes,
trimestre, semestre y año, porque lo que cambia es el conjunto de fechas
del contexto, no la fórmula. Lo que se rompe es el EJE: una columna
`Trimestre` que dice `"T1"` sin el año mezcla 2025 con 2026 y deja a
`SAMEPERIODLASTYEAR` sin nada que desplazar. Por eso lo primero que hace
este módulo es agregar columnas de orden ENTERAS (`AnioMesOrden` = 202601,
`AnioTrimestreOrden` = 20261, `AnioSemestreOrden` = 20261).

**`TREATAS` sobre esa columna, y no `DATEADD`.** Restar 100 al mes, 10 al
trimestre o 10 al semestre y volver a filtrar con `TREATAS` funciona con
selecciones NO contiguas (marzo y septiembre sueltos, que es lo que hace
cualquiera con un segmentador), donde `SAMEPERIODLASTYEAR` y `DATEADD`
devuelven cualquier cosa. Y resuelve el semestre, que en DAX no tiene
función nativa: `PREVIOUSSEMESTER` no existe.

**Un share no se arrastra.** El share del año pasado NO es el share de hoy
desplazado: es numerador y denominador recalculados JUNTOS en el período
anterior. Y el denominador tiene que ignorar el filtro de corporación pero
respetar todo lo demás (período, producto, área terapéutica) — si no,
filtrar la corporación propia da 100 % de share siempre, que es el error
clásico de un informe de participación.

La variación de un share se dice en **puntos porcentuales**, no en
porcentaje: pasar de 20 % a 22 % es «+2,0 pp», no «+10 %».
"""
from __future__ import annotations

import copy
import re
import uuid as _uuid

from .catalogo import (Catalogo, TIPOS_NUMERICOS, _norm,
                       referencias_dax, validar_referencias)
from .i18n import IDIOMA_DEFECTO, t as traducir

# El formato de una variación en puntos porcentuales: con signo siempre,
# un decimal, y la unidad escrita. «+0,4 pp» se lee sin ambigüedad; «0,4 %»
# encima de un share ya expresado en % no se sabe si es el share o el salto.
FORMATO_PP = '+0.0 "pp";-0.0 "pp";0.0 "pp"'
FORMATO_PCT = "+0.0 %;-0.0 %;0.0 %"

# Los granos de comparación, en el orden en que se leen en un informe.
GRANOS = ("mes", "trimestre", "semestre", "ytd", "anio")

# Cuánto hay que restarle a la columna de orden para caer en el mismo
# período del año anterior. El mes lleva 100 porque el orden es AAAAMM;
# trimestre y semestre llevan 10 porque son AAAAT y AAAAS.
_SALTO = {"mes": 100, "trimestre": 10, "semestre": 10}

# Nombres de columna que delatan la dimensión «quién vende»: la que hay que
# sacar del denominador del share.
#
# Van en dos grupos porque no valen lo mismo. «Corporación» o «laboratorio»
# es inequívoco. «Marca» casi nunca lo es: en un catálogo de productos, la
# marca es del PRODUCTO, no de quien lo vende — y si el share se calcula
# sacando el filtro de marca mientras el usuario filtra por corporación, el
# numerador y el denominador quedan los dos restringidos a su empresa y el
# share da 100 % siempre. Que es exactamente el error que este módulo
# existe para no cometer. Las débiles solo se usan si no hay ninguna fuerte.
_CORPORACION_FUERTE = ("corporacion", "corporation", "empresa", "compania",
                       "company", "laboratorio", "competidor", "competencia",
                       "fabricante", "holding", "grupo")
_CORPORACION_DEBIL = ("marca", "brand", "proveedor", "lab")

# Nombres que delatan una medida de VALOR y una de VOLUMEN. El share se
# calcula sobre las dos porque no dicen lo mismo: ganar volumen y perder
# valor a la vez es exactamente lo que pasa cuando bajás el precio.
_VALOR = ("venta", "ventas", "importe", "monto", "facturacion", "revenue",
          "sales", "receita", "vendas", "usd", "valor", "ingreso")
_VOLUMEN = ("unidad", "unidades", "units", "cantidad", "volumen", "volume",
            "qty", "quantidade")


def _tabla_ref(tabla: str) -> str:
    return tabla if tabla.isidentifier() else f"'{tabla}'"


def _ref(tabla: str, columna: str) -> str:
    return f"{_tabla_ref(tabla)}[{columna}]"


def _es(nombre: str, marcas: tuple[str, ...]) -> bool:
    n = _norm(nombre)
    return any(p in n for p in marcas)


# ==========================================================================
# 1 · Las columnas de orden — sin esto, ningún comparativo es confiable
# ==========================================================================
_COLS = {
    "es": {"mes_num": "MesNumero", "trimestre": "Trimestre",
           "semestre": "Semestre", "anio": "Anio",
           "orden_mes": "AnioMesOrden", "orden_tri": "AnioTrimestreOrden",
           "orden_sem": "AnioSemestreOrden"},
    "en": {"mes_num": "MonthNumber", "trimestre": "Quarter",
           "semestre": "Semester", "anio": "Year",
           "orden_mes": "YearMonthOrder", "orden_tri": "YearQuarterOrder",
           "orden_sem": "YearSemesterOrder"},
    "pt": {"mes_num": "MesNumero", "trimestre": "Trimestre",
           "semestre": "Semestre", "anio": "Ano",
           "orden_mes": "AnoMesOrdem", "orden_tri": "AnoTrimestreOrdem",
           "orden_sem": "AnoSemestreOrdem"},
}


def nombres_columnas(idioma: str = IDIOMA_DEFECTO) -> dict:
    return _COLS.get(idioma, _COLS["es"])


def _col_calculada(nombre: str, expresion: str, tipo: str,
                   **extra) -> dict:
    col = {
        "type": "calculated", "name": nombre, "dataType": tipo,
        "expression": expresion, "isDataTypeInferred": True,
        "lineageTag": str(_uuid.uuid4()),
        "annotations": [{"name": "SummarizationSetBy", "value": "Automatic"}],
    }
    col.update(extra)
    return col


def _busca_col(tabla: dict, *marcas: str) -> str | None:
    for c in tabla.get("columns", []):
        if _norm(c.get("name", "")) in {_norm(m) for m in marcas}:
            return c["name"]
    return None


_TIPO_M = {"int64": "Int64.Type", "string": "type text",
           "double": "type number"}


def _envolver_m(particion: dict, columnas: list[tuple[str, str, str]],
                origen: str) -> None:
    """Agrega columnas a una consulta M SIN tener que entenderla.

    La consulta original queda ADENTRO, entre paréntesis, como el primer
    paso de una consulta nueva. En M un `let … in …` es una expresión como
    cualquier otra, así que envolverla es siempre válido — y no hace falta
    adivinar cómo se llama el último paso, ni si termina en un nombre o en
    una expresión, ni si hay un comentario al final de la línea, ni si todo
    viene en un solo renglón.

    Insertar un `Table.AddColumn` «antes del `in`», que es lo que parece
    obvio, rompía las cuatro cosas: una consulta de una sola línea no tiene
    línea anterior, una que termina en `in Table.Sort(...)` daba un nombre
    de paso con comillas adentro, y la coma que hay que agregarle a la
    línea previa se metía dentro de un comentario `//`.

    Las columnas se calculan desde la columna de FECHA, no desde otras
    columnas del calendario: si `Anio` resultara ser una columna calculada
    en DAX, no existe todavía cuando corre el mashup y el refresco muere
    con «no se encontró la columna».
    """
    expr = particion.get("source", {}).get("expression")
    lineas = list(expr) if isinstance(expr, list) else str(expr).split("\n")
    salida = ["let", '    #"MV DAX origen" =', "        ("]
    salida += [f"            {ln}" for ln in lineas]
    salida.append("        ),")
    previo = '#"MV DAX origen"'
    for i, (nombre, expresion, tipo) in enumerate(columnas):
        paso = f'#"MV DAX {nombre}"'
        coma = "," if i < len(columnas) - 1 else ""
        salida.append(f"    {paso} = Table.AddColumn ( {previo}, "
                      f'"{nombre}", each {expresion}, '
                      f"{_TIPO_M.get(tipo, 'type any')} ){coma}")
        previo = paso
    salida += ["in", f"    {previo}"]
    particion["source"]["expression"] = salida
    del origen


# La forma EXACTA de los pasos que `_envolver_m` escribe. Es una inversa,
# no un parser de M: solo reconoce lo que este programa generó.
_RE_PASO_ENVUELTO = re.compile(
    r'^\s*#"MV DAX (?P<nombre>.+?)" = Table\.AddColumn \( .+?, '
    r'"(?P=nombre)", each (?P<resto>.+) \),?\s*$')

_TIPO_DESDE_M = {v: k for k, v in _TIPO_M.items()}


def pasos_envueltos(expresion) -> list[tuple[str, str, str]]:
    """Recupera las columnas que `_envolver_m` agregó a una consulta.

    Es lo que permite que esas columnas SOBREVIVAN al empotrado: al meter
    los datos adentro del archivo, la consulta se reescribe desde la
    materia prima del dataset — y el trimestre, el semestre y sus órdenes,
    agregados al preparar el modelo, desaparecían en silencio. El archivo
    declaraba columnas que la consulta ya no producía y el gate lo
    reprobaba; sin gate, la tabla quedaba en error al refrescar.
    """
    texto = ("\n".join(expresion) if isinstance(expresion, list)
             else str(expresion or ""))
    pasos: list[tuple[str, str, str]] = []
    for linea in texto.split("\n"):
        m = _RE_PASO_ENVUELTO.match(linea)
        if not m or m.group("nombre") == "origen":
            continue
        resto = m.group("resto")
        if ", " not in resto:
            continue
        expr, tipo_m = resto.rsplit(", ", 1)
        pasos.append((m.group("nombre"), expr,
                      _TIPO_DESDE_M.get(tipo_m.strip(), "string")))
    return pasos


def reenvolver(particion: dict, pasos: list[tuple[str, str, str]],
               origen: str) -> None:
    """Vuelve a aplicar los pasos recuperados sobre una consulta nueva."""
    if pasos:
        _envolver_m(particion, pasos, origen)


# Los sinónimos con los que puede venir cada columna del calendario. Se
# ACEPTAN los que ya estén (no se duplica una columna de año que se llama
# «Año»), y después las medidas tienen que referenciar EL NOMBRE REAL, no
# el canónico: si no, el DAX referencia algo que no existe, la validación
# lo rechaza y los comparativos desaparecen sin decir nada.
_SINONIMOS = {
    "anio": ("Anio", "Año", "Year", "Ano", "Ejercicio"),
    "mes_num": ("MesNumero", "MonthNumber", "NumeroMes", "MesNro",
                "NroMes", "MesNum"),
    "trimestre": ("Trimestre", "Quarter"),
    "semestre": ("Semestre", "Semester"),
    # Etiquetas que YA llevan el año: son biyectivas con su columna de
    # orden y por eso se pueden ordenar aunque ya existieran.
    "anio_mes": ("AnioMes", "AñoMes", "YearMonth", "AnoMes", "Periodo",
                 "Período"),
    "anio_semestre": ("AnioSemestre", "AñoSemestre", "YearSemester",
                      "AnoSemestre"),
    "orden_mes": ("AnioMesOrden", "AñoMesOrden", "YearMonthOrder",
                  "AnoMesOrdem"),
    "orden_tri": ("AnioTrimestreOrden", "YearQuarterOrder",
                  "AnoTrimestreOrdem"),
    "orden_sem": ("AnioSemestreOrden", "YearSemesterOrder",
                  "AnoSemestreOrdem"),
}


def columnas_resueltas(cat: Catalogo, idioma: str = IDIOMA_DEFECTO) -> dict:
    """El nombre REAL de cada columna del calendario en ESTE modelo.

    Un calendario en español escribe «Año»; uno en inglés, «Year». Las
    medidas tienen que apuntar a lo que hay, no a lo que este módulo
    hubiera puesto. Devuelve `{}` si no hay calendario.
    """
    cal = cat.tabla_fechas()
    if cal is None:
        return {}
    presentes = {_norm(c["nombre"]): c["nombre"] for c in cal["columnas"]}
    n = nombres_columnas(idioma)
    salida = {}
    for clave, alias in _SINONIMOS.items():
        # `.get`: no toda clave de sinónimos tiene un nombre canónico por
        # idioma —las etiquetas que ya llevan el año se resuelven solo por
        # sus alias— y pedirlo con corchetes reventaba el módulo entero.
        canonico = n.get(clave)
        real = next((presentes[_norm(a)]
                     for a in ((canonico, *alias) if canonico else alias)
                     if _norm(a) in presentes), None)
        # Sin nombre canónico y sin coincidencia, la clave no aplica a
        # este calendario: no se inventa un nombre que no existe.
        if real or canonico:
            salida[clave] = real or canonico
    return salida


def columnas_de_orden(modelo: dict,
                      idioma: str = IDIOMA_DEFECTO) -> tuple[dict,
                                                             list[str]]:
    """Le agrega al calendario lo que los comparativos necesitan.

    Trimestre y semestre con AÑO, y las tres columnas de orden enteras. El
    semestre casi nunca viene en el origen —hay que construirlo— y el
    trimestre suele venir como `"T1"` pelado, que es justo la forma que
    rompe la comparación interanual.

    Si ya están, no toca nada: se puede llamar dos veces sin duplicar.
    """
    modelo = copy.deepcopy(modelo)
    cat = Catalogo.desde_modelo(modelo)
    cal = cat.tabla_fechas()
    if cal is None:
        raise ValueError(traducir("pe_sin_calendario", idioma))

    tabla = next(t for t in modelo["model"]["tables"]
                 if t.get("name") == cal["nombre"])
    n = nombres_columnas(idioma)
    fecha = cat.columna_fecha()
    if fecha is None:
        raise ValueError(traducir("pe_sin_calendario", idioma))
    ref = _ref(*fecha)

    existentes = {_norm(c.get("name", "")) for c in tabla.get("columns", [])}
    reales = columnas_resueltas(cat, idioma)
    cambios: list[str] = []

    particion = next((p for p in tabla.get("partitions", [])
                      if p.get("source", {}).get("type") == "m"), None)
    en_m = particion is not None and not tabla.get("calculated")

    # Todo lo que se calcula sale de la columna de FECHA y de nada más: así
    # el M no depende de columnas que quizá se calculen en DAX (y que en el
    # mashup todavía no existen).
    fcol = fecha[1]
    m_anio = f"Date.Year ( [{fcol}] )"
    m_mes = f"Date.Month ( [{fcol}] )"
    m_tri = f"Number.RoundUp ( Date.Month ( [{fcol}] ) / 3 )"
    m_sem = f"( if Date.Month ( [{fcol}] ) <= 6 then 1 else 2 )"
    d_anio = f"YEAR ( {ref} )"
    d_mes = f"MONTH ( {ref} )"
    d_tri = f"ROUNDUP ( DIVIDE ( {d_mes}, 3 ), 0 )"
    d_sem = f"IF ( {d_mes} <= 6, 1, 2 )"

    nuevas_m: list[tuple[str, str, str]] = []
    creadas: set[str] = set()

    def sumar(clave: str, dax: str, m_expr: str, tipo: str = "int64",
              **extra):
        nombre = reales.get(clave) or n[clave]
        if _norm(nombre) in existentes:
            return
        nombre = n[clave]
        if en_m:
            nuevas_m.append((nombre, m_expr, tipo))
            tabla.setdefault("columns", []).append(
                {"name": nombre, "dataType": tipo, "sourceColumn": nombre,
                 "lineageTag": str(_uuid.uuid4()), **extra})
        else:
            tabla.setdefault("columns", []).append(
                _col_calculada(nombre, dax, tipo, **extra))
        existentes.add(_norm(nombre))
        creadas.add(clave)
        reales[clave] = nombre
        cambios.append(traducir(
            "pe_columna_m" if en_m else "pe_columna",
            idioma).format(columna=nombre, tabla=cal["nombre"]))

    sumar("anio", d_anio, m_anio, formatString="0")
    sumar("mes_num", d_mes, m_mes, isHidden=True)
    # El trimestre y el semestre CON el año adentro: un eje que repite la
    # misma etiqueta en dos años no se puede comparar contra el anterior.
    sumar("trimestre",
          f'FORMAT ( {d_anio}, "0000" ) & "-T" & FORMAT ( {d_tri}, "0" )',
          f'Text.From ( {m_anio} ) & "-T" & Text.From ( {m_tri} )',
          "string")
    sumar("semestre",
          f'FORMAT ( {d_anio}, "0000" ) & "-S" & FORMAT ( {d_sem}, "0" )',
          f'Text.From ( {m_anio} ) & "-S" & Text.From ( {m_sem} )',
          "string")
    sumar("orden_mes", f"{d_anio} * 100 + {d_mes}",
          f"{m_anio} * 100 + {m_mes}", formatString="0", isHidden=True)
    sumar("orden_tri", f"{d_anio} * 10 + {d_tri}",
          f"{m_anio} * 10 + {m_tri}", formatString="0", isHidden=True)
    sumar("orden_sem", f"{d_anio} * 10 + {d_sem}",
          f"{m_anio} * 10 + {m_sem}", formatString="0", isHidden=True)

    if nuevas_m:
        _envolver_m(particion, nuevas_m, cal["nombre"])

    # El eje se ordena por su columna de orden — pero SOLO si la etiqueta la
    # creamos nosotros. Un `Trimestre` que ya existía y dice «T1» mapea a
    # dos años distintos: ordenarlo por AnioTrimestreOrden es una relación
    # 1:N que Power BI rechaza, y el archivo directamente no abre.
    # Las etiquetas que YA llevan el año («2025-01», «2025-S1») son
    # biyectivas con su columna de orden, así que se pueden ordenar aunque
    # la etiqueta ya existiera: cada valor mapea a UN solo número. Las que
    # no lo llevan («T1», «S1») no, y por eso siguen pidiendo que la
    # etiqueta la hayamos creado nosotros.
    con_anio = {"anio_mes", "anio_semestre"}
    for clave, orden in (("trimestre", "orden_tri"),
                         ("semestre", "orden_sem"),
                         ("anio_mes", "orden_mes"),
                         ("anio_semestre", "orden_sem")):
        if orden not in creadas:
            continue
        if clave not in creadas and clave not in con_anio:
            continue
        if clave not in reales or orden not in reales:
            continue
        col = next((c for c in tabla["columns"]
                    if _norm(c.get("name", "")) == _norm(reales[clave])),
                   None)
        if col is not None and not col.get("sortByColumn"):
            col["sortByColumn"] = reales[orden]
    return modelo, cambios


# ==========================================================================
# 2 · Las medidas de comparación
# ==========================================================================
# Marcas de una medida que es el DENOMINADOR del share (el mercado entero)
# y no el numerador. Comparar «Ventas Mercado» contra sí misma da la
# evolución del mercado, que está bien — pero el share de esa medida
# siempre da 100 %, así que como BASE no sirve: la base es lo propio.
_MERCADO = ("mercado", "market", "universo", "industria", "sector")

# Una medida que YA es una comparación no se vuelve a comparar: «Ventas vs
# AA vs AA» no significa nada.
_YA_COMPARADA = ("vs ", " aa", "aa ", " py", "py ", "ytd", "qtd", "std",
                 "mtd", "acumulado", "variacion", "var ", "share", "anterior",
                 "color ")


def _clase_de(nombre: str) -> str | None:
    """«valor» (plata), «volumen» (unidades) o «otra» (todo lo demás que
    se suma).

    «otra» existe porque el filtro por vocabulario dejaba sin comparativos
    a todo lo que no se llamara ventas o unidades: visitas, recetas,
    envíos, clics. Sus páginas salían con un total suelto y ninguna forma
    de saber si ese número está bien o mal. Un total de visitas se compara
    contra el mes pasado igual que uno de ventas.
    """
    if _es(nombre, _VALOR):
        return "valor"
    if _es(nombre, _VOLUMEN):
        return "volumen"
    return "otra"


def _formula(dax: str) -> str:
    """La fórmula sin espacios ni mayúsculas: dos medidas con el mismo
    cálculo y distinto nombre son la MISMA medida."""
    return re.sub(r"\s+", " ", dax or "").strip().lower()


def _parecido(a: str, b: str) -> int:
    """Cuántas palabras comparten dos nombres de medida. Sirve para
    aparear «Ventas Adium USD» con «Ventas Mercado USD» y no con
    «Unidades Mercado»."""
    return len(set(_norm(a).split()) & set(_norm(b).split()))


def _bases(cat: Catalogo) -> list[dict]:
    """Las medidas sobre las que vale la pena comparar períodos.

    Se prefieren las medidas que YA existen —son las que el autor del
    modelo eligió— y, dentro de cada clase, la que mide **lo propio** antes
    que la que mide el mercado entero: el share de la medida de mercado da
    100 % por definición y no dice nada.
    """
    candidatas = []
    for m in cat.medidas():
        if m.get("oculta"):
            continue
        nombre = m["nombre"]
        clase = _clase_de(nombre)
        if clase is None or _es(nombre, _YA_COMPARADA):
            continue
        # Sólo se compara contra el año anterior lo que se SUMA. Una
        # medida de texto («el producto con más ventas») y una razón ya
        # cerrada («margen %») no son la base de un comparativo: la
        # primera no tiene aritmética y la segunda ya es el resultado de
        # una. Al abrir la puerta a las medidas sin vocabulario conocido,
        # las dos se colaron como bases.
        from .analizador import es_medida_de_texto
        if es_medida_de_texto(m.get("expresion", ""), cat):
            continue
        if "%" in (m.get("formato") or ""):
            continue
        candidatas.append({"nombre": nombre, "clase": clase,
                           "ref": f"[{nombre}]",
                           "es_mercado": _es(nombre, _MERCADO)})
    # Una de cada clase POR TABLA DE HECHOS. Antes era una por clase en
    # todo el modelo: en un informe con ventas, visitas, recetas e
    # interacciones digitales, sólo las ventas tenían «mes anterior» y
    # «YTD», y las otras cuatro páginas quedaban con un total suelto que
    # no responde «¿cómo venimos?». El tope por hecho evita el otro
    # extremo —con tres medidas de valor salen 150 comparativos que nadie
    # mira— y el orden dentro de cada grupo prefiere lo propio al
    # mercado: el share de la medida de mercado da 100 % por definición.
    from .tablero import tablas_de_medida

    por_hecho: dict[str, list[dict]] = {}
    for c in candidatas:
        hechos = tablas_de_medida(cat, c["nombre"]) or {""}
        clave = f'{sorted(hechos)[0]}|{c["clase"]}'
        por_hecho.setdefault(clave, []).append(c)
    elegidas = []
    for clave in sorted(por_hecho):
        grupo = por_hecho[clave]
        propias = [c for c in grupo if not c["es_mercado"]]
        elegidas.append((propias or grupo)[0])
    # La medida principal del modelo va primera: es la que manda en el
    # orden con que se leen las páginas y las tarjetas.
    _peso = {"valor": 0, "volumen": 1, "otra": 2}
    elegidas.sort(key=lambda c: (c["es_mercado"], _peso.get(c["clase"], 3)))
    return elegidas[:_MAX_BASES]


# Cuántas familias de comparativos como máximo. Seis cubre un informe
# gerencial de cinco o seis hechos sin que el panel de campos se vuelva
# inmanejable.
_MAX_BASES = 6


def _mercado_de(cat: Catalogo, base: dict) -> str | None:
    """La medida de mercado que ya existe para esta base, si la hay.

    Reusar la del modelo es mejor que fabricar «Ventas Adium USD Mercado»:
    el autor ya decidió qué es el mercado, y suele saber más que una regla
    de nombres (puede incluir productos que la corporación no vende).
    """
    mejor, mejor_p = None, 0
    for m in cat.medidas():
        nombre = m["nombre"]
        if not _es(nombre, _MERCADO) or _es(nombre, _YA_COMPARADA):
            continue
        if _clase_de(nombre) != base["clase"]:
            continue
        p = _parecido(nombre, base["nombre"])
        if p > mejor_p:
            mejor, mejor_p = nombre, p
    return f"[{mejor}]" if mejor else None


ANOTACION_EMPRESA = "MVDAX_EmpresaPropia"


def columna_corporacion(cat: Catalogo) -> tuple[str, str] | None:
    """La columna que dice QUIÉN vende: la que sale del denominador del
    share. `None` si el modelo no tiene competencia adentro — ahí no hay
    share que calcular y no se inventa uno.

    Una señal fuerte («Corporacion») le gana SIEMPRE a una débil («Marca»),
    esté donde esté: sacar del denominador la columna equivocada no da un
    error, da 100 % de share con toda confianza.
    """
    mejor = None
    muchos = {_norm(r["desde_tabla"]) for r in cat.relaciones}
    for tabla, col in cat.columnas(solo_visibles=True):
        if col["tipo"] in TIPOS_NUMERICOS:
            continue
        if _es(col["nombre"], _CORPORACION_FUERTE):
            fuerza = 2
        elif _es(col["nombre"], _CORPORACION_DEBIL):
            fuerza = 1
        else:
            continue
        # A igual fuerza, la dimensión le gana al hecho: filtrar por la
        # dimensión es lo que hace un usuario con un segmentador.
        peso = (fuerza, 0 if _norm(tabla) in muchos else 1)
        if mejor is None or peso > mejor[0]:
            mejor = (peso, tabla, col["nombre"])
    return (mejor[1], mejor[2]) if mejor else None


def _nombre_anterior(base: str, etiqueta: str, idioma: str) -> str:
    """«Ventas YTD» + grano YTD = «Ventas YTD AA», y no «Ventas YTD YTD AA».

    Cuando la medida base YA lleva el grano en el nombre (el acumulado del
    año se llama «… YTD»), repetirlo da un nombre que nadie escribiría.
    """
    if _norm(base).endswith(_norm(etiqueta)):
        return traducir("pe_anterior_simple", idioma).format(base=base)
    return traducir("pe_anterior", idioma).format(base=base, grano=etiqueta)


def _dax_anterior(base: str, cal: str, orden: str, salto: int) -> str:
    """El mismo período del año anterior, por desplazamiento de la columna
    de orden. `REMOVEFILTERS` sobre el calendario entero es obligatorio: si
    no, el filtro original de fecha sigue puesto y la intersección con el
    período anterior da vacío."""
    o = _ref(cal, orden)
    return (f"VAR Periodos = VALUES ( {o} )\n"
            f'VAR Anterior = SELECTCOLUMNS ( Periodos, "@orden", '
            f"{o} - {salto} )\n"
            f"RETURN\n"
            f"CALCULATE ( {base}, REMOVEFILTERS ( {_tabla_ref(cal)} ), "
            f"TREATAS ( Anterior, {o} ) )")


def columna_fecha_hechos(cat: Catalogo,
                        dax_base: str = "") -> tuple[str, str] | None:
    """La columna de fecha por la que los HECHOS se relacionan al calendario.

    No sirve «la primera columna dateTime que aparezca»: una dimensión
    Producto con `FechaAlta` viene antes que Ventas en el catálogo, y el
    mes de cierre saldría del último producto dado de alta en vez de la
    última venta. El número resultante es plausible, silencioso y falso.

    Entre varias tablas de hechos gana la que la MEDIDA usa: un modelo con
    Visitas, Recetas y Mercado tiene tres fechas, y el cierre de una medida
    de ventas es el de la tabla de ventas — no el de la primera relación
    que aparezca en la lista.
    """
    cal = cat.tabla_fechas()
    if cal is None:
        return None
    candidatas = []
    for r in cat.relaciones:
        if _norm(r["hacia_tabla"]) != _norm(cal["nombre"]):
            continue
        t = cat.tabla(r["desde_tabla"])
        if not t:
            continue
        col = next((c for c in t["columnas"]
                    if _norm(c["nombre"]) == _norm(r["desde_col"])), None)
        if col and col["tipo"] == "dateTime":
            candidatas.append((t["nombre"], col["nombre"]))
    if not candidatas:
        return None
    if dax_base:
        usadas = referencias_dax(dax_base)["columnas"]
        nombradas = {_norm(t) for t, _c in usadas}
        propia = next((c for c in candidatas if _norm(c[0]) in nombradas),
                      None)
        if propia:
            return propia
    return candidatas[0]


def _dax_ytd(base: str, cal: str, fecha: str, hecho: str,
             col_hecho: str, mes_num: str, anterior: bool = False) -> str:
    """El acumulado del año recortado al mes de cierre — de los DOS años.

    Sin el recorte, comparar un 2026 que llega a junio contra un 2025
    completo muestra una caída del 47 % que no existe: es la mitad del año
    que todavía no pasó.

    El del año anterior NO se saca con `REMOVEFILTERS` del calendario más
    un `TREATAS` del año: eso borra el contexto de mes, y en una tabla
    mensual la fila de marzo comparaba enero-marzo 2026 contra enero-JUNIO
    2025 — la misma caída inventada, mudada de lugar. Se desplaza con
    `SAMEPERIODLASTYEAR`, que conserva el período que el visual está
    mirando, y el recorte va con `KEEPFILTERS` para que se INTERSEQUE con
    el filtro de mes en vez de reemplazarlo.
    """
    fechas = (f"SAMEPERIODLASTYEAR ( {_ref(cal, fecha)} )" if anterior
              else _ref(cal, fecha))
    return (f"VAR Cierre = CALCULATE ( MAX ( {_ref(hecho, col_hecho)} ), "
            f"REMOVEFILTERS ( ) )\n"
            f"VAR MesCierre = MONTH ( Cierre )\n"
            f"RETURN\n"
            f"CALCULATE ( {base}, DATESYTD ( {fechas} ), "
            f"KEEPFILTERS ( {_ref(cal, mes_num)} <= MesCierre ) )")


def dax_var_comparable(actual: str, cal: str, fecha: str) -> str:
    """La variación interanual, en blanco cuando no hay con qué comparar.

    **La trampa del año incompleto.** `SAMEPERIODLASTYEAR` desplaza el
    período visible un año atrás y devuelve SÓLO las fechas que existen
    en el calendario. Si el modelo arranca en enero de 2025 y llega a
    junio de 2026, sin filtro de fecha el período visible son 18 meses y
    el desplazado cae en 2024 —que no existe—, así que apenas quedan los
    seis primeros meses de 2025. La cuenta compara entonces 18 meses
    contra 6 y devuelve un +211 %, que en pantalla parece un crecimiento
    espectacular y es puro artefacto: la comparación honesta del mismo
    tramo daba +9,7 %.

    **Negarse a responder no alcanzaba.** El primer arreglo contaba los
    días de cada lado y devolvía BLANK si no coincidían. Correcto y, en
    pantalla, peor: sin filtro de año —que es como se abre el informe— la
    columna entera quedaba vacía, y una columna vacía se lee como una
    medida rota, no como «no comparable». El usuario lo reportó así.

    Lo que se hace ahora es **recortar las dos puntas a la ventana que sí
    se puede comparar**. `FechasAnt` son las fechas del año anterior que
    EXISTEN en el calendario; `Actual` mide esas mismas fechas corridas un
    año adelante con `DATEADD`. Los dos lados abarcan siempre el mismo
    tramo, así que la respuesta es honesta y además hay respuesta: sin
    filtro da el +9,7 % real en vez de vacío. Sólo queda en blanco cuando
    de verdad no hay año anterior contra el cual comparar —seleccionando
    el primer año de la serie—, que es el único caso en que callarse es
    la respuesta correcta.

    Se usa `DATEADD` y no sumar 365 días porque los bisiestos correrían
    la ventana un día por año.
    """
    return ventana_comparable(actual, cal, fecha,
                              "DIVIDE ( Actual - Anterior, Anterior )")


def ventana_comparable(base: str, cal: str, fecha: str,
                       cuerpo: str) -> str:
    """Las dos puntas de la comparación recortadas al tramo que existe.

    Deja definidas las variables `Anterior` y `Actual` —las dos medidas
    sobre EL MISMO tramo de días— y devuelve `cuerpo`, que las combina
    como corresponda: `DIVIDE ( Actual - Anterior, Anterior )` para una
    variación en %, `( Actual - Anterior ) * 100` para un share en puntos
    porcentuales.

    Separarlo de `dax_var_comparable` es lo que permite que el share en pp
    reciba el mismo recorte: pp y % se restan distinto, pero el problema
    de comparar ventanas de distinto largo es idéntico.
    """
    ref = _ref(cal, fecha)
    return (f"VAR FechasAnt =\n"
            f"    CALCULATETABLE ( VALUES ( {ref} ), "
            f"SAMEPERIODLASTYEAR ( {ref} ) )\n"
            f"VAR Anterior = CALCULATE ( {base}, FechasAnt )\n"
            f"VAR Actual =\n"
            f"    CALCULATE ( {base}, DATEADD ( FechasAnt, 1, YEAR ) )\n"
            f"RETURN\n"
            f"    {cuerpo}")


def guardia_comparable(cal: str, fecha: str, cuerpo: str,
                       previas: str = "") -> str:
    """Envuelve una variación con la guardia del año incompleto.

    Sirve para las dos familias —la que desplaza con
    `SAMEPERIODLASTYEAR` y la que desplaza la columna de orden con
    `TREATAS`— porque lo que mide es una propiedad del RANGO VISIBLE, no
    de cómo se calculó el año anterior: si los días del período de hoy no
    son los mismos que los del período de hace un año que existen en el
    calendario, la comparación no es comparable y no se responde.
    """
    ref = _ref(cal, fecha)
    return (f"{previas}"
            f"VAR DiasHoy = COUNTROWS ( VALUES ( {ref} ) )\n"
            f"VAR DiasAntes =\n"
            f"    CALCULATE ( COUNTROWS ( VALUES ( {ref} ) ), "
            f"SAMEPERIODLASTYEAR ( {ref} ) )\n"
            f"RETURN\n"
            f"    IF ( DiasHoy = DiasAntes, {cuerpo} )")


def comparativos(cat: Catalogo, idioma: str = IDIOMA_DEFECTO,
                 granos: tuple[str, ...] = GRANOS,
                 propia: str | None = None) -> list[dict]:
    """Toda la matriz: por cada base y cada grano, el valor del año
    anterior, la variación, y —si hay competencia en el modelo— el share
    propio, el del año anterior y el salto en puntos porcentuales.

    Devuelve `[]` antes que inventar: cada DAX se valida contra el catálogo
    y lo que referencia algo que no existe no sale.
    """
    cal = cat.tabla_fechas()
    fecha = cat.columna_fecha()
    if cal is None or fecha is None:
        return []
    # Los nombres REALES de este calendario, no los canónicos: uno en
    # español escribe «Año» y uno en inglés «Year». Apuntar al nombre que
    # este módulo hubiera puesto hacía que `validar_referencias` rechazara
    # el DAX y toda la matriz desapareciera sin un solo aviso.
    n = columnas_resueltas(cat, idioma) or nombres_columnas(idioma)
    tabla_cal = cal["nombre"]
    ordenes = {"mes": n["orden_mes"], "trimestre": n["orden_tri"],
               "semestre": n["orden_sem"]}
    # El cierre se resuelve POR BASE: cada medida puede vivir en otra
    # tabla de hechos, con otra última fecha.
    def fecha_de(base: dict):
        m = cat.medida(base["nombre"])
        return columna_fecha_hechos(cat, (m or {}).get("expresion", ""))

    sugerencias: list[dict] = []
    existentes = {_norm(m["nombre"]) for m in cat.medidas()}
    # Copia de trabajo: cada medida propuesta se REGISTRA acá, porque las
    # que vienen después la referencian. La variación de un mes usa la
    # medida «mes AA» que se acaba de proponer, y validándola contra el
    # catálogo original salía «medida inexistente» — se caía toda la
    # segunda mitad de la matriz en silencio.
    trabajo = copy.deepcopy(cat)
    destino = next((t for t in trabajo.tablas if t["medidas"]),
                   trabajo.tablas[0] if trabajo.tablas else None)
    # Las fórmulas que el modelo YA tiene, normalizadas. Un modelo que
    # tiene «Var Ventas YTD %» no necesita «Ventas var YTD %» con
    # exactamente el mismo DAX: el nombre difiere, la medida es la misma, y
    # duplicarla es justo lo que el analizador denuncia (R05).
    formulas = {_formula(m.get("expresion", "")) for m in cat.medidas()}

    def proponer(nombre, dax, formato, carpeta, clave, **datos):
        if _norm(nombre) in existentes:
            return
        if _formula(dax) in formulas:
            return
        if validar_referencias(dax, trabajo):
            return
        formulas.add(_formula(dax))
        existentes.add(_norm(nombre))
        if destino is not None:
            destino["medidas"].append(
                {"nombre": nombre, "expresion": dax,
                 "formato": formato, "tabla": destino["nombre"],
                 "descripcion": "", "carpeta": carpeta})
        sugerencias.append({
            "nombre": nombre, "dax": dax, "formato": formato,
            "carpeta": carpeta,
            "por_que": traducir(clave, idioma).format(**datos)})

    corp = columna_corporacion(cat)
    # La empresa propia: la que el usuario eligió (anotación del modelo)
    # o la que se pasó. Con ella el share deja de depender del contexto:
    # «Share Empresa %» es lo de ESA corporación sobre el mercado, y en
    # una tarjeta sin filtro no da 100 % — que era el error que un
    # usuario vio en el informe entregado.
    propia = propia or cat.anotaciones.get(ANOTACION_EMPRESA) or None
    filtro_propia = (f'{_ref(*corp)} = "{propia.replace(chr(34), chr(34) * 2)}"'
                     if propia and corp else None)
    # Qué share ya se propuso para cada par (numerador, denominador).
    shares_hechos: dict[tuple[str, str], str] = {}
    shares_propia: dict[tuple[str, str], str] = {}
    carpeta_t = traducir("pe_carpeta_tiempo", idioma)
    carpeta_s = traducir("pe_carpeta_share", idioma)

    for base in _bases(cat):
        nb, rb = base["nombre"], base["ref"]
        fmt = "#,0.00" if base["clase"] == "valor" else "#,0"

        # ---- El mercado: el denominador del share ----
        # Si el modelo ya tiene su medida de mercado, se usa esa. Solo se
        # fabrica una cuando no hay, y ahí es el mismo número sin el filtro
        # de corporación.
        ref_mercado = _mercado_de(cat, base)
        nombre_mk = ref_mercado[1:-1] if ref_mercado else None
        if ref_mercado is None and corp:
            nombre_mk = traducir("pe_mercado", idioma).format(base=nb)
            proponer(nombre_mk,
                     f"CALCULATE ( {rb}, REMOVEFILTERS ( {_ref(*corp)} ) )",
                     fmt, carpeta_s, "pe_pq_mercado",
                     base=nb, columna=corp[1])
            if _norm(nombre_mk) in existentes:
                ref_mercado = f"[{nombre_mk}]"

        # ---- En qué puesto estamos ----
        # La pregunta que sigue al share y que ninguna otra medida
        # responde: cuántos venden más que nosotros. `ALL` sobre la
        # columna de corporación es lo que hace que el puesto se calcule
        # contra TODO el mercado y no contra lo que quedó filtrado.
        if corp:
            proponer(traducir("pe_ranking", idioma).format(base=nb),
                     f"RANKX ( ALL ( {_ref(*corp)} ), {rb},, DESC )",
                     "#,0", carpeta_s, "pe_pq_ranking",
                     base=nb, columna=corp[1])

        for grano in granos:
            etiqueta = traducir(f"pe_grano_{grano}", idioma)
            # `rb_grano` es lo que se compara en ESTE grano: la medida base
            # tal cual, salvo en YTD, donde lo que se compara es el
            # acumulado recortado al mes de cierre.
            rb_grano = rb
            if grano in ordenes:
                dax_ant = _dax_anterior(rb, tabla_cal, ordenes[grano],
                                        _SALTO[grano])
            elif grano == "anio":
                dax_ant = _dax_anterior(rb, tabla_cal, n["anio"], 1)
            else:                                   # ytd
                hecho_fecha = fecha_de(base)
                if hecho_fecha is None:
                    continue
                ht, hc = hecho_fecha
                nombre_ytd = traducir("pe_ytd", idioma).format(base=nb)
                proponer(nombre_ytd,
                         _dax_ytd(rb, tabla_cal, fecha[1], ht, hc,
                                  n["mes_num"]),
                         fmt, carpeta_t, "pe_pq_ytd", base=nb)
                if _norm(nombre_ytd) not in existentes:
                    continue
                rb_grano = f"[{nombre_ytd}]"
                # El YTD del año anterior se calcula desde la BASE, no
                # desplazando la medida YTD con REMOVEFILTERS: eso borra el
                # contexto de mes y en una tabla mensual compara enero-marzo
                # contra enero-cierre del año pasado.
                dax_ant = _dax_ytd(rb, tabla_cal, fecha[1], ht, hc,
                                   n["mes_num"], anterior=True)

            nombre_ant = _nombre_anterior(rb_grano[1:-1], etiqueta,
                                          idioma)
            proponer(nombre_ant, dax_ant, fmt, carpeta_t, "pe_pq_anterior",
                     base=nb, grano=etiqueta)
            if _norm(nombre_ant) not in existentes:
                continue

            proponer(
                traducir("pe_variacion", idioma).format(
                    base=nb, grano=etiqueta),
                ventana_comparable(
                    rb_grano, tabla_cal, fecha[1],
                    "DIVIDE ( Actual - Anterior, Anterior )"),
                FORMATO_PCT, carpeta_t, "pe_pq_variacion",
                base=nb, grano=etiqueta)

            # ---- El share, en el mismo período ----
            if not ref_mercado:
                continue
            # El denominador tiene que estar en el MISMO grano que el
            # numerador: un share YTD con mercado del mes es un número que
            # no significa nada. En YTD el mercado también se acumula y se
            # recorta al mes de cierre.
            mk_grano = ref_mercado
            if grano == "ytd":
                nombre_mk_ytd = traducir("pe_ytd", idioma).format(
                    base=nombre_mk)
                proponer(nombre_mk_ytd,
                         _dax_ytd(ref_mercado, tabla_cal, fecha[1], ht, hc,
                                  n["mes_num"]),
                         fmt, carpeta_s, "pe_pq_ytd", base=nombre_mk)
                mk_ytd_ant = _dax_ytd(ref_mercado, tabla_cal, fecha[1],
                                      ht, hc, n["mes_num"], anterior=True)
                if _norm(nombre_mk_ytd) not in existentes:
                    continue
                mk_grano = f"[{nombre_mk_ytd}]"

            nombre_mk_ant = _nombre_anterior(mk_grano[1:-1], etiqueta,
                                             idioma)
            if grano in ordenes:
                dax_mk_ant = _dax_anterior(mk_grano, tabla_cal,
                                           ordenes[grano], _SALTO[grano])
            elif grano == "ytd":
                dax_mk_ant = mk_ytd_ant
            else:
                dax_mk_ant = _dax_anterior(mk_grano, tabla_cal,
                                           n["anio"], 1)
            proponer(nombre_mk_ant, dax_mk_ant, fmt, carpeta_s,
                     "pe_pq_mercado_ant", base=nb, grano=etiqueta)
            if _norm(nombre_mk_ant) not in existentes:
                continue

            # El share DE HOY no depende del grano: «lo propio sobre el
            # mercado» da lo mismo mirando un mes, un trimestre o un año —
            # el grano lo pone el contexto del visual. Una medida por grano
            # serían cinco copias con el mismo DAX (y el analizador las
            # denuncia, con razón). Lo que sí cambia por grano es el AA.
            clave_share = (rb_grano, mk_grano)
            nombre_share = shares_hechos.get(clave_share)
            if nombre_share is None:
                nombre_share = traducir("pe_share_simple", idioma).format(
                    base=rb_grano[1:-1])
                proponer(nombre_share,
                         f"DIVIDE ( {rb_grano}, {mk_grano} )",
                         "0.0 %", carpeta_s, "pe_pq_share",
                         base=nb, grano=etiqueta)
                if _norm(nombre_share) not in existentes:
                    continue
                shares_hechos[clave_share] = nombre_share
            # ---- El share de la empresa propia, si se la conoce ----
            if filtro_propia:
                nombre_sp = shares_propia.get(clave_share)
                if nombre_sp is None:
                    nombre_sp = traducir("pe_share_propia", idioma).format(
                        empresa=propia, base=rb_grano[1:-1])
                    proponer(nombre_sp,
                             f"DIVIDE ( CALCULATE ( {rb_grano}, "
                             f"{filtro_propia} ), {mk_grano} )",
                             "0.0 %", carpeta_s, "pe_pq_share_propia",
                             base=nb, empresa=propia)
                    if _norm(nombre_sp) in existentes:
                        shares_propia[clave_share] = nombre_sp
                nombre_sp_ant = traducir("pe_share_propia_ant",
                                         idioma).format(
                    empresa=propia, base=nb, grano=etiqueta)
                proponer(nombre_sp_ant,
                         f"DIVIDE ( CALCULATE ( [{nombre_ant}], "
                         f"{filtro_propia} ), [{nombre_mk_ant}] )",
                         "0.0 %", carpeta_s, "pe_pq_share_propia_ant",
                         base=nb, empresa=propia, grano=etiqueta)
                if _norm(nombre_sp) in existentes and \
                        _norm(nombre_sp_ant) in existentes:
                    proponer(
                        traducir("pe_share_propia_pp", idioma).format(
                            empresa=propia, base=nb, grano=etiqueta),
                        ventana_comparable(
                            f"[{nombre_sp}]", tabla_cal, fecha[1],
                            "( Actual - Anterior ) * 100"),
                        FORMATO_PP, carpeta_s, "pe_pq_share_propia_pp",
                        base=nb, empresa=propia, grano=etiqueta)

            nombre_share_ant = traducir("pe_share_anterior", idioma).format(
                base=nb, grano=etiqueta)
            # El share del año anterior NO es el share de hoy desplazado:
            # es numerador Y denominador recalculados en ese período.
            proponer(nombre_share_ant,
                     f"DIVIDE ( [{nombre_ant}], [{nombre_mk_ant}] )",
                     "0.0 %", carpeta_s, "pe_pq_share_ant",
                     base=nb, grano=etiqueta)
            if _norm(nombre_share) in existentes and \
                    _norm(nombre_share_ant) in existentes:
                proponer(
                    traducir("pe_share_pp", idioma).format(
                        base=nb, grano=etiqueta),
                    ventana_comparable(
                        f"[{nombre_share}]", tabla_cal, fecha[1],
                        "( Actual - Anterior ) * 100"),
                    FORMATO_PP, carpeta_s, "pe_pq_pp",
                    base=nb, grano=etiqueta)
    return sugerencias


def agregar_comparativos(modelo: dict, idioma: str = IDIOMA_DEFECTO,
                         granos: tuple[str, ...] = GRANOS
                         ) -> tuple[dict, list[str]]:
    """Las columnas de orden + toda la matriz de comparativos, de una."""
    from . import transformador
    modelo, cambios = columnas_de_orden(modelo, idioma)
    cat = Catalogo.desde_modelo(modelo)
    propuestas = comparativos(cat, idioma, granos)
    if not propuestas:
        return modelo, cambios + [traducir("pe_nada", idioma)]
    for s in propuestas:
        modelo, c = transformador.agregar_medida(
            modelo, s["nombre"], s["dax"], formato=s["formato"],
            descripcion=s["por_que"], carpeta=s["carpeta"], idioma=idioma)
        cambios.extend(c)
    return modelo, cambios
