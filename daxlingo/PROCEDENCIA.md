# `dxl/` — copia vendorizada de MV DAX Lab

Esta carpeta **no se edita acá**. Es una copia de `dxl/` del producto MV DAX Lab,
traída al repo para que la etapa `powerbi` del pipeline pueda generar el `.pbit`
sin depender de que exista un checkout hermano.

| | |
|---|---|
| Origen | repositorio `Power-bi`, ruta `daxlingo/dxl` |
| Commit de origen | `53111150d5c4483312f1b9bdb9818faf8bff6fa6` |
| Qué se copió | sólo `dxl/` (1,5 MB) — no `web/`, `media/`, `tests/`, `app/` |

## Por qué vendorizado y no una dependencia de pip

El producto se instala en la VM de un cliente, muchas veces **sin salida a
internet** (ver `docs/CONFIDENCIAL.md`). Una dependencia `pip install` contra un
repositorio privado necesitaría credenciales de GitHub en esa VM y una conexión
que el modo confidencial justamente existe para prohibir. La copia viaja con el
programa.

## Qué usa el motor, exactamente

`mvde/powerbi.py` importa cinco módulos: `catalogo`, `dataset`, `tablero`,
`transformador`, `modelo` y `analizador`. El resto de `dxl/` viene con ellos
porque son sus dependencias internas; `dxl` no importa nada fuera de la
biblioteca estándar y Pillow.

## Cómo actualizarla

Copiar de nuevo desde el origen, excluyendo `__pycache__`, y actualizar el
commit de la tabla de arriba en el mismo cambio. Si la tabla y el contenido no
coinciden, nadie puede saber qué versión está corriendo un cliente.
