from PIL import Image

from fotoorganizer.thumbnails import ThumbnailCache, generate_thumbnail
from tests.fixtures import make_corrupt_jpeg, make_jpeg


def test_gera_miniatura_reduzida(tmp_path):
    original = make_jpeg(tmp_path / "foto.jpg", size=(1600, 1200))
    destino = tmp_path / "thumb.jpg"
    assert generate_thumbnail(original, destino, size=320) is True
    with Image.open(destino) as thumb:
        assert max(thumb.size) == 320


def test_orientacao_exif_aplicada(tmp_path):
    # Orientação 6 = 90° CW: paisagem vira retrato na miniatura.
    original = make_jpeg(tmp_path / "foto.jpg", size=(400, 200), orientacao=6)
    destino = tmp_path / "thumb.jpg"
    generate_thumbnail(original, destino, size=320)
    with Image.open(destino) as thumb:
        assert thumb.height > thumb.width


def test_corrompida_retorna_false_sem_excecao(tmp_path):
    original = make_corrupt_jpeg(tmp_path / "ruim.jpg")
    destino = tmp_path / "thumb.jpg"
    assert generate_thumbnail(original, destino) is False
    assert not destino.exists()


def test_cache_gera_uma_vez(tmp_path):
    original = make_jpeg(tmp_path / "foto.jpg", size=(800, 600))
    cache = ThumbnailCache(tmp_path / "cache")

    primeira = cache.get_or_generate("xxh3:abc123", original)
    assert primeira is not None and primeira.is_file()
    mtime = primeira.stat().st_mtime_ns

    segunda = cache.get_or_generate("xxh3:abc123", original)
    assert segunda == primeira
    assert segunda.stat().st_mtime_ns == mtime  # não regenerou


def test_cache_chave_sanitizada_e_metricas(tmp_path):
    original = make_jpeg(tmp_path / "foto.jpg")
    cache = ThumbnailCache(tmp_path / "cache")
    path = cache.get_or_generate("xxh3:com:dois_pontos", original)
    assert ":" not in path.name
    assert cache.tamanho_bytes() > 0
    cache.limpar()
    assert cache.tamanho_bytes() == 0
    assert cache.get("xxh3:com:dois_pontos") is None
