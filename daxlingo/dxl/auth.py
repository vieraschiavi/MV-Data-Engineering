# © 2026 Martín Viera. Todos los derechos reservados.

"""
MV DAX Lab · Login opcional, para cuando la app deja de correr en un escritorio.

**Por qué existe.** En la laptop del analista no hay login: el programa es de
quien está sentado en la máquina. Publicado en una VM del cliente, la URL
queda al alcance de una red entera — y desde acá se suben datasets, se leen
modelos y se bajan archivos. `despliegue/LEEME.md` listaba esto como el
primer pendiente y por eso los dos caminos de servidor escuchan en
`127.0.0.1`: sin autenticación, abrirlos era regalar la app.

**Cómo se enciende.** Declarando usuarios en `MVDAX_USUARIOS` (o en el
archivo al que apunte `MVDAX_USUARIOS_ARCHIVO`). Sin esa variable el
comportamiento es el de siempre, así que el `.bat`, el `.exe` y `run.sh`
siguen abriendo sin pedir nada. Es una decisión del despliegue, no del
código.

**No confundir con la licencia.** Son dos ejes distintos y se cruzan seguido:

    MVDAX_LICENCIA   QUÉ desbloquea el producto (edición, plan, vencimiento)
    MVDAX_USUARIOS   QUIÉN puede abrir ESTA instalación

Una licencia válida no dice quién sos, y un login válido no compra nada. En
una VM compartida hacen falta las dos.

**Las contraseñas nunca se guardan ni viajan en texto plano**: PBKDF2-HMAC-
SHA256 con sal por usuario, el mismo esquema que MV Kobra AI y MV SQL NLP. La
línea la genera:

    python -m dxl.auth <nombre>

que pide la contraseña sin mostrarla y no la escribe en ningún lado — solo
imprime el hash para pegar en la variable de entorno.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import time
from pathlib import Path

log = logging.getLogger("mvdax")

ALGORITMO = "pbkdf2_sha256"
ITERACIONES = 200_000

# Un atacante dentro de la red interna puede probar contraseñas a mano. Cinco
# intentos y cinco minutos de espera hacen inviable el diccionario sin
# castigar a quien simplemente se equivocó al tipear.
MAX_INTENTOS = 5
BLOQUEO_SEGUNDOS = 300

ENV_USUARIOS = "MVDAX_USUARIOS"
ENV_ARCHIVO = "MVDAX_USUARIOS_ARCHIVO"
CLAVE_SESION = "mvdax_auth_usuario"

# Intentos fallidos por usuario, en memoria del proceso. Un reinicio del
# contenedor los limpia: es un freno a la fuerza bruta de una sesión, no un
# castigo persistente que haya que ir a levantar a mano.
_INTENTOS: dict[str, list[float]] = {}


# ======================================================================
# Hashing
# ======================================================================
def hashear(password: str, iteraciones: int = ITERACIONES) -> str:
    """`pbkdf2_sha256$iteraciones$sal$hash`, listo para pegar en la variable."""
    if not password:
        raise ValueError("la contraseña no puede estar vacía")
    sal = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), sal,
                             iteraciones)
    return f"{ALGORITMO}${iteraciones}${sal.hex()}${dk.hex()}"


def _verificar_hash(password: str, guardado: str) -> bool:
    try:
        algo, iteraciones, sal_hex, esperado = guardado.split("$", 3)
        if algo != ALGORITMO:
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                 bytes.fromhex(sal_hex), int(iteraciones))
    except (ValueError, TypeError):
        return False
    # `compare_digest` y no `==`: comparar strings corta en el primer byte
    # distinto, y ese tiempo se puede medir.
    return hmac.compare_digest(dk.hex(), esperado)


def _quemar_tiempo() -> None:
    """Para un usuario inexistente se calcula igual un PBKDF2 descartable.

    Si no, la diferencia de tiempo entre «ese usuario no existe» y «la
    contraseña está mal» delata qué nombres son válidos, que es la mitad de
    la credencial servida.
    """
    hashlib.pbkdf2_hmac("sha256", b"x", b"y", ITERACIONES)


# ======================================================================
# Usuarios declarados
# ======================================================================
def _parsear(crudo: str) -> dict[str, str]:
    """`usuario:hash`, separados por `;` o por saltos de línea.

    Las líneas que empiezan con `#` son comentarios: el archivo de usuarios
    tiene que poder explicarse a sí mismo.
    """
    salida: dict[str, str] = {}
    for parte in crudo.replace("\n", ";").split(";"):
        linea = parte.strip()
        if not linea or linea.startswith("#"):
            continue
        if ":" not in linea:
            log.warning("MVDAX: entrada de usuario sin «:», ignorada")
            continue
        usuario, guardado = linea.split(":", 1)
        usuario, guardado = usuario.strip().lower(), guardado.strip()
        if not usuario or not guardado.startswith(ALGORITMO + "$"):
            log.warning("MVDAX: usuario «%s» con hash inválido, ignorado",
                        usuario or "?")
            continue
        salida[usuario] = guardado
    return salida


def usuarios() -> dict[str, str]:
    """Los usuarios declarados, desde la variable o desde el archivo."""
    crudo = os.environ.get(ENV_USUARIOS, "").strip()
    if not crudo:
        ruta = os.environ.get(ENV_ARCHIVO, "").strip()
        if ruta:
            try:
                crudo = Path(ruta).read_text(encoding="utf-8")
            except OSError as exc:
                # Se declaró el archivo y no se puede leer: no entra NADIE.
                # Falla cerrado a propósito. Un archivo de usuarios que
                # desaparece y deja la app abierta es la peor forma de
                # enterarse de que estaba mal montado el volumen.
                log.error("MVDAX: no se pudo leer %s: %s", ENV_ARCHIVO, exc)
                return {}
    return _parsear(crudo)


def activo() -> bool:
    """¿Hay que pedir login?

    Se mira la DECLARACIÓN, no si parseó bien: con la variable puesta y mal
    escrita no entra nadie, en vez de entrar todos. Un typo en el hash no
    puede ser la diferencia entre una app cerrada y una abierta.
    """
    return bool(os.environ.get(ENV_USUARIOS, "").strip()
                or os.environ.get(ENV_ARCHIVO, "").strip())


def desprotegido() -> bool:
    """Modo servidor y sin usuarios declarados: la combinación peligrosa.

    En escritorio no pedir login es lo correcto. En una VM es una app abierta
    a quien alcance la URL, y eso hay que decirlo en pantalla — callarlo es
    dejar que se descubra el día que entra alguien que no tenía que entrar.
    """
    from .entorno import es_servidor
    return es_servidor() and not activo()


# ======================================================================
# Intentos fallidos
# ======================================================================
def bloqueado(usuario: str) -> int:
    """Segundos que faltan para poder reintentar; 0 si no está bloqueado."""
    u = (usuario or "").strip().lower()
    ahora = time.time()
    recientes = [t for t in _INTENTOS.get(u, []) if ahora - t < BLOQUEO_SEGUNDOS]
    _INTENTOS[u] = recientes
    if len(recientes) < MAX_INTENTOS:
        return 0
    return int(BLOQUEO_SEGUNDOS - (ahora - recientes[-MAX_INTENTOS]))


def _anotar_fallo(usuario: str) -> None:
    _INTENTOS.setdefault((usuario or "").strip().lower(), []).append(time.time())


def limpiar_intentos(usuario: str | None = None) -> None:
    """Después de un login válido, o entre tests."""
    if usuario is None:
        _INTENTOS.clear()
    else:
        _INTENTOS.pop((usuario or "").strip().lower(), None)


# ======================================================================
# Login
# ======================================================================
def verificar(usuario: str, password: str) -> bool:
    """Valida la credencial. Nunca registra la contraseña, solo el resultado."""
    u = (usuario or "").strip().lower()
    if bloqueado(u):
        return False
    guardado = usuarios().get(u)
    if guardado is None:
        _quemar_tiempo()
        _anotar_fallo(u)
        log.warning("MVDAX: login fallido para «%s»", u or "?")
        return False
    if not _verificar_hash(password or "", guardado):
        _anotar_fallo(u)
        log.warning("MVDAX: login fallido para «%s»", u)
        return False
    limpiar_intentos(u)
    log.info("MVDAX: login correcto para «%s»", u)
    return True


def sesion_usuario(estado) -> str | None:
    """Quién está autenticado en esta sesión de Streamlit, o `None`."""
    try:
        return estado[CLAVE_SESION] if CLAVE_SESION in estado else None
    except (TypeError, KeyError):
        return None


def abrir_sesion(estado, usuario: str) -> None:
    estado[CLAVE_SESION] = (usuario or "").strip().lower()


def cerrar_sesion(estado) -> None:
    try:
        del estado[CLAVE_SESION]
    except (TypeError, KeyError):
        pass


# ======================================================================
# `python -m dxl.auth <nombre>` — generar la línea de credencial
# ======================================================================
def _principal(argv: list[str] | None = None) -> int:
    """Pide la contraseña sin mostrarla e imprime la línea para la variable.

    Va acá y no en un CLI aparte porque este repo no tiene uno: agregar un
    `cli.py` entero para un solo comando sería más superficie de la que la
    tarea pide.
    """
    import getpass
    import sys

    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1 or not args[0].strip():
        print("Uso: python -m dxl.auth <nombre-de-usuario>", file=sys.stderr)
        return 2

    clave = getpass.getpass("Contraseña (no se muestra): ")
    if clave != getpass.getpass("Repetila: "):
        print("Las contraseñas no coinciden.", file=sys.stderr)
        return 1
    try:
        linea = f"{args[0].strip().lower()}:{hashear(clave)}"
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"\nPegá esta línea en {ENV_USUARIOS} "
          "(varias se separan con «;»):\n")
    print(linea)
    print("\nLa contraseña no queda guardada en ningún lado: solo su hash.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_principal())
