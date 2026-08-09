"""Laço de reconciliação (fase 12, item B): confere se arquivos catalogados
ainda existem, sem depender de um re-scan manual. Barato (só `Path.exists()`
por linha) e auto-limitado por tempo/percentual, com checkpoint entre
chamadas."""

from sqlalchemy import select

from fotoorganizer.database import create_session_factory
from fotoorganizer.models import MediaFile, MediaRole, Source
from fotoorganizer.repositories.settings import SettingsRepository
from fotoorganizer.scanner.reconciliacao import (
    CHAVE_RECONCILIACAO_CHECKPOINT,
    reconciliar,
)
from tests.fixtures import make_jpeg


def _fonte(session, caminho, disponivel=True):
    source = Source(caminho=caminho, apelido=caminho, disponivel=disponivel)
    session.add(source)
    session.flush()
    return source


def _arquivo(session, source, caminho, **kw):
    media = MediaFile(
        source_id=source.id, caminho=str(caminho), pasta=str(caminho.parent)
        if hasattr(caminho, "parent") else "", nome=str(caminho).rsplit("/", 1)[-1],
        extensao="jpg", tamanho=1, **kw
    )
    session.add(media)
    session.flush()
    return media


def test_arquivo_removido_e_detectado_e_marcado_offline(migrated_engine, tmp_path):
    factory = create_session_factory(migrated_engine)
    alvo = make_jpeg(tmp_path / "some.jpg", seed=1)
    with factory() as session:
        f = _fonte(session, str(tmp_path))
        media_id = _arquivo(session, f, alvo).id
        session.commit()

    alvo.unlink()
    resultado = reconciliar(factory)

    assert resultado.verificados == 1
    assert resultado.marcados_offline == 1
    assert resultado.marcados_online == 0
    with factory() as session:
        media = session.get(MediaFile, media_id)
        assert media.arquivo_offline is True


def test_arquivo_que_volta_e_marcado_online(migrated_engine, tmp_path):
    factory = create_session_factory(migrated_engine)
    alvo = make_jpeg(tmp_path / "volta.jpg", seed=1)
    with factory() as session:
        f = _fonte(session, str(tmp_path))
        media_id = _arquivo(session, f, alvo, arquivo_offline=True).id
        session.commit()

    resultado = reconciliar(factory)

    assert resultado.marcados_online == 1
    assert resultado.marcados_offline == 0
    with factory() as session:
        media = session.get(MediaFile, media_id)
        assert media.arquivo_offline is False


def test_referencia_de_catalogo_externo_nunca_e_tocada(migrated_engine, tmp_path):
    """O teste mais importante desta fatia: uma linha `apple://uuid` ou
    `lightroom://uuid` não é caminho de filesystem. `Path.exists()` nela
    não tem sentido — e a revisão da fatia anterior (Item A) achou
    exatamente esta classe de bug (destruir referência de catálogo externo
    por não checar se o predicado se aplicava a ela)."""
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        f = _fonte(session, str(tmp_path))
        referencia = MediaFile(
            source_id=f.id, caminho="apple://UUID-1", pasta="",
            nome="IMG_1.HEIC", extensao="heic", tamanho=1,
            arquivo_ausente=True, papel=MediaRole.SINAL,
        )
        session.add(referencia)
        session.flush()
        ref_id = referencia.id
        session.commit()

    resultado = reconciliar(factory)

    assert resultado.verificados == 0
    with factory() as session:
        media = session.get(MediaFile, ref_id)
        # Nem tocada: nem marcada offline, nem qualquer outro campo mexido.
        assert media.arquivo_offline is False
        assert media.arquivo_ausente is True


def test_arquivo_ausente_nao_e_verificado(migrated_engine, tmp_path):
    """`arquivo_ausente=True` já diz que não há arquivo local — não há o
    que checar de novo."""
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        f = _fonte(session, str(tmp_path))
        media = MediaFile(
            source_id=f.id, caminho=str(tmp_path / "nunca_existiu.jpg"),
            pasta=str(tmp_path), nome="nunca_existiu.jpg", extensao="jpg",
            tamanho=1, arquivo_ausente=True,
        )
        session.add(media)
        session.commit()

    resultado = reconciliar(factory)
    assert resultado.verificados == 0


def test_fonte_indisponivel_nao_e_verificada(migrated_engine, tmp_path):
    """Fonte com o volume fora de alcance: um `Path.exists()` por arquivo
    de um HD desmontado seria custo puro e sempre daria negativo — a
    resposta certa já é `Source.disponivel`, não precisa reconferir cada
    arquivo."""
    factory = create_session_factory(migrated_engine)
    alvo = make_jpeg(tmp_path / "a.jpg", seed=1)
    with factory() as session:
        f = _fonte(session, str(tmp_path), disponivel=False)
        _arquivo(session, f, alvo)
        session.commit()

    resultado = reconciliar(factory)
    assert resultado.verificados == 0


def test_checkpoint_processa_parte_e_retoma_na_proxima_chamada(
    migrated_engine, tmp_path
):
    factory = create_session_factory(migrated_engine)
    caminhos = []
    with factory() as session:
        f = _fonte(session, str(tmp_path))
        for i in range(10):
            alvo = make_jpeg(tmp_path / f"img_{i:02d}.jpg", seed=i)
            _arquivo(session, f, alvo)
            caminhos.append(alvo)
        session.commit()

    # Orçamento por percentual: só 20% (2 de 10) nesta chamada.
    r1 = reconciliar(factory, orcamento_percentual=0.2, orcamento_segundos=999)
    assert r1.verificados == 2
    assert r1.ciclo_concluido is False

    checkpoint = SettingsRepository(factory).obter(CHAVE_RECONCILIACAO_CHECKPOINT)
    assert checkpoint["ultimo_media_id"] > 0

    # A chamada seguinte não reprocessa do zero nem pula nada: completa o
    # resto do acervo (8 restantes) e fecha o ciclo.
    r2 = reconciliar(factory, orcamento_percentual=1.0, orcamento_segundos=999)
    assert r2.verificados == 8
    assert r2.ciclo_concluido is True

    checkpoint2 = SettingsRepository(factory).obter(CHAVE_RECONCILIACAO_CHECKPOINT)
    assert checkpoint2["ultimo_media_id"] == 0
    assert "concluido_em" in checkpoint2

    # Nenhum arquivo real deveria ter sido marcado offline nesse percurso.
    with factory() as session:
        assert all(
            not m.arquivo_offline for m in session.scalars(select(MediaFile))
        )


def test_orcamento_de_tempo_para_a_passada_no_meio(migrated_engine, tmp_path):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        f = _fonte(session, str(tmp_path))
        for i in range(5):
            alvo = make_jpeg(tmp_path / f"t_{i}.jpg", seed=i)
            _arquivo(session, f, alvo)
        session.commit()

    # Orçamento de tempo zerado: para antes de processar qualquer linha.
    resultado = reconciliar(
        factory, orcamento_segundos=0.0, orcamento_percentual=1.0
    )
    assert resultado.verificados == 0
    assert resultado.ciclo_concluido is False
