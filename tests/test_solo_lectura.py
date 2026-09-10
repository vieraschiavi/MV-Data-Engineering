"""Las fuentes SQL son de SÓLO LECTURA, y eso se verifica — no se documenta.

El producto se conecta a la base de PRODUCCIÓN de un cliente. La promesa
«sólo lectura» es la que hace que se lo autoricen. Antes de estos tests la
promesa se sostenía con un regex que mirava únicamente el ARRANQUE de la
consulta: `SELECT 1; DROP TABLE clientes` la pasaba entera.

Dos capas, y las dos se prueban acá:
  1. la consulta tiene que EMPEZAR por SELECT o WITH (lista blanca), y no
     puede traer una segunda sentencia;
  2. la conexión se abre en sólo lectura donde el motor lo soporta, y en
     todos los casos se deshace la transacción al terminar.
"""
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mvde import fuentes  # noqa: E402

# Consultas legítimas: tienen que seguir funcionando. Si esto se rompe, el
# arreglo dejó al producto sin poder leer los datos que vino a procesar.
LEGITIMAS = [
    "SELECT 1",
    "select * from clientes",
    "  \n\t SELECT * FROM t WHERE x = 1",
    "WITH x AS (SELECT 1) SELECT * FROM x",
    "with a as (select 1), b as (select 2) select * from a join b on 1=1",
    "SELECT 1;",                                  # punto y coma final: válido
    "SELECT 1;   \n  ",                           # ídem con espacios
    "-- un comentario\nSELECT 1",
    "/* comentario */ SELECT 1",
    "(SELECT 1)",                                 # subconsulta entre paréntesis
    "SELECT 'texto; con punto y coma' AS t",      # el ; está DENTRO de un literal
    "SELECT 'a--b' AS t",                         # guiones dentro de un literal
    "SELECT nombre FROM t WHERE nota = 'update ya'",   # palabra clave dentro de un literal
    # Funciones de texto que la lista negra NO tiene que confundir con escrituras.
    # Si esto se rompe, el control rechaza consultas buenas y alguien lo apaga.
    "SELECT REPLACE(nombre,'a','b') FROM t",
    "SELECT SET_UNION(a) FROM t",
    "SELECT setores, calldata FROM t",
    "SELECT COUNT(*) FROM t GROUP BY seccional HAVING COUNT(*) > 1",
    "SELECT a FROM t ORDER BY a OFFSET 10 ROWS",
    "SELECT * FROM a INTERSECT SELECT * FROM b",
    'SELECT "update" FROM t',                      # columna citada que se llama como una palabra clave
]

# Cada una de estas ejecutaría una escritura en la base del cliente.
ATAQUES = [
    "SELECT 1; DROP TABLE clientes",
    "select 1; update cuentas set saldo=0",
    "SELECT 1;\nDELETE FROM cuotas",
    "SELECT 1; TRUNCATE TABLE remision",
    "(SELECT 1); DROP TABLE t",
    "SELECT 1;; DROP TABLE t",
    "/*c*/ DROP TABLE clientes",
    "-- inocente\nDROP TABLE clientes",
    "DROP TABLE clientes",
    "INSERT INTO t VALUES (1)",
    "UPDATE t SET a = 1",
    "EXEC sp_configure",
    "GRANT ALL ON t TO publico",
    "CREATE TABLE t (a int)",
    "SELECT 1 INTO nueva_tabla FROM t",           # SELECT ... INTO escribe
    "select * from t; select * from u",           # dos lecturas: tampoco
    "",
    "   ",
]


@pytest.mark.parametrize("q", LEGITIMAS)
def test_las_consultas_de_lectura_pasan(q):
    assert fuentes.es_solo_lectura(q) is True, q


@pytest.mark.parametrize("q", ATAQUES)
def test_ninguna_escritura_pasa(q):
    assert fuentes.es_solo_lectura(q) is False, q


@pytest.mark.parametrize("q", ATAQUES)
def test_el_motor_corta_con_un_error_que_se_entiende(q):
    """No alcanza con devolver False: la etapa tiene que cortar y decir por qué."""
    with pytest.raises(fuentes.FuenteError) as e:
        fuentes.exigir_solo_lectura(q, "remision")
    assert "sólo lectura" in str(e.value)
    assert "remision" in str(e.value)      # nombra la fuente, para saber cuál del YAML


def test_una_sentencia_de_lectura_no_dispara_el_error():
    fuentes.exigir_solo_lectura("SELECT * FROM t", "t")     # no levanta


# ── Credenciales: nunca en el YAML versionado ─────────────────────────────
def test_la_url_toma_la_credencial_del_entorno(monkeypatch):
    """La regla del proyecto es que la credencial va por entorno. Si el motor
    no expande la variable, la única forma de conectarse es escribir la
    contraseña en el YAML — que es justo lo que la regla prohíbe."""
    monkeypatch.setenv("MVDE_TEST_PWD", "s3cr3ta")
    url = fuentes.expandir_entorno("postgresql://u:${MVDE_TEST_PWD}@host/db", "cartera")
    assert url == "postgresql://u:s3cr3ta@host/db"


def test_falla_cerrado_si_la_variable_no_esta(monkeypatch):
    """Fallar ABIERTO acá sería lo peor: una URL con la contraseña vacía
    conecta mal y el error real queda escondido. Es el mismo modo de falla
    que el hash mutilado por la interpolación del .env."""
    monkeypatch.delenv("MVDE_TEST_FALTA", raising=False)
    with pytest.raises(fuentes.FuenteError) as e:
        fuentes.expandir_entorno("postgresql://u:${MVDE_TEST_FALTA}@host/db", "cartera")
    assert "MVDE_TEST_FALTA" in str(e.value)
    assert "cartera" in str(e.value)


def test_sin_variables_la_url_queda_igual():
    u = "postgresql://usuario:clave@host:5432/base"
    assert fuentes.expandir_entorno(u, "x") == u


def test_el_mensaje_de_error_no_filtra_la_contrasena(monkeypatch):
    """Un error que imprime la URL entera deja la contraseña en el log."""
    monkeypatch.setenv("MVDE_TEST_PWD", "s3cr3ta")
    f = {"nombre": "cartera", "tipo": "sql",
         "url": "postgresql://u:${MVDE_TEST_PWD}@host/db",
         "consulta": "SELECT 1; DROP TABLE t"}
    with pytest.raises(fuentes.FuenteError) as e:
        fuentes._leer_sql(f)
    assert "s3cr3ta" not in str(e.value)


# ── Prueba de fuego: atacar una base REAL y ver si sobrevive ──────────────
def _base_de_prueba(tmp_path):
    import sqlite3
    ruta = tmp_path / "cliente.db"
    con = sqlite3.connect(ruta)
    con.execute("CREATE TABLE remision (id INTEGER, litros REAL)")
    con.executemany("INSERT INTO remision VALUES (?,?)", [(1, 100.0), (2, 250.5)])
    con.commit()
    con.close()
    return ruta


def _filas(ruta):
    import sqlite3
    con = sqlite3.connect(ruta)
    try:
        return con.execute("SELECT COUNT(*) FROM remision").fetchone()[0]
    finally:
        con.close()


def test_la_lectura_normal_funciona_contra_una_base_real(tmp_path):
    ruta = _base_de_prueba(tmp_path)
    df, proc = fuentes.leer({"nombre": "remision", "tipo": "sqlite", "ruta": str(ruta)},
                            str(tmp_path))
    assert len(df) == 2 and set(df.columns) == {"id", "litros"}
    assert proc                      # deja procedencia de la lectura


@pytest.mark.parametrize("ataque", [
    "SELECT 1; DROP TABLE remision",
    "SELECT 1; DELETE FROM remision",
    "SELECT 1; UPDATE remision SET litros = 0",
    "DROP TABLE remision",
])
def test_el_ataque_no_toca_la_base(tmp_path, ataque):
    """Lo que se verifica no es el mensaje de error: es que la tabla siga entera."""
    ruta = _base_de_prueba(tmp_path)
    antes = _filas(ruta)
    with pytest.raises(fuentes.FuenteError):
        fuentes.leer({"nombre": "remision", "tipo": "sqlite", "ruta": str(ruta),
                      "consulta": ataque}, str(tmp_path))
    assert _filas(ruta) == antes == 2      # la tabla existe y tiene las dos filas
