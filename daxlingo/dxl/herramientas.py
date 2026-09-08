# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · Las herramientas del analista Power BI moderno, operativas.

Registro de las 10+ herramientas del stack (Desktop, Power Query, Service,
Bravo, DAX Studio, Tabular Editor, ALM Toolkit, VS Code + PBIP, Fabric y el
MCP de modelado de Power BI) con acciones concretas desde la plataforma:
detectar la instalación local y exportar el modelo en el formato que cada una
abre. La configuración MCP para agentes de IA vive en `proveedores_ia.py`
(soporta varios agentes: Claude, ChatGPT/Codex, Copilot, Gemini).

No todas se detectan igual, y por eso cada una declara su `tipo`:

  escritorio    se instala y se busca (registro de Windows, PATH, rutas)
  web           es un sitio: no hay nada que detectar
  dentro_de:X   viene adentro de otra (Power Query vive en Desktop)
  config        no es un programa sino un archivo que esta app genera (MCP)

Antes se les aplicaba la detección de escritorio a las diez, así que la
pestaña mostraba «no detectada acá» hasta para Power BI Service y Fabric, que
son páginas web. Un semáforo en rojo sobre algo que no se instala no informa:
hace dudar de los otros nueve.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

HERRAMIENTAS: list[dict] = [
    {
        "clave": "desktop", "tipo": "escritorio", "exe": "PBIDesktop.exe", "nombre": "Power BI Desktop",
        "etapa": "01 · Crear", "descripcion": "Informes y modelos.",
        "url": "https://www.microsoft.com/download/details.aspx?id=58494",
        "rutas": [r"C:\Program Files\Microsoft Power BI Desktop\bin\PBIDesktop.exe",
                  r"C:\Program Files (x86)\Microsoft Power BI Desktop\bin\PBIDesktop.exe",
                  # El ALIAS de la versión de la Store. La ruta real vive en
                  # WindowsApps, que tiene ACL restrictivo: ni listarla se
                  # puede, y el glob de abajo devolvía vacío EN SILENCIO. El
                  # alias, en cambio, es del usuario y siempre legible.
                  r"%LOCALAPPDATA%\Microsoft\WindowsApps\PBIDesktop.exe",
                  r"C:\Program Files\WindowsApps\Microsoft.MicrosoftPowerBIDesktop_*\bin\PBIDesktop.exe"],
        "asociacion": ".pbix",
        "desinstalacion": "Power BI Desktop",
        "integracion": "Los .pbit y PBIP que exporta esta plataforma se abren "
                       "con doble clic y se guardan como .pbix.",
    },
    {
        "clave": "powerquery", "tipo": "dentro_de:desktop", "nombre": "Power Query",
        "etapa": "01 · Crear", "descripcion": "Transforma datos antes del modelo.",
        "url": "https://learn.microsoft.com/power-query/",
        "rutas": [],
        "integracion": "Las particiones M del modelo cargado se ven en la "
                       "pestaña Modelo; el analizador sugiere mover columnas "
                       "calculadas a Power Query.",
    },
    {
        "clave": "service", "tipo": "web", "nombre": "Power BI Service",
        "etapa": "02 · Operar", "descripcion": "Publica y gobierna.",
        "url": "https://app.powerbi.com",
        "rutas": [],
        "integracion": "El PBIP exportado se publica vía Git integration o "
                       "subiendo el .pbix guardado desde Desktop.",
    },
    {
        "clave": "bravo", "tipo": "escritorio", "exe": "Bravo.exe", "nombre": "Bravo",
        "etapa": "02 · Operar", "descripcion": "Revisa el modelo (SQLBI).",
        "url": "https://bravo.bi",
        "rutas": [r"C:\Program Files\Bravo for Power BI\Bravo.exe",
                  r"%LOCALAPPDATA%\Programs\Bravo for Power BI\Bravo.exe"],
        "desinstalacion": "Bravo for Power BI",
        "integracion": "Exportá el modelo como .pbit, abrilo en Desktop y "
                       "conectá Bravo a esa instancia para analizar tamaño y "
                       "formatear el DAX.",
    },
    {
        "clave": "daxstudio", "tipo": "escritorio", "exe": "DaxStudio.exe", "nombre": "DAX Studio",
        "etapa": "03 · Modelar", "descripcion": "Mide y optimiza consultas DAX.",
        "url": "https://daxstudio.org",
        "rutas": [r"C:\Program Files\DAX Studio\DaxStudio.exe",
                  r"%LOCALAPPDATA%\DaxStudio\DaxStudio.exe",
                  r"%LOCALAPPDATA%\Programs\DAX Studio\DaxStudio.exe"],
        "desinstalacion": "DAX Studio",
        "integracion": "Acción «Exportar medidas .dax»: todas las medidas del "
                       "modelo en un archivo listo para pegar y medir "
                       "(Server Timings) en DAX Studio.",
    },
    {
        "clave": "tabulareditor", "tipo": "escritorio", "exe": "TabularEditor.exe", "nombre": "Tabular Editor",
        "etapa": "03 · Modelar", "descripcion": "Modelado avanzado y BPA.",
        "url": "https://tabulareditor.com",
        "rutas": [r"C:\Program Files (x86)\Tabular Editor\TabularEditor.exe",
                  r"C:\Program Files\Tabular Editor\TabularEditor.exe",
                  r"C:\Program Files\Tabular Editor 3\TabularEditor3.exe",
                  r"%LOCALAPPDATA%\Programs\Tabular Editor 3\TabularEditor3.exe"],
        "desinstalacion": "Tabular Editor",
        "integracion": "Acción «Exportar model.bim»: Tabular Editor lo abre "
                       "directo (File → Open → From File) con todo lo "
                       "transformado acá.",
    },
    {
        # El ejecutable real se llama AlmToolkit.exe — el mismo nombre que
        # usa la ruta de acá abajo. Windows no distingue mayúsculas, así que
        # el typo anterior («ALMTOolkit.exe») detectaba igual, pero dejaba
        # dos escrituras distintas del mismo nombre en la misma entrada.
        "clave": "almtoolkit", "tipo": "escritorio", "exe": "AlmToolkit.exe", "nombre": "ALM Toolkit",
        "etapa": "04 · Industrializar", "descripcion": "Compara y despliega.",
        "url": "http://alm-toolkit.com",
        "rutas": [r"C:\Program Files (x86)\ALM Toolkit\AlmToolkit.exe",
                  r"C:\Program Files\ALM Toolkit\AlmToolkit.exe"],
        "desinstalacion": "ALM Toolkit",
        "integracion": "Exportá dos versiones del modelo (antes/después de "
                       "las transformaciones) y comparalas como source y "
                       "target en ALM Toolkit.",
    },
    {
        "clave": "vscode", "tipo": "escritorio", "exe": "Code.exe", "nombre": "VS Code + PBIP",
        "etapa": "04 · Industrializar", "descripcion": "Versiona como código.",
        "url": "https://code.visualstudio.com",
        "rutas": [r"C:\Program Files\Microsoft VS Code\Code.exe",
                  r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"],
        "desinstalacion": "Microsoft Visual Studio Code",
        "integracion": "El export PBIP es texto plano (TMSL + report.json): "
                       "diff, blame y PRs como cualquier código.",
    },
    {
        "clave": "fabric", "tipo": "web", "nombre": "Microsoft Fabric",
        "etapa": "05 · Escalar con IA", "descripcion": "Datos y analítica.",
        "url": "https://app.fabric.microsoft.com",
        "rutas": [],
        "integracion": "Pestaña Fabric: publicación directa por API REST "
                       "(token BYOK) o vía integración Git del PBIP.",
    },
    {
        "clave": "mcp", "tipo": "config", "nombre": "Power BI MCP (local + remoto)",
        "etapa": "05 · Escalar con IA",
        "descripcion": "IA conectada al modelo (agentes).",
        "url": "https://learn.microsoft.com/power-bi/developer/mcp/"
               "remote-mcp-server-get-started",
        "rutas": [],
        "integracion": "Acción «Configuración MCP»: genera el .mcp.json con "
                       "el MCP remoto oficial de Power BI (Fabric, Entra "
                       "ID), el MCP local de modelado (Desktop/.pbix) y el "
                       "servidor MCP propio de esta plataforma (análisis, "
                       "NL→DAX, export).",
    },
]


def detectar(herramienta: dict) -> str | None:
    """Ruta local si la herramienta está instalada (Windows); si no, None.

    Tres vías, de la más barata a la más cara. Las rutas fijas solas no
    alcanzaban: DAX Studio y Tabular Editor se instalan por usuario en
    %LOCALAPPDATA% tanto como en Archivos de programa, y cualquiera puede
    elegir otra carpeta en el instalador. El registro es el que sabe dónde
    quedó de verdad.
    """
    # 1. las rutas conocidas. `%VAR%` se expande (LOCALAPPDATA y compañía):
    # varias de estas herramientas se instalan por usuario, no en Archivos
    # de programa.
    for patron in herramienta.get("rutas", []):
        patron = os.path.expandvars(patron)
        p = Path(patron)
        if "*" in patron:
            base = Path(patron.split("*")[0]).parent
            resto = patron.split("\\")[-1]
            if base.exists():
                encontrados = list(base.glob(f"**/{resto}"))
                if encontrados:
                    return str(encontrados[0])
        elif p.exists():
            return str(p)

    # 2. el registro de Windows (App Paths: donde Windows anota los .exe)
    exe = herramienta.get("exe")
    if exe:
        ruta = _desde_registro(exe)
        if ruta:
            return ruta
        # 3. el PATH — cubre VS Code, que se agrega solo, las portables y el
        # alias de ejecución de las apps de la Store.
        desde_path = shutil.which(Path(exe).stem)
        if desde_path:
            return desde_path

    # 4. la asociación de archivos: si el doble clic sobre un .pbix abre la
    # herramienta, el registro sabe con QUÉ ejecutable lo hace. Es la vía
    # más fiel para Power BI Desktop — el reporte de campo era exactamente
    # «dice no instalada» en la máquina de alguien que abre .pbix a diario.
    ext = herramienta.get("asociacion")
    if ext:
        ruta = _desde_asociacion(ext)
        if ruta:
            return ruta

    # 5. las entradas de desinstalación («Agregar o quitar programas»):
    # cubren cualquier carpeta que se haya elegido en el instalador. Es la
    # misma cadena que usa Convertir-a-version-dueno.bat.
    nombre = herramienta.get("desinstalacion")
    if nombre:
        ruta = _desde_desinstalacion(nombre, herramienta.get("exe", ""))
        if ruta:
            return ruta
    return None


def _desde_registro(exe: str) -> str | None:
    """Consulta `App Paths` del registro. Fuera de Windows devuelve None.

    Windows anota ahí el ejecutable de cada programa instalado, sin importar
    en qué carpeta lo pusieron. Es la misma clave que hace que `start bravo`
    funcione desde cualquier lado.
    """
    try:
        import winreg  # type: ignore[import-not-found]
    except ImportError:
        return None  # no es Windows: no hay registro que consultar

    sub = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{Path(exe).name}"
    for raiz in (getattr(winreg, "HKEY_CURRENT_USER"),
                 getattr(winreg, "HKEY_LOCAL_MACHINE")):
        try:
            with winreg.OpenKey(raiz, sub) as k:
                valor = winreg.QueryValueEx(k, "")[0]
                if valor and Path(valor).exists():
                    return str(valor)
        except OSError:
            continue
    return None


def _exe_de_comando(comando: str) -> str | None:
    """El ejecutable dentro de un comando del registro.

    Los comandos de `shell\\open\\command` vienen como
    `"C:\\...\\PBIDesktop.exe" "%1"` — con comillas y argumentos — o pelados.
    Función pura y aparte para poder probarla sin un registro de Windows.
    """
    comando = comando.strip()
    if not comando:
        return None
    if comando.startswith('"'):
        fin = comando.find('"', 1)
        return comando[1:fin] if fin > 1 else None
    # Sin comillas: hasta el primer espacio seguido de argumento.
    trozo = comando.split(" /")[0].split(" %")[0].split(" -")[0]
    return trozo.split('"')[0].strip() or None


def _desde_asociacion(ext: str) -> str | None:
    """El ejecutable asociado a una extensión (p. ej. `.pbix`), del registro."""
    try:
        import winreg  # type: ignore[import-not-found]
    except ImportError:
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, ext) as k:
            progid = winreg.QueryValueEx(k, "")[0]
        if not progid:
            return None
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT,
                            rf"{progid}\shell\open\command") as k:
            comando = winreg.QueryValueEx(k, "")[0]
    except OSError:
        return None
    exe = _exe_de_comando(os.path.expandvars(comando or ""))
    return exe if exe and Path(exe).exists() else None


def _desde_desinstalacion(nombre: str, exe: str) -> str | None:
    """Busca la herramienta en «Agregar o quitar programas».

    Recorre las tres raíces de Uninstall (por usuario, por máquina, y la de
    32 bits), matchea por DisplayName y saca la ruta de InstallLocation o,
    si no está, de la carpeta del DisplayIcon — que es exactamente el
    fallback que ya usa Convertir-a-version-dueno.bat, y por el mismo
    motivo: no todos los instaladores escriben InstallLocation.
    """
    try:
        import winreg  # type: ignore[import-not-found]
    except ImportError:
        return None
    raices = [
        (winreg.HKEY_CURRENT_USER,
         r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    objetivo = nombre.lower()
    for raiz, base in raices:
        try:
            with winreg.OpenKey(raiz, base) as padre:
                n = winreg.QueryInfoKey(padre)[0]
                for i in range(n):
                    try:
                        with winreg.OpenKey(padre, winreg.EnumKey(padre, i)) as k:
                            def leer(valor):
                                try:
                                    return str(winreg.QueryValueEx(k, valor)[0])
                                except OSError:
                                    return ""
                            if objetivo not in leer("DisplayName").lower():
                                continue
                            carpeta = leer("InstallLocation")
                            if not carpeta:
                                icono = leer("DisplayIcon").split(",")[0].strip('"')
                                carpeta = str(Path(icono).parent) if icono else ""
                            if not carpeta:
                                continue
                            if exe:
                                candidatos = list(Path(carpeta).glob(exe)) \
                                    + list(Path(carpeta).glob(f"**/{exe}"))
                                if candidatos:
                                    return str(candidatos[0])
                            if Path(carpeta).exists():
                                return carpeta
                    except OSError:
                        continue
        except OSError:
            continue
    return None


def estado(herramienta: dict, contexto: dict | None = None) -> dict:
    """Estado de una herramienta para mostrar en la UI.

    Devuelve `{"clave", "nivel", "detalle"}` donde `nivel` es uno de:
    `instalada`, `falta`, `web`, `incluida`, `lista` o `sin_soporte`.

    Existe porque la pestaña mostraba «no detectada acá» para las diez, y en
    seis de ellas eso era directamente falso: Power BI Service y Fabric son
    SITIOS —no hay nada que instalar—, Power Query viene adentro de Desktop, y
    el MCP no es un programa sino un archivo de configuración que esta misma
    app genera. Un semáforo que dice «no» sobre algo que no se instala no es
    un estado: es ruido que hace dudar de todo lo demás.
    """
    contexto = contexto or {}
    tipo = herramienta.get("tipo", "escritorio")

    if tipo == "web":
        return {"clave": herramienta["clave"], "nivel": "web", "detalle": None}

    if tipo == "config":
        return {"clave": herramienta["clave"], "nivel": "lista", "detalle": None}

    if tipo.startswith("dentro_de:"):
        anfitrion = tipo.split(":", 1)[1]
        # Power Query no se instala aparte: si está Desktop, está. Y si su
        # anfitriona no se puede ni buscar en este sistema, hereda eso — decir
        # «falta» en Linux sugeriría que hay algo que instalar, y no lo hay.
        if not _es_windows():
            return {"clave": herramienta["clave"], "nivel": "sin_soporte",
                    "detalle": None}
        return {"clave": herramienta["clave"],
                "nivel": "incluida" if contexto.get(anfitrion) else "falta",
                "detalle": anfitrion}

    if not _es_windows():
        # Decir «no detectada» en Linux/Mac sugiere que falta instalarla,
        # cuando el punto es que estas herramientas son de Windows.
        return {"clave": herramienta["clave"], "nivel": "sin_soporte",
                "detalle": None}

    ruta = detectar(herramienta)
    return {"clave": herramienta["clave"],
            "nivel": "instalada" if ruta else "falta", "detalle": ruta}


def _es_windows() -> bool:
    return os.name == "nt"


def estados(contexto_extra: dict | None = None) -> dict[str, dict]:
    """El estado de las diez, resuelto en el orden correcto.

    Las que viven adentro de otra (Power Query) necesitan saber si su
    anfitriona está: por eso primero se resuelven las de escritorio.
    """
    resueltos: dict[str, dict] = {}
    instaladas: dict[str, bool] = dict(contexto_extra or {})

    for h in HERRAMIENTAS:
        if not h.get("tipo", "escritorio").startswith("dentro_de:"):
            e = estado(h)
            resueltos[h["clave"]] = e
            instaladas[h["clave"]] = e["nivel"] == "instalada"
    for h in HERRAMIENTAS:
        if h.get("tipo", "").startswith("dentro_de:"):
            resueltos[h["clave"]] = estado(h, instaladas)
    return resueltos


def texto_medidas_dax(cat) -> str:
    """Todas las medidas del catálogo como una consulta DAX ejecutable.

    Sale como `DEFINE MEASURE … EVALUATE`, que es lo que DAX Studio necesita
    para **correr** el archivo y darte Server Timings. Antes salía en formato
    de definición (`[Medida] := …`), que se puede leer y pegar en Tabular
    Editor pero **no se ejecuta**: la pestaña Herramientas prometía «listo
    para pegar y medir» y lo que bajabas no se podía medir. Para el formato
    de definición está el `model.bim`, que es el camino de Tabular Editor.

    El `DEFINE MEASURE` redefine la medida **sólo dentro de la consulta**: se
    puede editar la expresión y medir el impacto sin tocar el modelo, que es
    justamente para lo que se abre Server Timings.
    """
    def _tabla(nombre: str) -> str:
        # En DAX el nombre de tabla va entre comillas simples y la comilla
        # de adentro se escapa duplicándola.
        return "'" + (nombre or "").replace("'", "''") + "'"

    medidas = list(cat.medidas())
    lineas = ["// Medidas exportadas por MV DAX Lab",
              f"// Modelo: {cat.nombre or '(sin nombre)'}",
              "//",
              "// Pegalo en DAX Studio y ejecutalo (F5) con Server Timings",
              "// prendido. Editá cualquier expresión de acá abajo para medir",
              "// el impacto sin tocar el modelo.", ""]
    if not medidas:
        lineas.append("// El modelo no tiene medidas.")
        return "\n".join(lineas)

    lineas.append("DEFINE")
    for m in medidas:
        cabecera = f"    // Tabla: {m['tabla']}"
        if m["carpeta"]:
            cabecera += f" · Carpeta: {m['carpeta']}"
        lineas.append(cabecera)
        if m["descripcion"]:
            lineas.append(f"    // {m['descripcion']}")
        if m["formato"]:
            lineas.append(f'    // formatString: "{m["formato"]}"')
        lineas.append(f"    MEASURE {_tabla(m['tabla'])}[{m['nombre']}] =")
        for linea in (m["expresion"] or "").splitlines() or [""]:
            lineas.append(f"        {linea}")
        lineas.append("")

    primera = medidas[0]["nombre"]
    lineas += ["// Cambiá la medida de acá abajo por la que quieras medir.",
               "EVALUATE",
               f'    ROW ( "{primera}", [{primera}] )', ""]
    return "\n".join(lineas)


def exportar_medidas_dax(cat, destino: str | Path) -> Path:
    """Todas las medidas del catálogo en un .dax para DAX Studio / revisión."""
    destino = Path(destino)
    destino.write_text(texto_medidas_dax(cat), encoding="utf-8")
    return destino
