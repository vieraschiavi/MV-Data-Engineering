#!/usr/bin/env bash
# MV Data Engineering · lanzador Linux/macOS: crea el entorno la primera vez y abre el programa.
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -x ".venv/bin/python" ]; then
    echo "[ES] Primera ejecución: creando entorno... [EN] First run... [PT] Primeira execução..."
    python3 -m venv .venv
    .venv/bin/python -m pip install -q -r requirements.txt
fi
exec .venv/bin/python -m streamlit run app/app.py --server.headless true --browser.gatherUsageStats false --client.toolbarMode minimal
