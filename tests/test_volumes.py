"""Identidade de volume e disponibilidade das fontes.

O que depende de `diskutil` e da tabela de montagem real é isolado por
injeção nos testes — a suíte não pode depender de que disco está plugado.
"""

from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import select

from fotoorganizer.database import create_session_factory
from fotoorganizer.models import Source
from fotoorganizer.security import volumes
from fotoorganizer.security.volumes import (
    Volume,
    identificar,
    ponto_de_montagem,
    volume_desmontado,
)
from fotoorganizer.sources.disponibilidade import verificar


# -- identidade --------------------------------------------------------------
def test_disco_desligado_nao_vira_o_disco_de_boot(monkeypatch):
    """O erro mais caro possível: subir a árvore a partir de um volume
    desmontado chega em `/` e atribui as fotos do HD externo ao disco
    interno — trocando "está na gaveta" por "está aqui"."""
    monkeypatch.setattr(volumes.os.path, "ismount", lambda p: str(p) == "/")

    alvo = "/Volumes/photo/Portfolio/Patagonia Fev.20/096A9198.DNG"
    assert volume_desmontado(alvo) == Path("/Volumes/photo")
    assert ponto_de_montagem(alvo) == Path("/Volumes/photo")

    v = identificar(alvo)
    assert v.montado is False
    assert v.identidade == "caminho:/Volumes/photo"
    assert v.ponto_de_montagem == Path("/Volumes/photo")


def test_caminho_comum_nao_e_confundido_com_volume(monkeypatch):
    monkeypatch.setattr(volumes.os.path, "ismount", lambda p: str(p) == "/")
    assert volume_desmontado("/Users/eu/Pictures/2026") is None
    assert volume_desmontado("/Volumes") is None


def test_uuid_manda_sobre_o_ponto_de_montagem(monkeypatch):
    """É o ponto todo: o mesmo disco em `/Volumes/photo` e em
    `/Volumes/photo 1` tem de ser o mesmo disco."""
    monkeypatch.setattr(volumes.os.path, "ismount",
                        lambda p: str(p).startswith("/Volumes/photo"))
    monkeypatch.setattr(volumes, "_tabela_de_montagem", lambda: {})
    monkeypatch.setattr(volumes, "_diskutil", lambda ponto: {
        "VolumeUUID": "ABC-123", "VolumeName": "photo",
        "FilesystemType": "apfs", "Ejectable": True,
    })

    um = identificar("/Volumes/photo/x.jpg")
    outro = identificar("/Volumes/photo 1/x.jpg")
    assert um.identidade == outro.identidade == "uuid:ABC-123"
    assert um.removivel is True and um.estavel is True


def test_nas_sem_uuid_usa_servidor_e_compartilhamento(monkeypatch):
    monkeypatch.setattr(volumes.os.path, "ismount",
                        lambda p: str(p) == "/Volumes/fotos")
    monkeypatch.setattr(volumes, "_diskutil", lambda ponto: {})
    monkeypatch.setattr(volumes, "_tabela_de_montagem",
                        lambda: {"/Volumes/fotos": ("//alex@nas/fotos", "smbfs")})

    v = identificar("/Volumes/fotos/2020")
    assert v.identidade == "rede://alex@nas/fotos"
    assert v.estavel is True and v.de_rede is True


def test_sem_uuid_e_sem_rede_a_identidade_e_fragil(monkeypatch):
    monkeypatch.setattr(volumes.os.path, "ismount", lambda p: str(p) == "/")
    monkeypatch.setattr(volumes, "_diskutil", lambda ponto: {})
    monkeypatch.setattr(volumes, "_tabela_de_montagem", lambda: {})
    v = identificar("/Users/eu/Pictures")
    assert v.identidade == "caminho:/"
    assert v.estavel is False        # quem depender disso precisa saber


def test_diskutil_quebrado_nao_derruba_a_identificacao(monkeypatch):
    """Falha de subprocesso devolve a identidade mais fraca e segue."""
    monkeypatch.setattr(volumes.os.path, "ismount", lambda p: str(p) == "/")
    monkeypatch.setattr(volumes, "_tabela_de_montagem", lambda: {})

    def explode(_ponto):
        raise OSError("diskutil sumiu")
    monkeypatch.setattr(volumes, "_diskutil", explode)

    with pytest.raises(OSError):
        identificar("/Users/eu")   # o erro é do dublê, não do módulo

    monkeypatch.setattr(volumes, "_diskutil", lambda p: {})
    assert identificar("/Users/eu").identidade == "caminho:/"


# -- disponibilidade ---------------------------------------------------------
def _fonte(session, caminho: str, **kw) -> Source:
    source = Source(caminho=caminho, **kw)
    session.add(source)
    return source


def test_fonte_alcancavel_e_marcada_e_datada(migrated_engine, tmp_path):
    factory = create_session_factory(migrated_engine)
    pasta = tmp_path / "fotos"
    pasta.mkdir()
    with factory() as session:
        _fonte(session, str(pasta), apelido="local")
        session.commit()

    (estado,) = verificar(factory)
    assert estado.disponivel is True
    assert estado.resumo() == "disponível"

    with factory() as session:
        source = session.scalar(select(Source))
        assert source.disponivel is True
        assert isinstance(source.visto_em, datetime)
        assert source.volume_id      # identidade gravada na primeira visita


def test_disco_na_gaveta_e_indisponivel_sem_perder_identidade(
    migrated_engine, monkeypatch
):
    """"Na gaveta" e "sumiu" são coisas diferentes, e a interface precisa
    dizer qual é."""
    monkeypatch.setattr(volumes.os.path, "ismount", lambda p: str(p) == "/")
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        _fonte(session, "/Volumes/photo/Portfolio", apelido="photo",
               volume_id="uuid:ABC-123", volume_nome="photo")
        session.commit()

    (estado,) = verificar(factory)
    assert estado.disponivel is False
    assert "gaveta" in estado.resumo()

    with factory() as session:
        source = session.scalar(select(Source))
        assert source.disponivel is False
        assert source.volume_id == "uuid:ABC-123"   # não se perde
        assert source.visto_em is None              # nunca esteve presente


def test_volume_que_voltou_noutro_ponto_e_apontado(migrated_engine, monkeypatch):
    """O caso que corrompe catálogo em silêncio: o disco voltou, com outro
    nome de montagem, e o app trataria como disco novo."""
    monkeypatch.setattr(volumes.os.path, "ismount", lambda p: str(p) == "/")
    monkeypatch.setattr(volumes, "montado_em",
                        lambda ident: Path("/Volumes/photo 1"))
    import fotoorganizer.sources.disponibilidade as disp
    monkeypatch.setattr(disp, "montado_em", lambda ident: Path("/Volumes/photo 1"))

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        _fonte(session, "/Volumes/photo/Portfolio", apelido="photo",
               volume_id="uuid:ABC-123")
        session.commit()

    (estado,) = verificar(factory)
    assert estado.mudou_de_lugar is True
    assert estado.ponto_atual == Path("/Volumes/photo 1")
    assert "mudou de lugar" in estado.resumo()

    with factory() as session:
        # A verificação NÃO reescreve o caminho: mover as linhas de mídia é
        # operação do usuário, não efeito colateral.
        assert session.scalar(select(Source)).caminho == "/Volumes/photo/Portfolio"
