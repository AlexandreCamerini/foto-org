"""Extrator via exiftool: conversão, protocolo em lote e falha limpa.

O que exige o binário instalado é pulado sem ele — o app funciona sem
exiftool, e a suíte tem de continuar verde numa máquina limpa.
"""

from datetime import datetime
from pathlib import Path

import pytest

from fotoorganizer.metadata import MediaMetadata, criar_extrator
from fotoorganizer.metadata.exiftool import ExifToolExtractor, _data
from fotoorganizer.metadata.purepython import PurePythonExtractor
from tests.fixtures import make_jpeg

tem_exiftool = pytest.mark.skipif(
    not ExifToolExtractor.disponivel(), reason="exiftool não instalado"
)


# -- conversão (não precisa do binário) --------------------------------------
def test_coordenada_vem_do_composite_com_sinal():
    """A tag crua é sempre positiva e o hemisfério mora no Ref. Usar
    `EXIF:GPSLatitude` direto põe o Rio no hemisfério norte."""
    meta = ExifToolExtractor._converter({
        "EXIF:GPSLatitude": "+22.95000000", "EXIF:GPSLatitudeRef": "South",
        "EXIF:GPSLongitude": "+43.18000000", "EXIF:GPSLongitudeRef": "West",
        "Composite:GPSLatitude": "-22.95000000",
        "Composite:GPSLongitude": "-43.18000000",
    })
    assert (meta.gps_lat, meta.gps_lon) == (-22.95, -43.18)


def test_orientacao_por_extenso_vira_numero():
    """`-n` daria o número e estragaria o resto da base bruta, que existe
    para ser lida por gente."""
    assert ExifToolExtractor._converter(
        {"EXIF:Orientation": "Rotate 90 CW"}).orientacao == 6
    assert ExifToolExtractor._converter(
        {"EXIF:Orientation": "Horizontal (normal)"}).orientacao == 1
    # Vocabulário desconhecido não vira palpite.
    assert ExifToolExtractor._converter(
        {"EXIF:Orientation": "coisa nova"}).orientacao is None


def test_data_aceita_subsegundo_e_fuso():
    assert _data("2025:11:08 01:16:32") == datetime(2025, 11, 8, 1, 16, 32)
    assert _data("2025:11:08 01:16:32.35") == datetime(2025, 11, 8, 1, 16, 32)
    assert _data("2019:03:30 18:53:38Z") == datetime(2019, 3, 30, 18, 53, 38)
    assert _data("") is None and _data(None) is None
    assert _data("ontem à tarde") is None


def test_grupos_derivados_e_binarios_ficam_fora_da_base_bruta():
    """`Composite` é cálculo do exiftool, não leitura do arquivo; `File`
    repete o filesystem. Entrar como se fossem metadado do arquivo faria a
    base bruta mentir sobre a própria origem."""
    meta = ExifToolExtractor._converter({
        "SourceFile": "/x/y.jpg",
        "EXIF:Make": "Canon",
        "File:FileSize": "6.1 MB",
        "ExifTool:ExifToolVersion": 13.55,
        "Composite:GPSPosition": "+1, -2",
        "EXIF:ThumbnailImage": "(Binary data 8654 bytes, use -b option)",
        "MakerNotes:LensType": "EF24-70mm",
    })
    chaves = {(ns, nome) for ns, nome, _ in meta.extras}
    assert ("exif", "Make") in chaves
    assert not any(ns in {"file", "exiftool", "composite"} for ns, _, _ in meta.extras)
    assert ("exif", "ThumbnailImage") not in chaves
    # MakerNotes tem exclusão própria, testada logo abaixo (D-027).
    assert meta.lente == "EF24-70mm"


def test_valor_estruturado_vira_json_em_vez_de_repr_python():
    (ns, nome, valor), = [
        e for e in ExifToolExtractor._converter(
            {"XMP:Subject": ["praia", "família"]}
        ).extras
    ]
    assert (ns, nome) == ("xmp", "Subject")
    assert valor == '["praia", "família"]'


# -- protocolo e falhas ------------------------------------------------------
def test_arquivo_inexistente_nao_levanta(tmp_path):
    """Contrato do Protocol: erro por arquivo nunca derruba a varredura."""
    meta = ExifToolExtractor().extract(tmp_path / "nao_existe.jpg")
    assert isinstance(meta, MediaMetadata)
    assert meta.erro is not None and meta.data_capturada is None


def test_quebra_de_linha_no_nome_vai_para_o_fallback(tmp_path):
    """O protocolo do -stay_open é delimitado por linha: um `\\n` no caminho
    dessincronizaria a conversa e envenenaria a leitura das próximas fotos."""
    class FallbackEspiao:
        def __init__(self): self.chamado_com = None
        def supported_extensions(self): return {".jpg"}
        def extract(self, path):
            self.chamado_com = path
            return MediaMetadata(make="do fallback")

    espiao = FallbackEspiao()
    estranho = tmp_path / "foto\ncom quebra.jpg"
    meta = ExifToolExtractor(fallback=espiao).extract(estranho)
    assert meta.make == "do fallback"
    assert espiao.chamado_com == estranho


def test_binario_ausente_cai_no_fallback(tmp_path):
    """Sem exiftool o app continua catalogando — com menos sinal."""
    foto = make_jpeg(tmp_path / "a.jpg")
    extrator = ExifToolExtractor(binario="exiftool-que-nao-existe-aqui")
    meta = extrator.extract(foto)
    assert isinstance(meta, MediaMetadata)
    assert meta.erro is None or "não encontrado" not in (meta.erro or "")


def test_extensoes_sao_as_que_o_app_trata(tmp_path):
    """O exiftool lê mais formatos do que o resto do app sabe tratar; quem
    manda continua sendo o fallback."""
    assert (ExifToolExtractor().supported_extensions()
            == PurePythonExtractor().supported_extensions())


# -- com o binário instalado -------------------------------------------------
@tem_exiftool
def test_le_um_jpeg_de_verdade(tmp_path):
    foto = make_jpeg(tmp_path / "sintetica.jpg")
    with ExifToolExtractor() as extrator:
        meta = extrator.extract(foto)
    assert meta.erro is None
    assert meta.largura and meta.altura
    assert any(ns == "exif" for ns, _, _ in meta.extras) or meta.extras == []


@tem_exiftool
def test_processo_e_reaproveitado_entre_arquivos(tmp_path):
    """O ganho do -stay_open é não pagar a partida do Perl por foto."""
    fotos = [make_jpeg(tmp_path / f"f{i}.jpg") for i in range(3)]
    with ExifToolExtractor() as extrator:
        primeiro = extrator._garantir()
        for foto in fotos:
            extrator.extract(foto)
        assert extrator._garantir() is primeiro
        assert primeiro.poll() is None


@tem_exiftool
def test_criar_extrator_prefere_exiftool_quando_existe():
    assert isinstance(criar_extrator(), ExifToolExtractor)
    assert isinstance(criar_extrator(preferir_exiftool=False),
                      PurePythonExtractor)


def test_makernotes_fica_fora_da_base_bruta():
    """D-027: 259 campos por CR3 sobre o estado interno da câmera, 83% de
    todo o metadado de um acervo real, e nada ali decide viagem, evento ou
    lugar. Fica fora — mas o que era aproveitável continua chegando."""
    meta = ExifToolExtractor._converter({
        "EXIF:Make": "Canon",
        "MakerNotes:LensType": "EF24-70mm f/2.8L II USM",
        "MakerNotes:FocusMode": "One-shot AF",
        "MakerNotes:ShutterCount": 32211,
    })
    assert not any(ns == "makernotes" for ns, _, _ in meta.extras)
    # A lente vem do bloco do fabricante e não se perde: ela é lida do JSON
    # inteiro, não da base bruta.
    assert meta.lente == "EF24-70mm f/2.8L II USM"
