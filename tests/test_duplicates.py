import shutil
from datetime import datetime, timedelta

import pytest
from PIL import Image
from sqlalchemy import select

from fotoorganizer.config.settings import ScannerSettings
from fotoorganizer.database import create_session_factory
from fotoorganizer.duplicates import BKTree, DuplicateDetector, distancia_hamming
from fotoorganizer.metadata import PurePythonExtractor
from fotoorganizer.models import (
    DuplicateGroup,
    DuplicateLevel,
    DuplicateRole,
    MediaFile,
    Source,
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


def test_bytes_recuperaveis(ambiente):
    factory, detector, fotos = ambiente
    detector.detectar()
    repo = DuplicateRepository(factory)
    grupo = next(g for g in repo.listar_grupos()
                 if g.nivel == DuplicateLevel.EXATO)
    tamanhos = sorted((m.tamanho for m in grupo.membros), reverse=True)
    assert grupo.bytes_recuperaveis == sum(tamanhos[1:]) > 0
