"""Login opcional del despliegue en servidor: hash, verificación, bloqueo por
intentos y el interruptor que lo mantiene apagado en el escritorio."""
import pytest

from mvde import auth


@pytest.fixture(autouse=True)
def sin_estado(monkeypatch):
    """Cada test arranca sin usuarios declarados y sin intentos acumulados."""
    monkeypatch.delenv("MVDE_USUARIOS", raising=False)
    monkeypatch.delenv("MVDE_USUARIOS_ARCHIVO", raising=False)
    auth.limpiar_intentos()
    yield
    auth.limpiar_intentos()


def _declarar(monkeypatch, usuario="martin", clave="tolstoi-1869"):
    monkeypatch.setenv("MVDE_USUARIOS", f"{usuario}:{auth.hashear(clave)}")
    return usuario, clave


def test_sin_usuarios_declarados_no_hay_login():
    assert auth.activo() is False
    assert auth.usuarios() == {}


def test_hash_no_guarda_la_contrasena_y_cambia_con_la_sal():
    clave = "tolstoi-1869"
    a, b = auth.hashear(clave), auth.hashear(clave)
    assert clave not in a and a.startswith("pbkdf2_sha256$200000$")
    assert a != b, "dos hashes de la misma clave no pueden coincidir: la sal es por usuario"
    assert auth._verificar_hash(clave, a) and auth._verificar_hash(clave, b)
    assert not auth._verificar_hash("otra", a)


def test_verifica_la_credencial_correcta_y_rechaza_la_mala(monkeypatch):
    usuario, clave = _declarar(monkeypatch)
    assert auth.activo() is True
    assert auth.verificar(usuario, clave) is True
    assert auth.verificar(usuario.upper(), clave) is True, "el usuario no distingue mayúsculas"
    auth.limpiar_intentos()
    assert auth.verificar(usuario, "otra") is False
    assert auth.verificar("nadie", clave) is False


def test_bloquea_despues_de_cinco_intentos(monkeypatch):
    usuario, clave = _declarar(monkeypatch)
    for _ in range(auth.MAX_INTENTOS):
        assert auth.verificar(usuario, "mala") is False
    assert auth.bloqueado(usuario) > 0
    # Con el usuario bloqueado, ni la contraseña correcta entra.
    assert auth.verificar(usuario, clave) is False
    auth.limpiar_intentos(usuario)
    assert auth.bloqueado(usuario) == 0
    assert auth.verificar(usuario, clave) is True


def test_varios_usuarios_y_entradas_invalidas(monkeypatch):
    linea = (f"ana:{auth.hashear('clave-ana')};"
             "# comentario\n"
             f"beto:{auth.hashear('clave-beto')};"
             "roto-sin-dos-puntos;"
             "cacho:texto_plano")
    monkeypatch.setenv("MVDE_USUARIOS", linea)
    assert set(auth.usuarios()) == {"ana", "beto"}, "las entradas inválidas se descartan"
    assert auth.verificar("ana", "clave-ana") and auth.verificar("beto", "clave-beto")
    assert auth.verificar("cacho", "texto_plano") is False


def test_variable_declarada_pero_ilegible_no_deja_entrar_a_nadie(monkeypatch, tmp_path):
    """Falla cerrado: si el archivo de usuarios no se puede leer, el login sigue
    exigido y sin credenciales válidas, en vez de abrirse para todos."""
    monkeypatch.setenv("MVDE_USUARIOS_ARCHIVO", str(tmp_path / "no_existe.txt"))
    assert auth.activo() is True
    assert auth.usuarios() == {}
    assert auth.verificar("quien", "sea") is False


def test_usuarios_desde_archivo(monkeypatch, tmp_path):
    ruta = tmp_path / "usuarios.txt"
    ruta.write_text(f"# usuarios del despliegue\nana:{auth.hashear('clave-ana')}\n", encoding="utf-8")
    monkeypatch.setenv("MVDE_USUARIOS_ARCHIVO", str(ruta))
    assert auth.activo() and auth.verificar("ana", "clave-ana")


def test_sesion_se_abre_y_se_cierra(monkeypatch):
    usuario, _ = _declarar(monkeypatch)
    estado: dict = {}
    assert auth.sesion_usuario(estado) is None
    auth.abrir_sesion(estado, usuario.upper())
    assert auth.sesion_usuario(estado) == usuario
    auth.cerrar_sesion(estado)
    assert auth.sesion_usuario(estado) is None


def test_hashear_rechaza_contrasena_vacia():
    with pytest.raises(ValueError):
        auth.hashear("")
