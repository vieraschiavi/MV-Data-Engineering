# © 2026 Martín Viera. Todos los derechos reservados.
"""El orquestador: corre las 12 etapas en orden con gate, deja evidencia y
artefactos por etapa, persiste el estado y permite reanudar desde cualquiera.

    from mvde.orquestador import Pipeline
    p = Pipeline.desde_yaml("proyecto.yaml")
    estado = p.correr()                 # todo
    estado = p.correr(desde="gold")     # reanudar
    p.etapa("calidad")                  # una sola

Regla: una etapa devuelve `Resultado`; si `ok` es False y la etapa no es
opcional, las siguientes no corren. Nada de `except: pass`.
"""
from __future__ import annotations

import json
import logging
import shutil
import time
import traceback
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from . import ETAPAS, __version__
from . import almacen, bronze, calidad, dax, fuentes, gobernanza, gold, ml, powerbi, proyecto, reporte, silver

log = logging.getLogger("mvde")
OPCIONALES = {"ml", "powerbi"}


@dataclass
class Resultado:
    etapa: str
    ok: bool
    resumen: str = ""
    evidencia: dict = field(default_factory=dict)
    artefactos: list[str] = field(default_factory=list)
    error: str = ""
    omitida: bool = False
    segundos: float = 0.0
    en: str = ""

    def estado(self) -> str:
        return "omitida" if self.omitida else "ok" if self.ok else "fallo"


class Pipeline:
    def __init__(self, spec: dict, salida: Path | None = None):
        self.spec = spec
        base = Path(spec.get("_base") or ".")
        self.salida = Path(salida) if salida else base / str(spec.get("salida") or "salidas") / _slug(spec["nombre"])
        self.salida.mkdir(parents=True, exist_ok=True)
        self.dirs = {k: self.salida / k for k in ("bronze", "silver", "gold", "almacen", "gobernanza", "ml", "reporte", "powerbi", "entrega")}
        self.tablas: dict[str, pd.DataFrame] = {}
        self.silver: dict[str, pd.DataFrame] = {}
        self.gold: dict[str, pd.DataFrame] = {}
        self.procedencia: dict[str, dict] = {}
        self.calidad: dict = {}
        self.kpis: list[dict] = []
        self.catalogo = pd.DataFrame()
        self.ml: dict | None = None
        self.medidas: list[dict] = []
        self.resultados: dict[str, Resultado] = {}
        self._cargar_estado()

    # ------------------------------------------------------------ helpers
    @classmethod
    def desde_yaml(cls, ruta: str | Path, salida: Path | None = None) -> "Pipeline":
        return cls(proyecto.cargar(ruta), salida)

    @property
    def ruta_db(self) -> Path:
        return self.dirs["almacen"] / "warehouse.duckdb"

    def _estado_path(self) -> Path:
        return self.salida / "estado.json"

    def _cargar_estado(self) -> None:
        p = self._estado_path()
        if p.exists():
            try:
                datos = json.loads(p.read_text(encoding="utf-8"))
                for e, r in datos.get("etapas", {}).items():
                    self.resultados[e] = Resultado(**r)
            except (json.JSONDecodeError, TypeError):
                pass

    def guardar_estado(self) -> Path:
        datos = {"proyecto": self.spec["nombre"], "version": __version__, "actualizado": datetime.now().isoformat(timespec="seconds"),
                 "etapas": {e: asdict(r) for e, r in self.resultados.items()}}
        self._estado_path().write_text(json.dumps(datos, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        return self._estado_path()

    def _rehidratar(self, hasta: str) -> None:
        """Al reanudar desde una etapa, se cargan de disco los productos de las anteriores."""
        idx = ETAPAS.index(hasta)
        if idx > ETAPAS.index("bronze"):
            for f in self.spec["fuentes"]:
                p = self.dirs["bronze"] / f["nombre"] / "part-000.parquet"
                if p.exists():
                    self.tablas[f["nombre"]] = bronze.leer(f["nombre"], self.dirs["bronze"])
        if idx > ETAPAS.index("silver"):
            for p in self.dirs["silver"].glob("*.parquet"):
                self.silver[p.stem] = pd.read_parquet(p)
        if idx > ETAPAS.index("calidad") and (self.dirs["silver"] / "calidad.json").exists():
            self.calidad = json.loads((self.dirs["silver"] / "calidad.json").read_text(encoding="utf-8"))
        if idx > ETAPAS.index("gold"):
            for p in self.dirs["gold"].glob("*.parquet"):
                self.gold[p.stem] = pd.read_parquet(p)
        if idx > ETAPAS.index("gobernanza") and (self.dirs["gobernanza"] / "catalogo.csv").exists():
            self.catalogo = pd.read_csv(self.dirs["gobernanza"] / "catalogo.csv")
        if idx > ETAPAS.index("ml") and (self.dirs["ml"] / "ml.json").exists():
            self.ml = json.loads((self.dirs["ml"] / "ml.json").read_text(encoding="utf-8"))
        if idx > ETAPAS.index("reporte") and (self.dirs["reporte"] / "kpis.json").exists():
            self.kpis = json.loads((self.dirs["reporte"] / "kpis.json").read_text(encoding="utf-8"))
        if idx > ETAPAS.index("dax") and (self.dirs["powerbi"] / "medidas.json").exists():
            self.medidas = json.loads((self.dirs["powerbi"] / "medidas.json").read_text(encoding="utf-8"))

    # ------------------------------------------------------------ correr
    def correr(self, desde: str = "fuentes", hasta: str = "entrega") -> dict[str, Resultado]:
        if desde not in ETAPAS or hasta not in ETAPAS:
            raise ValueError(f"etapa desconocida; válidas: {ETAPAS}")
        if desde != "fuentes":
            self._rehidratar(desde)
        for e in ETAPAS[ETAPAS.index(desde): ETAPAS.index(hasta) + 1]:
            r = self.etapa(e)
            if not r.ok and not r.omitida:
                log.error("gate: %s falló → se detiene el pipeline", e)
                break
        return self.resultados

    def etapa(self, nombre: str) -> Resultado:
        fn = getattr(self, f"_{nombre}")
        t0 = time.perf_counter()
        log.info("=== %s", nombre)
        try:
            r = fn()
        except Exception as exc:  # noqa: BLE001 - se registra completo y se relanza en el estado
            r = Resultado(nombre, False, error=f"{type(exc).__name__}: {exc}",
                          evidencia={"traceback": traceback.format_exc().splitlines()[-6:]})
            if nombre in OPCIONALES:
                r.omitida, r.ok = True, False
                r.resumen = f"omitida: {r.error}"
        r.segundos = round(time.perf_counter() - t0, 2)
        r.en = datetime.now().isoformat(timespec="seconds")
        self.resultados[nombre] = r
        for e in ETAPAS[ETAPAS.index(nombre) + 1:]:
            self.resultados.pop(e, None)          # lo posterior queda desactualizado
        self.guardar_estado()
        log.info("=== %s %s (%.1fs) %s", nombre, r.estado().upper(), r.segundos, r.resumen or r.error)
        return r

    # ------------------------------------------------------------ etapas
    def _fuentes(self) -> Resultado:
        base = self.spec.get("_base") or "."
        self.tablas, self.procedencia = {}, {}
        for f in self.spec["fuentes"]:
            df, proc = fuentes.leer(f, base)
            self.tablas[f["nombre"]] = df
            self.procedencia[f["nombre"]] = proc
        ev = {n: {k: v for k, v in p.items() if k != "nombre"} for n, p in self.procedencia.items()}
        return Resultado("fuentes", True, f"{len(self.tablas)} fuentes leídas", ev)

    def _bronze(self) -> Resultado:
        if not self.tablas:
            raise RuntimeError("no hay fuentes cargadas: corré la etapa fuentes")
        rutas = []
        for n, df in self.tablas.items():
            rutas.append(str(bronze.escribir(n, df, self.procedencia.get(n, {}), self.dirs["bronze"])))
        return Resultado("bronze", True, f"{len(rutas)} tablas en Parquet con linaje",
                         {n: {"filas": int(len(df)), "columnas": int(df.shape[1])} for n, df in self.tablas.items()}, rutas)

    def _silver(self) -> Resultado:
        if not self.tablas:
            raise RuntimeError("no hay bronze: corré desde fuentes")
        self.dirs["silver"].mkdir(parents=True, exist_ok=True)
        cfg = self.spec.get("silver") or {}
        ev, rutas = {}, []
        self.silver = {}
        for n, df in self.tablas.items():
            out, notas = silver.transformar(n, df, cfg.get(n))
            self.silver[n] = out
            p = self.dirs["silver"] / f"{n}.parquet"
            out.to_parquet(p, index=False)
            rutas.append(str(p))
            ev[n] = {"filas": int(len(out)), "columnas": int(out.shape[1]), "notas": notas}
        return Resultado("silver", True, f"{len(self.silver)} tablas conformadas", ev, rutas)

    def _calidad(self) -> Resultado:
        if not self.silver:
            raise RuntimeError("no hay silver")
        self.calidad = calidad.correr(self.spec, self.silver)
        p = self.dirs["silver"] / "calidad.json"
        reporte.guardar_json(p, self.calidad)
        ev = {"puntaje": self.calidad["puntaje"], "reglas": self.calidad["reglas"],
              "por_dimension": self.calidad["por_dimension"], "fallidas": self.calidad["fallidas"]}
        if not self.calidad["paso"]:
            return Resultado("calidad", False, error="reglas críticas fallidas: " + ", ".join(self.calidad["criticas_fallidas"]),
                             evidencia=ev, artefactos=[str(p)])
        return Resultado("calidad", True, f"puntaje {self.calidad['puntaje']} · {self.calidad['reglas']} reglas · {len(self.calidad['fallidas'])} hallazgos no críticos", ev, [str(p)])

    def _gold(self) -> Resultado:
        if not self.silver:
            raise RuntimeError("no hay silver")
        self.dirs["gold"].mkdir(parents=True, exist_ok=True)
        previo = {p.stem: pd.read_parquet(p) for p in self.dirs["gold"].glob("dim_*.parquet")}
        self.gold, notas = gold.construir(self.spec, self.silver, previo, date.today())
        rutas = []
        for n, df in self.gold.items():
            p = self.dirs["gold"] / f"{n}.parquet"
            df.to_parquet(p, index=False)
            rutas.append(str(p))
        return Resultado("gold", True, f"{len(self.gold)} tablas del modelo",
                         {"tablas": {n: int(len(df)) for n, df in self.gold.items()}, "notas": notas}, rutas)

    def _almacen(self) -> Resultado:
        if not self.gold:
            raise RuntimeError("no hay gold")
        info = almacen.cargar(self.gold, self.ruta_db, self.spec.get("vistas") or {})
        ev = dict(info)
        pub = (self.spec.get("almacen") or {}).get("publicar")
        if pub and pub.get("url"):
            ev["publicacion"] = almacen.publicar(self.gold, pub["url"], pub.get("esquema"))
        if info["vistas_con_error"]:
            return Resultado("almacen", False, error="vistas con error: " + "; ".join(f"{k}: {v}" for k, v in info["vistas_con_error"].items()), evidencia=ev)
        return Resultado("almacen", True, f"{len(info['tablas'])} tablas y {len(info['vistas'])} vistas en DuckDB", ev, [str(self.ruta_db)])

    def _gobernanza(self) -> Resultado:
        self.dirs["gobernanza"].mkdir(parents=True, exist_ok=True)
        capas = {"silver": self.silver, "gold": self.gold}
        self.catalogo = gobernanza.catalogo(capas, self.spec)
        lin = gobernanza.linaje(self.spec, self.spec.get("silver") or {}, self.gold)
        punt = gobernanza.puntajes(self.calidad, self.catalogo)
        p1 = self.dirs["gobernanza"] / "catalogo.csv"
        self.catalogo.to_csv(p1, index=False)
        p2 = reporte.guardar_json(self.dirs["gobernanza"] / "linaje.json", lin)
        p3 = reporte.guardar_json(self.dirs["gobernanza"] / "gobernanza.json", {"proyecto": self.spec["nombre"], "dueno": (self.spec.get("gobernanza") or {}).get("dueno", ""),
                                                                                  "puntajes": punt, "linaje": lin, "catalogo": self.catalogo.to_dict(orient="records")})
        return Resultado("gobernanza", True, f"{punt['tablas']} tablas catalogadas · {len(lin)} aristas de linaje · {punt['columnas_pii']} columnas PII",
                         {"puntajes": punt, "linaje": lin[:40]}, [str(p1), str(p2), str(p3)])

    def _ml(self) -> Resultado:
        cfg = self.spec.get("ml")
        if not cfg or not cfg.get("target"):
            return Resultado("ml", True, "sin configuración `ml` en el YAML", omitida=True)
        tabla = cfg.get("tabla")
        if cfg.get("sql"):
            df = almacen.consultar(self.ruta_db, cfg["sql"])      # set de entrenamiento armado en SQL
            tabla = "sql"
        else:
            df = self.gold.get(tabla) if tabla in self.gold else self.silver.get(tabla)
        if df is None:
            raise RuntimeError(f"tabla «{tabla}» no existe ni en gold ni en silver")
        if cfg["target"] not in df.columns:
            raise RuntimeError(f"target «{cfg['target']}» no está en {tabla}")
        res = ml.entrenar(df, cfg)
        self.dirs["ml"].mkdir(parents=True, exist_ok=True)
        scores = res.pop("scores")
        p_scores = self.dirs["ml"] / "ml_scores.parquet"
        scores.to_parquet(p_scores, index=False)
        self.gold["ml_scores"] = scores
        scores.to_parquet(self.dirs["gold"] / "ml_scores.parquet", index=False)
        almacen.cargar({"ml_scores": scores}, self.ruta_db)
        self.ml = res
        p = reporte.guardar_json(self.dirs["ml"] / "ml.json", res)
        met = " · ".join(f"{k} {v}" for k, v in res["metricas"].items() if v is not None)
        return Resultado("ml", True, f"{res['tipo']} · {met}", res, [str(p), str(p_scores)])

    def _reporte(self) -> Resultado:
        if not self.ruta_db.exists():
            raise RuntimeError("no hay almacén")
        self.dirs["reporte"].mkdir(parents=True, exist_ok=True)
        self.kpis = reporte.calcular_kpis(self.spec, self.ruta_db)
        malos = [k for k in self.kpis if not k["ok"]]
        if malos and len(malos) == len(self.kpis) and self.kpis:
            raise RuntimeError("ningún KPI se pudo calcular: " + malos[0].get("error", ""))
        imgs = reporte.graficos(self.spec, self.ruta_db, self.gold, self.dirs["reporte"] / "graficos")
        p_k = reporte.guardar_json(self.dirs["reporte"] / "kpis.json", self.kpis)
        p_x = reporte.excel(self.dirs["reporte"] / "reporte.xlsx", self.spec, self.kpis, self.calidad, self.catalogo, self.gold, self.ml)
        p_h = reporte.html_reporte(self.dirs["reporte"] / "reporte.html", self.spec, self.kpis, self.calidad, imgs, self.ml, self.spec.get("idioma", "es"))
        ev = {"kpis": [{"nombre": k["nombre"], "valor": k["texto"], **({"error": k["error"]} if not k["ok"] else {})} for k in self.kpis], "graficos": [p.name for p in imgs]}
        return Resultado("reporte", True, f"{len(self.kpis) - len(malos)}/{len(self.kpis)} KPIs · {len(imgs)} gráficos · Excel + HTML", ev,
                         [str(p_k), str(p_x), str(p_h)] + [str(p) for p in imgs])

    def _dax(self) -> Resultado:
        self.dirs["powerbi"].mkdir(parents=True, exist_ok=True)
        texto, self.medidas = dax.generar(self.spec, list(self.gold))
        p = self.dirs["powerbi"] / "measures.dax"
        p.write_text(texto, encoding="utf-8")
        p2 = reporte.guardar_json(self.dirs["powerbi"] / "medidas.json", self.medidas)
        return Resultado("dax", True, f"{len(self.medidas)} medidas generadas",
                         {"medidas": [{"nombre": m["nombre"], "expresion": m["expresion"]} for m in self.medidas]}, [str(p), str(p2)])

    def _powerbi(self) -> Resultado:
        cfg = self.spec.get("powerbi") or {}
        if not cfg.get("generar", True):
            return Resultado("powerbi", True, "desactivado en el YAML", omitida=True)
        if not powerbi.disponible():
            return Resultado("powerbi", True, "MV DAX Lab (daxlingo) no está disponible en esta instalación", omitida=True)
        nombre = _slug(cfg.get("nombre") or self.spec["nombre"])
        gold_pbi = {k: v for k, v in self.gold.items() if k != "ml_scores"}
        info = powerbi.generar(self.spec, gold_pbi, self.medidas, self.dirs["gold"] / "csv", self.dirs["powerbi"], nombre,
                               embebido=False, idioma=self.spec.get("idioma", "es"))
        demo = None
        if all(len(df) <= 45_000 for df in gold_pbi.values()):
            demo = powerbi.generar(self.spec, gold_pbi, self.medidas, self.dirs["gold"] / "csv_demo", self.dirs["powerbi"], nombre + "_demo",
                                   embebido=True, idioma=self.spec.get("idioma", "es"))
        ev = {"tablas": info["tablas"], "medidas": info["medidas"], "relaciones": info["relaciones"], "auditoria": info["auditoria"],
              "hallazgos": info["hallazgos"], **({"demo_embebida": demo["auditoria"]} if demo else {})}
        arts = [info["pbit"], info["pbip"]] + ([demo["pbit"]] if demo else [])
        return Resultado("powerbi", True, f".pbit + PBIP · auditoría {info['auditoria']}/100", ev, arts)

    def _entrega(self) -> Resultado:
        self.dirs["entrega"].mkdir(parents=True, exist_ok=True)
        manifiesto = {"proyecto": self.spec["nombre"], "generado": datetime.now().isoformat(timespec="seconds"), "version": __version__,
                      "etapas": {e: {"estado": r.estado(), "resumen": r.resumen or r.error, "segundos": r.segundos, "artefactos": r.artefactos}
                                 for e, r in self.resultados.items()}}
        p1 = reporte.guardar_json(self.dirs["entrega"] / "manifiesto.json", manifiesto)
        lineas = [f"# {self.spec['nombre']} · entrega", "", f"Generado {manifiesto['generado']} por MV Data Engineering v{__version__}", "",
                  "| Etapa | Estado | Resumen | s |", "|---|---|---|---|"]
        for e in ETAPAS:
            r = self.resultados.get(e)
            if r and e != "entrega":
                lineas.append(f"| {e} | {r.estado()} | {(r.resumen or r.error).replace('|', '/')} | {r.segundos} |")
        if self.kpis:
            lineas += ["", "## KPIs", "", "| KPI | Valor |", "|---|---|"] + [f"| {k['nombre']} | {k['texto']} |" for k in self.kpis]
        if self.calidad:
            lineas += ["", f"## Calidad · {self.calidad.get('puntaje')} / 100 · {self.calidad.get('reglas')} reglas", ""]
            lineas += [f"- {r['regla']}: {r['detalle']} ({'crítica' if r['critico'] else 'informativa'})" for r in self.calidad.get("fallidas", [])] or ["- sin hallazgos"]
        if self.ml:
            lineas += ["", "## Modelo", ""] + [f"- {k}: {v}" for k, v in self.ml["metricas"].items()]
        lineas += ["", "## Artefactos", ""] + [f"- `{a}`" for e, r in self.resultados.items() for a in r.artefactos]
        p2 = self.dirs["entrega"] / "RESUMEN.md"
        p2.write_text("\n".join(lineas) + "\n", encoding="utf-8")
        # copia de lo que se entrega, junto
        for src in (self.dirs["reporte"] / "reporte.xlsx", self.dirs["reporte"] / "reporte.html"):
            if src.exists():
                shutil.copy(src, self.dirs["entrega"] / src.name)
        for p in self.dirs["powerbi"].glob("*.pbit"):
            shutil.copy(p, self.dirs["entrega"] / p.name)
        return Resultado("entrega", True, f"manifiesto + resumen + {len(list(self.dirs['entrega'].iterdir())) - 2} archivos copiados",
                         {"carpeta": str(self.dirs["entrega"])}, [str(p1), str(p2)])


def _slug(txt: str) -> str:
    import re
    import unicodedata
    s = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")
    return s or "proyecto"
