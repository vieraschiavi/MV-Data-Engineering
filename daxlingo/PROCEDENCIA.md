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

1. Copiar de nuevo desde el origen, excluyendo `__pycache__`.
2. Actualizar el commit de la tabla de arriba **en el mismo cambio**.
3. Volver a firmar el inventario:

```bash
python scripts/verificar_vendor.py --firmar
```

El paso 3 no es opcional: `HASHES.txt` es el inventario firmado de la copia, y
el CI lo verifica en cada push (`scripts/verificar_vendor.py` en el job
`calidad`). Si el disco y la tabla no dicen lo mismo, el build falla.

## Qué atrapa el chequeo, y qué no

Atrapa las dos formas en que esto se rompe en silencio: que alguien **edite la
copia a mano** para probar algo y quede así, y que se **re-copie sin actualizar
el commit**, dejando una tabla que miente.

Lo que **no** puede saber: si el ORIGEN cambió. El origen es otro repositorio y
el chequeo corre sin acceso a él. Para eso hay que re-copiar y volver a firmar
—que es justo cuando se actualiza el commit—. Si pasa mucho tiempo entre
re-copias, la copia puede estar íntegra y vieja al mismo tiempo: íntegra es
verificable acá, al día no.
