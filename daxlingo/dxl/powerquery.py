# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · Power Query: SQL que se pliega al origen.

Por qué existe
--------------
La ficha de entrevista lo resume en una línea: «lo más cerca del origen
posible». Limpieza, tipado, filtros, combinaciones y columnas fijas van en
Power Query — o mejor todavía, en la vista SQL del origen, para que el
trabajo lo haga el servidor y no el motor local. En DAX quedan sólo los
cálculos que dependen del contexto de filtro del usuario.

Este módulo arma esas consultas: normalizar (de columnas a filas),
desnormalizar (traer la dimensión al hecho) y columnas calculadas resueltas
en el origen en vez de en DAX.

Dos advertencias que el producto tiene que decir en voz alta
------------------------------------------------------------
1. **El SQL nativo rompe el plegado de los pasos siguientes.** Poner una
   consulta nativa está perfecto como PRIMER paso —de hecho es lo que más
   pliega, porque la ejecuta entera el servidor— pero todo lo que venga
   después en el editor deja de traducirse a SQL y lo procesa el motor
   local. Por eso las recetas se generan para ser el paso inicial.

2. **Los nombres salen del modelo, no de la base.** El catálogo de un
   `.pbit` tiene los nombres de las tablas del MODELO, que casi siempre
   coinciden con la vista o tabla de origen pero no tienen por qué. Cada
   receta lo dice y el SQL queda a la vista para revisarlo antes de pegarlo.

La barrera de solo-lectura viene de MV SQL NLP (`conectores.py`): mismo
producto de la casa, misma regla — nunca se genera nada que escriba en la
base del cliente.
"""
from __future__ import annotations

import re

from .i18n import IDIOMA_DEFECTO, t as traducir


class SQLNoPermitido(Exception):
    """El SQL generado o pegado no es una lectura pura."""


# Operaciones que nunca salen de acá. Se matchean con \b y no como substring
# con espacio: "delete " no matchea "DELETE\nFROM", y ésa es justamente la
# forma de saltearse un filtro ingenuo.
#
# La lista es corta a propósito. Como abajo ya se exige un solo statement que
# empiece con SELECT/WITH, lo único que queda por frenar es un CTE modificador
# (`WITH x AS (DELETE … RETURNING) SELECT …`). Agregar palabras «por las
# dudas» tiene costo: REPLACE() es una función de texto legítima y bloquearla
# rompería consultas válidas, así que sólo se frena en su forma peligrosa.
_PROHIBIDAS = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|"
    r"exec|execute|merge|grant|revoke|attach|detach|vacuum|reindex|pragma|"
    # 'into' cubre las tres formas de ESCRITURA que arrancan con SELECT y
    # pasarían el prefijo: SELECT … INTO OUTFILE/DUMPFILE (MySQL escribe un
    # archivo en el server), REPLACE INTO, y SELECT … INTO tabla.
    r"into|"
    # Funciones de filesystem del server: son SELECT puros, así que una
    # barrera de prefijo sola las deja pasar.
    r"load_file|outfile|dumpfile|"                                    # MySQL
    r"pg_read_file|pg_read_binary_file|pg_ls_dir|lo_export|lo_import|"  # PG
    r"openrowset|opendatasource|xp_cmdshell|"                   # SQL Server
    r"utl_file|dbms_)"                                              # Oracle
    r"\b"
    r"|\bxp_|\bsp_executesql",
    re.IGNORECASE,
)

# Los comentarios se sacan antes de mirar el SQL: `DELETE/**/FROM` o un `--`
# que esconda medio statement no deben poder tapar una operación.
_COMENTARIO_BLOQUE = re.compile(r"/\*.*?\*/", re.DOTALL)
_COMENTARIO_LINEA = re.compile(r"--[^\n]*")

# Literal de texto SQL, con '' como comilla escapada adentro. Se reemplaza por
# '' ANTES de buscar operaciones y ';': así `SELECT ';' AS sep` no dispara la
# alarma, y nada de lo que se esconda DENTRO de un string puede evadirla.
_LITERAL = re.compile(r"'(?:[^']|'')*'")


def asegurar_solo_lectura(sql: str) -> bool:
    """Lanza SQLNoPermitido si el SQL no es una lectura pura."""
    if not sql or not sql.strip():
        raise SQLNoPermitido(traducir("pq_sql_vacio", IDIOMA_DEFECTO))

    limpio = _COMENTARIO_LINEA.sub(" ", _COMENTARIO_BLOQUE.sub(" ", sql)).strip()
    sin_lit = _LITERAL.sub("''", limpio)

    # Un ';' con algo después es encadenamiento; el ';' final suelto no.
    if ";" in sin_lit.rstrip().rstrip(";"):
        raise SQLNoPermitido(traducir("pq_varios_statements", IDIOMA_DEFECTO))
    if not re.match(r"^\s*(select|with)\b", sin_lit, re.IGNORECASE):
        raise SQLNoPermitido(traducir("pq_no_select", IDIOMA_DEFECTO))
    hallada = _PROHIBIDAS.search(sin_lit)
    if hallada:
        raise SQLNoPermitido(traducir("pq_operacion_prohibida", IDIOMA_DEFECTO)
                             .format(op=hallada.group(0).strip()))
    return True


# ==========================================================================
# Envoltura M
# ==========================================================================
MOTORES = {
    "sqlserver": {"m": "Sql.Database",      "nombre": "SQL Server"},
    "postgres":  {"m": "PostgreSQL.Database", "nombre": "PostgreSQL"},
    "mysql":     {"m": "MySQL.Database",    "nombre": "MySQL / MariaDB"},
    "oracle":    {"m": "Oracle.Database",   "nombre": "Oracle"},
}


def _m_literal(texto: str) -> str:
    """Un string de M.

    Dos escapes, no uno. La comilla doble se duplica, como en casi todos
    lados. Pero además `#(` abre una secuencia de escape en M —`#(lf)` es un
    salto de línea— así que un `#(` que venga del SQL rompe el literal y el
    paso no compila. Se escribe `#(#)(` para que quede el `#(` literal.
    """
    s = str(texto).replace('"', '""')
    return '"' + s.replace("#(", "#(#)(") + '"'


def envolver_m(sql: str, servidor: str, base: str,
               motor: str = "sqlserver", paso: str = "Origen") -> str:
    """Envuelve un SELECT en la función M que lo ejecuta en el origen.

    Se valida ANTES de envolver: una vez adentro del M el texto ya salió del
    programa, y revisar después de entregar no sirve de nada.
    """
    asegurar_solo_lectura(sql)
    fn = MOTORES.get(motor, MOTORES["sqlserver"])["m"]
    # El SQL va como literal M en una sola pieza; se normalizan los saltos
    # para que quede legible en el editor avanzado.
    cuerpo = "\n".join(linea.rstrip() for linea in sql.strip().splitlines())
    if motor == "oracle":
        args = f"{_m_literal(servidor)}"
    else:
        args = f"{_m_literal(servidor)}, {_m_literal(base)}"
    return (f"let\n"
            f"    {paso} = {fn}({args}, [Query={_m_literal(cuerpo)}])\n"
            f"in\n"
            f"    {paso}")


# ==========================================================================
# Recetas
# ==========================================================================
def _ref(nombre: str) -> str:
    """Corchetes sólo si el nombre no es un identificador simple."""
    return nombre if re.fullmatch(r"[A-Za-z_]\w*", nombre) else f"[{nombre}]"


def _tabla_col(tabla: str, columna: str) -> str:
    return f"{_ref(tabla)}.{_ref(columna)}"


def desnormalizar(hecho: str, dimension: str, clave_hecho: str,
                  clave_dim: str, columnas: list[str],
                  idioma: str = IDIOMA_DEFECTO) -> dict:
    """Trae columnas de la dimensión al hecho con un LEFT JOIN.

    LEFT y no INNER a propósito: un INNER descarta en silencio las filas del
    hecho que no tienen dimensión, y el total deja de cerrar contra la suma
    cruda sin que nadie se entere. Si hay huérfanos, el resultado los muestra
    en NULL y ahí se ven.
    """
    if not columnas:
        return {"ok": False, "error": traducir("pq_sin_columnas", idioma)}
    sel = ["    h.*"]
    sel += [f"    d.{_ref(c)} AS {_ref(c)}" for c in columnas]
    sql = ("SELECT\n" + ",\n".join(sel) + "\n"
           f"FROM {_ref(hecho)} AS h\n"
           f"LEFT JOIN {_ref(dimension)} AS d\n"
           f"    ON h.{_ref(clave_hecho)} = d.{_ref(clave_dim)}")
    return {
        "ok": True, "sql": sql,
        "titulo": traducir("pq_titulo_desnormalizar", idioma).format(
            dim=dimension, hecho=hecho),
        "nota": traducir("pq_nota_desnormalizar", idioma).format(
            hecho=hecho, dim=dimension),
    }


def normalizar(tabla: str, columnas_fijas: list[str],
               columnas_a_filas: list[str],
               nombre_atributo: str = "Atributo",
               nombre_valor: str = "Valor",
               idioma: str = IDIOMA_DEFECTO) -> dict:
    """De columnas a filas (unpivot): «Ene, Feb, Mar» pasan a ser datos.

    Un modelo con una columna por mes obliga a reescribir el informe cada vez
    que aparece un mes nuevo. Con los meses como filas, el mismo DAX sirve
    para siempre.

    Se genera el UNION ALL y no el operador UNPIVOT: UNPIVOT existe en SQL
    Server y Oracle pero no en MySQL ni PostgreSQL, y esto tiene que servir
    en los cuatro. También se da el paso equivalente en M, que es una sola
    línea y pliega si el origen lo soporta.
    """
    if not columnas_a_filas:
        return {"ok": False, "error": traducir("pq_sin_columnas", idioma)}
    fijas = ", ".join(_ref(c) for c in columnas_fijas)
    coma_fijas = f"{fijas}, " if fijas else ""
    bloques = []
    for c in columnas_a_filas:
        lit = "'" + str(c).replace("'", "''") + "'"
        bloques.append(f"    SELECT {coma_fijas}{lit} AS {_ref(nombre_atributo)}, "
                       f"{_ref(c)} AS {_ref(nombre_valor)} FROM {_ref(tabla)}")
    sql = "\nUNION ALL\n".join(bloques)

    m = (f'Table.UnpivotOtherColumns(Origen, '
         f'{{{", ".join(_m_literal(c) for c in columnas_fijas)}}}, '
         f'{_m_literal(nombre_atributo)}, {_m_literal(nombre_valor)})')
    return {
        "ok": True, "sql": sql, "m_paso": m,
        "titulo": traducir("pq_titulo_normalizar", idioma).format(tabla=tabla),
        "nota": traducir("pq_nota_normalizar", idioma).format(
            cuantas=str(len(columnas_a_filas)), atributo=nombre_atributo),
    }


def columna_calculada(tabla: str, nombre: str, expresion: str,
                      idioma: str = IDIOMA_DEFECTO) -> dict:
    """Resuelve una columna en el origen en vez de en DAX.

    La ficha lo dice al revés y es la misma regla: columna calculada sólo
    cuando el valor se necesita para filtrar, agrupar o relacionar — y si se
    puede calcular en el origen, mejor, porque comprime mejor y no ocupa
    lugar en el modelo.
    """
    if not nombre.strip() or not expresion.strip():
        return {"ok": False, "error": traducir("pq_sin_expresion", idioma)}
    # La expresión la escribe el usuario y termina dentro de un SELECT: se
    # valida como cualquier otro SQL antes de devolverla.
    sonda = f"SELECT {expresion} AS {_ref(nombre)} FROM {_ref(tabla)}"
    asegurar_solo_lectura(sonda)
    sql = (f"SELECT\n    *,\n    {expresion} AS {_ref(nombre)}\n"
           f"FROM {_ref(tabla)}")
    m = (f'Table.AddColumn(Origen, {_m_literal(nombre)}, '
         f'each null /* {traducir("pq_m_reemplazar", idioma)} */)')
    return {
        "ok": True, "sql": sql, "m_paso": m,
        "titulo": traducir("pq_titulo_columna", idioma).format(
            nombre=nombre, tabla=tabla),
        "nota": traducir("pq_nota_columna", idioma).format(nombre=nombre),
    }


def recetas_sugeridas(cat, idioma: str = IDIOMA_DEFECTO) -> list[dict]:
    """Qué conviene bajar al origen en ESTE modelo, mirando el catálogo.

    Sólo se sugiere lo que se puede justificar con lo que hay en el modelo:
    una columna calculada existente (se puede resolver en el origen) y una
    relación (se puede desnormalizar). Nada inventado.
    """
    fuera: list[dict] = []
    for t in cat.tablas:
        if t.get("interna"):
            continue
        for c in t["columnas"]:
            if c.get("calculada"):
                fuera.append({
                    "tipo": "columna_calculada",
                    "tabla": t["nombre"], "columna": c["nombre"],
                    "expresion_dax": c.get("expresion", ""),
                    "por_que": traducir("pq_sug_columna", idioma).format(
                        col=c["nombre"], tabla=t["nombre"]),
                })
    for r in cat.relaciones:
        if r.get("activa", True) and not r.get("muchos_a_muchos"):
            fuera.append({
                "tipo": "desnormalizar",
                "hecho": r["desde_tabla"], "dimension": r["hacia_tabla"],
                "clave_hecho": r["desde_col"], "clave_dim": r["hacia_col"],
                "por_que": traducir("pq_sug_join", idioma).format(
                    dim=r["hacia_tabla"], hecho=r["desde_tabla"]),
            })
    return fuera
