"""Modo confidencial: el programa NO PUEDE sacar datos de la red donde corre.

Estos tests son la evidencia que se le muestra al área de seguridad del
cliente. Cada uno recorre un camino de salida real del motor con el modo
encendido y verifica que corta — y, tan importante como eso, que con el modo
apagado el camino sigue existiendo, para que nadie confunda «bloqueado» con
«roto».
"""
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mvde import confidencial, fuentes, ia  # noqa: E402


@pytest.fixture
def modo_on(monkeypatch):
    monkeypatch.setenv(confidencial.ENV, "1")


@pytest.fixture
def modo_off(monkeypatch):
    monkeypatch.delenv(confidencial.ENV, raising=False)


# ── El interruptor ────────────────────────────────────────────────────────
def test_el_modo_se_lee_del_entorno_en_cada_llamada(monkeypatch):
    """Se lee cada vez y no al importar: si se cacheara, el estado dependería
    del orden en que se cargaron los módulos y un test no podría apagarlo."""
    monkeypatch.delenv(confidencial.ENV, raising=False)
    assert not confidencial.activo()
    monkeypatch.setenv(confidencial.ENV, "1")
    assert confidencial.activo()
    monkeypatch.setenv(confidencial.ENV, "0")
    assert not confidencial.activo()


@pytest.mark.parametrize("valor", ["1", "true", "TRUE", "si", "sí", "yes", "on"])
def test_acepta_las_formas_en_que_la_gente_escribe_que_si(monkeypatch, valor):
    """Que el modo dependa de acertar la palabra exacta sería justo la
    fragilidad que este módulo existe para no tener."""
    monkeypatch.setenv(confidencial.ENV, valor)
    assert confidencial.activo()


@pytest.mark.parametrize("valor", ["", "0", "false", "no", "off", "  "])
def test_no_se_enciende_solo(monkeypatch, valor):
    monkeypatch.setenv(confidencial.ENV, valor)
    assert not confidencial.activo()


# ── Fuentes ───────────────────────────────────────────────────────────────
@pytest.mark.parametrize("ruta", [
    "https://ejemplo.com/datos.csv",
    "http://ejemplo.com/datos.csv",
    "s3://bucket/datos.csv",
    "gs://bucket/datos.csv",
    "az://cuenta/datos.csv",
    "abfss://cont@cuenta.dfs.core.windows.net/datos.csv",
])
def test_ninguna_ruta_remota_pasa_con_el_modo_activo(modo_on, ruta):
    """Cubre el caso que se escapa de `_leer_url`: una fuente declarada
    `tipo: csv` cuya `ruta` es un http:// o un s3://."""
    with pytest.raises(confidencial.SalidaBloqueada) as e:
        fuentes._ruta({"nombre": "x", "ruta": ruta}, ".")
    assert ruta in str(e.value)          # el mensaje nombra el destino


def test_la_ruta_local_sigue_funcionando(modo_on, tmp_path):
    """El borde que se defiende es la SALIDA de la red del cliente, no el
    acceso a lo que ya está adentro. Si esto se rompiera, el modo dejaría al
    producto sin poder leer los datos que vino a procesar."""
    (tmp_path / "d.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    assert fuentes._ruta({"nombre": "x", "ruta": "d.csv"}, str(tmp_path)).endswith("d.csv")


def test_kaggle_no_descarga_con_el_modo_activo(modo_on, tmp_path):
    with pytest.raises(confidencial.SalidaBloqueada):
        fuentes._leer_kaggle({"dataset": "alguien/algo", "archivo": "x.csv"}, str(tmp_path))


def test_kaggle_ya_descargado_se_lee_sin_red(modo_on, tmp_path):
    """Sólo se bloquea la DESCARGA. Un archivo que ya está en el disco de la VM
    no cruza ningún borde al leerse."""
    destino = tmp_path / "data" / "raw"
    destino.mkdir(parents=True)
    (destino / "x.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    df = fuentes._leer_kaggle({"dataset": "alguien/algo", "archivo": "x.csv"}, str(tmp_path))
    assert list(df.columns) == ["a", "b"] and len(df) == 1


def test_sin_el_modo_la_ruta_remota_se_resuelve(modo_off):
    """El camino existe: lo que cambia es el permiso, no la capacidad."""
    assert fuentes._ruta({"nombre": "x", "ruta": "s3://b/d.csv"}, ".") == "s3://b/d.csv"


# ── IA ────────────────────────────────────────────────────────────────────
def test_la_ia_externa_no_esta_disponible_con_el_modo_activo(modo_on):
    """No es un error: `preguntar()` mira `disponible()` y cae solo al modo
    LOCAL, que responde con los datos de la corrida sin salir de la máquina."""
    assert ia.disponible() is False


def test_listar_modelos_corta_porque_viaja_con_la_clave(modo_on):
    """Acá no se degrada: el pedido lleva la API key y le confirma al proveedor
    que existe un despliegue usándola."""
    with pytest.raises(confidencial.SalidaBloqueada):
        ia.listar_modelos("claude", api_key="sk-loquesea")


def test_el_modo_local_de_ia_sigue_respondiendo(modo_on):
    """La función no se rompe, deja de viajar: sin proveedor la respuesta sale
    igual, armada con lo que hay en el proyecto."""
    assert isinstance(ia.proveedores(), dict) and ia.proveedores()


# ── Constancia para la auditoría ──────────────────────────────────────────
def test_el_estado_queda_por_escrito(modo_on):
    e = confidencial.estado()
    assert e["activo"] is True
    assert e["variable"] == "MVDE_CONFIDENCIAL"
    assert "proveedores de IA" in e["bloquea"]
    assert "no pudo sacar datos" in e["nota"]


def test_apagado_el_estado_lo_dice_sin_ambiguedad(modo_off):
    e = confidencial.estado()
    assert e["activo"] is False and e["bloquea"] == []
    assert "APAGADO" in e["nota"]


def test_el_manifiesto_de_una_corrida_lleva_el_modo(modo_on, tmp_path):
    """Una corrida sobre datos de un cliente que no deja constancia de si podía
    salir a internet obliga a confiar en la memoria de alguien."""
    from mvde import demos
    from mvde.orquestador import Pipeline
    ruta = demos.crear("cartera", tmp_path)
    p = Pipeline.desde_yaml(ruta)
    p.correr(hasta="entrega")
    import json
    man = json.loads((p.dirs["entrega"] / "manifiesto.json").read_text(encoding="utf-8"))
    assert man["confidencial"]["activo"] is True
    resumen = (p.dirs["entrega"] / "RESUMEN.md").read_text(encoding="utf-8")
    assert "Modo confidencial ACTIVO" in resumen
