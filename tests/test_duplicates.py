import shutil
from datetime import datetime, timedelta

import pytest
from PIL import Image
from sqlalchemy import select

from fotoorganizer.config.settings import ScannerSettings
from fotoorganizer.database import create_session_factory
from fotoorganizer.duplicates import BKTree, DuplicateDetector, distancia_hamming
from fotoorganizer.duplicates.resolucao import escolher_principal_automatico
from fotoorganizer.metadata import PurePythonExtractor
from fotoorganizer.models import (
    DuplicateGroup,
    DuplicateLevel,
    DuplicateMember,
    DuplicateRole,
    MediaFile,
    MetadataEntry,
    Source,
    SourceType,
)
from fotoorganizer.repositories import DuplicateRepository
from fotoorganizer.scanner import CatalogScanner


# -- BK-tree ---------------------------------------------------------------
def test_distancia_hamming():
    assert distancia_hamming(0b1010, 0b1010) == 0
    assert distancia_hamming(0b1010, 0b0101) == 4


def test_bktree_busca_por_distancia():
    tree = BKTree()
    valores = {0b0000: "a", 0b0001: "b", 0b0011: "c", 0b1111: "d"}
    for valor, nome in valores.items():
        tree.inserir(valor, nome)

    vizinhos = tree.buscar(0b0000, max_dist=1)
    achados = {payload for _d, _v, payloads in vizinhos for payload in payloads}
    assert achados == {"a", "b"}

    vizinhos = tree.buscar(0b0000, max_dist=2)
    achados = {payload for _d, _v, payloads in vizinhos for payload in payloads}
    assert achados == {"a", "b", "c"}


def test_bktree_payloads_iguais_agrupados():
    tree = BKTree()
    tree.inserir(42, "x")
    tree.inserir(42, "y")
    (d, _v, payloads), = tree.buscar(42, 0)
    assert d == 0 and payloads == ["x", "y"]


# -- regra de desempate de grupo EXATO (pura, sem banco) --------------------
def _midia_solta(id_, nome, pasta, *, tipo=SourceType.PASTA) -> MediaFile:
    media = MediaFile(
        id=id_, source_id=1, caminho=f"{pasta}/{nome}", pasta=pasta,
        nome=nome, extensao="jpg", tamanho=100,
    )
    media.source = Source(tipo=tipo, caminho=pasta)
    return media


def test_resolucao_prefere_fonte_propria_sobre_externa():
    propria = _midia_solta(1, "a.jpg", "/fotos", tipo=SourceType.PASTA)
    externa = _midia_solta(2, "a.jpg", "/import", tipo=SourceType.APPLE_PHOTOS)
    assert escolher_principal_automatico([externa, propria]) is propria
    assert escolher_principal_automatico([propria, externa]) is propria


def test_resolucao_prefere_caminho_mais_organizado_em_empate_de_fonte():
    raiz = _midia_solta(1, "foto.jpg", "/fotos")
    organizada = _midia_solta(2, "foto.jpg", "/fotos/2024/viagem")
    assert escolher_principal_automatico([raiz, organizada]) is organizada


def test_resolucao_prefere_nome_descritivo_sobre_generico():
    generico = _midia_solta(1, "IMG_1234.jpg", "/fotos")
    descritivo = _midia_solta(2, "aniversario_maria.jpg", "/fotos")
    assert escolher_principal_automatico([generico, descritivo]) is descritivo
    assert escolher_principal_automatico([descritivo, generico]) is descritivo


def test_resolucao_desempata_por_id_e_e_estavel_a_ordem_de_entrada():
    menor = _midia_solta(3, "foto.jpg", "/fotos")
    maior = _midia_solta(5, "foto.jpg", "/fotos")
    assert escolher_principal_automatico([maior, menor]) is menor
    assert escolher_principal_automatico([menor, maior]) is menor


# -- imagens de teste --------------------------------------------------------
def _gradiente(size=(256, 192)) -> Image.Image:
    img = Image.new("RGB", size)
    px = img.load()
    for x in range(size[0]):
        for y in range(size[1]):
            px[x, y] = (x % 256, y % 256, (x + y) % 256)
    return img


@pytest.fixture()
def ambiente(migrated_engine, tmp_path):
    fotos = tmp_path / "fotos"
    fotos.mkdir()

    # EXATO: bytes idênticos
    _gradiente().save(fotos / "original.jpg", quality=90)
    shutil.copy(fotos / "original.jpg", fotos / "copia_exata.jpg")
    # CONTEUDO: mesma imagem, compressão diferente (bytes diferem, phash igual)
    _gradiente().save(fotos / "recomprimida.jpg", quality=35)
    # Única, bem diferente
    Image.new("RGB", (256, 192), "white").save(fotos / "solo.jpg")

    factory = create_session_factory(migrated_engine)
    scanner = CatalogScanner(factory, PurePythonExtractor(), ScannerSettings())
    scanner.scan_source(fotos)
    detector = DuplicateDetector(factory)
    return factory, detector, fotos


def test_deteccao_exato_e_conteudo(ambiente):
    factory, detector, fotos = ambiente
    stats = detector.detectar()
    assert stats["exato"] == 1

    with factory() as session:
        grupos = list(session.scalars(select(DuplicateGroup)))
        exato = next(g for g in grupos if g.nivel == DuplicateLevel.EXATO)
        nomes = set()
        for membro in exato.membros:
            media = session.get(MediaFile, membro.media_id)
            nomes.add(media.nome)
        assert nomes == {"original.jpg", "copia_exata.jpg"}

        # A recomprimida deve cair num grupo phash (conteúdo ou visual),
        # nunca no exato — e "solo.jpg" não entra em grupo nenhum.
        agrupados = {
            session.get(MediaFile, m.media_id).nome
            for g in grupos for m in g.membros
        }
        assert "recomprimida.jpg" in agrupados
        assert "solo.jpg" not in agrupados


def test_deteccao_nao_modifica_arquivos(ambiente):
    factory, detector, fotos = ambiente
    antes = {
        p.name: (p.stat().st_size, p.stat().st_mtime_ns, p.read_bytes())
        for p in fotos.iterdir()
    }
    detector.detectar()
    depois = {
        p.name: (p.stat().st_size, p.stat().st_mtime_ns, p.read_bytes())
        for p in fotos.iterdir()
    }
    assert antes == depois  # invariante 1: somente leitura


def test_sha256_calculado_so_para_candidatos(ambiente):
    factory, detector, fotos = ambiente
    detector.detectar()
    with factory() as session:
        por_nome = {
            m.nome: m for m in session.scalars(select(MediaFile))
        }
    # candidatos (mesmo tamanho+hash rápido) ganham sha256…
    assert por_nome["original.jpg"].hash_sha256 is not None
    assert por_nome["copia_exata.jpg"].hash_sha256 is not None
    # …quem não tem par candidato não paga o hash completo.
    assert por_nome["solo.jpg"].hash_sha256 is None


def test_redeteccao_preserva_decisao(ambiente):
    factory, detector, fotos = ambiente
    detector.detectar()
    repo = DuplicateRepository(factory)

    grupo = next(g for g in repo.listar_grupos()
                 if g.nivel == DuplicateLevel.EXATO)
    principal = grupo.membros[0]
    repo.escolher_principal(grupo.id, principal.media_id)

    stats = detector.detectar()
    assert stats["preservados"] >= 1

    depois = next(g for g in repo.listar_grupos() if g.id == grupo.id)
    papeis = {m.media_id: m.papel for m in depois.membros}
    assert papeis[principal.media_id] == DuplicateRole.PRINCIPAL


def test_acoes_do_repositorio(ambiente):
    factory, detector, fotos = ambiente
    detector.detectar()
    repo = DuplicateRepository(factory)
    grupo = repo.listar_grupos()[0]

    repo.escolher_principal(grupo.id, grupo.membros[0].media_id)
    atual = next(g for g in repo.listar_grupos() if g.id == grupo.id)
    assert atual.decidido
    papeis = [m.papel for m in atual.membros]
    assert papeis.count(DuplicateRole.PRINCIPAL) == 1
    assert papeis.count(DuplicateRole.VERSAO) == len(papeis) - 1

    repo.ignorar_grupo(grupo.id)
    atual = next(g for g in repo.listar_grupos() if g.id == grupo.id)
    assert all(m.papel == DuplicateRole.IGNORADO for m in atual.membros)

    repo.desfazer_grupo(grupo.id)
    atual = next(g for g in repo.listar_grupos() if g.id == grupo.id)
    assert not atual.decidido


def test_grupo_exato_e_resolvido_automaticamente(migrated_engine):
    """SHA-256 idêntico não deixa ambiguidade sobre o conteúdo: o detector
    já grava PRINCIPAL/VERSAO sozinho, preferindo a fonte própria."""
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        propria = Source(caminho="/fotos", tipo=SourceType.PASTA)
        externa = Source(caminho="/import", tipo=SourceType.APPLE_PHOTOS)
        session.add_all([propria, externa])
        session.flush()
        a = _inserir_midia(session, propria.id, "IMG_0001.jpg",
                            "0000000000000000", tamanho=100,
                            hash_rapido="xxh3:igual")
        b = _inserir_midia(session, externa.id, "IMG_0001.jpg",
                            "0000000000000000", tamanho=100,
                            hash_rapido="xxh3:igual")
        session.flush()
        a.hash_sha256 = b.hash_sha256 = "sha256:igual"
        session.commit()
        a_id, b_id = a.id, b.id

    stats = DuplicateDetector(factory).detectar()
    assert stats["exato"] == 1

    repo = DuplicateRepository(factory)
    (grupo,) = repo.listar_grupos()
    assert grupo.resolvido_automaticamente
    papeis = {m.media_id: m.papel for m in grupo.membros}
    assert papeis[a_id] == DuplicateRole.PRINCIPAL  # fonte própria vence
    assert papeis[b_id] == DuplicateRole.VERSAO


def test_nova_copia_identica_se_junta_a_grupo_resolvido_automaticamente(
    migrated_engine,
):
    """Um grupo EXATO resolvido sozinho não pode travar no tamanho de quando
    foi criado — resolvido_automaticamente não é decisão humana, então a
    redetecção regenera o grupo e a terceira cópia entra nele, em vez de
    ficar invisível para sempre (o próprio motivo de existir a coluna)."""
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = Source(caminho="/fotos", tipo=SourceType.PASTA)
        session.add(fonte)
        session.flush()
        a = _inserir_midia(session, fonte.id, "a.jpg", "0000000000000000",
                            tamanho=100, hash_rapido="xxh3:igual")
        b = _inserir_midia(session, fonte.id, "b.jpg", "0000000000000000",
                            tamanho=100, hash_rapido="xxh3:igual")
        session.flush()
        a.hash_sha256 = b.hash_sha256 = "sha256:igual"
        session.commit()

    detector = DuplicateDetector(factory)
    detector.detectar()
    repo = DuplicateRepository(factory)
    (grupo,) = repo.listar_grupos()
    assert len(grupo.membros) == 2
    assert grupo.resolvido_automaticamente  # ninguém tocou ainda

    with factory() as session:
        c = _inserir_midia(session, fonte.id, "c.jpg", "0000000000000000",
                            tamanho=100, hash_rapido="xxh3:igual")
        session.flush()
        c.hash_sha256 = "sha256:igual"
        session.commit()

    detector.detectar()
    (grupo,) = repo.listar_grupos()  # continua um grupo só, agora com 3
    assert len(grupo.membros) == 3
    assert grupo.resolvido_automaticamente
    papeis = [m.papel for m in grupo.membros]
    assert papeis.count(DuplicateRole.PRINCIPAL) == 1
    assert papeis.count(DuplicateRole.VERSAO) == 2


def test_decisao_humana_substitui_resolucao_automatica(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = Source(caminho="/fotos", tipo=SourceType.PASTA)
        session.add(fonte)
        session.flush()
        a = _inserir_midia(session, fonte.id, "a.jpg", "0000000000000000",
                            tamanho=100, hash_rapido="xxh3:igual")
        b = _inserir_midia(session, fonte.id, "b.jpg", "0000000000000000",
                            tamanho=100, hash_rapido="xxh3:igual")
        session.flush()
        a.hash_sha256 = b.hash_sha256 = "sha256:igual"
        session.commit()
        b_id = b.id

    DuplicateDetector(factory).detectar()
    repo = DuplicateRepository(factory)
    (grupo,) = repo.listar_grupos()
    assert grupo.resolvido_automaticamente

    # Humano discorda da escolha automática e escolhe o outro membro.
    repo.escolher_principal(grupo.id, b_id)
    atual = next(g for g in repo.listar_grupos() if g.id == grupo.id)
    assert not atual.resolvido_automaticamente
    assert next(m.papel for m in atual.membros if m.media_id == b_id) == (
        DuplicateRole.PRINCIPAL
    )


def test_desfazer_reverte_resolucao_automatica(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = Source(caminho="/fotos", tipo=SourceType.PASTA)
        session.add(fonte)
        session.flush()
        a = _inserir_midia(session, fonte.id, "a.jpg", "0000000000000000",
                            tamanho=100, hash_rapido="xxh3:igual")
        b = _inserir_midia(session, fonte.id, "b.jpg", "0000000000000000",
                            tamanho=100, hash_rapido="xxh3:igual")
        session.flush()
        a.hash_sha256 = b.hash_sha256 = "sha256:igual"
        session.commit()

    DuplicateDetector(factory).detectar()
    repo = DuplicateRepository(factory)
    (grupo,) = repo.listar_grupos()

    repo.desfazer_grupo(grupo.id)
    atual = next(g for g in repo.listar_grupos() if g.id == grupo.id)
    assert not atual.resolvido_automaticamente
    assert not atual.decidido
    assert all(m.papel == DuplicateRole.INDEFINIDO for m in atual.membros)


def test_grupo_conteudo_nao_e_resolvido_automaticamente(factory_com_source):
    """Só EXATO tem certeza sobre o CONTEÚDO. Os demais níveis (CONTEUDO,
    VISUAL, SEQUENCIA — este último já coberto pelos testes de rajada
    abaixo) dependem de julgamento humano e continuam nascendo INDEFINIDO."""
    factory, source_id = factory_com_source
    base = datetime(2025, 5, 24, 17, 0, 0)
    with factory() as session:
        # phash idêntico, câmeras diferentes: CONTEUDO, não SEQUENCIA.
        _inserir_midia(session, source_id, "c1.jpg", "00000000000000ff",
                       model="EOS R6", quando=base)
        _inserir_midia(session, source_id, "c2.jpg", "00000000000000ff",
                       model="iPhone 15", quando=base + timedelta(hours=1))
        session.commit()

    stats = DuplicateDetector(factory).detectar()
    assert stats["conteudo"] == 1

    repo = DuplicateRepository(factory)
    (grupo,) = repo.listar_grupos()
    assert not grupo.resolvido_automaticamente
    assert all(m.papel == DuplicateRole.INDEFINIDO for m in grupo.membros)


# -- rajadas (sequência) vs duplicata visual ---------------------------------
def _inserir_midia(session, source_id, nome, phash, *, make="Canon",
                   model="EOS R6", quando=None, tamanho=1000,
                   hash_rapido=None):
    """Linha de catálogo direto no banco: phash já preenchido faz a
    detecção pular qualquer acesso a arquivo."""
    media = MediaFile(
        source_id=source_id, caminho=f"/fake/{nome}", pasta="/fake",
        nome=nome, extensao="jpg", tamanho=tamanho,
        hash_rapido=hash_rapido or f"xxh3:{nome}",
        hash_perceptual=phash, make=make, model=model,
        data_capturada=quando,
    )
    session.add(media)
    return media


@pytest.fixture()
def factory_com_source(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        source = Source(caminho="/fake")
        session.add(source)
        session.commit()
        source_id = source.id
    return factory, source_id


def test_rajada_mesma_camera_vira_sequencia(factory_com_source):
    factory, source_id = factory_com_source
    base = datetime(2025, 5, 24, 17, 0, 0)
    with factory() as session:
        # phash a distância 2, mesma câmera, 2s entre frames.
        _inserir_midia(session, source_id, "burst_1.jpg",
                       "0000000000000000", quando=base)
        _inserir_midia(session, source_id, "burst_2.jpg",
                       "0000000000000003", quando=base + timedelta(seconds=2))
        session.commit()

    stats = DuplicateDetector(factory).detectar()
    assert stats["sequencia"] == 1
    assert stats["visual"] == 0

    with factory() as session:
        grupo = session.scalars(select(DuplicateGroup)).one()
        assert grupo.nivel == DuplicateLevel.SEQUENCIA


def test_phash_identico_em_rajada_tambem_e_sequencia(factory_com_source):
    factory, source_id = factory_com_source
    base = datetime(2025, 5, 24, 17, 0, 0)
    with factory() as session:
        # Cena estática em burst: phash idêntico, bytes diferentes.
        _inserir_midia(session, source_id, "static_1.jpg",
                       "00000000000000ff", quando=base)
        _inserir_midia(session, source_id, "static_2.jpg",
                       "00000000000000ff", quando=base + timedelta(seconds=1))
        session.commit()

    stats = DuplicateDetector(factory).detectar()
    assert stats["sequencia"] == 1
    assert stats["conteudo"] == 0


def test_fotos_parecidas_de_cameras_diferentes_seguem_visuais(factory_com_source):
    factory, source_id = factory_com_source
    base = datetime(2025, 5, 24, 17, 0, 0)
    with factory() as session:
        _inserir_midia(session, source_id, "a.jpg", "0000000000000000",
                       model="EOS R6", quando=base)
        _inserir_midia(session, source_id, "b.jpg", "0000000000000003",
                       model="iPhone 15", quando=base + timedelta(seconds=2))
        session.commit()

    stats = DuplicateDetector(factory).detectar()
    assert stats["visual"] == 1
    assert stats["sequencia"] == 0


def test_parecidas_com_horas_de_distancia_nao_sao_rajada(factory_com_source):
    factory, source_id = factory_com_source
    base = datetime(2025, 5, 24, 17, 0, 0)
    with factory() as session:
        _inserir_midia(session, source_id, "a.jpg", "0000000000000000",
                       quando=base)
        _inserir_midia(session, source_id, "b.jpg", "0000000000000003",
                       quando=base + timedelta(hours=3))
        session.commit()

    stats = DuplicateDetector(factory).detectar()
    assert stats["visual"] == 1
    assert stats["sequencia"] == 0


def test_sem_data_de_captura_nao_afirma_rajada(factory_com_source):
    factory, source_id = factory_com_source
    with factory() as session:
        _inserir_midia(session, source_id, "a.jpg", "0000000000000000",
                       quando=None)
        _inserir_midia(session, source_id, "b.jpg", "0000000000000003",
                       quando=None)
        session.commit()

    stats = DuplicateDetector(factory).detectar()
    assert stats["visual"] == 1
    assert stats["sequencia"] == 0


def test_mesma_foto_em_duas_fontes_conta_n_fontes(migrated_engine, tmp_path):
    """Cópia da mesma foto em fontes diferentes: o grupo sabe que é um
    vínculo entre catálogos (n_fontes=2), não só espaço a recuperar."""
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        f1 = Source(caminho="/fotos/pasta")
        f2 = Source(caminho="/fotos/takeout")
        session.add_all([f1, f2])
        session.flush()
        _inserir_midia(session, f1.id, "raw.jpg", "00000000000000aa",
                       hash_rapido="xxh3:igual", tamanho=500)
        _inserir_midia(session, f2.id, "copia.jpg", "00000000000000aa",
                       hash_rapido="xxh3:igual2", tamanho=500)
        session.commit()

    DuplicateDetector(factory).detectar()
    repo = DuplicateRepository(factory)
    (grupo,) = repo.listar_grupos()
    assert grupo.n_fontes == 2


def test_bytes_recuperaveis(ambiente):
    factory, detector, fotos = ambiente
    detector.detectar()
    repo = DuplicateRepository(factory)
    grupo = next(g for g in repo.listar_grupos()
                 if g.nivel == DuplicateLevel.EXATO)
    tamanhos = sorted((m.tamanho for m in grupo.membros), reverse=True)
    assert grupo.bytes_recuperaveis == sum(tamanhos[1:]) > 0


def test_resolucao_prefere_quem_sabe_mais_antes_de_cair_no_id():
    """Num grupo EXATO os bytes são idênticos, então o tamanho não desempata
    — mas a quantidade de metadado sim, e neste acervo o metadado é o ativo.
    Entra antes do `id`, que é ordem de indexação e não significa nada."""
    pobre = _midia_solta(3, "foto.jpg", "/fotos")
    rica = _midia_solta(5, "foto.jpg", "/fotos")
    metadados = {3: 4, 5: 57}
    assert escolher_principal_automatico([pobre, rica], metadados) is rica
    assert escolher_principal_automatico([rica, pobre], metadados) is rica
    # Sem a contagem, a regra antiga vale e o menor id ganha.
    assert escolher_principal_automatico([rica, pobre]) is pobre


def test_riqueza_nao_atropela_os_criterios_anteriores():
    """Fonte própria continua vencendo catálogo externo, por mais rico que
    ele seja: o critério novo é desempate, não nova prioridade."""
    propria = _midia_solta(1, "IMG_1.jpg", "/fotos", tipo=SourceType.PASTA)
    externa = _midia_solta(2, "IMG_1.jpg", "/import",
                           tipo=SourceType.APPLE_PHOTOS)
    assert escolher_principal_automatico(
        [propria, externa], {1: 2, 2: 400}
    ) is propria


def test_principal_herda_o_metadado_que_so_a_versao_tinha(migrated_engine):
    """Escolher a principal tira as versões da grade. Se o que sai levasse
    junto a única entrada de GPS do grupo, a escolha teria custado
    informação — e é a informação que este catálogo existe para guardar."""
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        session.add(Source(id=1, caminho="/fotos", tipo=SourceType.PASTA))
        for i in (1, 2):
            session.add(MediaFile(
                id=i, source_id=1, caminho=f"/fotos/{i}.jpg", pasta="/fotos",
                nome=f"{i}.jpg", extensao="jpg", tamanho=100,
            ))
        grupo = DuplicateGroup(id=1, nivel=DuplicateLevel.EXATO)
        session.add(grupo)
        session.add(DuplicateMember(group_id=1, media_id=1))
        session.add(DuplicateMember(group_id=1, media_id=2))
        # A principal sabe a câmera; só a versão sabe o GPS e o álbum.
        session.add(MetadataEntry(media_id=1, namespace="exif",
                                  chave="Model", valor="Canon R5"))
        session.add(MetadataEntry(media_id=2, namespace="apple",
                                  chave="gps", valor="-22.95,-43.17"))
        session.add(MetadataEntry(media_id=2, namespace="apple",
                                  chave="album", valor="Pantanal"))
        # Chave que as duas têm: a da principal não pode ser sobrescrita.
        session.add(MetadataEntry(media_id=2, namespace="exif",
                                  chave="Model", valor="iPhone"))
        session.commit()

    DuplicateRepository(factory).escolher_principal(1, 1)

    with factory() as session:
        entradas = {
            (e.namespace, e.chave): e.valor
            for e in session.scalars(
                select(MetadataEntry).where(MetadataEntry.media_id == 1)
            )
        }
        assert entradas[("apple", "gps")] == "-22.95,-43.17"
        assert entradas[("apple", "album")] == "Pantanal"
        assert entradas[("exif", "Model")] == "Canon R5"  # não sobrescreve
        # Nada é apagado da versão (invariante 8).
        restantes = session.scalars(
            select(MetadataEntry).where(MetadataEntry.media_id == 2)
        ).all()
        assert len(restantes) == 3


def _midia_variante(id_, nome, *, data=None, make="Canon", model="R5"):
    media = _midia_solta(id_, nome, "/fotos")
    media.extensao = nome.rsplit(".", 1)[-1].lower()
    media.data_capturada = data or datetime(2020, 5, 1, 10, 0, 0)
    media.make, media.model = make, model
    return media


def test_raw_e_jpeg_do_mesmo_clique_sao_variante_nao_duplicata():
    """O RAW é o negativo e o JPEG é a cópia de trabalho: o dono quase sempre
    quer os dois. Apresentar como duplicata pede uma escolha que está errada
    por construção — mesmo motivo pelo qual SEQUENCIA existe."""
    from fotoorganizer.duplicates.detector import _eh_variante_de_revelacao

    par = [_midia_variante(1, "IMG_1234.CR3"),
           _midia_variante(2, "IMG_1234.JPG")]
    assert _eh_variante_de_revelacao(par) is True


def test_duas_copias_do_mesmo_raw_nao_sao_variante():
    """Mesma extensão em pastas diferentes é cópia, não variante — continua
    caindo em CONTEUDO, que é onde deve cair."""
    from fotoorganizer.duplicates.detector import _eh_variante_de_revelacao

    copias = [_midia_variante(1, "IMG_1234.CR3"),
              _midia_variante(2, "IMG_1234.CR3")]
    assert _eh_variante_de_revelacao(copias) is False


def test_jpeg_e_png_sem_raw_nao_e_variante():
    """Sem RAW no grupo não há par de revelação: são dois exports."""
    from fotoorganizer.duplicates.detector import _eh_variante_de_revelacao

    exports = [_midia_variante(1, "IMG_1234.JPG"),
               _midia_variante(2, "IMG_1234.PNG")]
    assert _eh_variante_de_revelacao(exports) is False


def test_nomes_base_diferentes_nao_sao_variante():
    from fotoorganizer.duplicates.detector import _eh_variante_de_revelacao

    outros = [_midia_variante(1, "IMG_1234.CR3"),
              _midia_variante(2, "IMG_9999.JPG")]
    assert _eh_variante_de_revelacao(outros) is False


def test_variante_vence_rajada_na_classificacao():
    """Um par RAW+JPEG é sempre da mesma câmera no mesmo segundo, então
    casaria como rajada também — e 'rajada' convida a escolher o melhor
    frame, que aqui não é a pergunta."""
    from fotoorganizer.duplicates.detector import (
        _eh_rajada,
        _eh_variante_de_revelacao,
    )

    par = [_midia_variante(1, "IMG_1234.CR3"),
           _midia_variante(2, "IMG_1234.JPG")]
    assert _eh_rajada(par) is True            # casaria nos dois
    assert _eh_variante_de_revelacao(par) is True
