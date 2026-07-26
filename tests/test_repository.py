from datetime import datetime

import pytest

from fotoorganizer.database import create_session_factory
from fotoorganizer.models import MediaFile, Source
from fotoorganizer.repositories import MediaFilters, MediaRepository


@pytest.fixture()
def repo(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte_a = Source(caminho="/fotos/a")
        fonte_b = Source(caminho="/fotos/b")
        session.add_all([fonte_a, fonte_b])
        session.flush()
        dados = [
            ("praia.jpg", "jpg", fonte_a.id, datetime(2024, 5, 4), 100),
            ("montanha.jpg", "jpg", fonte_a.id, datetime(2023, 1, 1), 300),
            ("cidade.png", "png", fonte_b.id, datetime(2024, 7, 10), 200),
            ("sem_data.heic", "heic", fonte_b.id, None, 50),
        ]
        for nome, ext, source_id, data, tamanho in dados:
            session.add(
                MediaFile(
                    source_id=source_id, caminho=f"/fotos/{nome}", pasta="/fotos",
                    nome=nome, extensao=ext, tamanho=tamanho, data_capturada=data,
                    erro_leitura="falhou" if nome == "sem_data.heic" else None,
                )
            )
        session.commit()
    return MediaRepository(factory)


def test_listar_ordenado_por_data_desc(repo):
    nomes = [m.nome for m in repo.listar(MediaFilters(), limit=10, offset=0)]
    # Mais recentes primeiro; sem data vai para o fim (nulls_last).
    assert nomes == ["cidade.png", "praia.jpg", "montanha.jpg", "sem_data.heic"]


def test_paginacao(repo):
    pagina1 = repo.listar(MediaFilters(), limit=2, offset=0)
    pagina2 = repo.listar(MediaFilters(), limit=2, offset=2)
    assert len(pagina1) == 2 and len(pagina2) == 2
    assert {m.nome for m in pagina1}.isdisjoint({m.nome for m in pagina2})


def test_filtro_busca(repo):
    achados = repo.listar(MediaFilters(busca="prai"), limit=10, offset=0)
    assert [m.nome for m in achados] == ["praia.jpg"]


def test_filtro_extensao_e_contagem(repo):
    assert repo.contar(MediaFilters(extensao="jpg")) == 2
    assert repo.contar(MediaFilters(extensao="png")) == 1


def test_filtro_ano(repo):
    assert repo.contar(MediaFilters(ano=2024)) == 2
    assert repo.contar(MediaFilters(ano=2023)) == 1


def test_filtro_fonte(repo):
    fontes = repo.fontes_com_contagem()
    assert [(s.caminho, n) for s, n in fontes] == [("/fotos/a", 2), ("/fotos/b", 2)]
    source_a_id = fontes[0][0].id
    assert repo.contar(MediaFilters(source_id=source_a_id)) == 2


def test_anos_e_extensoes(repo):
    assert repo.anos() == [2024, 2023]
    assert repo.extensoes() == ["heic", "jpg", "png"]


def test_estatisticas(repo):
    stats = repo.estatisticas()
    assert stats == {
        "total": 4, "erros": 1, "fontes": 2,
        "referencias": 0, "referencias_com_gps": 0,
    }


def test_ordenacao_tamanho(repo):
    maiores = repo.listar(MediaFilters(ordenacao="tamanho_desc"), 10, 0)
    assert [m.tamanho for m in maiores] == [300, 200, 100, 50]
