"""Inventário: o que existe e onde, contando foto e não registro."""

from fotoorganizer.database import create_session_factory
from fotoorganizer.models import MediaFile, MediaRole, Source
from fotoorganizer.repositories.inventario import levantar


def _fonte(session, caminho, apelido, disponivel=True):
    source = Source(caminho=caminho, apelido=apelido, disponivel=disponivel)
    session.add(source)
    session.flush()
    return source


def _arquivo(session, source, pasta, nome, **kw):
    session.add(MediaFile(
        source_id=source.id, caminho=f"{pasta}/{nome}", pasta=pasta,
        nome=nome, extensao=nome.rsplit(".", 1)[-1].lower(), tamanho=1, **kw
    ))


def _referencia(session, source, ref, pasta, nome, **kw):
    session.add(MediaFile(
        source_id=source.id, caminho=f"lightroom://{ref}", pasta=pasta,
        nome=nome, extensao=nome.rsplit(".", 1)[-1].lower(), tamanho=1,
        arquivo_ausente=True, papel=MediaRole.SINAL, **kw
    ))


def test_a_mesma_foto_em_duas_fontes_conta_uma(migrated_engine):
    """O caso que inflava o número: a pasta Dubai tinha 2.405 arquivos no
    disco e 2.405 referências do Lightroom — 2.405 fotos, não 4.810."""
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        disco = _fonte(session, "/Users/eu/Pictures", "Pictures")
        lr = _fonte(session, "/Users/eu/cat.lrcat", "Lightroom")
        _arquivo(session, disco, "/Users/eu/Pictures/Dubai", "a.jpg")
        _referencia(session, lr, "UUID-1", "/Users/eu/Pictures/Dubai", "a.jpg")
        session.commit()

    inv = levantar(factory)
    assert inv.total_registros == 2
    assert inv.fotos == 1
    (lugar,) = inv.lugares
    assert lugar.fotos == 1
    assert lugar.fontes == ("Lightroom", "Pictures")


def test_maiuscula_no_caminho_nao_duplica_no_macos(migrated_engine):
    """O Lightroom grava "/Users", o scan gravou "/users". É o mesmo lugar e
    o mesmo arquivo."""
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        disco = _fonte(session, "/users/eu", "scan")
        lr = _fonte(session, "/Users/eu/cat.lrcat", "Lightroom")
        _arquivo(session, disco, "/users/eu/Fotos", "b.jpg")
        _referencia(session, lr, "UUID-2", "/Users/eu/Fotos", "b.jpg")
        session.commit()

    inv = levantar(factory)
    assert inv.fotos == 1
    assert [l.raiz for l in inv.lugares] == ["/Users/eu"]


def test_alcancavel_vem_da_fonte_e_nao_de_arquivo_ausente(migrated_engine):
    """Um arquivo catalogado do HD externo tem `arquivo_ausente=0` e
    continua inalcançável com o disco na gaveta. A primeira versão dizia
    "98 alcançáveis" para um volume desmontado."""
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        gaveta = _fonte(session, "/Volumes/Externo", "Externo",
                        disponivel=False)
        aqui = _fonte(session, "/Users/eu/Pictures", "Pictures")
        _arquivo(session, gaveta, "/Volumes/Externo/2019", "c.jpg")
        _arquivo(session, aqui, "/Users/eu/Pictures", "d.jpg")
        session.commit()

    inv = levantar(factory)
    por_raiz = {l.raiz: l for l in inv.lugares}
    assert por_raiz["/Volumes/Externo"].alcancaveis == 0
    assert por_raiz["/Volumes/Externo"].so_no_catalogo == 1
    assert por_raiz["/Users/eu"].alcancaveis == 1
    assert inv.alcancaveis == 1


def test_referencia_de_nuvem_existe_e_nao_tem_lugar(migrated_engine):
    """Uma foto só no iCloud existe. Contá-la como lacuna de lugar seria
    inventar um problema; omiti-la seria esconder a foto."""
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        apple = _fonte(session, "/Users/eu/Fotos.photoslibrary", "Apple Fotos")
        session.add(MediaFile(
            source_id=apple.id, caminho="apple://UUID-9", pasta="",
            nome="IMG_1.HEIC", extensao="heic", tamanho=1,
            arquivo_ausente=True, papel=MediaRole.SINAL,
        ))
        session.commit()

    inv = levantar(factory)
    assert inv.sem_caminho == 1
    assert inv.lugares == ()
    assert inv.fotos == 1        # existe, mesmo sem lugar no disco


def test_catalogo_vazio_nao_quebra(migrated_engine):
    inv = levantar(create_session_factory(migrated_engine))
    assert (inv.fotos, inv.alcancaveis, inv.lugares) == (0, 0, ())
