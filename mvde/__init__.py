# © 2026 Martín Viera. Todos los derechos reservados.
# Software propietario. Ver LICENSE — prohibida su redistribución.
"""
MV Data Engineering · motor de pipelines end-to-end por etapas con gate.

Un proyecto se declara en un YAML (fuentes → bronze → silver → calidad → gold
→ almacén → gobernanza → ML → reporte → DAX → Power BI → entrega) y el
orquestador lo corre etapa por etapa: cada una deja evidencia y artefactos,
y si una falla las siguientes no corren. Importable y testeable sin Streamlit.
"""
__version__ = "1.0.0"
APP_NAME = "MV Data Engineering"

# Paleta de marca (misma familia visual que MV Kobra AI / MV Data Governance)
BRAND = {
    "navy": "#081527",
    "navy2": "#0c2137",
    "amber": "#f2b441",
    "amber2": "#e39a2e",
    "blue": "#2f74c0",
    "green": "#00c896",
    "red": "#e05c5c",
    "ink": "#eaf1fb",
    "muted": "#9db0c8",
}

ETAPAS = ["fuentes", "bronze", "silver", "calidad", "gold", "almacen",
          "gobernanza", "ml", "reporte", "dax", "powerbi", "entrega"]
