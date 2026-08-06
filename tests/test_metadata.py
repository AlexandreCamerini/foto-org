from datetime import datetime
from pathlib import Path

import pytest

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


# -- base bruta: tudo que o arquivo diz, não só os 8 campos tipados ----------
def test_extras_trazem_as_tags_do_arquivo(tmp_path):
    """O catálogo guarda 8 colunas; o arquivo carrega dezenas de tags. As
    correlações que ainda não foram escritas precisam do resto."""
    path = make_jpeg(
        tmp_path / "foto.jpg", data_exif="2024:05:04 10:30:00",
        gps=(43.95, 4.8083), make="Canon", model="EOS R6",
        lente="RF 50mm", orientacao=6,
    )
    meta = PurePythonExtractor().extract(path)
    chaves = {(ns, chave) for ns, chave, _ in meta.extras}
    assert ("exif", "Make") in chaves
    assert ("exif", "DateTimeOriginal") in chaves
    assert ("exif", "LensModel") in chaves
    assert ("gps", "GPSLatitude") in chaves
    # Valor legível, não repr de objeto binário.
    valores = {chave: v for _, chave, v in meta.extras}
    assert valores["Make"] == "Canon"
    assert len(meta.extras) > 8


def test_valor_ilegivel_ou_gigante_fica_de_fora():
    from fotoorganizer.metadata.purepython import _coletar, _valor_legivel

    assert _valor_legivel(b"\x00\x01binario") is None
    assert _valor_legivel("x" * 5000) is None
    assert _valor_legivel("  Canon  ") == "Canon"
    assert _valor_legivel(None) is None

    destino: list = []
    _coletar(destino, "exif", [("MakerNote", "seja o que for"), ("ISO", 100)])
    assert destino == [("exif", "ISO", "100")]


def _com_iptc(caminho: Path, campos: list[tuple[int, int, bytes]]) -> Path:
    """JPEG com bloco IPTC/IIM dentro de um APP13 Photoshop IRB."""
    from PIL import Image

    def iim(reg: int, campo: int, valor: bytes) -> bytes:
        return b"\x1c" + bytes([reg, campo]) + len(valor).to_bytes(2, "big") + valor

    bloco = b"".join(iim(r, c, v) for r, c, v in campos)
    Image.new("RGB", (32, 24), (90, 110, 130)).save(caminho, "JPEG")
    irb = (b"Photoshop 3.0\x00" + b"8BIM\x04\x04\x00\x00"
           + len(bloco).to_bytes(4, "big") + bloco)
    bruto = caminho.read_bytes()
    caminho.write_bytes(
        bruto[:2] + b"\xff\xed" + (len(irb) + 2).to_bytes(2, "big") + irb + bruto[2:]
    )
    return caminho


def test_iptc_traz_autor_direitos_e_palavras_chave(tmp_path):
    """O namespace iptc estava declarado no schema desde o M1 e nunca
    recebia uma linha: o extrator não olhava para ele. É onde vivem autor,
    direitos e palavras-chave em arquivo vindo de agência ou Photoshop."""
    from fotoorganizer.metadata import PurePythonExtractor

    caminho = _com_iptc(tmp_path / "com_iptc.jpg", [
        (2, 5, "Ponte de Avignon".encode()),
        (2, 80, "Alexandre Camerini".encode()),
        (2, 25, b"viagem"), (2, 25, b"franca"),
        (2, 116, "(c) 2024".encode()),
        (2, 90, b"Avignon"),
    ])

    meta = PurePythonExtractor().extract(caminho)
    iptc = {chave: valor for ns, chave, valor in meta.extras if ns == "iptc"}

    assert iptc["ObjectName"] == "Ponte de Avignon"
    assert iptc["By-line"] == "Alexandre Camerini"
    # Campo repetível vira lista separada por ponto e vírgula — não índice
    # na chave, que não sobrevive a reprocessamento.
    assert iptc["Keywords"] == "viagem; franca"
    assert iptc["CopyrightNotice"] == "(c) 2024"
    assert iptc["City"] == "Avignon"
    assert meta.erro is None


def test_arquivo_sem_iptc_nao_inventa_namespace(tmp_path):
    from fotoorganizer.metadata import PurePythonExtractor

    caminho = make_jpeg(tmp_path / "limpa.jpg", seed=3)
    meta = PurePythonExtractor().extract(caminho)
    assert not [e for e in meta.extras if e[0] == "iptc"]


def test_xmp_traz_autor_e_palavras_chave(tmp_path):
    """XMP exige defusedxml (parser seguro para XML não confiável). Sem ele
    o extrator degrada em silêncio — o teste pula, não falha."""
    pytest.importorskip("defusedxml")
    from PIL import Image

    from fotoorganizer.metadata import PurePythonExtractor

    xmp = (
        '<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        '<rdf:Description rdf:about="" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/">'
        "<dc:creator><rdf:Seq><rdf:li>Alexandre Camerini</rdf:li>"
        "</rdf:Seq></dc:creator>"
        "<dc:subject><rdf:Bag><rdf:li>viagem</rdf:li><rdf:li>franca</rdf:li>"
        "</rdf:Bag></dc:subject>"
        "</rdf:Description></rdf:RDF></x:xmpmeta><?xpacket end='w'?>"
    ).encode()

    caminho = tmp_path / "com_xmp.jpg"
    Image.new("RGB", (32, 24), (100, 120, 140)).save(caminho, "JPEG", xmp=xmp)

    meta = PurePythonExtractor().extract(caminho)
    achatado = {c: v for ns, c, v in meta.extras if ns == "xmp"}
    juntos = " ".join(f"{c}={v}" for c, v in achatado.items())
    assert "Alexandre Camerini" in juntos
    assert "viagem" in juntos and "franca" in juntos


def test_sem_exif_a_data_vem_dos_extras_iptc_ou_xmp():
    """Arquivo editado perde EXIF e conserva IPTC/XMP: a data de captura
    não pode se perder junto. O IIM grava a data como '20150420' (8
    dígitos) e o XMP como ISO-8601 — os dois caminhos valem."""
    from fotoorganizer.metadata.purepython import _data_dos_extras
    from datetime import datetime

    assert _data_dos_extras([
        ("iptc", "DateCreated", "20150420"),
    ]) == datetime(2015, 4, 20)
    assert _data_dos_extras([
        ("xmp", "photoshop.DateCreated", "2018-11-02T09:15:30"),
    ]) == datetime(2018, 11, 2, 9, 15, 30)
    # Chave que não é de captura (data de modificação) não entra.
    assert _data_dos_extras([
        ("xmp", "xmp.ModifyDate", "2018-11-02T09:15:30"),
    ]) is None
    assert _data_dos_extras([("iptc", "City", "Paraty")]) is None


def test_data_dos_extras_chega_a_data_capturada_num_jpeg_com_xmp(tmp_path):
    """Ponta a ponta no extrator puro-Python: JPEG sem EXIF, com
    photoshop:DateCreated no XMP → data_capturada preenchida."""
    from datetime import datetime

    from PIL import Image

    xmp = (
        '<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        '<rdf:Description rdf:about="" '
        'xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/">'
        "<photoshop:DateCreated>2018-11-02T09:15:30</photoshop:DateCreated>"
        "</rdf:Description></rdf:RDF></x:xmpmeta><?xpacket end='w'?>"
    ).encode()
    caminho = tmp_path / "sem_exif_com_xmp.jpg"
    Image.new("RGB", (32, 24), (10, 20, 30)).save(caminho, "JPEG", xmp=xmp)

    meta = PurePythonExtractor().extract(caminho)
    assert meta.data_capturada == datetime(2018, 11, 2, 9, 15, 30)
