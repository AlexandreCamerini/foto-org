from datetime import datetime

from fotoorganizer.metadata import PurePythonExtractor
from tests.fixtures import make_corrupt_jpeg, make_jpeg, make_png


def test_jpeg_com_exif_completo(tmp_path):
    path = make_jpeg(
        tmp_path / "foto.jpg",
        data_exif="2024:05:04 10:30:00",
        gps=(43.95, 4.8083),  # Avignon
        make="Canon", model="EOS R6", lente="RF 50mm", orientacao=6,
    )
    meta = PurePythonExtractor().extract(path)
    assert meta.erro is None
    assert meta.data_capturada == datetime(2024, 5, 4, 10, 30)
    assert meta.make == "Canon"
    assert meta.model == "EOS R6"
    assert meta.lente == "RF 50mm"
    assert meta.orientacao == 6
    assert meta.largura == 64 and meta.altura == 48
    assert abs(meta.gps_lat - 43.95) < 0.001
    assert abs(meta.gps_lon - 4.8083) < 0.001


def test_png_sem_exif(tmp_path):
    meta = PurePythonExtractor().extract(make_png(tmp_path / "img.png"))
    assert meta.erro is None
    assert meta.data_capturada is None
    assert meta.gps_lat is None
    assert meta.largura == 32


def test_data_exif_invalida_nao_quebra(tmp_path):
    path = make_jpeg(tmp_path / "foto.jpg", data_exif="0000:00:00 00:00:00")
    meta = PurePythonExtractor().extract(path)
    assert meta.erro is None
    assert meta.data_capturada is None
    # Data inválida fica registrada como metadado bruto para diagnóstico.
    assert ("exif", "data_invalida", "0000:00:00 00:00:00") in meta.extras


def test_arquivo_corrompido_registra_erro(tmp_path):
    meta = PurePythonExtractor().extract(make_corrupt_jpeg(tmp_path / "ruim.jpg"))
    assert meta.erro is not None


def test_extensoes_suportadas_incluem_raw_e_heif():
    exts = PurePythonExtractor().supported_extensions()
    assert {".jpg", ".png", ".webp", ".tiff"} <= exts
    # rawpy e pillow-heif estão nas dependências do projeto.
    assert {".dng", ".cr3", ".heic", ".hif"} <= exts


# -- RAW: lente e orientação vêm do libraw, inclusive em CR3 ------------------
class _FakeSizes:
    def __init__(self, flip: int) -> None:
        self.width, self.height, self.flip = 6000, 4000, flip


class _FakeRaw:
    """Dublê do rawpy: fotos RAW reais não entram no repositório, e gerar um
    CR3 sintético não é viável — o que importa aqui é o mapeamento."""

    def __init__(self, flip: int, lente: str) -> None:
        from types import SimpleNamespace

        self.other = SimpleNamespace(timestamp=datetime(2025, 11, 1, 3, 43, 37))
        self.sizes = _FakeSizes(flip)
        self.lens = SimpleNamespace(model=lente)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def _extrair_raw(monkeypatch, tmp_path, nome: str, flip: int, lente: str):
    from types import SimpleNamespace

    from fotoorganizer.metadata import purepython

    arquivo = tmp_path / nome
    arquivo.write_bytes(b"nao e um raw de verdade")
    monkeypatch.setattr(purepython, "_HAS_RAW", True)
    monkeypatch.setattr(
        purepython, "rawpy",
        SimpleNamespace(imread=lambda _p: _FakeRaw(flip, lente)),
        raising=False,
    )
    return PurePythonExtractor().extract(arquivo)


def test_raw_ganha_lente_e_orientacao_do_libraw(monkeypatch, tmp_path):
    """65% da amostra real do acervo ficava sem lente e sem orientação, e
    toda ela era RAW — o exifread não lê CR3, o libraw lê."""
    meta = _extrair_raw(
        monkeypatch, tmp_path, "ACM_0001.CR3", flip=6,
        lente="  EF24-70mm f/2.8L II USM  ",
    )
    assert meta.lente == "EF24-70mm f/2.8L II USM"
    assert meta.orientacao == 6  # flip 6 (dcraw) == 90° horário (EXIF)
    assert meta.data_capturada == datetime(2025, 11, 1, 3, 43, 37)
    assert (meta.largura, meta.altura) == (6000, 4000)


def test_flip_do_libraw_vira_orientacao_exif(monkeypatch, tmp_path):
    for flip, esperado in [(0, 1), (3, 3), (5, 8), (6, 6)]:
        meta = _extrair_raw(
            monkeypatch, tmp_path, f"f{flip}.dng", flip=flip, lente="x"
        )
        assert meta.orientacao == esperado, flip


def test_raw_sem_lente_ou_rotacao_conhecida_nao_inventa(monkeypatch, tmp_path):
    meta = _extrair_raw(monkeypatch, tmp_path, "vazio.dng", flip=-1, lente="")
    assert meta.lente is None
    assert meta.orientacao is None
