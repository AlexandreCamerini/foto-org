from pathlib import Path

import pytest
from sqlalchemy import select

from fotoorganizer.config.settings import Settings, load_settings
from fotoorganizer.database import create_session_factory
from fotoorganizer.faces import NullFaceProvider
from fotoorganizer.models import FaceEmbedding, FaceOccurrence, FaceState, Person
from fotoorganizer.repositories.people import PeopleRepository
from fotoorganizer.security.crypto import EmbeddingCipher, FileKeyStore
from fotoorganizer.vision import NullVisionProvider


# -- criptografia -------------------------------------------------------------
def test_cifra_e_decifra_embedding(tmp_path):
    cipher = EmbeddingCipher(FileKeyStore(tmp_path))
    vetor = [0.1, -0.5, 0.99]
    blob = cipher.cifrar(vetor)
    assert b"0.1" not in blob  # nada em claro
    assert cipher.decifrar(blob) == vetor


def test_chave_persiste_com_permissao_restrita(tmp_path):
    store = FileKeyStore(tmp_path)
    chave1 = store.obter_ou_criar_chave()
    chave2 = FileKeyStore(tmp_path).obter_ou_criar_chave()
    assert chave1 == chave2
    assert (tmp_path / "embeddings.key").stat().st_mode & 0o777 == 0o600


# -- pessoas ---------------------------------------------------------------
@pytest.fixture()
def repo(migrated_engine, tmp_path):
    from fotoorganizer.models import MediaFile, Source

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        media = MediaFile(
            source_id=fonte.id, caminho="/fotos/retrato.jpg", pasta="/fotos",
            nome="retrato.jpg", extensao="jpg", tamanho=1,
        )
        session.add(media)
        session.commit()
        media_id = media.id
    cipher = EmbeddingCipher(FileKeyStore(tmp_path))
    return PeopleRepository(factory, cipher), factory, media_id


def test_cadastro_e_embedding_cifrado_em_repouso(repo):
    people, factory, _media_id = repo
    ana = people.criar_pessoa("Ana", relacao="familiar")
    people.adicionar_embedding(ana, [1.0, 2.0, 3.0], modelo="stub-v0")

    # No banco, só bytes cifrados.
    with factory() as session:
        blob = session.scalar(select(FaceEmbedding.blob_criptografado))
        assert b"1.0" not in blob and b"[" not in blob
    # Pela API, o vetor volta.
    assert people.embeddings_de(ana) == [[1.0, 2.0, 3.0]]


def test_apagar_pessoa_remove_todos_os_vestigios(repo):
    people, factory, media_id = repo
    ana = people.criar_pessoa("Ana")
    people.adicionar_embedding(ana, [1.0], modelo="stub-v0")
    occ = people.registrar_deteccao(media_id=media_id)
    people.associar_manual(occ, ana)

    people.apagar_pessoa(ana)

    with factory() as session:
        assert session.scalars(select(Person)).all() == []
        assert session.scalars(select(FaceEmbedding)).all() == []
        assert session.scalars(select(FaceOccurrence)).all() == []


def test_associacao_manual_e_correcao(repo):
    people, factory, media_id = repo
    ana = people.criar_pessoa("Ana", relacao="familiar")
    occ = people.registrar_deteccao(media_id=media_id,
                                    bbox={"x": 0.1, "y": 0.2,
                                          "w": 0.3, "h": 0.3})
    # Detecção NÃO associa ninguém.
    with factory() as session:
        registro = session.get(FaceOccurrence, occ)
        assert registro.estado == FaceState.DETECTADO
        assert registro.person_id is None

    people.associar_manual(occ, ana)
    assert people.ocorrencias_confirmadas(media_id) == [(ana, "Ana")]

    people.marcar_incorreto(occ)
    assert people.ocorrencias_confirmadas(media_id) == []


# -- stubs e defaults -------------------------------------------------------
def test_stubs_sao_locais_e_inertes(tmp_path):
    visao = NullVisionProvider()
    assert visao.local is True
    assert visao.analisar(tmp_path / "x.jpg") is None

    rostos = NullFaceProvider()
    assert rostos.local is True
    assert rostos.detectar(tmp_path / "x.jpg") == []
    assert rostos.similaridade([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert rostos.similaridade([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_recursos_sensiveis_desligados_por_padrao(tmp_path):
    settings = load_settings(tmp_path / "nao_existe.toml")
    assert settings.privacidade.servicos_externos is False
    assert settings.privacidade.reconhecimento_facial is False


# -- manutenção ----------------------------------------------------------------
def test_remover_catalogo_preserva_fotos(tmp_path):
    from fotoorganizer.app.maintenance import limpar_cache, remover_catalogo
    from fotoorganizer.database import upgrade_to_head

    settings = Settings(data_dir=tmp_path / "dados", cache_dir=tmp_path / "cache")
    settings.ensure_dirs()
    upgrade_to_head(settings.db_path)
    (settings.cache_dir / "thumbs").mkdir(parents=True)
    (settings.cache_dir / "thumbs" / "t.jpg").write_bytes(b"thumb")
    FileKeyStore(settings.data_dir).obter_ou_criar_chave()

    foto = tmp_path / "minhas_fotos" / "importante.jpg"
    foto.parent.mkdir()
    foto.write_bytes(b"original precioso")

    limpar_cache(settings)
    assert not (settings.cache_dir / "thumbs").exists()

    remover_catalogo(settings)
    assert not settings.db_path.exists()
    assert not (settings.data_dir / "embeddings.key").exists()
    # A foto original está intocada.
    assert foto.read_bytes() == b"original precioso"
