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
