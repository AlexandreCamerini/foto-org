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


def test_exiftool_travado_cai_no_fallback_dentro_do_teto(tmp_path, monkeypatch):
    """A única espera potencialmente infinita do scan: um arquivo que faça o
    exiftool emudecer congelava a fila inteira em RODANDO para sempre (o
    readline do -stay_open não tem fim). Depois do teto, o processo é morto
    e o fallback responde — o scan segue."""
    import time

    import fotoorganizer.metadata.exiftool as mod
    monkeypatch.setattr(mod, "_TIMEOUT_S", 0.5)

    travado = tmp_path / "exiftool-travado"
    travado.write_text("#!/bin/bash\nwhile read linha; do :; done\n")
    travado.chmod(0o755)

    class FallbackEspiao:
        def supported_extensions(self): return {".jpg"}
        def extract(self, path): return MediaMetadata(make="do fallback")

    foto = make_jpeg(tmp_path / "a.jpg")
    extrator = ExifToolExtractor(binario=str(travado), fallback=FallbackEspiao())
    inicio = time.monotonic()
    meta = extrator.extract(foto)
    assert meta.make == "do fallback"
    assert time.monotonic() - inicio < 5  # teto + fallback, não a eternidade


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


def test_data_impossivel_nao_entra_na_coluna():
    """Uma foto não pode ter sido tirada depois de agora. Um registro datado
    de 2100 bastava para dominar o topo da grade ordenada por data e fazer a
    tela parecer quebrada.

    O valor bruto não se perde: continua na base bruta, que é o que o dono
    inspeciona. O que não entra é a coluna, que alimenta agrupamento e
    correlação."""
    meta = ExifToolExtractor._converter({
        "EXIF:DateTimeOriginal": "2100:08:07 12:00:00",
        "EXIF:Make": "Canon",
    })
    assert meta.data_capturada is None
    assert ("exif", "DateTimeOriginal") in {
        (ns, nome) for ns, nome, _ in meta.extras
    }


def test_sem_exif_a_data_vem_do_iptc():
    """Scan de agência ou arquivo digitalizado: o EXIF se perdeu na edição,
    mas o IPTC DateCreated (data em que a foto foi FEITA, pelo padrão IIM)
    sobreviveu. 7.957 JPGs do acervo real estão sem data por caminhos
    assim."""
    meta = ExifToolExtractor._converter({
        "IPTC:DateCreated": "2015:04:20",
        "IPTC:City": "Paraty",
    })
    assert meta.data_capturada == datetime(2015, 4, 20)


def test_sem_exif_a_data_vem_do_xmp_iso():
    """Lightroom/Photoshop escrevem XMP em ISO-8601 — que o parser não
    entendia: só o formato com dois-pontos do EXIF."""
    meta = ExifToolExtractor._converter({
        "XMP:DateCreated": "2018-11-02T09:15:30",
    })
    assert meta.data_capturada == datetime(2018, 11, 2, 9, 15, 30)


def test_exif_continua_mandando_sobre_iptc_e_xmp():
    meta = ExifToolExtractor._converter({
        "EXIF:DateTimeOriginal": "2020:01:05 08:00:00",
        "IPTC:DateCreated": "2015:04:20",
        "XMP:DateCreated": "2018-11-02T09:15:30",
    })
    assert meta.data_capturada == datetime(2020, 1, 5, 8, 0)


def test_data_antiga_continua_valendo():
    """Não há piso: filme digitalizado com data manual pode ser de 1950, e um
    piso arbitrário transformaria acervo antigo em erro."""
    meta = ExifToolExtractor._converter(
        {"EXIF:DateTimeOriginal": "1962:03:15 10:00:00"}
    )
    assert meta.data_capturada == datetime(1962, 3, 15, 10, 0)


def test_subsegundo_desempata_rajada_sem_mudar_a_hora():
    """`SubSecDateTimeOriginal` vence `DateTimeOriginal` porque é a MESMA
    data com mais precisão. Seis fotos de uma rajada dividem o segundo; sem
    o subsegundo a ordem entre elas era arbitrária."""
    meta = ExifToolExtractor._converter({
        "EXIF:DateTimeOriginal": "2025:11:08 01:16:32",
        "Composite:SubSecDateTimeOriginal": "2025:11:08 01:16:32.87",
    })
    assert meta.data_capturada == datetime(2025, 11, 8, 1, 16, 32)


def test_gps_datetime_nao_entra_como_hora_de_parede():
    """`GPSDateTime` é a data mais confiável do arquivo e é UTC. Usá-la como
    hora de parede deslocaria a foto pelo tamanho do fuso — o mesmo defeito
    que o Takeout tinha."""
    meta = ExifToolExtractor._converter({
        "Composite:GPSDateTime": "2019:07:14 12:00:00Z",
    })
    assert meta.data_capturada is None


def test_offset_declarado_vira_instante_absoluto():
    """1.527 fotos do acervo declaram `OffsetTimeOriginal` e ele era jogado
    fora, enquanto a correlação gastava estatística para adivinhar o fuso."""
    meta = ExifToolExtractor._converter({
        "EXIF:DateTimeOriginal": "2019:07:14 14:00:00",
        "EXIF:OffsetTimeOriginal": "+02:00",
    })
    assert meta.data_capturada == datetime(2019, 7, 14, 14, 0)
    assert meta.data_capturada_utc == datetime(2019, 7, 14, 12, 0)


def test_offset_negativo_e_sem_dois_pontos():
    meta = ExifToolExtractor._converter({
        "EXIF:DateTimeOriginal": "2020:01:01 09:00:00",
        "EXIF:OffsetTime": "-0300",
    })
    assert meta.data_capturada_utc == datetime(2020, 1, 1, 12, 0)


def test_sem_offset_o_extrator_nao_inventa_instante():
    """Igualdade entre os dois instantes é dita por quem GRAVA, nunca por um
    palpite daqui — mesma regra do provider do Apple Fotos."""
    meta = ExifToolExtractor._converter({
        "EXIF:DateTimeOriginal": "2020:01:01 09:00:00",
    })
    assert meta.data_capturada_utc is None


@pytest.mark.parametrize("bruto", ["", None, "meio-dia", "+25:00", "+02:99"])
def test_offset_invalido_e_ignorado(bruto):
    from fotoorganizer.metadata.exiftool import _offset

    assert _offset(bruto) is None


# --- sidecar .xmp (A3) e palavras-chave unificadas (A4) --------------------

def test_sidecar_e_encontrado_nos_dois_padroes(tmp_path):
    from fotoorganizer.metadata.exiftool import _sidecar_de

    foto = tmp_path / "IMG_1.jpg"
    foto.write_bytes(b"x")
    assert _sidecar_de(foto) is None

    adobe = tmp_path / "IMG_1.jpg.xmp"
    adobe.write_text("<x/>")
    assert _sidecar_de(foto) == adobe

    adobe.unlink()
    darktable = tmp_path / "IMG_1.xmp"
    darktable.write_text("<x/>")
    assert _sidecar_de(foto) == darktable


def test_sidecar_vence_o_arquivo_e_leva_a_data_junto():
    """Se o sidecar declara data, TODAS as datas do original saem — inclusive
    o offset. Casar a data que o editor gravou com o fuso que a câmera gravou
    produz um instante que nunca existiu, e o erro seria invisível."""
    from fotoorganizer.metadata.exiftool import _fundir_sidecar

    fundido = _fundir_sidecar(
        {
            "EXIF:DateTimeOriginal": "2019:07:14 14:00:00",
            "EXIF:OffsetTimeOriginal": "+02:00",
            "EXIF:Model": "Canon R5",
        },
        {"XMP:DateCreated": "2020-01-01T09:00:00", "XMP:Rating": "5"},
    )
    assert "EXIF:DateTimeOriginal" not in fundido
    assert "EXIF:OffsetTimeOriginal" not in fundido
    assert fundido["EXIF:Model"] == "Canon R5"       # o resto do original fica
    assert fundido["XMPSidecar:Rating"] == "5"       # origem preservada
    meta = ExifToolExtractor._converter(fundido)
    assert meta.data_capturada == datetime(2020, 1, 1, 9, 0)
    assert meta.data_capturada_utc is None           # o fuso saiu junto


def test_sidecar_sem_data_nao_apaga_a_do_arquivo():
    from fotoorganizer.metadata.exiftool import _fundir_sidecar

    fundido = _fundir_sidecar(
        {"EXIF:DateTimeOriginal": "2019:07:14 14:00:00"},
        {"XMP:Rating": "4"},
    )
    assert fundido["EXIF:DateTimeOriginal"] == "2019:07:14 14:00:00"


def test_palavras_chave_dos_quatro_formatos_sem_repetir():
    """A mesma curadoria chega pelos quatro formatos quando o arquivo passou
    por mais de um programa. Contar quatro vezes somaria confiança sobre uma
    afirmação só — o que docs/CONFIANCA.md proíbe."""
    meta = ExifToolExtractor._converter({
        "XMP:TagsList": ["Viagens|2019|Patagônia"],
        "XMP:HierarchicalSubject": ["Viagens|2019|Patagônia"],
        "XMP:Subject": ["Patagônia", "Selected"],
        "IPTC:Keywords": ["Patagônia"],
    })
    assert meta.palavras_chave == (
        "Viagens|2019|Patagônia", "Viagens", "2019", "Patagônia", "Selected",
    )


def test_hierarquia_entra_inteira_e_por_nivel():
    """O caminho completo responde 'onde isto estava organizado?'; cada nível
    isolado é o termo que a classificação procura."""
    meta = ExifToolExtractor._converter(
        {"XMP:HierarchicalSubject": "Eventos|Casamento"}
    )
    assert meta.palavras_chave == ("Eventos|Casamento", "Eventos", "Casamento")


def test_sem_palavra_chave_o_campo_fica_vazio():
    assert ExifToolExtractor._converter({}).palavras_chave == ()
