#!/usr/bin/env bash
# MV Data Engineering · lanzador Linux/macOS: crea el entorno la primera vez y abre el programa.
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -x ".venv/bin/python" ]; then
    echo "[ES] Primera ejecución: creando entorno... [EN] First run... [PT] Primeira execução..."
    python3 -m venv .venv
    .venv/bin/python -m pip install --disable-pip-version-check -q -r requirements.txt
fi
# Mismo lanzador que la version portable de Windows y que la instalada: elige
# un puerto libre en vez del 8501 fijo (que choca con los otros programas de
# la casa), espera a que el motor conteste y recien ahi abre el navegador.
exec .venv/bin/python packaging/lanzador.py
