# © 2026 Martín Viera. Todos los derechos reservados.
"""Autenticación opcional, para cuando la app deja de correr en un escritorio.

En el escritorio no hay login: el programa es de quien está sentado en la
máquina. Publicada en una VM, la URL queda al alcance de una red entera y eso
deja de alcanzar, porque desde la app se conecta a bases y se leen archivos.

El login se enciende declarando usuarios en la variable de entorno
``MVDE_USUARIOS`` (o en el archivo al que apunte ``MVDE_USUARIOS_ARCHIVO``).
Sin esa variable el comportamiento es el de siempre, así el .bat y run.sh
siguen abriendo sin pedir nada.

Las contraseñas nunca se guardan ni viajan en texto plano: se guarda
PBKDF2-HMAC-SHA256 con sal por usuario, el mismo esquema de MV Kobra AI y
MV SQL NLP. La línea la genera ``python -m mvde usuario <nombre>``, que pide
la contraseña sin mostrarla y nunca la escribe en disco.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import time
from pathlib import Path

log = logging.getLogger("mvde")

ALGORITMO = "pbkdf2_sha256"
ITERACIONES = 200_000
# Un atacante en la red interna puede probar contraseñas a mano; cinco intentos
# y cinco minutos de espera hacen que el ataque por diccionario no sea viable
# sin molestar a quien simplemente se equivocó al tipear.
MAX_INTENTOS = 5
BLOQUEO_SEGUNDOS = 300

_ENV_USUARIOS = "MVDE_USUARIOS"
_ENV_ARCHIVO = "MVDE_USUARIOS_ARCHIVO"
_SESSION_KEY = "mvde_auth_usuario"

# Intentos fallidos por usuario, en memoria del proceso. Un reinicio del
# contenedor los limpia: es un bloqueo contra la fuerza bruta de una sesión,
# no un castigo persistente.
_INTENTOS: dict[str, list[float]] = {}


# ------------------------------------------------------------------ hashing
def hashear(password: str, iteraciones: int = ITERACIONES) -> str:
    """Devuelve `pbkdf2_sha256$iteraciones$sal$hash` para pegar en la variable."""
    if not password:
        raise ValueError("la contraseña no puede estar vacía")
    sal = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), sal, iteraciones)
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
    return hmac.compare_digest(dk.hex(), esperado)


def _quemar_tiempo() -> None:
    """Para un usuario inexistente se calcula igual un PBKDF2 descartable: si no,
    la diferencia de tiempo entre «no existe» y «contraseña mala» delata qué
    usuarios son válidos."""
    hashlib.pbkdf2_hmac("sha256", b"x", b"y", ITERACIONES)


# ------------------------------------------------------------------ usuarios
def _parsear(crudo: str) -> dict[str, str]:
    """`usuario:hash` separados por `;` o por saltos de línea. Las líneas que
    empiezan con `#` son comentarios."""
    salida: dict[str, str] = {}
    for parte in crudo.replace("\n", ";").split(";"):
        linea = parte.strip()
        if not linea or linea.startswith("#"):
            continue
        if ":" not in linea:
            log.warning("MVDE: entrada de usuario sin «:», ignorada")
            continue
        usuario, guardado = linea.split(":", 1)
        usuario, guardado = usuario.strip().lower(), guardado.strip()
        if not usuario or not guardado.startswith(ALGORITMO + "$"):
            log.warning("MVDE: usuario «%s» con hash inválido, ignorado", usuario or "?")
            continue
        salida[usuario] = guardado
    return salida


def usuarios() -> dict[str, str]:
    """Los usuarios declarados, desde la variable o desde el archivo."""
    crudo = os.environ.get(_ENV_USUARIOS, "").strip()
    if not crudo:
        ruta = os.environ.get(_ENV_ARCHIVO, "").strip()
        if ruta:
            try:
                crudo = Path(ruta).read_text(encoding="utf-8")
            except OSError as exc:
                # Se declaró el archivo y no se puede leer: nadie entra. Falla
                # cerrado a propósito, no abierto.
                log.error("MVDE: no se pudo leer %s: %s", _ENV_ARCHIVO, exc)
                return {}
    return _parsear(crudo)


def activo() -> bool:
    """True si hay que pedir login. Se mira la declaración, no si parseó bien:
    con la variable puesta y mal escrita nadie entra, en vez de entrar todos."""
    return bool(os.environ.get(_ENV_USUARIOS, "").strip()
                or os.environ.get(_ENV_ARCHIVO, "").strip())


# ------------------------------------------------------------------ intentos
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
    u = (usuario or "").strip().lower()
    _INTENTOS.setdefault(u, []).append(time.time())


def limpiar_intentos(usuario: str | None = None) -> None:
    """Después de un login válido, o entre tests."""
    if usuario is None:
        _INTENTOS.clear()
    else:
        _INTENTOS.pop((usuario or "").strip().lower(), None)


# ------------------------------------------------------------------ login
def verificar(usuario: str, password: str) -> bool:
    """Valida la credencial. Nunca registra la contraseña, sólo el resultado."""
    u = (usuario or "").strip().lower()
    if bloqueado(u):
        return False
    guardado = usuarios().get(u)
    if guardado is None:
        _quemar_tiempo()
        _anotar_fallo(u)
        log.warning("MVDE: login fallido para «%s»", u or "?")
        return False
    if not _verificar_hash(password or "", guardado):
        _anotar_fallo(u)
        log.warning("MVDE: login fallido para «%s»", u)
        return False
    limpiar_intentos(u)
    log.info("MVDE: login correcto para «%s»", u)
    return True


def sesion_usuario(estado) -> str | None:
    """Quién está autenticado en esta sesión de Streamlit, o None."""
    if not activo():
        return estado.get(_SESSION_KEY) if hasattr(estado, "get") else None
    return estado.get(_SESSION_KEY)


def abrir_sesion(estado, usuario: str) -> None:
    estado[_SESSION_KEY] = (usuario or "").strip().lower()


def cerrar_sesion(estado) -> None:
    estado.pop(_SESSION_KEY, None)
