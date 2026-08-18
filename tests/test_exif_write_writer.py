"""Testes das primitivas de escrita EXIF de localização (fase 6, plano 02).

O que exige o binário `exiftool` é marcado com `tem_exiftool` e pulado sem
ele — mesmo contrato de `tests/test_exiftool_extractor.py`. O resto (diff de
tags, validação de campos, detecção de pasta sincronizada, allowlist de
formatos) é puro Python, sem subprocesso, e roda sempre.
"""

from __future__ import annotations

import pytest

from fotoorganizer.exif_write.verificacao import DiffTags, campo_gravado, diferenca
from fotoorganizer.metadata.exiftool import ExifToolExtractor

tem_exiftool = pytest.mark.skipif(
    not ExifToolExtractor.disponivel(), reason="exiftool não instalado"
)


# -- Task 1: verificacao.py — dump, allowlist estrutural, diff --------------


def test_diferenca_dumps_identicos_devolve_tres_dicionarios_vazios():
    antes = {"EXIF:Make": "Canon", "File:FileSize": "123"}
    depois = dict(antes)
    diff = diferenca(antes, depois)
    assert diff == DiffTags(esperadas={}, estruturais={}, inesperadas={})


def test_diferenca_classifica_gps_completo_em_esperadas():
    antes: dict[str, str] = {}
    depois = {
        "GPS:GPSLatitude": "-23.55052",
        "GPS:GPSLatitudeRef": "S",
        "GPS:GPSLongitude": "-46.633308",
        "GPS:GPSLongitudeRef": "W",
    }
    diff = diferenca(antes, depois)
    assert diff.esperadas == depois
    assert diff.inesperadas == {}
    assert diff.estruturais == {}


def test_diferenca_classifica_tags_de_andaime_em_estruturais_nao_inesperadas():
    antes: dict[str, str] = {}
    depois = {
        "GPS:GPSVersionID": "2 3 0 0",
        "IPTC:ApplicationRecordVersion": "4",
        "File:CurrentIPTCDigest": "abc123",
        "XMP-x:XMPToolkit": "Image::ExifTool 13.55",
    }
    diff = diferenca(antes, depois)
    assert diff.estruturais == depois
    assert diff.inesperadas == {}
    assert diff.esperadas == {}


def test_diferenca_ignora_tags_volateis():
    antes = {
        "File:FileSize": "100",
        "File:FileModifyDate": "2026:08:18 10:00:00",
        "System:FileSize": "100",
        "Composite:GPSPosition": "0 0",
    }
    depois = {
        "File:FileSize": "200",
        "File:FileModifyDate": "2026:08:18 11:00:00",
        "System:FileSize": "200",
        "Composite:GPSPosition": "-23.5 -46.6",
    }
    diff = diferenca(antes, depois)
    assert diff.inesperadas == {}
    assert diff.esperadas == {}
    assert diff.estruturais == {}


def test_diferenca_marca_mudanca_fora_de_escopo_como_inesperada():
    diff = diferenca({"EXIF:Make": "Canon"}, {"EXIF:Make": "Nikon"})
    assert diff.inesperadas == {"EXIF:Make": ("Canon", "Nikon")}
    assert diff.esperadas == {}
    assert diff.estruturais == {}


def test_diferenca_tag_de_localizacao_que_sumiu_vai_para_inesperadas():
    diff = diferenca({"GPS:GPSLatitude": "-23.55052"}, {})
    assert diff.inesperadas == {"GPS:GPSLatitude": ("-23.55052", None)}
    assert diff.esperadas == {}


def test_campo_gravado_exige_todas_as_tags_do_campo():
    diff_completo = diferenca(
        {}, {"IPTC:City": "São Paulo", "XMP-photoshop:City": "São Paulo"}
    )
    assert campo_gravado("cidade", diff_completo) is True

    diff_parcial = diferenca({}, {"IPTC:City": "São Paulo"})
    assert campo_gravado("cidade", diff_parcial) is False
