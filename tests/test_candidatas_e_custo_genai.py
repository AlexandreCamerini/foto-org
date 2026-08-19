"""Pré-filtro D-01 de pastas candidatas e estimativa de custo (D-04/D-05,
decisão híbrida D-079) da classificação de pasta por GenAI.
"""

from datetime import datetime

import pytest

from fotoorganizer.classification.candidatas_de_pasta import (
    CandidataDePasta,
    candidatas,
)
from fotoorganizer.classification.custo_genai import (
    CAMBIO_FONTE_PADRAO,
    PRECO_ENTRADA_USD_POR_MTOK,
    PRECO_SAIDA_USD_POR_MTOK,
    contar_exato,
    estimar,
)
from fotoorganizer.database import create_session_factory
from fotoorganizer.models import ConfidenceLevel, Evidence, MediaFile, MediaRole, Source


# -- fixtures locais, no molde de tests/test_inventario.py -----------------

def _fonte(session, apelido="scan") -> Source:
    source = Source(caminho="/Users/eu/Pictures", apelido=apelido)
    session.add(source)
    session.flush()
    return source


def _arquivo(session, source, pasta, nome, organizavel=True, **kw) -> MediaFile:
    extras = {}
    if not organizavel:
        extras["papel"] = MediaRole.SINAL
    extras.update(kw)
    media = MediaFile(
        source_id=source.id, caminho=f"{pasta}/{nome}", pasta=pasta,
        nome=nome, extensao=nome.rsplit(".", 1)[-1].lower(), tamanho=1,
        **extras,
    )
    session.add(media)
    session.flush()
    return media


def _evidencia(session, media_id, campo, valor="x") -> None:
    session.add(Evidence(
        media_id=media_id, campo=campo, origem="teste", valor=valor,
        nivel=ConfidenceLevel.ALTA, score=0.9,
        justificativa="fixture de teste", versao_logica="0.1.0",
    ))


# -- candidatas() — pré-filtro D-01 -----------------------------------------

def test_candidata_pasta_sem_categoria(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = _fonte(session)
        m = _arquivo(session, fonte, "/Users/eu/Pictures/Praia", "a.jpg")
        _evidencia(session, m.id, "cidade")
        session.commit()

        resultado = candidatas(session, set())

    assert resultado == [CandidataDePasta(
        pasta="/Users/eu/Pictures/Praia", n_fotos=1,
        campos_ausentes=("categoria",), periodo=None,
    )]


def test_candidata_pasta_sem_cidade_pais(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = _fonte(session)
        m = _arquivo(session, fonte, "/Users/eu/Pictures/Sem categoria", "a.jpg")
        _evidencia(session, m.id, "categoria", "Viagens")
        session.commit()

        resultado = candidatas(session, set())

    assert len(resultado) == 1
    assert resultado[0].campos_ausentes == ("cidade_pais",)


def test_candidata_pasta_com_os_dois_campos_vazios_na_ordem(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = _fonte(session)
        _arquivo(session, fonte, "/Users/eu/Pictures/Nova", "a.jpg")
        session.commit()

        resultado = candidatas(session, set())

    assert len(resultado) == 1
    assert resultado[0].campos_ausentes == ("categoria", "cidade_pais")


def test_pasta_completa_nao_e_candidata(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = _fonte(session)
        m = _arquivo(session, fonte, "/Users/eu/Pictures/Completa", "a.jpg")
        _evidencia(session, m.id, "categoria", "Família")
        _evidencia(session, m.id, "pais", "Brasil")
        session.commit()

        resultado = candidatas(session, set())

    assert resultado == []


def test_pasta_ja_classificada_nao_e_candidata(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = _fonte(session)
        _arquivo(session, fonte, "/Users/eu/Pictures/Ja Feita", "a.jpg")
        session.commit()

        resultado = candidatas(session, {"/Users/eu/Pictures/Ja Feita"})

    assert resultado == []


def test_candidata_ignora_evidencia_de_midia_nao_organizavel(migrated_engine):
    """Uma miniatura (papel=SINAL) com `categoria` inferida não pode
    "completar" uma pasta cuja foto real (organizável) continua vazia."""
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = _fonte(session)
        real = _arquivo(session, fonte, "/Users/eu/Pictures/Mista", "a.jpg")
        miniatura = _arquivo(
            session, fonte, "/Users/eu/Pictures/Mista", "thumb.jpg",
            organizavel=False,
        )
        _evidencia(session, miniatura.id, "categoria", "Viagens")
        session.commit()

        resultado = candidatas(session, set())

    assert len(resultado) == 1
    assert resultado[0].n_fotos == 1
    assert "categoria" in resultado[0].campos_ausentes


def test_pasta_so_com_nao_acervo_nao_e_candidata(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = _fonte(session)
        _arquivo(
            session, fonte, "/Users/eu/Pictures/So Miniatura", "thumb.jpg",
            organizavel=False,
        )
        session.commit()

        resultado = candidatas(session, set())

    assert resultado == []


def test_candidata_conta_apenas_midia_organizavel_em_n_fotos(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = _fonte(session)
        _arquivo(session, fonte, "/Users/eu/Pictures/Duas", "a.jpg")
        _arquivo(session, fonte, "/Users/eu/Pictures/Duas", "b.jpg")
        _arquivo(
            session, fonte, "/Users/eu/Pictures/Duas", "thumb.jpg",
            organizavel=False,
        )
        session.commit()

        resultado = candidatas(session, set())

    assert len(resultado) == 1
    assert resultado[0].n_fotos == 2


def test_candidata_periodo_none_sem_data(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = _fonte(session)
        _arquivo(session, fonte, "/Users/eu/Pictures/Sem Data", "a.jpg")
        session.commit()

        resultado = candidatas(session, set())

    assert resultado[0].periodo is None


def test_candidata_periodo_do_menor_ao_maior(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = _fonte(session)
        _arquivo(
            session, fonte, "/Users/eu/Pictures/Viagem", "a.jpg",
            data_capturada=datetime(2024, 3, 19),
        )
        _arquivo(
            session, fonte, "/Users/eu/Pictures/Viagem", "b.jpg",
            data_capturada=datetime(2024, 3, 12),
        )
        session.commit()

        resultado = candidatas(session, set())

    assert resultado[0].periodo == "2024-03-12 a 2024-03-19"


def test_candidatas_ordenadas_por_pasta_deterministico(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = _fonte(session)
        _arquivo(session, fonte, "/Users/eu/Pictures/Zebra", "a.jpg")
        _arquivo(session, fonte, "/Users/eu/Pictures/Alfa", "b.jpg")
        _arquivo(session, fonte, "/Users/eu/Pictures/Meio", "c.jpg")
        session.commit()

        resultado = candidatas(session, set())

    assert [c.pasta for c in resultado] == [
        "/Users/eu/Pictures/Alfa",
        "/Users/eu/Pictures/Meio",
        "/Users/eu/Pictures/Zebra",
    ]


# -- estimar() / contar_exato() — D-04/D-05, decisão híbrida D-079 ---------

class _ContagemFalsa:
    def __init__(self, input_tokens: int) -> None:
        self.input_tokens = input_tokens


class _ClienteDeContagem:
    def __init__(self, resultado) -> None:
        self._resultado = resultado
        self.chamado_com: dict | None = None

    @property
    def messages(self):
        return self

    def count_tokens(self, **kw):
        self.chamado_com = kw
        if isinstance(self._resultado, Exception):
            raise self._resultado
        return self._resultado


def _corpo(max_tokens=16000, pastas=2):
    return {
        "model": "claude-sonnet-5",
        "max_tokens": max_tokens,
        "thinking": {"type": "disabled"},
        "system": "Você classifica PASTAS de um acervo de fotos pessoal.",
        "messages": [{
            "role": "user",
            "content": '{"pastas": [' + ", ".join(
                f'{{"pasta": "p{i}"}}' for i in range(pastas)
            ) + "]}",
        }],
    }


def test_custo_calcula_entrada_e_saida_pelas_constantes_de_preco():
    custo = estimar(_corpo(), cambio_usd_brl=5.0)

    assert custo.custo_entrada_usd == pytest.approx(
        custo.tokens_entrada / 1_000_000 * PRECO_ENTRADA_USD_POR_MTOK
    )
    assert custo.teto_custo_saida_usd == pytest.approx(
        custo.teto_tokens_saida / 1_000_000 * PRECO_SAIDA_USD_POR_MTOK
    )


def test_teto_tokens_saida_vem_do_max_tokens_do_corpo():
    custo = estimar(_corpo(max_tokens=16000), cambio_usd_brl=5.0)
    assert custo.teto_tokens_saida == 16000


def test_custo_total_soma_entrada_e_saida_e_converte_para_brl():
    custo = estimar(_corpo(), cambio_usd_brl=5.0)

    assert custo.teto_custo_total_usd == pytest.approx(
        custo.custo_entrada_usd + custo.teto_custo_saida_usd
    )
    assert custo.teto_custo_total_brl == pytest.approx(
        custo.teto_custo_total_usd * 5.0
    )


def test_entrada_exata_false_na_estimativa_local():
    custo = estimar(_corpo(), cambio_usd_brl=5.0)
    assert custo.entrada_exata is False


def test_cambio_fonte_nunca_vazio():
    custo = estimar(_corpo(), cambio_usd_brl=5.0)
    assert custo.cambio_fonte
    assert custo.cambio_fonte == CAMBIO_FONTE_PADRAO


def test_estimar_sessao_vazia_devolve_custo_zero():
    custo = estimar({}, cambio_usd_brl=5.0)

    assert custo.tokens_entrada == 0
    assert custo.custo_entrada_usd == 0.0
    assert custo.teto_tokens_saida == 0
    assert custo.teto_custo_saida_usd == 0.0
    assert custo.teto_custo_total_usd == 0.0
    assert custo.teto_custo_total_brl == 0.0
    assert custo.entrada_exata is False


def test_contar_exato_devolve_input_tokens_do_client():
    cliente = _ClienteDeContagem(_ContagemFalsa(input_tokens=3420))
    corpo = _corpo()

    resultado = contar_exato(cliente, corpo)

    assert resultado == 3420
    assert "max_tokens" not in cliente.chamado_com


def test_contar_exato_cliente_que_levanta_devolve_zero():
    cliente = _ClienteDeContagem(RuntimeError("indisponível"))
    resultado = contar_exato(cliente, _corpo())
    assert resultado == 0
