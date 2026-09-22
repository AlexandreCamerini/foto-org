"""Geração de sugestões em lote (`_TAMANHO_LOTE`) — travessia e resumo.

`_persistir_sugestao` limpava a sugestão pendente antiga mídia por mídia
(SELECT + 2 DELETE + flush, × cada uma); virou limpeza em bloco por lote
de 500 (`_limpar_sugestoes_antigas`), chamada uma vez por lote ANTES do
laço que gera as sugestões novas DESSE lote — medido ~4x mais rápido num
catálogo sintético de 8k (mesmo banco, antes/depois). Estes dois testes
provam o que o benchmark de tempo não prova: que o laço atravessa
CORRETAMENTE mais de um lote (nenhuma mídia sobra ou duplica na fronteira
dos 500), e que uma queda no meio da rodada não apaga a sugestão de quem
ainda nem foi alcançado — a garantia de resumo que motivou limpar por
lote em vez de tudo de uma vez no início da rodada inteira.
"""
import pytest
from datetime import datetime, timedelta

from sqlalchemy import func, select

from fotoorganizer.classification import SuggestionEngine
from fotoorganizer.classification.engine import _TAMANHO_LOTE
from fotoorganizer.database import create_session_factory
from fotoorganizer.geolocation import LocationResolver
from fotoorganizer.models import (
    ConfidenceLevel,
    MediaFile,
    Source,
    Suggestion,
    SuggestionStatus,
)


class _SemGeocoder:
    def resolve(self, lat, lon):
        return None


def _popular(factory, n: int, com_sugestao_antiga: bool = False) -> list[int]:
    base = datetime(2020, 1, 1, 10, 0)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        ids = []
        for i in range(n):
            m = MediaFile(
                source_id=fonte.id, caminho=f"/fotos/IMG_{i}.jpg",
                pasta="/fotos", nome=f"IMG_{i}.jpg", extensao="jpg",
                tamanho=100, data_capturada=base + timedelta(hours=i),
                mtime=base + timedelta(hours=i),
            )
            session.add(m)
            session.flush()
            ids.append(m.id)
            if com_sugestao_antiga:
                session.add(Suggestion(
                    media_id=m.id, destino_sugerido="Não classificadas/velha",
                    template="{ano}", nivel=ConfidenceLevel.BAIXA,
                    status=SuggestionStatus.PENDENTE, versao_logica="antiga",
                ))
        session.commit()
        return ids


def test_gera_sugestao_pra_todo_mundo_atravessando_mais_de_um_lote(migrated_engine):
    """N > 2×`_TAMANHO_LOTE`: prova que a fronteira do lote não perde nem
    duplica mídia (off-by-one no range/slice do laço novo)."""
    factory = create_session_factory(migrated_engine)
    n = _TAMANHO_LOTE * 2 + 137
    ids = _popular(factory, n)

    engine = SuggestionEngine(factory, LocationResolver(_SemGeocoder()))
    resultado = engine.gerar()
    assert resultado["sugestoes"] == n

    with factory() as session:
        total = session.scalar(select(func.count(Suggestion.id)))
        assert total == n
        media_com_sugestao = set(session.scalars(select(Suggestion.media_id)))
        assert media_com_sugestao == set(ids)


def test_queda_no_meio_da_rodada_nao_apaga_sugestao_de_quem_nao_foi_alcancado(
    migrated_engine,
):
    """Simula uma exceção logo no início do 2º lote (antes de qualquer
    limpeza dele rodar): a sugestão antiga da mídia do 2º lote tem que
    continuar exatamente a MESMA linha (mesmo id) — nunca "sem nenhuma".
    A do 1º lote, já commitado, vira nova (versao_logica atual)."""
    factory = create_session_factory(migrated_engine)
    n = _TAMANHO_LOTE + 10
    ids = _popular(factory, n, com_sugestao_antiga=True)

    with factory() as session:
        id_antiga_2o_lote = session.scalar(
            select(Suggestion.id).where(
                Suggestion.media_id == ids[_TAMANHO_LOTE + 1]
            )
        )
    assert id_antiga_2o_lote is not None

    engine = SuggestionEngine(factory, LocationResolver(_SemGeocoder()))

    chamadas = {"n": 0}
    original = engine._limpar_sugestoes_antigas

    def explode_no_segundo_lote(session, media_ids):
        chamadas["n"] += 1
        if chamadas["n"] == 2:
            raise RuntimeError("queda simulada no meio da rodada")
        return original(session, media_ids)

    engine._limpar_sugestoes_antigas = explode_no_segundo_lote

    with pytest.raises(RuntimeError, match="queda simulada"):
        engine.gerar()

    with factory() as session:
        primeira = session.scalar(
            select(Suggestion).where(Suggestion.media_id == ids[0])
        )
        assert primeira is not None
        assert primeira.versao_logica != "antiga"

        segunda = session.scalar(
            select(Suggestion).where(
                Suggestion.media_id == ids[_TAMANHO_LOTE + 1]
            )
        )
        assert segunda is not None
        assert segunda.id == id_antiga_2o_lote
        assert segunda.versao_logica == "antiga"
