import os

from fotoorganizer.scanner import DiscoveryConfig, iter_media_files
from tests.fixtures import make_jpeg

EXTS = frozenset({".jpg", ".jpeg", ".png"})


def _paths(root, config):
    return sorted(str(p.relative_to(root)) for p in iter_media_files(root, config))


def test_encontra_recursivo_com_unicode(tmp_path):
    make_jpeg(tmp_path / "a.jpg")
    make_jpeg(tmp_path / "Viagens" / "日本" / "fotografía é vida.jpg")
    found = _paths(tmp_path, DiscoveryConfig(extensoes=EXTS))
    assert found == ["Viagens/日本/fotografía é vida.jpg", "a.jpg"]


def test_ignora_ocultos_por_padrao(tmp_path):
    make_jpeg(tmp_path / ".escondida.jpg")
    make_jpeg(tmp_path / ".pasta_oculta" / "dentro.jpg")
    make_jpeg(tmp_path / "normal.jpg")

    assert _paths(tmp_path, DiscoveryConfig(extensoes=EXTS)) == ["normal.jpg"]
    com_ocultos = _paths(
        tmp_path, DiscoveryConfig(extensoes=EXTS, incluir_ocultos=True)
    )
    assert len(com_ocultos) == 3


def test_nao_atravessa_symlink_e_evita_ciclo(tmp_path):
    real = tmp_path / "real"
    make_jpeg(real / "foto.jpg")
    # Symlink de diretório apontando para o pai — ciclo clássico.
    os.symlink(tmp_path, real / "loop")
    # Symlink de arquivo também não deve ser seguido por padrão.
    os.symlink(real / "foto.jpg", tmp_path / "atalho.jpg")

    found = _paths(tmp_path, DiscoveryConfig(extensoes=EXTS))
    assert found == ["real/foto.jpg"]


def test_padroes_ignorados(tmp_path):
    make_jpeg(tmp_path / "Exportadas" / "e.jpg")
    make_jpeg(tmp_path / "Viagens" / "v.jpg")
    config = DiscoveryConfig(extensoes=EXTS, padroes_ignorados=("Exportadas",))
    assert _paths(tmp_path, config) == ["Viagens/v.jpg"]


def test_extensao_desconhecida_ignorada(tmp_path):
    make_jpeg(tmp_path / "foto.jpg")
    (tmp_path / "video.mp4").write_bytes(b"nao e foto")
    (tmp_path / "Thumbs.db").write_bytes(b"lixo de sistema")
    assert _paths(tmp_path, DiscoveryConfig(extensoes=EXTS)) == ["foto.jpg"]
