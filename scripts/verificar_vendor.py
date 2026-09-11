#!/usr/bin/env python3
# © 2026 Martín Viera. Todos los derechos reservados.
"""Verifica que la copia vendorizada de `dxl` no haya derivado.

Qué problema resuelve
---------------------
`daxlingo/dxl` es una COPIA del motor de MV DAX Lab, traída al repositorio para
que la etapa `powerbi` funcione sin un checkout hermano. `PROCEDENCIA.md` anota
de qué commit salió — pero hasta acá nada verificaba que el contenido siguiera
siendo ese. Dos formas de romperse, las dos silenciosas:

  1. alguien edita un archivo de la copia «para probar algo» y queda así;
  2. se re-copia desde el origen y nadie actualiza el commit anotado, así que
     la tabla dice una versión y el disco tiene otra.

En los dos casos el cliente termina corriendo algo que nadie puede identificar.

Qué verifica, y qué NO
----------------------
Verifica que la copia coincida **con el inventario firmado** de
`daxlingo/HASHES.txt`: mismos archivos, mismo contenido, y el commit anotado en
`PROCEDENCIA.md` igual al del inventario. Eso atrapa las dos formas de arriba.

Lo que NO puede verificar desde este repositorio: si el ORIGEN cambió. El
origen es un repositorio privado distinto y este chequeo corre sin acceso a él.
Para eso hay que re-copiar y regenerar el inventario a mano — que es
exactamente cuando se actualiza el commit.

Uso
---
    python scripts/verificar_vendor.py            # verifica (lo corre el CI)
    python scripts/verificar_vendor.py --firmar   # regenera el inventario
"""
from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
VENDOR = RAIZ / "daxlingo" / "dxl"
INVENTARIO = RAIZ / "daxlingo" / "HASHES.txt"
PROCEDENCIA = RAIZ / "daxlingo" / "PROCEDENCIA.md"
RE_COMMIT = re.compile(r"\b([0-9a-f]{40})\b")


def archivos() -> list[Path]:
    return sorted(p for p in VENDOR.rglob("*")
                  if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")


def sha(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def commit_de_procedencia() -> str | None:
    if not PROCEDENCIA.exists():
        return None
    m = RE_COMMIT.search(PROCEDENCIA.read_text(encoding="utf-8"))
    return m.group(1) if m else None


def inventario_actual() -> dict[str, str]:
    return {str(p.relative_to(VENDOR)): sha(p) for p in archivos()}


def leer_inventario() -> tuple[str | None, dict[str, str]]:
    if not INVENTARIO.exists():
        return None, {}
    commit, filas = None, {}
    for linea in INVENTARIO.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            if linea.startswith("# commit:"):
                commit = linea.split(":", 1)[1].strip()
            continue
        h, _, rel = linea.partition("  ")
        if rel:
            filas[rel.strip()] = h.strip()
    return commit, filas


def firmar() -> int:
    commit = commit_de_procedencia()
    if not commit:
        print("ERROR: no encontré un commit de 40 caracteres en daxlingo/PROCEDENCIA.md.")
        print("       Anotá de qué commit salió la copia antes de firmarla.")
        return 1
    inv = inventario_actual()
    lineas = [
        "# Inventario firmado de la copia vendorizada de dxl.",
        "# Lo genera y verifica scripts/verificar_vendor.py — no se edita a mano.",
        f"# commit: {commit}",
        f"# archivos: {len(inv)}",
        "",
    ] + [f"{h}  {rel}" for rel, h in inv.items()]
    INVENTARIO.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"Inventario firmado: {len(inv)} archivos, commit {commit[:12]}.")
    return 0


def verificar() -> int:
    if not VENDOR.is_dir():
        print(f"ERROR: no existe {VENDOR.relative_to(RAIZ)}. La etapa `powerbi` no va a funcionar.")
        return 1
    commit_inv, esperado = leer_inventario()
    if not esperado:
        print("ERROR: falta daxlingo/HASHES.txt. Generalo con:")
        print("       python scripts/verificar_vendor.py --firmar")
        return 1

    actual = inventario_actual()
    faltan = sorted(set(esperado) - set(actual))
    sobran = sorted(set(actual) - set(esperado))
    cambiados = sorted(r for r in set(esperado) & set(actual) if esperado[r] != actual[r])
    commit_proc = commit_de_procedencia()

    problemas = []
    if faltan:
        problemas.append(f"{len(faltan)} archivo(s) faltan en la copia: " + ", ".join(faltan[:5]))
    if sobran:
        problemas.append(f"{len(sobran)} archivo(s) aparecieron sin firmar: " + ", ".join(sobran[:5]))
    if cambiados:
        problemas.append(f"{len(cambiados)} archivo(s) cambiaron de contenido: " + ", ".join(cambiados[:5]))
    if commit_proc != commit_inv:
        problemas.append(
            f"PROCEDENCIA.md dice el commit {str(commit_proc)[:12]} y el inventario dice "
            f"{str(commit_inv)[:12]}: la tabla y el disco no hablan de la misma versión")

    if problemas:
        print("La copia vendorizada de dxl DERIVÓ:\n")
        for x in problemas:
            print(f"  · {x}")
        print("\nQué hacer:")
        print("  · si el cambio fue a propósito (se re-copió desde el origen), actualizá el")
        print("    commit en daxlingo/PROCEDENCIA.md y corré:")
        print("        python scripts/verificar_vendor.py --firmar")
        print("  · si NO fue a propósito, alguien editó la copia a mano: revertilo.")
        print("\nUna copia que nadie puede identificar es una copia que el cliente corre a ciegas.")
        return 1

    print(f"Copia vendorizada íntegra: {len(actual)} archivos, commit {str(commit_inv)[:12]}.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--firmar", action="store_true", help="regenerar el inventario")
    return firmar() if ap.parse_args().firmar else verificar()


if __name__ == "__main__":
    raise SystemExit(main())
