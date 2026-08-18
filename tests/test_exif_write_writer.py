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

from fotoorganizer.exif_write.formatos import caminho_sidecar, motivo, suportado
from fotoorganizer.exif_write.sync_detect import pasta_sincronizada
from fotoorganizer.exif_write.verificacao import (
    DiffTags,
    avisos,
    campo_gravado,
    diferenca,
    reclassificar_deslocamentos_de_offset,
)
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


# -- Deviação (plano 06-04): avisos() colapsava duplicatas via -j e contava
# o resumo "Validate" como se fosse ele próprio um aviso novo -------------


def test_avisos_nao_conta_melhora_do_resumo_validate_como_aviso_novo(monkeypatch):
    """Achado da medição real (plano 06-04): um JPEG com "3 Warnings" antes
    da escrita virou "Validate: OK" depois (exiftool renormalizou o IFD),
    o que um diff textual ingênuo contaria como aviso NOVO — é melhora, não
    regressão. `Validate` não é warning nem error; fica fora do conjunto.
    """
    saida_antes = (
        "Validate                        : 3 Warnings (all minor)\n"
        "Warning                         : [minor] Odd offset for ExifIFD tag\n"
    )
    saida_depois = "Validate                        : OK\n"

    respostas = iter([saida_antes, saida_depois])

    def _fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(
            args=_args, returncode=0, stdout=next(respostas), stderr=""
        )

    monkeypatch.setattr("subprocess.run", _fake_run)
    antes = avisos(Path("qualquer.jpg"))
    depois = avisos(Path("qualquer.jpg"))
    assert depois - antes == set()
    assert "Validate: OK" not in depois
    assert "Validate: 3 Warnings (all minor)" not in antes


def test_avisos_preserva_todos_os_warnings_duplicados(monkeypatch):
    """Achado da medição real: a saída `-j` do exiftool colapsa tags
    `Warning` repetidas em uma só (verificado contra um TIFF real com 6
    warnings, JSON devolvia 1) — texto plano lista cada ocorrência."""
    saida = (
        "Validate                        : 6 Warnings (3 minor)\n"
        "Warning                         : Non-standard format (undef) for IFD0\n"
        "Warning                         : [minor] IPTC TimeCreated too short\n"
        "Warning                         : Missing required TIFF ExifIFD tag\n"
        "Warning                         : [minor] ExifIFD tag not allowed in TIFF (a)\n"
        "Warning                         : [minor] ExifIFD tag not allowed in TIFF (b)\n"
        "Warning                         : Invalid value for IFD0 tag Compression\n"
    )

    def _fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(args=_args, returncode=0, stdout=saida, stderr="")

    monkeypatch.setattr("subprocess.run", _fake_run)
    resultado = avisos(Path("qualquer.tif"))
    assert len(resultado) == 6
    assert all(chave.startswith("Warning:") for chave in resultado)
    assert not any(chave.startswith("Validate") for chave in resultado)


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


# -- Deviação (correção de meio-de-fase, D-077): reclassificar_deslocamentos
# _de_offset() — allowlist byte a byte para deslocamento de offset/ponteiro,
# generalizando o achado de D-076 (miniatura embutida idêntica byte a byte
# depois do exiftool deslocar IFD1:ThumbnailOffset). -----------------------


@tem_exiftool
def test_reclassificar_offset_real_byte_identico_vira_esperada_condicional(tmp_path):
    """Caso real, produzido pelo mesmo caminho de código de produção: um
    JPEG sintético com miniatura embutida (injetada via exiftool, mesmo
    truque usado para reproduzir o achado de D-076 sem precisar de foto
    real do acervo) tem IFD1:ThumbnailOffset deslocado ao escrever
    GPS/cidade/país — o conteúdo apontado é byte a byte idêntico, e a tag
    deve sair de `inesperadas` e entrar em `esperadas_condicionais`, sem
    reprovar a verificação.
    """
    foto = make_jpeg(tmp_path / "com_thumb.jpg", gps=None)
    binario = shutil.which("exiftool")
    subprocess.run(
        [binario, "-overwrite_original", f"-ThumbnailImage<={foto}", str(foto)],
        capture_output=True, text=True, check=True,
    )

    from fotoorganizer.exif_write.verificacao import dump

    antes = dump(foto)
    assert "IFD1:ThumbnailOffset" in antes  # pré-condição: miniatura presente

    writer = ExifToolWriter()
    resultado = writer.escrever(
        foto, {"gps": (-23.55052, -46.633308), "cidade": "São Paulo", "pais": "Brasil"}
    )
    assert resultado.returncode == 0, resultado.stderr
    depois = dump(foto)

    diff = diferenca(antes, depois)
    assert "IFD1:ThumbnailOffset" in diff.inesperadas  # reproduz o achado de D-076

    backup = ExifToolWriter.caminho_backup(foto)
    assert backup.exists()

    diff_reclassificado = reclassificar_deslocamentos_de_offset(
        diff, antes, depois, backup, foto
    )
    assert "IFD1:ThumbnailOffset" not in diff_reclassificado.inesperadas
    assert "IFD1:ThumbnailOffset" in diff_reclassificado.esperadas_condicionais
    # As demais categorias não regridem: cidade/gps/país continuam gravados.
    assert campo_gravado("gps", diff_reclassificado) is True
    assert campo_gravado("cidade", diff_reclassificado) is True
    assert campo_gravado("pais", diff_reclassificado) is True


def test_reclassificar_conteudo_corrompido_continua_inesperada_e_reprova(tmp_path):
    """Prova de segurança central desta mudança (a que não pode falhar):
    dois arquivos onde o par offset+tamanho descreve um deslocamento
    normal (mesmo padrão de ThumbnailOffset/ThumbnailLength), mas o
    conteúdo apontado no arquivo "depois" foi alterado — simula corrupção
    real, não relocação. A tag TEM que continuar em `inesperadas` e a
    verificação (checada via `diff.inesperadas`, o sinal que
    `scripts/testar_escrita_exif.py` usa para reprovar) TEM que continuar
    falhando. Se este teste passar com a tag promovida, a allowlist deixou
    de ser conservadora — não é aceitável relaxar por qualquer motivo.
    """
    conteudo_original = b"miniatura-fake-conteudo-binario-fixo-32b"
    arquivo_antes = tmp_path / "antes.bin"
    arquivo_depois = tmp_path / "depois.bin"
    tamanho = len(conteudo_original)

    arquivo_antes.write_bytes(b"\x00" * 10 + conteudo_original)
    conteudo_corrompido = b"X" * tamanho  # deliberadamente diferente
    arquivo_depois.write_bytes(b"\x00" * 20 + conteudo_corrompido)

    antes = {
        "IFD1:ThumbnailOffset": "10",
        "IFD1:ThumbnailLength": str(tamanho),
    }
    depois = {
        "IFD1:ThumbnailOffset": "20",
        "IFD1:ThumbnailLength": str(tamanho),
    }
    diff = diferenca(antes, depois)
    assert diff.inesperadas == {"IFD1:ThumbnailOffset": ("10", "20")}

    diff_reclassificado = reclassificar_deslocamentos_de_offset(
        diff, antes, depois, arquivo_antes, arquivo_depois
    )
    assert "IFD1:ThumbnailOffset" in diff_reclassificado.inesperadas
    assert diff_reclassificado.esperadas_condicionais == {}


def _diff_e_arquivos_offset_valido(tmp_path, tag_offset, tag_tamanho, grupo="IFD1"):
    """Monta um cenário de relocação pura válida — mesmo conteúdo, endereço
    diferente — reutilizado pelos testes de borda abaixo."""
    conteudo = b"conteudo-binario-de-teste-identico-nos-dois-lados"
    tamanho = len(conteudo)
    arquivo_antes = tmp_path / "antes.bin"
    arquivo_depois = tmp_path / "depois.bin"
    arquivo_antes.write_bytes(b"\x00" * 5 + conteudo)
    arquivo_depois.write_bytes(b"\x00" * 15 + conteudo)

    antes = {f"{grupo}:{tag_offset}": "5", f"{grupo}:{tag_tamanho}": str(tamanho)}
    depois = {f"{grupo}:{tag_offset}": "15", f"{grupo}:{tag_tamanho}": str(tamanho)}
    return antes, depois, arquivo_antes, arquivo_depois


def test_reclassificar_promove_todas_as_seis_tags_conhecidas(tmp_path):
    """As seis tags do mapa fechado (achado real de D-076, os 3 formatos
    com amostra) promovem quando o conteúdo bate — cobertura de todo o
    mapa, não só do caso ThumbnailOffset já coberto no teste com exiftool."""
    casos = [
        ("ThumbnailOffset", "ThumbnailLength", "IFD1"),
        ("PreviewImageStart", "PreviewImageLength", "IFD0"),
        ("StripOffsets", "StripByteCounts", "IFD2"),
        ("TileOffsets", "TileByteCounts", "SubIFD4"),
        ("JpgFromRawStart", "JpgFromRawLength", "SubIFD2"),
        ("MPImageStart", "MPImageLength", "MPImage2"),
    ]
    for tag_offset, tag_tamanho, grupo in casos:
        sub = tmp_path / f"{grupo}_{tag_offset}"
        sub.mkdir()
        antes, depois, arquivo_antes, arquivo_depois = _diff_e_arquivos_offset_valido(
            sub, tag_offset, tag_tamanho, grupo
        )
        diff = diferenca(antes, depois)
        chave = f"{grupo}:{tag_offset}"
        assert chave in diff.inesperadas, f"pré-condição falhou para {chave}"

        resultado = reclassificar_deslocamentos_de_offset(
            diff, antes, depois, arquivo_antes, arquivo_depois
        )
        assert chave not in resultado.inesperadas, f"{chave} devia ter sido promovida"
        assert chave in resultado.esperadas_condicionais, f"{chave} ausente do resultado"


def test_reclassificar_nao_promove_tag_fora_do_mapa_de_sufixos(tmp_path):
    """Tag mudou de endereço mas o nome não está no mapa fechado (ex.:
    uma tag hipotética `EXIF:AlgumOffset` não catalogada) — fica
    inesperada, sem tentativa de adivinhar o par de tamanho."""
    diff = diferenca({"EXIF:AlgumOffset": "10"}, {"EXIF:AlgumOffset": "20"})
    resultado = reclassificar_deslocamentos_de_offset(
        diff, {"EXIF:AlgumOffset": "10"}, {"EXIF:AlgumOffset": "20"},
        tmp_path / "a", tmp_path / "b",
    )
    assert "EXIF:AlgumOffset" in resultado.inesperadas
    assert resultado.esperadas_condicionais == {}


def test_reclassificar_nao_promove_quando_falta_tag_de_tamanho_irma(tmp_path):
    """Sem a tag de tamanho irmã no dump (nem antes, nem depois), não dá
    para delimitar a leitura — fica inesperada, nunca adivinha um
    comprimento."""
    antes = {"IFD1:ThumbnailOffset": "10"}
    depois = {"IFD1:ThumbnailOffset": "20"}
    diff = diferenca(antes, depois)
    resultado = reclassificar_deslocamentos_de_offset(
        diff, antes, depois, tmp_path / "a", tmp_path / "b"
    )
    assert "IFD1:ThumbnailOffset" in resultado.inesperadas
    assert resultado.esperadas_condicionais == {}


def test_reclassificar_nao_promove_quando_tamanho_muda_junto(tmp_path):
    """Tamanho apontado mudou também (não é só relocação de endereço) —
    fica inesperada mesmo que o conteúdo no novo intervalo por acaso
    exista e seja lido com sucesso."""
    conteudo = b"x" * 20
    arquivo_antes = tmp_path / "antes.bin"
    arquivo_depois = tmp_path / "depois.bin"
    arquivo_antes.write_bytes(b"\x00" * 5 + conteudo)
    arquivo_depois.write_bytes(b"\x00" * 15 + conteudo)

    antes = {"IFD1:ThumbnailOffset": "5", "IFD1:ThumbnailLength": "20"}
    depois = {"IFD1:ThumbnailOffset": "15", "IFD1:ThumbnailLength": "21"}
    diff = diferenca(antes, depois)
    resultado = reclassificar_deslocamentos_de_offset(
        diff, antes, depois, arquivo_antes, arquivo_depois
    )
    assert "IFD1:ThumbnailOffset" in resultado.inesperadas
    assert resultado.esperadas_condicionais == {}


def test_reclassificar_nao_promove_valor_nao_numerico_binario(tmp_path):
    """Achado real contra o acervo (DNG, `SubIFD:TileOffsets` com muitos
    tiles): o dump do exiftool devolve `"(Binary data N bytes, use -b
    option to extract)"` em vez de lista de inteiros, quando há tiles
    demais. Fica inesperada — nunca extrai um número de dentro do texto
    (esse "N" é o tamanho da descrição, não um offset real)."""
    antes = {
        "SubIFD:TileOffsets": "(Binary data 2479 bytes, use -b option to extract)",
        "SubIFD:TileByteCounts": "(Binary data 1763 bytes, use -b option to extract)",
    }
    depois = {
        "SubIFD:TileOffsets": "(Binary data 2479 bytes, use -b option to extract, moved)",
        "SubIFD:TileByteCounts": "(Binary data 1763 bytes, use -b option to extract)",
    }
    diff = diferenca(antes, depois)
    assert "SubIFD:TileOffsets" in diff.inesperadas
    resultado = reclassificar_deslocamentos_de_offset(
        diff, antes, depois, tmp_path / "a", tmp_path / "b"
    )
    assert "SubIFD:TileOffsets" in resultado.inesperadas
    assert resultado.esperadas_condicionais == {}


def test_reclassificar_nao_promove_tag_que_sumiu(tmp_path):
    """Tag de offset que sumiu (estava em antes, ausente em depois) não é
    relocação — `diferenca()` já marca como `(valor, None)`; a
    reclassificação tem que preservar essa marcação, nunca promovê-la."""
    diff = diferenca({"IFD1:ThumbnailOffset": "10"}, {})
    resultado = reclassificar_deslocamentos_de_offset(
        diff, {"IFD1:ThumbnailOffset": "10"}, {}, tmp_path / "a", tmp_path / "b"
    )
    assert resultado.inesperadas == {"IFD1:ThumbnailOffset": ("10", None)}
    assert resultado.esperadas_condicionais == {}


def test_reclassificar_leitura_alem_do_fim_do_arquivo_fica_inesperada(tmp_path):
    """Tamanho declarado excede o que o arquivo realmente tem — leitura
    curta, `_ler_intervalo` devolve `None`, fail-safe mantém inesperada."""
    arquivo_antes = tmp_path / "antes.bin"
    arquivo_depois = tmp_path / "depois.bin"
    arquivo_antes.write_bytes(b"\x00" * 5 + b"conteudo-curto")
    arquivo_depois.write_bytes(b"\x00" * 5)  # arquivo "depois" bem menor

    antes = {"IFD1:ThumbnailOffset": "5", "IFD1:ThumbnailLength": "500"}
    depois = {"IFD1:ThumbnailOffset": "5", "IFD1:ThumbnailLength": "500"}
    diff = diferenca(antes, depois)
    # Mesmo offset não muda o valor da tag ("5"=="5") — força a mudança
    # artificialmente para exercitar o caminho de leitura.
    diff = DiffTags(
        esperadas={}, estruturais={},
        inesperadas={"IFD1:ThumbnailOffset": ("5", "5")},
    )
    resultado = reclassificar_deslocamentos_de_offset(
        diff, antes, depois, arquivo_antes, arquivo_depois
    )
    assert "IFD1:ThumbnailOffset" in resultado.inesperadas
    assert resultado.esperadas_condicionais == {}


# -- Task 3: sync_detect.py e formatos.py ------------------------------------


def test_pasta_sincronizada_detecta_icloud_drive():
    caminho = Path("~/Library/Mobile Documents/com~apple~CloudDocs/f.jpg").expanduser()
    assert pasta_sincronizada(caminho) == "iCloud Drive"


def test_pasta_sincronizada_detecta_cloudstorage():
    caminho = Path("~/Library/CloudStorage/OneDrive-Pessoal/f.jpg").expanduser()
    assert pasta_sincronizada(caminho) == "Nuvem (File Provider)"


def test_pasta_sincronizada_detecta_dropbox_legado():
    caminho = Path("~/Dropbox/f.jpg").expanduser()
    assert pasta_sincronizada(caminho) == "Dropbox (legado)"


def test_pasta_sincronizada_fora_de_qualquer_raiz_devolve_none(tmp_path):
    assert pasta_sincronizada(tmp_path / "f.jpg") is None


def test_pasta_sincronizada_resolve_symlink_antes_de_comparar(tmp_path):
    raiz_simulada = tmp_path / "raiz_sync"
    raiz_simulada.mkdir()
    alvo_real = raiz_simulada / "f.jpg"
    alvo_real.write_bytes(b"")

    link_dir = tmp_path / "Desktop"
    link_dir.symlink_to(raiz_simulada)

    resultado = pasta_sincronizada(
        link_dir / "f.jpg", raizes={"Sync Simulado": raiz_simulada}
    )
    assert resultado == "Sync Simulado"


def test_pasta_sincronizada_nunca_propaga_oserror(monkeypatch, tmp_path):
    def _explode(self, *_args, **_kwargs):
        raise OSError("símile de falha de resolução")

    monkeypatch.setattr(Path, "resolve", _explode)
    assert pasta_sincronizada(tmp_path / "f.jpg") is None


def test_suportado_case_insensitive_e_recusa_cr3():
    """Remedição (correção de meio-de-fase, D-077, 2026-08-18): `.jpg` e
    `.cr2` passam a aprovar sob a allowlist byte a byte de
    `reclassificar_deslocamentos_de_offset` (20/20 e 12/12 amostras); `.dng`
    continua reprovado (tiles demais para parsear o offset como inteiro,
    fail-safe). Este teste cobre case-insensitividade (mesmo resultado
    maiúsculo ou minúsculo) e a recusa de CR3 (D-09, sem amostra testável
    no acervo) e DNG (D-077, motivo de parsing, não de conteúdo)."""
    assert suportado(".jpg") is True
    assert suportado(".JPG") is suportado(".jpg")
    assert suportado(".cr2") is True
    assert suportado(".dng") is False
    assert suportado(".cr3") is False


def test_motivo_cr3_cita_sem_teste_de_escrita():
    texto = motivo(".cr3")
    assert texto is not None
    assert "sem teste de escrita neste acervo" in texto
    assert "CR3" in texto


def test_motivo_extensao_desconhecida_nunca_e_none():
    texto = motivo(".xyz")
    assert texto is not None
    assert texto != ""


def test_caminho_sidecar_convencao_foto_ext_xmp():
    assert caminho_sidecar(Path("/a/foto.CR3")) == Path("/a/foto.CR3.xmp")
