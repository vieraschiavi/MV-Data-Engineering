# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · La empresa propia: quién es «nosotros» en el modelo.

Un dataset de mercado trae varias corporaciones y nada dice cuál es la
del informe. Sin saberlo, el share solo puede calcularse «lo filtrado
sobre el mercado»: correcto con la corporación en el eje, y 100 % en
una tarjeta sin filtro — que fue exactamente lo que un usuario vio en un
informe entregado. Con la empresa conocida existe «Share Empresa %»: lo
de ESA corporación sobre el mercado, valga lo que valga el contexto.

La elección se guarda como anotación del modelo: viaja adentro del
archivo, así que quien lo reciba no tiene que volver a decirla. De dónde
sale, en orden de confianza:

  1. La anotación, si ya está.
  2. Lo que las medidas del modelo nombran («Ventas Adium USD» dice de
     qué lado está parado quien lo escribió).
  3. El usuario, eligiendo entre los valores reales de la columna de
     corporación o escribiéndola.
  4. La IA, a pedido y con la clave del usuario: propone una de las
     candidatas reales, nunca un nombre inventado.
"""
from __future__ import annotations

import copy

from .catalogo import Catalogo, _norm
from .i18n import IDIOMA_DEFECTO, t as traducir
from .periodos import ANOTACION_EMPRESA, columna_corporacion

ANOTACION = ANOTACION_EMPRESA


def propia(modelo: dict) -> str | None:
    """La empresa anotada en el modelo, o `None`."""
    for a in modelo.get("model", {}).get("annotations", []) or []:
        if isinstance(a, dict) and a.get("name") == ANOTACION:
            return str(a.get("value") or "") or None
    return None


def fijar(modelo: dict, nombre: str,
          idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[str]]:
    """Anota la empresa propia en el modelo (o la borra con vacío)."""
    modelo = copy.deepcopy(modelo)
    m = modelo.setdefault("model", {})
    anots = [a for a in m.get("annotations", []) or []
             if not (isinstance(a, dict) and a.get("name") == ANOTACION)]
    nombre = (nombre or "").strip()
    if nombre:
        anots.append({"name": ANOTACION, "value": nombre})
        cambios = [traducir("em_fijada", idioma).format(empresa=nombre)]
    else:
        cambios = [traducir("em_borrada", idioma)]
    m["annotations"] = anots
    return modelo, cambios


def columna(cat: Catalogo) -> tuple[str, str] | None:
    """La columna que dice quién vende, si el modelo tiene competencia."""
    return columna_corporacion(cat)


def candidatas(modelo: dict, datos: dict | None = None) -> list[str]:
    """Los valores reales de la columna de corporación, de más a menos
    frecuente. `datos` es `{tabla: (columnas, filas)}`; sin él se leen las
    filas que el modelo lleve adentro."""
    from .dataset import datos_del_modelo

    cat = Catalogo.desde_modelo(modelo)
    corp = columna_corporacion(cat)
    if not corp:
        return []
    datos = datos or datos_del_modelo(modelo)
    conteo: dict[str, int] = {}
    for tabla, (cols, filas) in (datos or {}).items():
        if _norm(tabla) != _norm(corp[0]):
            continue
        idx = next((i for i, c in enumerate(cols)
                    if _norm(c) == _norm(corp[1])), None)
        if idx is None:
            continue
        for f in filas:
            if idx < len(f) and f[idx] not in (None, ""):
                v = str(f[idx])
                conteo[v] = conteo.get(v, 0) + 1
    return [v for v, _n in sorted(conteo.items(), key=lambda p: (-p[1], p[0]))]


def detectar(modelo: dict, valores: list[str] | None = None) -> str | None:
    """La empresa propia sin preguntar, solo con evidencia: la anotación o
    lo que las medidas nombran. `None` cuando no hay cómo saberlo — ahí se
    pregunta, no se adivina por tamaño."""
    anotada = propia(modelo)
    if anotada:
        return anotada
    cat = Catalogo.desde_modelo(modelo)
    valores = valores if valores is not None else candidatas(modelo)
    nombres = " ".join(_norm(m["nombre"]) for m in cat.medidas())
    nombres += " " + _norm(modelo.get("name", ""))
    halladas = {v for v in valores if _norm(v) and _norm(v) in nombres}
    if len(halladas) == 1:
        return halladas.pop()
    return None


def detectar_con_ia(modelo: dict, valores: list[str],
                    contexto: str = "", proveedor: str = "", modelo_ia: str = "",
                    api_key: str | None = None, endpoint: str = "") -> str | None:
    """Le pide a la IA que elija UNA de las candidatas reales. Lo que
    devuelva se acepta solo si está en la lista: un nombre inventado es
    `None`, no una empresa."""
    from . import proveedores_ia

    if not valores:
        return None
    cat = Catalogo.desde_modelo(modelo)
    pistas = {
        "archivo_o_modelo": contexto or modelo.get("name", ""),
        "tablas": [t["nombre"] for t in cat.tablas if not t.get("interna")],
        "medidas": [m["nombre"] for m in cat.medidas()][:40],
        "corporaciones": valores,
    }
    import json
    sistema = ("Un modelo de Power BI trae varias corporaciones en su "
               "columna de mercado. Decidí cuál es la EMPRESA DUEÑA del "
               "informe (la propia; las demás son competidoras) usando el "
               "nombre del archivo, de las tablas y de las medidas. "
               "Respondé SOLO con uno de los valores de «corporaciones», "
               "tal cual está escrito, o con NINGUNA si no hay evidencia.")
    kwargs = {"api_key": api_key, "endpoint": endpoint, "modelo": modelo_ia}
    if proveedor:
        kwargs["proveedor"] = proveedor
    respuesta = proveedores_ia.consultar(
        [{"role": "user", "content": json.dumps(pistas, ensure_ascii=False)}],
        sistema=sistema, **kwargs)
    texto = _norm(respuesta.strip().strip('"').strip("'"))
    for v in valores:
        if _norm(v) == texto or (_norm(v) and _norm(v) in texto
                                 and len(_norm(v)) > 2):
            return v
    return None


def elegir(modelo: dict, texto: str, valores: list[str] | None = None,
           idioma: str = IDIOMA_DEFECTO) -> tuple[dict, list[str]]:
    """Fija la empresa escrita por el usuario. Si hay valores reales y el
    texto coincide con uno (sin acentos ni mayúsculas), se guarda el valor
    REAL — el share filtra por igualdad exacta y «adium» no es «ADIUM»."""
    texto = (texto or "").strip()
    valores = valores if valores is not None else candidatas(modelo)
    real = next((v for v in valores if _norm(v) == _norm(texto)), None)
    if valores and real is None:
        parecidas = [v for v in valores if _norm(texto) in _norm(v)
                     or _norm(v) in _norm(texto)]
        if len(parecidas) == 1:
            real = parecidas[0]
    if valores and real is None:
        raise ValueError(traducir("em_no_esta", idioma).format(
            texto=texto, lista=", ".join(valores[:12])))
    return fijar(modelo, real or texto, idioma)
