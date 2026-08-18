"""Testes das primitivas de escrita EXIF de localização (fase 6, plano 02).

O que exige o binário `exiftool` é marcado com `tem_exiftool` e pulado sem
ele — mesmo contrato de `tests/test_exiftool_extractor.py`. O resto (diff de
tags, validação de campos, detecção de pasta sincronizada, allowlist de
formatos) é puro Python, sem subprocesso, e roda sempre.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from fotoorganizer.exif_write.verificacao import DiffTags, campo_gravado, diferenca
from fotoorganizer.exif_write.writer import ExifToolWriter, ValorInvalido, validar_campos
from fotoorganizer.metadata.exiftool import ExifToolExtractor
from fotoorganizer.security.hashing import sha256_full
from tests.fixtures import make_jpeg

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


# -- Task 2: writer.py — validação Python-side e escrita direta + sidecar ---


def test_validar_campos_recusa_valores_fora_de_faixa_ou_malformados():
    casos_invalidos = [
        {"gps": (999.0, 0.0)},
        {"gps": (0.0, 200.0)},
        {"gps": (float("nan"), 0.0)},
        {"gps": (0.0, float("inf"))},
        {"cidade": "  "},
        {"pais": "x" * 201},
        {"cidade": "São Paulo\nBrasil"},
    ]
    for campos in casos_invalidos:
        with pytest.raises(ValorInvalido):
            validar_campos(campos)


def test_validar_campos_aceita_valores_validos():
    validar_campos({
        "gps": (-23.55052, -46.633308),
        "cidade": "São Paulo",
        "pais": "Brasil",
    })  # não levanta


def test_validar_campos_nao_chama_subprocesso(monkeypatch):
    def _explode(*_args, **_kwargs):
        raise AssertionError("validar_campos não deveria chamar subprocess")

    monkeypatch.setattr("subprocess.run", _explode)
    with pytest.raises(ValorInvalido):
        validar_campos({"gps": (999.0, 0.0)})


@tem_exiftool
def test_escrever_grava_os_3_campos_sem_tocar_fora_de_localizacao(tmp_path):
    """Prova automatizada de EXIF-04: inesperadas vazio após escrever."""
    foto = make_jpeg(tmp_path / "sem_local.jpg", gps=None)
    from fotoorganizer.exif_write.verificacao import dump

    antes = dump(foto)
    writer = ExifToolWriter()
    campos = {"gps": (-23.55052, -46.633308), "cidade": "São Paulo", "pais": "Brasil"}
    resultado = writer.escrever(foto, campos)
    assert resultado.returncode == 0, resultado.stderr
    depois = dump(foto)

    diff = diferenca(antes, depois)
    assert diff.inesperadas == {}
    assert campo_gravado("gps", diff) is True
    assert campo_gravado("cidade", diff) is True
    assert campo_gravado("pais", diff) is True


@tem_exiftool
def test_escrever_deixa_backup_original_ao_lado(tmp_path):
    foto = make_jpeg(tmp_path / "com_backup.jpg", gps=None)
    writer = ExifToolWriter()
    resultado = writer.escrever(foto, {"cidade": "São Paulo"})
    assert resultado.returncode == 0, resultado.stderr
    backup = ExifToolWriter.caminho_backup(foto)
    assert backup.exists()


@tem_exiftool
def test_escrever_com_destino_xmp_cria_sidecar_autonomo_sem_iptc(tmp_path):
    foto = make_jpeg(tmp_path / "para_sidecar.jpg", gps=None)
    hash_antes = sha256_full(foto)
    sidecar = Path(str(foto) + ".xmp")

    from fotoorganizer.exif_write.verificacao import dump

    writer = ExifToolWriter()
    campos = {"gps": (-23.55052, -46.633308), "cidade": "São Paulo", "pais": "Brasil"}
    resultado = writer.escrever(foto, campos, destino=sidecar)
    assert resultado.returncode == 0, resultado.stderr
    assert sidecar.exists()

    dump_sidecar = dump(sidecar)
    assert "XMP-photoshop:City" in dump_sidecar
    assert "XMP-photoshop:Country" in dump_sidecar
    assert "XMP-exif:GPSLatitude" in dump_sidecar
    assert not any(chave.startswith("IPTC:") for chave in dump_sidecar)
    assert sha256_full(foto) == hash_antes


@tem_exiftool
def test_escrever_tag_gps_malformada_falha_sozinha(tmp_path):
    """Pitfall 2: o processo sai 0, mas só a tag malformada não entra."""
    foto = make_jpeg(tmp_path / "malformado.jpg", gps=None)
    from fotoorganizer.exif_write.verificacao import dump

    antes = dump(foto)
    binario = shutil.which("exiftool")
    resultado = subprocess.run(
        [
            binario,
            "-GPSLatitude=notanumber", "-GPSLatitudeRef=S",
            "-IPTC:City=São Paulo", "-XMP:City=São Paulo",
            "-charset", "filename=utf8", str(foto),
        ],
        capture_output=True, text=True, check=False,
    )
    assert resultado.returncode == 0
    depois = dump(foto)
    diff = diferenca(antes, depois)
    assert campo_gravado("gps", diff) is False
    assert campo_gravado("cidade", diff) is True
