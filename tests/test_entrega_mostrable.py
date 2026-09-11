"""La carpeta de entrega tiene que poder abrirse delante de un gerente.

Dos defectos que rompían una presentación, los dos generales a cualquier
proyecto y los dos encontrados mirando la salida real de la demo `conaprole`:

1. **La etapa `powerbi` genera DOS `.pbit`** y nada decía cuál era cuál. El
   parametrizado (33 KB) pide la carpeta de los CSV al abrirlo; el `_demo`
   (431 KB) trae los datos adentro y abre solo. Los dos caían en `entrega/`
   con nombres casi iguales, y el resumen de la etapa decía «.pbit + PBIP» en
   singular. Quien hace la demo abre el chico, Power BI le pide una ruta
   delante de la sala, y ahí se termina la demo.
2. **`RESUMEN.md` y `manifiesto.json` listaban rutas absolutas.** Los dos
   documentos se le entregan al cliente y llevaban adentro el árbol de
   carpetas y el nombre de usuario de la máquina que corrió el pipeline.
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import pytest  # noqa: E402

from mvde import demos  # noqa: E402
from mvde.orquestador import Pipeline  # noqa: E402


@pytest.fixture(scope="module")
def entregado(tmp_path_factory):
    d = tmp_path_factory.mktemp("entrega")
    p = Pipeline.desde_yaml(demos.crear("conaprole", d))
    p.correr(hasta="entrega")
    return p


def test_dice_cual_pbit_abrir_en_una_demo(entregado):
    ev = entregado.resultados["powerbi"].evidencia
    if not ev.get("para_abrir_en_una_demo"):
        pytest.skip("este proyecto no generó la copia con datos embebidos")
    assert ev["para_abrir_en_una_demo"].endswith("_demo.pbit")
    assert ev["para_conectar_a_los_datos"] != ev["para_abrir_en_una_demo"]
    # Y lo dice en el resumen de la etapa, que es lo que se lee de un vistazo.
    assert "abrir" in entregado.resultados["powerbi"].resumen


def test_el_resumen_de_entrega_tiene_una_seccion_de_que_abrir(entregado):
    texto = (entregado.dirs["entrega"] / "RESUMEN.md").read_text(encoding="utf-8")
    assert "## Qué abrir" in texto
    assert "trae los datos adentro" in texto
    assert "DataPath" in texto, "hay que decir que el otro pide una ruta, no dejar que la descubran"
    assert "reporte.html" in texto


def test_los_dos_pbit_llegan_a_la_carpeta_de_entrega(entregado):
    nombres = {p.name for p in entregado.dirs["entrega"].glob("*.pbit")}
    ev = entregado.resultados["powerbi"].evidencia
    assert ev["para_conectar_a_los_datos"] in nombres
    if ev.get("para_abrir_en_una_demo"):
        assert ev["para_abrir_en_una_demo"] in nombres


def test_el_resumen_no_lleva_rutas_absolutas_de_la_maquina(entregado):
    """Lo que se le manda al cliente no tiene por qué contar cómo está armado
    el disco de la consultora."""
    texto = (entregado.dirs["entrega"] / "RESUMEN.md").read_text(encoding="utf-8")
    for linea in texto.splitlines():
        if linea.startswith("- `") and "`" in linea[3:]:
            ruta = linea[3:].split("`")[0]
            assert not ruta.startswith(("/", "\\")), f"ruta absoluta en el resumen: {ruta}"
            assert ":\\" not in ruta, f"ruta absoluta de Windows en el resumen: {ruta}"


def test_el_manifiesto_tampoco(entregado):
    m = json.loads((entregado.dirs["entrega"] / "manifiesto.json").read_text(encoding="utf-8"))
    for etapa, datos in m["etapas"].items():
        for a in datos["artefactos"]:
            assert not a.startswith(("/", "\\")) and ":\\" not in a, f"{etapa}: {a}"


def test_los_artefactos_declarados_existen_de_verdad(entregado):
    """Una lista de artefactos con un archivo que no está es peor que no tener
    lista: manda a buscar algo que no se generó."""
    m = json.loads((entregado.dirs["entrega"] / "manifiesto.json").read_text(encoding="utf-8"))
    faltan = [a for datos in m["etapas"].values() for a in datos["artefactos"]
              if not (entregado.salida / a).exists()]
    assert not faltan, f"declarados y ausentes: {faltan}"


def test_en_memoria_las_rutas_siguen_siendo_absolutas(entregado):
    """La app necesita abrir los archivos: lo que se relativiza es el
    documento, no el objeto."""
    arts = entregado.resultados["reporte"].artefactos
    assert arts and all(Path(a).is_absolute() for a in arts)
