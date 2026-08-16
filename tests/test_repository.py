from datetime import datetime

import pytest

from fotoorganizer.database import create_session_factory
from fotoorganizer.models import MediaFile, MediaRole, Source
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


@pytest.fixture()
def repo_com_testemunha(migrated_engine):
    """Fonte disponível com quatro registros: acervo com arquivo, acervo sem
    arquivo, referência externa (SINAL sem arquivo local — ex. Apple Fotos
    iCloud-only, a feature do commit 1b125f7) e testemunha com arquivo local
    real (SINAL com arquivo — miniatura/derivado dentro de pacote, o caso
    medido em docs/AVALIACAO_UX.md §C.2). Fixture dedicada — `repo` não tem
    SINAL nem ausente e é reaproveitada por vários testes de ordenação que
    não devem mudar de forma."""
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = Source(caminho="/fotos/c")
        session.add(fonte)
        session.flush()
        session.add_all([
            MediaFile(
                source_id=fonte.id, caminho="/fotos/c/acervo_ok.jpg",
                pasta="/fotos/c", nome="acervo_ok.jpg", extensao="jpg",
                tamanho=100,
            ),
            MediaFile(
                source_id=fonte.id, caminho="/fotos/c/acervo_ausente.jpg",
                pasta="/fotos/c", nome="acervo_ausente.jpg", extensao="jpg",
                tamanho=0, arquivo_ausente=True,
            ),
            MediaFile(
                source_id=fonte.id, caminho="apple://UUID-1",
                pasta="/fotos/c", nome="referencia_externa.jpg",
                extensao="jpg", tamanho=0,
                arquivo_ausente=True, papel=MediaRole.SINAL,
            ),
            MediaFile(
                source_id=fonte.id,
                caminho="/fotos/c/testemunha_com_arquivo.jpg",
                pasta="/fotos/c", nome="testemunha_com_arquivo.jpg",
                extensao="jpg", tamanho=50, papel=MediaRole.SINAL,
            ),
        ])
        session.commit()
    return MediaRepository(factory)


def test_alcance_tudo_inclui_acervo_e_referencia_sem_testemunha_com_arquivo(
    repo_com_testemunha,
):
    # acervo_ok + acervo_ausente + referencia_externa; testemunha_com_arquivo
    # (papel=SINAL, arquivo local real) fica fora — é o próprio BUG-03.
    # referencia_externa (papel=SINAL, sem arquivo local) continua dentro —
    # é a feature do commit 1b125f7 (referência do iCloud não "some" da
    # grade e faz o import parecer que "o sistema esqueceu").
    assert repo_com_testemunha.contar(MediaFilters(alcance="tudo")) == 3
    nomes_tudo = [
        m.nome for m in
        repo_com_testemunha.listar(MediaFilters(alcance="tudo"), 10, 0)
    ]
    assert "testemunha_com_arquivo.jpg" not in nomes_tudo
    assert "referencia_externa.jpg" in nomes_tudo


def test_alcance_organizaveis_inalterado(repo_com_testemunha):
    assert repo_com_testemunha.contar(MediaFilters(alcance="organizaveis")) == 1


def test_alcance_faltantes_inclui_os_dois_tipos_de_testemunha(
    repo_com_testemunha,
):
    # Não-objetivo travado (ver <phase_scope> do plano): ALCANCES["faltantes"]
    # promete "não é acervo", e os dois tipos de SINAL são exatamente isso —
    # tirá-los daqui contradiria o próprio rótulo. `faltantes` não muda
    # nesta fase.
    assert repo_com_testemunha.contar(MediaFilters(alcance="faltantes")) == 3
    nomes_faltantes = [
        m.nome for m in
        repo_com_testemunha.listar(MediaFilters(alcance="faltantes"), 10, 0)
    ]
    assert "testemunha_com_arquivo.jpg" in nomes_faltantes
    assert "referencia_externa.jpg" in nomes_faltantes
