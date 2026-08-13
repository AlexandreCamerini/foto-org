from __future__ import annotations

from pathlib import PurePosixPath

import pytest
from lib import (
    EXTENSOES_SIDECAR,
    AssinaturaConhecida,
    CasoDeteccao,
    classificar,
    precisa_reenfileirar,
    resolver_sidecar,
)

# --- extensões sidecar -----------------------------------------------------


def test_extensoes_sidecar_e_so_xmp():
    assert EXTENSOES_SIDECAR == {".xmp"}


# --- resolver_sidecar: convenção Adobe (foto.jpg.xmp) -----------------------


def test_resolver_convencao_adobe_acha_a_midia():
    xmp = PurePosixPath("/fotos/2019/foto.jpg.xmp")
    conhecidos = frozenset({PurePosixPath("/fotos/2019/foto.jpg")})
    r = resolver_sidecar(xmp, conhecidos)
    assert r.midia == PurePosixPath("/fotos/2019/foto.jpg")
    assert r.ambiguo is False


def test_resolver_convencao_adobe_extensao_raw():
    xmp = PurePosixPath("/fotos/foto.cr3.xmp")
    conhecidos = frozenset({PurePosixPath("/fotos/foto.cr3")})
    r = resolver_sidecar(xmp, conhecidos)
    assert r.midia == PurePosixPath("/fotos/foto.cr3")


def test_resolver_convencao_adobe_case_insensitive_na_extensao():
    xmp = PurePosixPath("/fotos/foto.JPG.xmp")
    conhecidos = frozenset({PurePosixPath("/fotos/foto.jpg")})
    r = resolver_sidecar(xmp, conhecidos)
    assert r.midia == PurePosixPath("/fotos/foto.jpg")


# --- resolver_sidecar: convenção darktable/Lightroom (foto.xmp) ------------


def test_resolver_convencao_darktable_acha_a_midia():
    xmp = PurePosixPath("/fotos/foto.xmp")
    conhecidos = frozenset({PurePosixPath("/fotos/foto.nef")})
    r = resolver_sidecar(xmp, conhecidos)
    assert r.midia == PurePosixPath("/fotos/foto.nef")
    assert r.ambiguo is False


def test_resolver_convencao_darktable_ignora_pasta_diferente():
    xmp = PurePosixPath("/fotos/2019/foto.xmp")
    # mesmo nome, pasta diferente — não é o mesmo disparo, não deve casar.
    conhecidos = frozenset({PurePosixPath("/fotos/2020/foto.nef")})
    r = resolver_sidecar(xmp, conhecidos)
    assert r.midia is None
    assert r.ambiguo is False


# --- resolver_sidecar: ambiguidade, a armadilha citada no prompt de origem -


def test_resolver_ambiguo_quando_jpg_e_raw_coexistem():
    # "foto.xmp casando com o foto.jpg errado numa pasta com foto.jpg e
    # foto.cr3" — o resolvedor não adivinha, marca ambíguo.
    xmp = PurePosixPath("/fotos/foto.xmp")
    conhecidos = frozenset({
        PurePosixPath("/fotos/foto.jpg"),
        PurePosixPath("/fotos/foto.cr3"),
    })
    r = resolver_sidecar(xmp, conhecidos)
    assert r.midia is None
    assert r.ambiguo is True


def test_resolver_sem_candidato_nenhum_nao_e_ambiguo():
    xmp = PurePosixPath("/fotos/orfao.xmp")
    r = resolver_sidecar(xmp, frozenset())
    assert r.midia is None
    assert r.ambiguo is False


def test_resolver_convencao_adobe_nao_conta_como_ambiguidade_com_outro_stem():
    # foto.jpg.xmp -> candidato único "foto.jpg"; a presença de "foto.cr3"
    # (stem "foto", diferente de "foto.jpg") não deveria interferir.
    xmp = PurePosixPath("/fotos/foto.jpg.xmp")
    conhecidos = frozenset({
        PurePosixPath("/fotos/foto.jpg"),
        PurePosixPath("/fotos/foto.cr3"),
    })
    r = resolver_sidecar(xmp, conhecidos)
    assert r.midia == PurePosixPath("/fotos/foto.jpg")
    assert r.ambiguo is False


def test_resolver_levanta_erro_se_nao_for_xmp():
    with pytest.raises(ValueError):
        resolver_sidecar(PurePosixPath("/fotos/foto.jpg"), frozenset())


# --- classificar: os cinco casos --------------------------------------------


def test_classificar_par_nunca_visto_e_sidecar_novo():
    caso = classificar(100.0, 50.0, conhecida=None)
    assert caso == CasoDeteccao.SIDECAR_NOVO


def test_classificar_nada_mudou():
    conhecida = AssinaturaConhecida(mtime_sidecar=100.0, mtime_midia=50.0)
    caso = classificar(100.0, 50.0, conhecida)
    assert caso == CasoDeteccao.SEM_MUDANCA


def test_classificar_so_sidecar_mudou_e_o_caso_que_hoje_e_invisivel():
    conhecida = AssinaturaConhecida(mtime_sidecar=100.0, mtime_midia=50.0)
    caso = classificar(200.0, 50.0, conhecida)
    assert caso == CasoDeteccao.SO_SIDECAR_MUDOU


def test_classificar_so_midia_mudou():
    conhecida = AssinaturaConhecida(mtime_sidecar=100.0, mtime_midia=50.0)
    caso = classificar(100.0, 999.0, conhecida)
    assert caso == CasoDeteccao.MIDIA_MUDOU


def test_classificar_ambos_mudaram():
    conhecida = AssinaturaConhecida(mtime_sidecar=100.0, mtime_midia=50.0)
    caso = classificar(200.0, 999.0, conhecida)
    assert caso == CasoDeteccao.AMBOS_MUDARAM


def test_classificar_mtime_midia_desconhecido_nao_derruba():
    # mídia sem mtime conhecido na assinatura anterior (referência sem
    # arquivo local, por exemplo) não deve ser tratada como "mudou".
    conhecida = AssinaturaConhecida(mtime_sidecar=100.0, mtime_midia=None)
    caso = classificar(200.0, 50.0, conhecida)
    assert caso == CasoDeteccao.SO_SIDECAR_MUDOU


# --- precisa_reenfileirar ---------------------------------------------------


@pytest.mark.parametrize(
    "caso,esperado",
    [
        (CasoDeteccao.SEM_MUDANCA, False),
        (CasoDeteccao.SIDECAR_NOVO, True),
        (CasoDeteccao.SO_SIDECAR_MUDOU, True),
        (CasoDeteccao.AMBOS_MUDARAM, True),
        # MIDIA_MUDOU sozinho já é coberto pelo scan incremental normal —
        # reenfileirar de novo aqui duplicaria trabalho, não cobertura.
        (CasoDeteccao.MIDIA_MUDOU, False),
    ],
)
def test_precisa_reenfileirar(caso, esperado):
    assert precisa_reenfileirar(caso) is esperado


# --- ponta a ponta: o cenário do prompt de origem ---------------------------


def test_cenario_estrela_nova_do_lightroom_dispara_reenfileiramento():
    """Simula: mídia já indexada, sidecar existia e ganhou uma estrela nova
    no Lightroom (mtime do .xmp mudou), o arquivo de mídia em si não foi
    tocado. O scan incremental de hoje pularia a mídia por assinatura
    inalterada; este módulo é o que enxerga a mudança."""
    xmp = PurePosixPath("/fotos/2019/viagem/DSC001.xmp")
    conhecidos = frozenset({PurePosixPath("/fotos/2019/viagem/DSC001.nef")})
    resolucao = resolver_sidecar(xmp, conhecidos)
    assert resolucao.midia is not None

    conhecida = AssinaturaConhecida(mtime_sidecar=1_000.0, mtime_midia=500.0)
    caso = classificar(
        mtime_sidecar_atual=1_500.0, mtime_midia_atual=500.0, conhecida=conhecida
    )
    assert caso == CasoDeteccao.SO_SIDECAR_MUDOU
    assert precisa_reenfileirar(caso) is True
