"""Provider do Lightroom Classic: leitura do .lrcat e falha com instrução.

O catálogo de teste é construído aqui, com o mínimo do esquema real do
Lightroom — nunca um .lrcat pessoal no repositório.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

from fotoorganizer.models import SourceType
from fotoorganizer.sources import LightroomError, LightroomProvider
from fotoorganizer.sources.lightroom import _data

_ESQUEMA = """
create table AgLibraryRootFolder (id_local integer primary key,
                                  absolutePath text, name text);
create table AgLibraryFolder (id_local integer primary key,
                              rootFolder integer, pathFromRoot text);
create table AgLibraryFile (id_local integer primary key, id_global text,
                            folder integer, baseName text, extension text);
create table Adobe_images (id_local integer primary key, rootFile integer,
                           captureTime text, rating integer, pick real);
create table AgHarvestedExifMetadata (id_local integer primary key,
                                      image integer, gpsLatitude real,
                                      gpsLongitude real);
create table AgLibraryCollection (id_local integer primary key, name text);
create table AgLibraryCollectionimage (id_local integer primary key,
                                       collection integer, image integer);
create table AgLibraryKeyword (id_local integer primary key, name text);
create table AgLibraryKeywordImage (id_local integer primary key,
                                    tag integer, image integer);
"""


def _lrcat(tmp_path: Path, **ajustes) -> Path:
    """Catálogo com duas fotos: uma em volume externo, outra local."""
    caminho = tmp_path / "Catálogo de Teste.lrcat"
    con = sqlite3.connect(caminho)
    con.executescript(_ESQUEMA)
    con.executemany(
        "insert into AgLibraryRootFolder values (?,?,?)",
        [(1, "/Volumes/photo/", "photo"), (2, "/Users/eu/Pictures/", "Pictures")],
    )
    con.executemany(
        "insert into AgLibraryFolder values (?,?,?)",
        [(10, 1, "Portfolio/Patagonia Fev.20/"), (11, 2, "2026/")],
    )
    con.executemany(
        "insert into AgLibraryFile values (?,?,?,?,?)",
        [(100, "UUID-EXTERNA", 10, "096A9198", "DNG"),
         (101, "UUID-LOCAL", 11, "ACM_8019", "CR3")],
    )
    con.executemany(
        "insert into Adobe_images values (?,?,?,?,?)",
        [(1000, 100, ajustes.get("captura", "2020-02-14T12:35:23.67"), 5, 0.0),
         (1001, 101, "2026-02-08T15:07:45.57", 1, 0.0)],
    )
    con.execute("insert into AgHarvestedExifMetadata values (1,1000,-54.9272,-67.4884)")
    con.execute("insert into AgLibraryCollection values (1,'Melhores 2020')")
    con.execute("insert into AgLibraryCollectionimage values (1,1,1000)")
    con.execute("insert into AgLibraryKeyword values (1,'patagônia')")
    con.execute("insert into AgLibraryKeywordImage values (1,1,1000)")
    con.commit()
    con.close()
    return caminho


def _por_nome(provider) -> dict:
    return {a.nome: a for a in provider.iter_assets()}


def test_le_caminho_data_gps_e_intencao(tmp_path):
    achados = _por_nome(LightroomProvider(_lrcat(tmp_path)))
    assert set(achados) == {"096A9198.DNG", "ACM_8019.CR3"}

    externa = achados["096A9198.DNG"]
    assert externa.referencia == "UUID-EXTERNA"
    assert externa.caminho_original == Path(
        "/Volumes/photo/Portfolio/Patagonia Fev.20/096A9198.DNG"
    )
    assert externa.data_capturada == datetime(2020, 2, 14, 12, 35, 23, 670000)
    assert (externa.gps_lat, externa.gps_lon) == (-54.9272, -67.4884)
    assert externa.albuns == ("Melhores 2020",)
    assert externa.palavras_chave == ("patagônia",)
    assert externa.favorito is True          # 5 estrelas


def test_nada_e_aberto_do_disco(tmp_path):
    """A foto pode estar num volume desmontado — e é justamente aí que este
    provider vale. Abrir o arquivo derrubaria a leitura inteira."""
    for asset in LightroomProvider(_lrcat(tmp_path)).iter_assets():
        assert asset.caminho is None
        assert asset.referencia


def test_nota_baixa_nao_e_favorito(tmp_path):
    """1 estrela é material de trabalho; 4 e 5 são o corte de portfólio."""
    assert _por_nome(LightroomProvider(_lrcat(tmp_path)))[
        "ACM_8019.CR3"].favorito is False


def test_catalogo_inexistente_diz_o_que_houve(tmp_path):
    with pytest.raises(LightroomError, match="não encontrado"):
        list(LightroomProvider(tmp_path / "nao_existe.lrcat").iter_assets())


def test_arquivo_que_nao_e_catalogo_ensina_a_resolver(tmp_path):
    falso = tmp_path / "Isto nao e um catalogo.lrcat"
    falso.write_bytes(b"nem sqlite isto e")
    with pytest.raises(LightroomError, match="Lightroom Classic"):
        list(LightroomProvider(falso).iter_assets())


def test_tabela_auxiliar_ausente_nao_derruba_o_mapa(tmp_path):
    """Versões diferentes do Lightroom trocam tabelas de lugar. Perder as
    coleções é aceitável; perder as 54 mil fotos não é."""
    caminho = _lrcat(tmp_path)
    con = sqlite3.connect(caminho)
    con.execute("drop table AgLibraryCollectionimage")
    con.commit()
    con.close()

    achados = _por_nome(LightroomProvider(caminho))
    assert len(achados) == 2
    assert achados["096A9198.DNG"].albuns == ()
    # As palavras-chave, que vêm de outra consulta, sobrevivem.
    assert achados["096A9198.DNG"].palavras_chave == ("patagônia",)


def test_identidade_e_o_arquivo_do_catalogo(tmp_path):
    provider = LightroomProvider(_lrcat(tmp_path))
    assert provider.tipo is SourceType.LIGHTROOM
    assert provider.raiz.name.endswith(".lrcat")
    assert "Catálogo de Teste" in provider.apelido


@pytest.mark.parametrize("bruto,esperado", [
    ("2020-02-14T12:35:23.67", datetime(2020, 2, 14, 12, 35, 23, 670000)),
    ("2020-02-14T12:35:23", datetime(2020, 2, 14, 12, 35, 23)),
    ("2020-02-14", datetime(2020, 2, 14)),
    ("2020-02-14T12:35:23Z", datetime(2020, 2, 14, 12, 35, 23)),
    ("", None), (None, None), ("data estranha", None),
])
def test_formatos_de_data_do_lightroom(bruto, esperado):
    assert _data(bruto) == esperado


def test_referencia_importada_e_testemunha_no_catalogo(tmp_path, migrated_engine):
    """`papel` e `arquivo_ausente` são ortogonais, menos numa direção: quem
    não tem arquivo local não pode ser acervo — não há o que mostrar na
    grade nem o que copiar no plano.

    Na primeira importação real, 54.086 referências do Lightroom entraram
    dizendo `ACERVO` e "sem arquivo" ao mesmo tempo.
    """
    from sqlalchemy import select
    from fotoorganizer.database import create_session_factory
    from fotoorganizer.metadata import PurePythonExtractor
    from fotoorganizer.models import MediaFile, MediaRole
    from fotoorganizer.config.settings import ScannerSettings
    from fotoorganizer.sources import ExternalCatalogImporter

    factory = create_session_factory(migrated_engine)
    importer = ExternalCatalogImporter(
        factory, PurePythonExtractor(), ScannerSettings()
    )
    importer.importar(LightroomProvider(_lrcat(tmp_path)))

    with factory() as session:
        refs = list(session.scalars(
            select(MediaFile).where(MediaFile.caminho.like("lightroom://%"))
        ))
        assert len(refs) == 2
        for media in refs:
            assert media.arquivo_ausente is True
            assert media.papel is MediaRole.SINAL
            assert media.organizavel is False
        # A pasta de origem sobrevive: é o que responde "de que disco veio?"
        externa = next(m for m in refs if m.nome == "096A9198.DNG")
        assert externa.pasta == "/Volumes/photo/Portfolio/Patagonia Fev.20"


def _lrcat_com_nulos(tmp_path: Path) -> Path:
    """Catálogo com os três pedaços de caminho que faltam na vida real.

    Regressão do defeito da concatenação em SQL: `a || b` é NULL se qualquer
    parte for NULL, então uma extensão ausente apagava o caminho inteiro — e
    a referência perdia a única pista de lugar que tinha, sem erro nem log.
    """
    caminho = tmp_path / "Nulos.lrcat"
    con = sqlite3.connect(caminho)
    con.executescript(_ESQUEMA)
    con.execute("insert into AgLibraryRootFolder values (1,'/Volumes/Ext/','Ext')")
    con.execute("insert into AgLibraryRootFolder values (2,NULL,'Sem raiz')")
    con.executemany(
        "insert into AgLibraryFolder values (?,?,?)",
        [(1, 1, "2020/"), (2, 1, None), (3, 2, "2021/")],
    )
    con.executemany(
        "insert into AgLibraryFile values (?,?,?,?,?)",
        [
            (1, "U-SEM-EXT", 1, "IMG_1", None),      # extensão ausente
            (2, "U-NA-RAIZ", 2, "IMG_2", "jpg"),     # pathFromRoot ausente
            (3, "U-SEM-RAIZ", 3, "IMG_3", "jpg"),    # absolutePath ausente
            (4, "U-INTEIRA", 1, "IMG_4", "cr3"),     # completa
        ],
    )
    con.executemany(
        "insert into Adobe_images values (?,?,?,?,?)",
        [(i, i, "2020-01-0%dT10:00:00" % i, 0, 0) for i in range(1, 5)],
    )
    con.commit()
    con.close()
    return caminho


def test_extensao_ausente_nao_apaga_o_caminho(tmp_path):
    achados = {
        a.referencia: a
        for a in LightroomProvider(_lrcat_com_nulos(tmp_path)).iter_assets()
    }
    assert len(achados) == 4  # nenhuma some

    sem_ext = achados["U-SEM-EXT"]
    assert sem_ext.nome == "IMG_1"
    assert sem_ext.caminho_original == Path("/Volumes/Ext/2020/IMG_1")


def test_foto_na_raiz_do_volume_mantem_o_caminho(tmp_path):
    na_raiz = {
        a.referencia: a
        for a in LightroomProvider(_lrcat_com_nulos(tmp_path)).iter_assets()
    }["U-NA-RAIZ"]
    assert na_raiz.caminho_original == Path("/Volumes/Ext/IMG_2.jpg")


def test_sem_volume_perde_o_lugar_mas_nao_o_nome(tmp_path):
    """Sem `absolutePath` não há lugar — mas nome, data e GPS continuam
    valendo para a correlação. Perder a linha inteira seria pior."""
    sem_raiz = {
        a.referencia: a
        for a in LightroomProvider(_lrcat_com_nulos(tmp_path)).iter_assets()
    }["U-SEM-RAIZ"]
    assert sem_raiz.caminho_original is None
    assert sem_raiz.nome == "IMG_3.jpg"


def test_avisa_quantas_referencias_ficaram_sem_lugar(tmp_path, caplog):
    with caplog.at_level("WARNING"):
        list(LightroomProvider(_lrcat_com_nulos(tmp_path)).iter_assets())
    assert "1 itens sem caminho reconstruível" in caplog.text
