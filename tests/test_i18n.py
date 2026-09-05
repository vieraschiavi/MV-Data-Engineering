from mvde import ETAPAS
from mvde.i18n import LANGS, _T, all_keys, t


def test_paridad_de_idiomas():
    for key, entry in _T.items():
        for lang in LANGS:
            assert entry.get(lang), f"falta {lang} para {key}"


def test_cada_etapa_tiene_nombre_y_descripcion():
    for e in ETAPAS:
        assert f"st_{e}" in _T and f"d_{e}" in _T


def test_fallback():
    assert t("clave_inexistente", "en") == "clave_inexistente"
    assert t("app_title", "xx") == t("app_title", "es")
    assert len(all_keys()) > 60
