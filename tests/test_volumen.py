"""El techo de volumen: medido, avisado, y con el CSV leído por el motor rápido.

Tres cosas se verifican acá:

1. La lectura de CSV detecta el separador SOLA (como antes) pero por el motor
   en C, no por el de Python. Medido sobre 1 000 000 de filas: 5,42 s con el
   motor de Python contra 0,67 s con el de C — 8 veces. Lo pagaba cada lectura
   de cada corrida.
2. El motor AVISA cuando la tabla que va a cargar no entra cómoda en la
   memoria de la máquina, en vez de morir con MemoryError a mitad de camino.
3. `limite_filas` permite cortar a propósito, para probar un pipeline nuevo
   contra una fuente grande sin esperar la carga entera.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mvde import fuentes  # noqa: E402


# ── 1 · el separador se sigue detectando solo, pero por el motor rápido ────
@pytest.mark.parametrize("sep,nombre", [
    (",", "coma"),
    (";", "punto y coma — el default de Excel en español"),
    ("\t", "tabulación"),
    ("|", "pipe"),
])
def test_detecta_el_separador_solo(tmp_path, sep, nombre):
    p = tmp_path / "d.csv"
    p.write_text(f"a{sep}b{sep}c\n1{sep}2{sep}3\n4{sep}5{sep}6\n", encoding="utf-8")
    df, _ = fuentes.leer({"nombre": "d", "tipo": "csv", "ruta": "d.csv"}, str(tmp_path))
    assert list(df.columns) == ["a", "b", "c"], nombre
    assert len(df) == 2, nombre


def test_usa_el_motor_en_c(tmp_path):
    """El motor de Python es ~8 veces más lento. Si alguien vuelve a poner
    `engine="python"` como default, este test lo marca."""
    p = tmp_path / "d.csv"
    p.write_text("a,b\n1,2\n", encoding="utf-8")
    plan = fuentes.plan_lectura_csv(str(p), {})
    assert plan.get("engine") != "python"
    assert plan.get("sep") == ","


def test_respeta_lo_que_el_yaml_declara_explicito(tmp_path):
    """Si el YAML pide un separador o un motor, gana el YAML: la detección
    automática es una comodidad, no una imposición."""
    p = tmp_path / "d.csv"
    p.write_text("a;b\n1;2\n", encoding="utf-8")
    plan = fuentes.plan_lectura_csv(str(p), {"sep": "\t", "engine": "python"})
    assert plan["sep"] == "\t" and plan["engine"] == "python"


def test_el_bom_de_excel_no_se_come_el_primer_encabezado(tmp_path):
    p = tmp_path / "d.csv"
    p.write_bytes("﻿a,b\n1,2\n".encode("utf-8"))
    df, _ = fuentes.leer({"nombre": "d", "tipo": "csv", "ruta": "d.csv"}, str(tmp_path))
    assert list(df.columns) == ["a", "b"]


def test_un_csv_raro_no_rompe_la_lectura(tmp_path):
    """Si no se puede detectar el separador, cae al camino de antes en vez de
    fallar: perder velocidad es aceptable, no poder leer no."""
    p = tmp_path / "d.csv"
    p.write_text("unaColumnaSola\n1\n2\n", encoding="utf-8")
    df, _ = fuentes.leer({"nombre": "d", "tipo": "csv", "ruta": "d.csv"}, str(tmp_path))
    assert len(df) == 2


# ── 2 · el aviso de volumen ────────────────────────────────────────────────
def test_estima_la_memoria_de_un_dataframe():
    df = pd.DataFrame({"a": range(1000), "b": ["texto"] * 1000})
    mb = fuentes.memoria_mb(df)
    assert mb > 0 and mb < 5


def test_avisa_cuando_la_tabla_no_entra_comoda(monkeypatch):
    """No es un corte: es un aviso que queda en la evidencia de la etapa. Cortar
    sería peor — el que decide si sigue es el dueño del proyecto."""
    df = pd.DataFrame({"a": range(200_000), "b": ["x" * 50] * 200_000})
    mb = fuentes.memoria_mb(df)
    # Se fija la RAM simulada EN FUNCIÓN de lo que mide el DataFrame, para que
    # el test no dependa de cuánto ocupa un str en esta versión de pandas.
    monkeypatch.setattr(fuentes, "ram_disponible_mb", lambda: mb * 2)
    aviso = fuentes.aviso_de_volumen("hechos", df)
    assert aviso and "hechos" in aviso
    assert "memoria" in aviso.lower()
    assert f"{mb:,.0f} MB" in aviso          # dice el número medido, no uno genérico


def test_no_avisa_cuando_entra_sobrado(monkeypatch):
    monkeypatch.setattr(fuentes, "ram_disponible_mb", lambda: 32_000.0)
    assert fuentes.aviso_de_volumen("chica", pd.DataFrame({"a": [1, 2, 3]})) == ""


def test_sin_dato_de_ram_no_inventa_un_aviso(monkeypatch):
    """En un sistema donde no se puede leer la RAM, callarse es lo correcto:
    un aviso inventado entrena a la gente a ignorar los avisos."""
    monkeypatch.setattr(fuentes, "ram_disponible_mb", lambda: None)
    df = pd.DataFrame({"a": range(50_000)})
    assert fuentes.aviso_de_volumen("x", df) == ""


# ── 3 · límite deliberado de filas ─────────────────────────────────────────
def test_limite_filas_corta_la_lectura(tmp_path):
    p = tmp_path / "d.csv"
    p.write_text("a,b\n" + "".join(f"{i},{i*2}\n" for i in range(500)), encoding="utf-8")
    df, proc = fuentes.leer({"nombre": "d", "tipo": "csv", "ruta": "d.csv",
                             "limite_filas": 100}, str(tmp_path))
    assert len(df) == 100
    assert proc.get("limite_filas") == 100      # queda en la procedencia


def test_el_limite_queda_registrado_para_que_nadie_lo_confunda_con_el_total(tmp_path):
    """Una corrida limitada que no lo dice es una corrida que alguien va a
    presentar como si fuera el total."""
    p = tmp_path / "d.csv"
    p.write_text("a\n" + "".join(f"{i}\n" for i in range(50)), encoding="utf-8")
    _, proc = fuentes.leer({"nombre": "d", "tipo": "csv", "ruta": "d.csv",
                            "limite_filas": 10}, str(tmp_path))
    assert proc["limite_filas"] == 10
    assert proc.get("parcial") is True


def test_sin_limite_no_marca_parcial(tmp_path):
    p = tmp_path / "d.csv"
    p.write_text("a\n1\n2\n", encoding="utf-8")
    _, proc = fuentes.leer({"nombre": "d", "tipo": "csv", "ruta": "d.csv"}, str(tmp_path))
    assert not proc.get("parcial")
