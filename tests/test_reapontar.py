"""Reapontar fonte que mudou de lugar — reescreve o catálogo, nunca o disco.

`disponibilidade.py` detecta o volume remontado e recusa reescrever; este
módulo é a operação que ela recusa fazer. A suíte cobre a matemática do
prefixo, a disciplina dry-run → validação → transação, e a guarda que
recusa fontes fora da convenção `/Volumes/<nome>`.
"""

from pathlib import Path

import pytest
from sqlalchemy import select

from fotoorganizer.database import create_session_factory
from fotoorganizer.models import AuditLog, MediaFile, Source
from fotoorganizer.sources.disponibilidade import EstadoDaFonte
from fotoorganizer.sources.reapontar import (
    ColisaoDeCaminho,
    ReapontamentoInaplicavel,
    ValidacaoFalhou,
    aplicar,
    desfazer_por_auditoria,
    prefixos_do_estado,
    previa,
    resolver_fonte,
)


def _fonte(session, caminho: str, **kw) -> Source:
    source = Source(caminho=caminho, **kw)
    session.add(source)
    session.flush()
    return source


def _midia(session, source_id: int, caminho: str, **kw) -> MediaFile:
    # Defaults derivados do caminho; `**kw` pode sobrescrevê-los — usado
    # pelo cenário de referência (`apple://uuid`) que não tem pasta real.
    campos = dict(
        source_id=source_id, caminho=caminho,
        pasta=str(Path(caminho).parent), nome=Path(caminho).name,
        extensao=Path(caminho).suffix.lstrip("."), tamanho=100,
    )
    campos.update(kw)
    m = MediaFile(**campos)
    session.add(m)
    return m


# -- prefixos_do_estado -------------------------------------------------------

def test_prefixo_calculado_a_partir_do_estado():
    estado = EstadoDaFonte(
        source_id=1, apelido="photo", caminho="/Volumes/photo/DCIM",
        volume=None, disponivel=False,
        ponto_atual=Path("/Volumes/photo 1"),
        identidade_gravada="uuid:ABC-123",
    )
    antigo, novo = prefixos_do_estado(estado)
    assert antigo == "/Volumes/photo/DCIM"
    assert novo == "/Volumes/photo 1/DCIM"


def test_prefixo_recusa_fonte_sem_mudanca_de_lugar():
    estado = EstadoDaFonte(
        source_id=1, apelido="photo", caminho="/Volumes/photo/DCIM",
        volume=None, disponivel=True, ponto_atual=None,
    )
    with pytest.raises(ReapontamentoInaplicavel):
        prefixos_do_estado(estado)


def test_prefixo_recusa_fonte_que_nao_e_volume():
    """Disco interno, ou identidade `caminho:` frágil: nunca vira um
    replace genérico que pode corromper caminho errado."""
    estado = EstadoDaFonte(
        source_id=1, apelido="interno", caminho="/Users/eu/Pictures",
        volume=None, disponivel=False,
        ponto_atual=Path("/Volumes/qualquer"),
    )
    with pytest.raises(ReapontamentoInaplicavel):
        prefixos_do_estado(estado)


# -- previa (dry-run) ---------------------------------------------------------

def test_dry_run_nao_escreve_nada_no_banco(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        source = _fonte(session, "/Volumes/photo/DCIM", apelido="photo")
        for i in range(3):
            _midia(session, source.id, f"/Volumes/photo/DCIM/img_{i}.jpg")
        session.commit()
        source_id = source.id

    p = previa(factory, source_id, "/Volumes/photo/DCIM", "/Volumes/photo 1/DCIM")
    assert p.total_media_files == 3
    assert p.total_ignoradas_sem_prefixo == 0
    assert len(p.amostra) == 3
    assert p.amostra[0] == (
        "/Volumes/photo/DCIM/img_0.jpg", "/Volumes/photo 1/DCIM/img_0.jpg",
    )

    with factory() as session:
        assert session.scalar(select(Source)).caminho == "/Volumes/photo/DCIM"
        assert all(
            m.caminho.startswith("/Volumes/photo/DCIM")
            for m in session.scalars(select(MediaFile))
        )
        assert session.scalar(select(AuditLog)) is None


def test_fonte_mista_dry_run_so_conta_e_amostra_o_que_tem_o_prefixo(
    migrated_engine,
):
    """`MediaFile.caminho` de uma fonte Apple Fotos/Lightroom mistura
    caminho de arquivo com referência `apple://uuid` (`sources/importer.py`)
    — a referência nunca começa com `/Volumes/...` e não pode ser fatiada
    como se fosse um caminho: destruiria a única testemunha da foto
    (invariante 8)."""
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        source = _fonte(session, "/Volumes/photo/DCIM", apelido="photo")
        for i in range(2):
            _midia(session, source.id, f"/Volumes/photo/DCIM/img_{i}.jpg")
        for i in range(3):
            _midia(session, source.id, f"apple://UUID-{i}",
                   pasta="", nome=f"UUID-{i}", extensao="")
        session.commit()
        source_id = source.id

    p = previa(factory, source_id, "/Volumes/photo/DCIM", "/Volumes/photo 1/DCIM")
    assert p.total_media_files == 2
    assert p.total_ignoradas_sem_prefixo == 3
    assert {antigo for antigo, _novo in p.amostra} == {
        "/Volumes/photo/DCIM/img_0.jpg", "/Volumes/photo/DCIM/img_1.jpg",
    }


# -- aplicar --------------------------------------------------------------

def test_validacao_aborta_a_operacao_inteira_se_um_caminho_novo_nao_existe(
    migrated_engine, tmp_path,
):
    """Prefixo errado não pode reescrever 45 mil linhas para lugar nenhum:
    se UMA amostra falha, NENHUMA linha é alterada."""
    novo_ponto = tmp_path / "photo 1"
    (novo_ponto / "DCIM").mkdir(parents=True)
    (novo_ponto / "DCIM" / "img_0.jpg").write_bytes(b"x")
    # img_1.jpg deliberadamente ausente em novo_ponto

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        source = _fonte(session, "/Volumes/photo/DCIM", apelido="photo")
        _midia(session, source.id, "/Volumes/photo/DCIM/img_0.jpg")
        _midia(session, source.id, "/Volumes/photo/DCIM/img_1.jpg")
        session.commit()
        source_id = source.id

    with pytest.raises(ValidacaoFalhou):
        aplicar(
            factory, source_id,
            "/Volumes/photo/DCIM", str(novo_ponto / "DCIM"),
        )

    with factory() as session:
        assert session.scalar(select(Source)).caminho == "/Volumes/photo/DCIM"
        caminhos = {m.caminho for m in session.scalars(select(MediaFile))}
        assert caminhos == {
            "/Volumes/photo/DCIM/img_0.jpg", "/Volumes/photo/DCIM/img_1.jpg",
        }
        assert session.scalar(select(AuditLog)) is None


def test_aplicar_reescreve_source_e_media_files_da_fonte_e_mais_nenhuma(
    migrated_engine, tmp_path,
):
    novo_ponto = tmp_path / "photo 1"
    (novo_ponto / "DCIM").mkdir(parents=True)
    for i in range(3):
        (novo_ponto / "DCIM" / f"img_{i}.jpg").write_bytes(b"x")

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        alvo = _fonte(session, "/Volumes/photo/DCIM", apelido="photo")
        for i in range(3):
            _midia(session, alvo.id, f"/Volumes/photo/DCIM/img_{i}.jpg")
        outra = _fonte(session, str(tmp_path / "outra"), apelido="outra")
        _midia(session, outra.id, str(tmp_path / "outra" / "z.jpg"))
        session.commit()
        alvo_id, outra_id = alvo.id, outra.id

    r = aplicar(
        factory, alvo_id,
        "/Volumes/photo/DCIM", str(novo_ponto / "DCIM"),
    )
    assert r.linhas_media_files == 3
    assert r.prefixo_novo == str(novo_ponto / "DCIM")

    with factory() as session:
        fonte_alvo = session.get(Source, alvo_id)
        assert fonte_alvo.caminho == str(novo_ponto / "DCIM")
        caminhos_alvo = {
            m.caminho for m in session.scalars(
                select(MediaFile).where(MediaFile.source_id == alvo_id)
            )
        }
        assert caminhos_alvo == {
            str(novo_ponto / "DCIM" / f"img_{i}.jpg") for i in range(3)
        }

        # A outra fonte não foi tocada.
        fonte_outra = session.get(Source, outra_id)
        assert fonte_outra.caminho == str(tmp_path / "outra")
        media_outra = session.scalar(
            select(MediaFile).where(MediaFile.source_id == outra_id)
        )
        assert media_outra.caminho == str(tmp_path / "outra" / "z.jpg")


def test_fonte_mista_execucao_so_reescreve_o_que_tem_o_prefixo(
    migrated_engine, tmp_path,
):
    """O bug real: fatiar `apple://UUID` pelo mesmo prefixo de um caminho
    de disco destrói a referência em silêncio (a fatia pode virar string
    vazia, ou lixo, dependendo do tamanho). Depois de reapontar, as
    referências saem EXATAMENTE iguais."""
    novo_ponto = tmp_path / "photo 1"
    (novo_ponto / "DCIM").mkdir(parents=True)
    (novo_ponto / "DCIM" / "img_0.jpg").write_bytes(b"x")
    (novo_ponto / "DCIM" / "img_1.jpg").write_bytes(b"x")

    referencias = ["apple://UUID-0000", "lightroom://UUID-COMPRIDO-O-BASTANTE"]

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        source = _fonte(session, "/Volumes/photo/DCIM", apelido="photo")
        for i in range(2):
            _midia(session, source.id, f"/Volumes/photo/DCIM/img_{i}.jpg")
        for ref in referencias:
            _midia(session, source.id, ref, pasta="", nome=ref, extensao="")
        session.commit()
        source_id = source.id

    r = aplicar(
        factory, source_id,
        "/Volumes/photo/DCIM", str(novo_ponto / "DCIM"),
    )
    assert r.linhas_media_files == 2

    with factory() as session:
        caminhos = {m.caminho for m in session.scalars(select(MediaFile))}
        assert caminhos == {
            str(novo_ponto / "DCIM" / "img_0.jpg"),
            str(novo_ponto / "DCIM" / "img_1.jpg"),
            *referencias,
        }


def test_colisao_de_caminho_aborta_sem_escrever_nada(migrated_engine, tmp_path):
    """Uma linha reapontada pode cair exatamente em cima de outra linha da
    MESMA fonte que fica intocada (não tinha o prefixo) — violaria a UNIQUE
    (source_id, caminho). Detectado ANTES de tocar o banco, com mensagem
    clara em vez de IntegrityError cru; nenhuma linha é alterada."""
    prefixo_antigo = "/Volumes/photo/DCIM"
    novo_ponto = tmp_path / "photo 1"
    prefixo_novo = str(novo_ponto / "DCIM")
    (novo_ponto / "DCIM").mkdir(parents=True)
    (novo_ponto / "DCIM" / "img.jpg").write_bytes(b"x")

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        source = _fonte(session, prefixo_antigo, apelido="photo")
        # Depois de reapontada, esta linha viraria exatamente igual à
        # próxima, que já está gravada assim e NÃO tem o prefixo antigo
        # (fica intocada) — um caso raro, mas a colisão precisa de tratamento
        # mesmo assim.
        _midia(session, source.id, f"{prefixo_antigo}/img.jpg")
        _midia(session, source.id, f"{prefixo_novo}/img.jpg")
        session.commit()
        source_id = source.id
        caminhos_antes = {
            m.caminho for m in session.scalars(select(MediaFile))
        }

    with pytest.raises(ColisaoDeCaminho):
        aplicar(factory, source_id, prefixo_antigo, prefixo_novo)

    with factory() as session:
        assert session.scalar(select(Source)).caminho == prefixo_antigo
        caminhos_depois = {
            m.caminho for m in session.scalars(select(MediaFile))
        }
        assert caminhos_depois == caminhos_antes
        assert session.scalar(select(AuditLog)) is None


def test_audit_log_criado_com_os_prefixos(migrated_engine, tmp_path):
    novo_ponto = tmp_path / "photo 1"
    (novo_ponto / "DCIM").mkdir(parents=True)
    (novo_ponto / "DCIM" / "img_0.jpg").write_bytes(b"x")

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        source = _fonte(session, "/Volumes/photo/DCIM", apelido="photo")
        _midia(session, source.id, "/Volumes/photo/DCIM/img_0.jpg")
        session.commit()
        source_id = source.id

    r = aplicar(
        factory, source_id, "/Volumes/photo/DCIM", str(novo_ponto / "DCIM"),
    )

    with factory() as session:
        entrada = session.get(AuditLog, r.audit_log_id)
        assert entrada is not None
        assert entrada.plan_id is None
        assert entrada.acao == "reapontar_fonte"
        assert entrada.detalhe == {
            "source_id": source_id,
            "prefixo_antigo": "/Volumes/photo/DCIM",
            "prefixo_novo": str(novo_ponto / "DCIM"),
            "linhas_media_files": 1,
        }


def test_desfazer_por_auditoria_reverte_bit_a_bit(migrated_engine, tmp_path):
    """Ida e volta: `aplicar` A→B, depois `desfazer_por_auditoria` no
    audit_log resultante. O catálogo volta ao estado anterior — mesmos
    caminhos, mesma contagem — reaproveitando a mesma validação de amostra
    e deixando uma NOVA entrada de auditoria (desfazer-o-desfazer continua
    funcionando)."""
    novo_ponto = tmp_path / "photo 1"
    (novo_ponto / "DCIM").mkdir(parents=True)
    for i in range(3):
        (novo_ponto / "DCIM" / f"img_{i}.jpg").write_bytes(b"x")
    # A validação do DESFAZER confere os caminhos ANTIGOS — precisam existir
    # de verdade no disco para o teste, então a raiz original também é um
    # caminho real em tmp_path (não um `/Volumes/...` inexistente).
    (tmp_path / "photo" / "DCIM").mkdir(parents=True)
    for i in range(3):
        (tmp_path / "photo" / "DCIM" / f"img_{i}.jpg").write_bytes(b"x")
    caminho_original = str(tmp_path / "photo" / "DCIM")

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        source = _fonte(session, caminho_original, apelido="photo")
        for i in range(3):
            _midia(session, source.id, f"{caminho_original}/img_{i}.jpg")
        session.commit()
        source_id = source.id
        caminhos_originais = {
            m.caminho for m in session.scalars(select(MediaFile))
        }

    ida = aplicar(factory, source_id, caminho_original, str(novo_ponto / "DCIM"))
    assert ida.linhas_media_files == 3

    volta = desfazer_por_auditoria(factory, ida.audit_log_id)
    assert volta.linhas_media_files == 3
    assert volta.prefixo_antigo == str(novo_ponto / "DCIM")
    assert volta.prefixo_novo == caminho_original

    with factory() as session:
        fonte = session.get(Source, source_id)
        assert fonte.caminho == caminho_original
        caminhos_depois = {
            m.caminho for m in session.scalars(select(MediaFile))
        }
        assert caminhos_depois == caminhos_originais

        # Desfazer-o-desfazer continua funcionando: a entrada nova também
        # existe e aponta para os prefixos trocados.
        entrada_volta = session.get(AuditLog, volta.audit_log_id)
        assert entrada_volta.detalhe["prefixo_antigo"] == str(novo_ponto / "DCIM")
        assert entrada_volta.detalhe["prefixo_novo"] == caminho_original


def test_aplicar_recusa_prefixo_antigo_que_nao_bate_com_a_fonte(migrated_engine):
    """Guarda extra: se o prefixo_antigo informado não é o caminho atual da
    fonte, aborta em vez de reescrever a fonte errada."""
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        source = _fonte(session, "/Volumes/photo/DCIM", apelido="photo")
        session.commit()
        source_id = source.id

    with pytest.raises(ReapontamentoInaplicavel):
        aplicar(factory, source_id, "/Volumes/errado/DCIM", "/Volumes/photo 1/DCIM")


# -- resolver_fonte -----------------------------------------------------------

def test_resolver_fonte_aceita_id_ou_apelido(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        source = _fonte(session, "/Volumes/photo/DCIM", apelido="photo")
        session.commit()
        source_id = source.id

    assert resolver_fonte(factory, str(source_id)) == source_id
    assert resolver_fonte(factory, "photo") == source_id
    with pytest.raises(ReapontamentoInaplicavel):
        resolver_fonte(factory, "não existe")


# -- comando CLI ---------------------------------------------------------

def test_cli_reapontar_mostra_dry_run_depois_confirma(monkeypatch, tmp_path, capsys):
    """Ponta a ponta: `reapontar <apelido>` sem `--confirmar` só mostra o
    dry-run; com `--confirmar`, reescreve o catálogo de verdade."""
    import fotoorganizer.cli as cli
    import fotoorganizer.security.volumes as volumes
    import fotoorganizer.sources.disponibilidade as disp
    from fotoorganizer.cli import main
    from fotoorganizer.config.settings import Settings
    from fotoorganizer.database import (
        create_db_engine, create_session_factory, upgrade_to_head,
    )

    settings = Settings(data_dir=tmp_path / "dados", cache_dir=tmp_path / "cache")
    settings.ensure_dirs()
    upgrade_to_head(settings.db_path)
    factory = create_session_factory(create_db_engine(settings.db_path))
    monkeypatch.setattr(cli, "load_settings", lambda: settings)

    caminho_antigo = "/Volumes/photo/DCIM"
    novo_ponto = tmp_path / "photo 1"
    (novo_ponto / "DCIM").mkdir(parents=True)
    (novo_ponto / "DCIM" / "img_0.jpg").write_bytes(b"x")

    with factory() as session:
        source = _fonte(session, caminho_antigo, apelido="photo",
                         volume_id="uuid:ABC-123")
        _midia(session, source.id, f"{caminho_antigo}/img_0.jpg")
        session.commit()

    monkeypatch.setattr(volumes.os.path, "ismount", lambda p: str(p) == "/")
    monkeypatch.setattr(disp, "montado_em", lambda ident: novo_ponto)
    # Só o caminho antigo (o volume "desmontado") finge não existir — o
    # resto do disco (inclusive os arquivos em novo_ponto que a validação
    # da amostra confere) continua sendo o filesystem real.
    original_exists = disp.Path.exists

    def _exists_dublado(self):
        return False if str(self) == caminho_antigo else original_exists(self)

    monkeypatch.setattr(disp.Path, "exists", _exists_dublado)

    assert main(["reapontar", "photo"]) == 0
    saida = capsys.readouterr().out
    assert caminho_antigo in saida
    assert str(novo_ponto / "DCIM") in saida
    assert "Dry-run só" in saida
    with factory() as session:
        assert session.scalar(select(Source)).caminho == caminho_antigo

    assert main(["reapontar", "photo", "--confirmar"]) == 0
    saida = capsys.readouterr().out
    assert "1 linha(s) reapontada(s)" in saida
    assert "--desfazer" in saida
    with factory() as session:
        assert session.scalar(select(Source)).caminho == str(novo_ponto / "DCIM")
        assert session.scalar(select(AuditLog)).acao == "reapontar_fonte"


def test_cli_desfazer_reverte_via_audit_log(monkeypatch, tmp_path, capsys):
    """`reapontar --desfazer <audit_log_id>` não depende de nenhum volume
    montado — só lê a entrada de auditoria e reaplica com os prefixos
    trocados. Sem `fonte`, o argumento posicional fica de fora."""
    import fotoorganizer.cli as cli
    from fotoorganizer.cli import main
    from fotoorganizer.config.settings import Settings
    from fotoorganizer.database import (
        create_db_engine, create_session_factory, upgrade_to_head,
    )
    from fotoorganizer.sources.reapontar import aplicar as aplicar_direto

    settings = Settings(data_dir=tmp_path / "dados", cache_dir=tmp_path / "cache")
    settings.ensure_dirs()
    upgrade_to_head(settings.db_path)
    factory = create_session_factory(create_db_engine(settings.db_path))
    monkeypatch.setattr(cli, "load_settings", lambda: settings)

    raiz_a, raiz_b = tmp_path / "a", tmp_path / "b"
    raiz_a.mkdir()
    raiz_b.mkdir()
    (raiz_a / "img.jpg").write_bytes(b"x")
    (raiz_b / "img.jpg").write_bytes(b"x")

    with factory() as session:
        source = _fonte(session, str(raiz_a), apelido="photo")
        _midia(session, source.id, str(raiz_a / "img.jpg"))
        session.commit()
        source_id = source.id

    r = aplicar_direto(factory, source_id, str(raiz_a), str(raiz_b))

    assert main(["reapontar", "--desfazer", str(r.audit_log_id)]) == 0
    assert "Desfeito" in capsys.readouterr().out
    with factory() as session:
        assert session.scalar(select(Source)).caminho == str(raiz_a)


def test_cli_reapontar_sem_fonte_nem_desfazer_avisa(tmp_path, monkeypatch, capsys):
    import fotoorganizer.cli as cli
    from fotoorganizer.cli import main
    from fotoorganizer.config.settings import Settings

    settings = Settings(data_dir=tmp_path / "dados", cache_dir=tmp_path / "cache")
    monkeypatch.setattr(cli, "load_settings", lambda: settings)

    assert main(["reapontar"]) == 1
    assert "Informe a fonte" in capsys.readouterr().out


def test_cli_reapontar_recusa_fonte_que_nao_mudou_de_lugar(
    monkeypatch, tmp_path, capsys,
):
    import fotoorganizer.cli as cli
    from fotoorganizer.cli import main
    from fotoorganizer.config.settings import Settings
    from fotoorganizer.database import (
        create_db_engine, create_session_factory, upgrade_to_head,
    )

    settings = Settings(data_dir=tmp_path / "dados", cache_dir=tmp_path / "cache")
    settings.ensure_dirs()
    upgrade_to_head(settings.db_path)
    factory = create_session_factory(create_db_engine(settings.db_path))
    monkeypatch.setattr(cli, "load_settings", lambda: settings)

    pasta = tmp_path / "fotos"
    pasta.mkdir()
    with factory() as session:
        _fonte(session, str(pasta), apelido="local")
        session.commit()

    assert main(["reapontar", "local"]) == 1
    assert "não mudou de lugar" in capsys.readouterr().out
