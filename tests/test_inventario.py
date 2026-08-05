"""Inventário: o que existe e onde, contando foto e não registro."""

from fotoorganizer.database import create_session_factory
from fotoorganizer.models import MediaFile, MediaRole, Source
from fotoorganizer.repositories.inventario import funil, levantar


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


def test_alcance_e_da_foto_nao_da_primeira_linha_encontrada(migrated_engine):
    """A mesma foto conhecida por duas fontes, uma desmontada e outra não.

    A contagem antiga decidia pela PRIMEIRA linha que o loop encontrasse:
    entrando pela fonte desmontada, a foto era dada como fora de alcance
    embora houvesse outro caminho até o arquivo. No acervo do dono isso
    tirava 2.620 fotos da contagem de alcançáveis.
    """
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        # A desmontada entra primeiro de propósito: é a ordem que expunha o
        # defeito.
        gaveta = _fonte(session, "/Volumes/HD", "HD", disponivel=False)
        aqui = _fonte(session, "/Users/eu/Pictures", "Pictures")
        _arquivo(session, gaveta, "/Users/eu/Pictures/Dubai", "a.jpg")
        _arquivo(session, aqui, "/Users/eu/Pictures/Dubai", "a.jpg")
        session.commit()

    inv = levantar(factory)
    assert inv.fotos == 1
    assert inv.alcancaveis == 1
    assert inv.lugares[0].alcancaveis == 1


def test_funil_diz_os_tres_degraus_na_ordem_em_que_estreitam(migrated_engine):
    """Os cinco números que se contradiziam viram uma leitura só."""
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        disco = _fonte(session, "/Users/eu/Pictures", "Pictures")
        gaveta = _fonte(session, "/Volumes/HD", "HD", disponivel=False)
        lr = _fonte(session, "/Users/eu/cat.lrcat", "Lightroom")
        _arquivo(session, disco, "/Users/eu/Pictures", "a.jpg")
        _arquivo(session, gaveta, "/Volumes/HD", "b.jpg")
        # Mesma foto que a do disco: registro a mais, foto nenhuma a mais.
        _referencia(session, lr, "UUID-9", "/Users/eu/Pictures", "a.jpg")
        session.commit()

    f = funil(factory)
    assert f.registros == 3        # linhas no catálogo
    assert f.conhecidas == 2       # fotos: a duplicada conta uma vez
    assert f.alcancaveis == 1      # a do HD desmontado não abre agora
    assert f.organizaveis == 1     # a alcançável é acervo
    # Cada degrau é menor ou igual ao anterior — se algum dia deixar de ser,
    # a tela volta a mostrar um funil que não afunila.
    assert f.registros >= f.conhecidas >= f.alcancaveis >= f.organizaveis


def test_organizavel_conta_foto_e_nao_linha(migrated_engine):
    """A mesma foto conhecida por duas fontes é UMA organizável.

    O funil contava foto em "conhecidas" e "alcançáveis" e linha em
    "organizáveis": no acervo real, 26.023 linhas eram 22.150 fotos. Dois
    degraus mediam uma coisa e o terceiro media outra, dentro do mesmo
    número que existe para acabar com exatamente esse problema.
    """
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        a = _fonte(session, "/Users/eu/Pictures", "Pictures")
        b = _fonte(session, "/Users/eu/outra", "Outra")
        _arquivo(session, a, "/Users/eu/Pictures/Dubai", "x.jpg")
        _arquivo(session, b, "/Users/eu/Pictures/Dubai", "x.jpg")
        session.commit()

    inv = levantar(factory)
    assert inv.total_registros == 2
    assert inv.fotos == 1
    assert inv.organizaveis == 1


def test_arquivo_offline_nao_conta_como_alcancavel(migrated_engine):
    """A fonte responde (disponivel=True), mas ESTE arquivo sumiu de onde
    estava. `Source.disponivel` sozinho não é suficiente para "alcançável"
    — precisa também que o arquivo específico não tenha sumido (fase 12,
    item B)."""
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        f = _fonte(session, "/Users/eu/Pictures", "Pictures")
        _arquivo(session, f, "/Users/eu/Pictures", "ok.jpg")
        _arquivo(session, f, "/Users/eu/Pictures", "sumiu.jpg",
                 arquivo_offline=True)
        session.commit()

    inv = levantar(factory)
    assert inv.fotos == 2
    assert inv.alcancaveis == 1
    (lugar,) = inv.lugares
    assert lugar.fotos == 2
    assert lugar.alcancaveis == 1


def test_testemunha_nao_conta_como_organizavel(migrated_engine):
    """Rebaixar a SINAL tira da contagem sem tirar do banco (invariante 8)."""
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        f = _fonte(session, "/Users/eu/Pictures", "Pictures")
        _arquivo(session, f, "/Users/eu/Pictures", "real.jpg")
        _arquivo(session, f, "/Users/eu/Pictures/cache", "derivado.jpg",
                 papel=MediaRole.SINAL)
        session.commit()

    inv = levantar(factory)
    assert inv.total_registros == 2   # nada saiu do banco
    assert inv.fotos == 2             # as duas existem
    assert inv.organizaveis == 1      # só uma é acervo


def test_organizavel_exige_a_fonte_respondendo(migrated_engine):
    """O caso que quebrava a promessa do funil: a pasta "Dubai, Thai & Viet"
    saiu do disco, e suas 2.405 fotos continuavam contadas como organizáveis
    enquanto a grade escrevia "volume ou pasta fora de alcance" em cada
    miniatura. Acervo é classificação; alcance é uma pergunta sobre agora, e
    o terceiro degrau precisa das duas. Ver D-068."""
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        gaveta = _fonte(session, "/Volumes/HD", "HD", disponivel=False)
        _arquivo(session, gaveta, "/Volumes/HD/Dubai", "a.jpg")
        session.commit()

    f = funil(factory)
    assert f.conhecidas == 1
    assert f.alcancaveis == 0
    assert f.organizaveis == 0     # é acervo, e mesmo assim não abre agora


def test_miniatura_alcancavel_nao_e_organizavel(migrated_engine):
    """A outra metade da regra continua valendo: estar ao alcance não faz de
    uma miniatura do pacote do Apple Fotos acervo do dono (invariante 8)."""
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        apple = _fonte(session, "/Users/eu/Fotos.photoslibrary", "Apple Fotos")
        session.add(MediaFile(
            source_id=apple.id, caminho="/Users/eu/Fotos.photoslibrary/t.jpg",
            pasta="/Users/eu/Fotos.photoslibrary", nome="t.jpg",
            extensao="jpg", tamanho=1, papel=MediaRole.SINAL,
        ))
        session.commit()

    f = funil(factory)
    assert (f.conhecidas, f.alcancaveis, f.organizaveis) == (1, 1, 0)


def test_uma_fonte_montada_basta_para_organizar_a_foto(migrated_engine):
    """A mesma foto conhecida por duas fontes, uma na gaveta e outra montada.

    O alcance já era decidido por foto e não por linha; o degrau de acervo
    tinha de seguir a mesma regra, senão a foto seria alcançável e não
    organizável — o funil afunilando pelo motivo errado."""
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        gaveta = _fonte(session, "/Volumes/HD", "HD", disponivel=False)
        aqui = _fonte(session, "/Users/eu/Pictures", "Pictures")
        _arquivo(session, gaveta, "/Users/eu/Pictures/Dubai", "a.jpg")
        _arquivo(session, aqui, "/Users/eu/Pictures/Dubai", "a.jpg")
        session.commit()

    f = funil(factory)
    assert (f.registros, f.conhecidas) == (2, 1)
    assert (f.alcancaveis, f.organizaveis) == (1, 1)