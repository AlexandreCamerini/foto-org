from datetime import datetime

import pytest
from sqlalchemy import select

from fotoorganizer.database import create_session_factory
from fotoorganizer.models import (
    AuditLog,
    ConfidenceLevel,
    DuplicateGroup,
    DuplicateLevel,
    DuplicateMember,
    DuplicateRole,
    MediaFile,
    OperationItem,
    OperationStatus,
    Source,
    Suggestion,
    SuggestionStatus,
)
from fotoorganizer.operations import (
    ExecutionControl,
    OperationExecutor,
    OperationPlanner,
)
from fotoorganizer.operations.executor import DryRunObrigatorio
from fotoorganizer.repositories.operations import OperationRepository


@pytest.fixture()
def ambiente(migrated_engine, tmp_path):
    """3 fotos aprovadas (uma com mesmo nome de outra → colisão no destino),
    1 pendente (fica fora do plano)."""
    origem_dir = tmp_path / "origem"
    destino_dir = tmp_path / "destino"
    origem_dir.mkdir()
    destino_dir.mkdir()

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = Source(caminho=str(origem_dir))
        session.add(fonte)
        session.flush()
        casos = [
            ("a/IMG_1.jpg", b"foto A", "Viagens/2024 - Franca", SuggestionStatus.APROVADA),
            ("b/IMG_1.jpg", b"foto B", "Viagens/2024 - Franca", SuggestionStatus.APROVADA),
            ("a/IMG_2.jpg", b"foto C", "Familia/2023", SuggestionStatus.EDITADA),
            ("a/IMG_3.jpg", b"foto D", "Eventos", SuggestionStatus.PENDENTE),
        ]
        for rel, conteudo, destino_sugerido, status in casos:
            arquivo = origem_dir / rel
            arquivo.parent.mkdir(exist_ok=True)
            arquivo.write_bytes(conteudo)
            media = MediaFile(
                source_id=fonte.id, caminho=str(arquivo), pasta=str(arquivo.parent),
                nome=arquivo.name, extensao="jpg", tamanho=len(conteudo),
                data_capturada=datetime(2024, 1, 1),
            )
            session.add(media)
            session.flush()
            session.add(Suggestion(
                media_id=media.id, destino_sugerido=destino_sugerido,
                template="t", nivel=ConfidenceLevel.ALTA, status=status,
                versao_logica="test",
            ))
        session.commit()

    planner = OperationPlanner(factory)
    executor = OperationExecutor(factory)
    return factory, planner, executor, origem_dir, destino_dir


def test_plano_so_inclui_aprovadas_e_resolve_colisao(ambiente):
    factory, planner, executor, origem, destino = ambiente
    plan_id = planner.criar_plano(destino)
    itens = OperationRepository(factory).itens(plan_id)

    assert len(itens) == 3  # a pendente fica fora
    destinos = [i.destino for i in itens]
    assert len(set(destinos)) == 3  # colisão IMG_1 x IMG_1 resolvida
    com_conflito = [i for i in itens if i.conflito]
    assert len(com_conflito) == 1
    assert "renomeado" in com_conflito[0].conflito


def test_plano_exclui_versao_de_duplicata_exata(ambiente):
    """VERSAO é a cópia redundante de um grupo já resolvido (automático ou
    humano) — não faz sentido copiar duas vezes o mesmo conteúdo."""
    factory, planner, executor, origem, destino = ambiente
    with factory() as session:
        medias = {m.caminho: m for m in session.scalars(select(MediaFile))}
        principal = medias[str(origem / "a/IMG_1.jpg")]
        versao = medias[str(origem / "b/IMG_1.jpg")]
        grupo = DuplicateGroup(
            nivel=DuplicateLevel.EXATO, resolvido_automaticamente=True
        )
        session.add(grupo)
        session.flush()
        session.add(DuplicateMember(
            group_id=grupo.id, media_id=principal.id,
            papel=DuplicateRole.PRINCIPAL,
        ))
        session.add(DuplicateMember(
            group_id=grupo.id, media_id=versao.id, papel=DuplicateRole.VERSAO,
        ))
        session.commit()

    plan_id = planner.criar_plano(destino)
    itens = OperationRepository(factory).itens(plan_id)
    origens = {i.origem for i in itens}

    assert str(origem / "b/IMG_1.jpg") not in origens
    assert str(origem / "a/IMG_1.jpg") in origens
    assert len(itens) == 2  # 3 aprovadas - 1 versão redundante


def test_plano_inclui_grupo_ignorado_por_inteiro(ambiente):
    """IGNORADO é diferente de VERSAO: o usuário olhou o grupo e decidiu que
    não são duplicatas de fato — nenhum arquivo fica fora do plano por isso
    (fotoorganizer/repositories/duplicates.py: "nenhum arquivo será
    tocado")."""
    factory, planner, executor, origem, destino = ambiente
    with factory() as session:
        medias = {m.caminho: m for m in session.scalars(select(MediaFile))}
        par = [
            medias[str(origem / "a/IMG_1.jpg")],
            medias[str(origem / "b/IMG_1.jpg")],
        ]
        grupo = DuplicateGroup(nivel=DuplicateLevel.EXATO)
        session.add(grupo)
        session.flush()
        for media in par:
            session.add(DuplicateMember(
                group_id=grupo.id, media_id=media.id,
                papel=DuplicateRole.IGNORADO,
            ))
        session.commit()

    plan_id = planner.criar_plano(destino)
    itens = OperationRepository(factory).itens(plan_id)
    assert len(itens) == 3  # nenhuma exclusão — grupo ignorado, não resolvido


def test_execucao_exige_dry_run(ambiente):
    factory, planner, executor, origem, destino = ambiente
    plan_id = planner.criar_plano(destino)
    with pytest.raises(DryRunObrigatorio):
        executor.executar(plan_id)
    # E nada foi copiado.
    assert list(destino.rglob("*.jpg")) == []


def test_copia_verificada_preserva_originais(ambiente):
    factory, planner, executor, origem, destino = ambiente
    originais = {p: p.read_bytes() for p in origem.rglob("*.jpg")}

    plan_id = planner.criar_plano(destino)
    relatorio = executor.dry_run(plan_id)
    assert relatorio["prontos"] == 3
    assert relatorio["espaco_suficiente"]

    stats = executor.executar(plan_id)
    assert stats == {"copiados": 3, "erros": 0, "pulados": 0,
                     "cancelado": False}

    # Originais intactos.
    assert {p: p.read_bytes() for p in origem.rglob("*.jpg")} == originais
    # Cópias existem, com conteúdo idêntico e hash registrado.
    copiados = sorted(destino.rglob("*.jpg"))
    assert len(copiados) == 3
    with factory() as session:
        for item in session.scalars(select(OperationItem)):
            assert item.status == OperationStatus.CONCLUIDA
            assert item.hash_pre == item.hash_pos
            assert item.hash_pre.startswith("sha256:")


def test_sobrescrita_impossivel(ambiente):
    factory, planner, executor, origem, destino = ambiente
    plan_id = planner.criar_plano(destino)
    executor.dry_run(plan_id)

    # Alguém cria um arquivo no destino exato entre o dry-run e a execução.
    itens = OperationRepository(factory).itens(plan_id)
    alvo = itens[0]
    from pathlib import Path

    caminho_alvo = Path(alvo.destino)
    caminho_alvo.parent.mkdir(parents=True, exist_ok=True)
    caminho_alvo.write_bytes(b"conteudo preexistente")

    stats = executor.executar(plan_id)
    assert stats["erros"] == 1
    assert stats["copiados"] == 2
    # O arquivo preexistente segue intacto.
    assert caminho_alvo.read_bytes() == b"conteudo preexistente"
    with factory() as session:
        item = session.get(OperationItem, alvo.id)
        assert "sobrescrita bloqueada" in item.erro


def test_cancelamento_e_retomada(ambiente):
    factory, planner, executor, origem, destino = ambiente
    plan_id = planner.criar_plano(destino)
    executor.dry_run(plan_id)

    control = ExecutionControl()

    def cancela_apos_primeiro(n, _total, _origem):
        if n >= 2:
            control.cancelar()

    stats = executor.executar(plan_id, progress=cancela_apos_primeiro,
                              control=control)
    assert stats["cancelado"] is True
    assert 0 < stats["copiados"] < 3

    # Retomada: termina o resto sem refazer o que já foi.
    stats2 = executor.executar(plan_id)
    assert stats2["pulados"] == stats["copiados"]
    assert stats["copiados"] + stats2["copiados"] == 3
    assert len(list(destino.rglob("*.jpg"))) == 3


def test_origem_indisponivel_nao_para_o_resto(ambiente):
    factory, planner, executor, origem, destino = ambiente
    plan_id = planner.criar_plano(destino)
    executor.dry_run(plan_id)

    (origem / "a/IMG_1.jpg").unlink()  # simula volume desconectado

    stats = executor.executar(plan_id)
    assert stats["erros"] == 1
    assert stats["copiados"] == 2


def test_destino_dentro_da_origem_e_conflito(ambiente):
    factory, planner, executor, origem, destino = ambiente
    plan_id = planner.criar_plano(origem / "organizadas")
    itens = OperationRepository(factory).itens(plan_id)
    assert all("origem" in (i.conflito or "") for i in itens)


def test_audit_log_completo(ambiente):
    factory, planner, executor, origem, destino = ambiente
    plan_id = planner.criar_plano(destino)
    executor.dry_run(plan_id)
    executor.executar(plan_id)

    with factory() as session:
        acoes = [a.acao for a in session.scalars(
            select(AuditLog).where(AuditLog.plan_id == plan_id)
            .order_by(AuditLog.id)
        )]
    assert acoes[0] == "plano_criado"
    assert "dry_run" in acoes
    assert "execucao_iniciada" in acoes
    assert acoes.count("copia_verificada") == 3
    assert acoes[-1] == "execucao_finalizada"


def test_plano_nao_refaz_midias_ja_copiadas(ambiente):
    factory, planner, executor, origem, destino = ambiente
    plan_id = planner.criar_plano(destino)
    executor.dry_run(plan_id)
    executor.executar(plan_id)

    assert planner.criar_plano(destino) is None  # nada novo a planejar


def test_execucao_recusa_plano_sem_nada_copiavel(ambiente):
    """Ter rodado o dry-run não basta — ele precisa ter aprovado algo.

    Caso real: 97 fotos cujas origens estavam todas num volume desmontado.
    O dry-run marcou 97 problemas e 0 prontos, mas o plano seguia com
    "0 erros" (que conta erro de EXECUÇÃO) e a porta se abria.
    """
    factory, planner, executor, origem, destino = ambiente
    plan_id = planner.criar_plano(destino)

    for rel in ("a/IMG_1.jpg", "b/IMG_1.jpg", "a/IMG_2.jpg"):
        (origem / rel).unlink()  # volume desconectado
    relatorio = executor.dry_run(plan_id)
    assert relatorio["prontos"] == 0
    assert len(relatorio["problemas"]) == 3

    with pytest.raises(DryRunObrigatorio, match="nenhum arquivo copiável"):
        executor.executar(plan_id)


def test_resumo_do_plano_carrega_o_veredito_do_dry_run(ambiente):
    factory, planner, executor, origem, destino = ambiente
    plan_id = planner.criar_plano(destino)
    repo = OperationRepository(factory)

    # Antes do dry-run não há veredito, e o plano não é executável.
    row = repo.plano(plan_id)
    assert (row.prontos, row.problemas) == (None, None)
    assert row.executavel is False

    executor.dry_run(plan_id)
    row = repo.plano(plan_id)
    assert row.prontos == 3 and row.problemas == 0
    assert row.executavel is True

    # Origens somem: o dry-run seguinte derruba o veredito.
    for rel in ("a/IMG_1.jpg", "b/IMG_1.jpg", "a/IMG_2.jpg"):
        (origem / rel).unlink()
    executor.dry_run(plan_id)
    row = repo.plano(plan_id)
    assert row.prontos == 0 and row.problemas == 3
    assert row.executavel is False
    assert row.com_erro == 0  # o campo que enganava: nada executou ainda
