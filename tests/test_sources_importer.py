"""Fontes tipadas e importador de catálogos externos (F1 do M8)."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select

from fotoorganizer.config.settings import ScannerSettings
from fotoorganizer.database import create_session_factory
from fotoorganizer.metadata import PurePythonExtractor
from fotoorganizer.models import MediaFile, MetadataEntry, Source, SourceType
from fotoorganizer.sources import (
    ExternalAsset,
    ExternalCatalogImporter,
    ImportMetrics,
)
from tests.fixtures import make_jpeg


class FakeProvider:
    """Provider mínimo: catálogo externo com 2 fotos e metadados ricos."""

    def __init__(self, raiz: Path, assets: list[ExternalAsset]) -> None:
        self._raiz = raiz
        self._assets = assets

    @property
    def tipo(self) -> SourceType:
        return SourceType.GOOGLE_TAKEOUT

    @property
    def raiz(self) -> Path:
        return self._raiz

    @property
    def apelido(self) -> str:
        return "Google Takeout (teste)"

    def iter_assets(self):
        yield from self._assets


@pytest.fixture()
def importer(migrated_engine):
    factory = create_session_factory(migrated_engine)
    return factory, ExternalCatalogImporter(
        factory, PurePythonExtractor(), ScannerSettings()
    )


def test_fonte_padrao_e_pasta(migrated_engine):
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        session.add(Source(caminho="/qualquer"))
        session.commit()
        source = session.scalars(select(Source)).one()
        assert source.tipo == SourceType.PASTA


def test_importa_e_funde_metadados(importer, tmp_path):
    factory, imp = importer
    # Foto SEM data EXIF e sem GPS — o catálogo externo tem os dois.
    foto = make_jpeg(tmp_path / "takeout" / "praia.jpg", data_exif=None)
    asset = ExternalAsset(
        caminho=foto,
        data_capturada=datetime(2025, 11, 2, 15, 30),
        gps_lat=25.2048, gps_lon=55.2708,
        titulo="Praia em Dubai", favorito=True,
        albuns=("Viagem 2025",),
    )
    metrics = imp.importar(FakeProvider(tmp_path / "takeout", [asset]))

    assert metrics.importados == 1 and metrics.erros == 0
    with factory() as session:
        source = session.scalars(select(Source)).one()
        assert source.tipo == SourceType.GOOGLE_TAKEOUT
        media = session.scalars(select(MediaFile)).one()
        # Lacunas preenchidas pelo catálogo externo:
        assert media.data_capturada == datetime(2025, 11, 2, 15, 30)
        assert media.gps_lat == pytest.approx(25.2048)
        entradas = {
            (e.chave, e.valor)
            for e in session.scalars(select(MetadataEntry).where(
                MetadataEntry.namespace == "google"
            ))
        }
        assert ("titulo", "Praia em Dubai") in entradas
        assert ("favorito", "true") in entradas
        assert ("album", "Viagem 2025") in entradas


def test_exif_do_arquivo_vence_o_catalogo_externo(importer, tmp_path):
    factory, imp = importer
    # Foto COM data EXIF — a data divergente do catálogo NÃO sobrescreve.
    foto = make_jpeg(tmp_path / "t" / "com_exif.jpg",
                     data_exif="2024:05:04 10:30:00")
    asset = ExternalAsset(
        caminho=foto, data_capturada=datetime(2020, 1, 1, 0, 0),
    )
    imp.importar(FakeProvider(tmp_path / "t", [asset]))

    with factory() as session:
        media = session.scalars(select(MediaFile)).one()
        assert media.data_capturada == datetime(2024, 5, 4, 10, 30)


# -- os dois instantes (hora de parede + instante absoluto) -----------------
def test_arquivo_sem_data_herda_o_par_inteiro_do_catalogo_externo(
    importer, tmp_path
):
    """Lacuna do arquivo preenchida pelo catálogo externo: os dois instantes
    vêm juntos, da MESMA origem. Nunca a hora de um com o fuso do outro."""
    factory, imp = importer
    foto = make_jpeg(tmp_path / "t" / "sem_exif.jpg", data_exif=None)
    asset = ExternalAsset(
        caminho=foto,
        data_capturada=datetime(2019, 7, 14, 14, 0),      # parede, em Roma
        data_capturada_utc=datetime(2019, 7, 14, 12, 0),  # absoluto
    )
    imp.importar(FakeProvider(tmp_path / "t", [asset]))

    with factory() as session:
        media = session.scalars(select(MediaFile)).one()
        assert media.data_capturada == datetime(2019, 7, 14, 14, 0)
        assert media.data_capturada_utc == datetime(2019, 7, 14, 12, 0)


def test_fuso_do_catalogo_vale_quando_a_hora_de_parede_bate_com_o_exif(
    importer, tmp_path
):
    """O caso que dá o ganho: o arquivo diz a hora, o Apple Fotos diz o fuso.
    Concordando na hora de parede, é a mesma captura descrita duas vezes.

    O subsegundo do catálogo externo é de propósito e não é enfeite: o Apple
    Fotos guarda a data com microssegundo (65% das 44.661 linhas do acervo
    real) e o EXIF trunca no segundo. Com igualdade exata em vez de
    tolerância, o fuso medido seria descartado em quase toda foto — e em
    silêncio, porque não há coluna de offset onde a perda apareceria.

    O que se empresta é o OFFSET, aplicado à hora do arquivo: a diferença
    entre as duas colunas tem de dar duas horas cravadas, não 1h59min59,184s.
    """
    factory, imp = importer
    foto = make_jpeg(tmp_path / "t" / "com_exif.jpg",
                     data_exif="2019:07:14 14:00:00")
    asset = ExternalAsset(
        caminho=foto,
        data_capturada=datetime(2019, 7, 14, 14, 0, 0, 816000),
        data_capturada_utc=datetime(2019, 7, 14, 12, 0, 0, 816000),
    )
    imp.importar(FakeProvider(tmp_path / "t", [asset]))

    with factory() as session:
        media = session.scalars(select(MediaFile)).one()
        assert media.data_capturada == datetime(2019, 7, 14, 14, 0)
        assert media.data_capturada_utc == datetime(2019, 7, 14, 12, 0)
        offset = media.data_capturada - media.data_capturada_utc
        assert offset == timedelta(hours=2)


def test_hora_de_parede_divergente_nao_empresta_o_fuso_do_catalogo(
    importer, tmp_path
):
    """Data editada no catálogo externo: o arquivo manda, como sempre, e o
    offset volta a ser desconhecido (os dois instantes iguais). Casar a hora
    do arquivo com o absoluto do catálogo inventaria um fuso de 5 horas que
    ninguém mediu — e, sem coluna de offset, a mentira seria invisível."""
    factory, imp = importer
    foto = make_jpeg(tmp_path / "t" / "editada.jpg",
                     data_exif="2024:05:04 10:30:00")
    asset = ExternalAsset(
        caminho=foto,
        data_capturada=datetime(2020, 1, 1, 0, 0),
        data_capturada_utc=datetime(2020, 1, 1, 5, 0),
    )
    imp.importar(FakeProvider(tmp_path / "t", [asset]))

    with factory() as session:
        media = session.scalars(select(MediaFile)).one()
        assert media.data_capturada == datetime(2024, 5, 4, 10, 30)
        assert media.data_capturada_utc == datetime(2024, 5, 4, 10, 30)


def test_referencia_guarda_o_fuso_quando_o_catalogo_externo_sabe(
    importer, tmp_path
):
    factory, imp = importer
    imp.importar(FakeProvider(tmp_path / "t", [ExternalAsset(
        caminho=None, referencia="UUID-TZ",
        data_capturada=datetime(2019, 7, 14, 14, 0),
        data_capturada_utc=datetime(2019, 7, 14, 12, 0),
    )]))

    with factory() as session:
        media = session.scalars(select(MediaFile)).one()
        assert media.data_capturada == datetime(2019, 7, 14, 14, 0)
        assert media.data_capturada_utc == datetime(2019, 7, 14, 12, 0)


def test_referencia_sem_fuso_iguala_os_dois_e_nunca_deixa_o_absoluto_nulo(
    importer, tmp_path
):
    """A garantia que vale para linha nova, não só para o backfill: hora
    local preenchida e instante absoluto nulo diria "não sei quando", que é
    outra coisa — e bem pior — do que "não sei o fuso"."""
    factory, imp = importer
    imp.importar(FakeProvider(tmp_path / "t", [ExternalAsset(
        caminho=None, referencia="UUID-SEM-TZ",
        data_capturada=datetime(2019, 7, 14, 14, 0),
    )]))

    with factory() as session:
        media = session.scalars(select(MediaFile)).one()
        assert media.data_capturada_utc == media.data_capturada
        assert media.data_capturada_utc == datetime(2019, 7, 14, 14, 0)


@pytest.mark.parametrize("desvio_ms, empresta", [
    (999, True),    # subsegundo: mesma captura, precisão diferente
    (1000, False),  # um segundo cravado: já é outra data, arquivo manda
])
def test_fronteira_da_tolerancia_de_um_segundo(
    importer, tmp_path, desvio_ms, empresta
):
    """A tolerância existe só para absorver precisão (Apple grava com
    microssegundo, EXIF trunca no segundo) — não é folga de relógio. Um
    segundo cravado já é outra data, e aí o arquivo manda sozinho."""
    factory, imp = importer
    foto = make_jpeg(tmp_path / "t" / f"f{desvio_ms}.jpg",
                     data_exif="2019:07:14 14:00:00")
    local = datetime(2019, 7, 14, 14, 0) + timedelta(milliseconds=desvio_ms)
    imp.importar(FakeProvider(tmp_path / "t", [ExternalAsset(
        caminho=foto,
        data_capturada=local,
        data_capturada_utc=local - timedelta(hours=2),
    )]))

    with factory() as session:
        media = session.scalars(select(MediaFile)).one()
        esperado = (
            datetime(2019, 7, 14, 12, 0) if empresta
            else datetime(2019, 7, 14, 14, 0)  # igual à local: desconhecido
        )
        assert media.data_capturada_utc == esperado


@pytest.mark.parametrize("offset, nome", [
    (timedelta(hours=-3), "Rio, negativo"),
    (timedelta(hours=5, minutes=30), "Índia, meia hora"),
    (timedelta(hours=5, minutes=45), "Nepal, quarto de hora"),
    (timedelta(hours=-9, minutes=-30), "Marquesas, negativo e meia hora"),
])
def test_offsets_que_nao_sao_hora_cheia_sobrevivem_ao_par(
    importer, tmp_path, offset, nome
):
    """O offset nunca é coluna, então ele só sobrevive se a diferença entre
    as duas datas for exata. Fuso de meia hora e de quarto de hora existe, e
    é onde arredondamento silencioso apareceria primeiro."""
    factory, imp = importer
    foto = make_jpeg(tmp_path / "t" / f"{abs(offset.total_seconds())}.jpg",
                     data_exif=None)
    local = datetime(2019, 7, 14, 14, 0)
    imp.importar(FakeProvider(tmp_path / "t", [ExternalAsset(
        caminho=foto, data_capturada=local, data_capturada_utc=local - offset,
    )]))

    with factory() as session:
        media = session.scalars(select(MediaFile)).one()
        derivado = media.data_capturada - media.data_capturada_utc
        assert derivado == offset, nome


def test_fuso_zero_real_fica_indistinguivel_de_desconhecido(
    importer, tmp_path
):
    """Limitação aceita e documentada (D-038): Londres no inverno tem offset
    +00:00 de verdade, e o par fica idêntico ao de quem não sabe o fuso. A
    saída não é uma terceira coluna — é `tz_estimado`, na fase 11. O teste
    existe para que a limitação seja uma escolha registrada, não uma
    surpresa de quem for mexer nisso depois."""
    factory, imp = importer
    foto = make_jpeg(tmp_path / "t" / "londres.jpg", data_exif=None)
    local = datetime(2019, 1, 14, 14, 0)
    imp.importar(FakeProvider(tmp_path / "t", [ExternalAsset(
        caminho=foto,
        data_capturada=local,
        data_capturada_utc=local,  # offset real de +00:00
    )]))

    with factory() as session:
        media = session.scalars(select(MediaFile)).one()
        assert media.data_capturada_utc == media.data_capturada


def test_reimportar_referencia_ganha_o_fuso_que_antes_era_descartado(
    importer, tmp_path
):
    """O caminho de correção que a migração 0014 promete: linha gravada antes
    desta fatia (os dois instantes iguais, "fuso desconhecido") passa a ter o
    fuso real na reimportação. Vale para REFERÊNCIA, que é reescrita a cada
    import — as 44.661 linhas do Apple Fotos no acervo real são todas assim.
    Asset com arquivo local é pulado por assinatura inalterada e só se
    atualiza quando o arquivo mudar."""
    factory, imp = importer
    antes = ExternalAsset(
        caminho=None, referencia="UUID-1",
        data_capturada=datetime(2019, 7, 14, 14, 0),
    )
    depois = ExternalAsset(
        caminho=None, referencia="UUID-1",
        data_capturada=datetime(2019, 7, 14, 14, 0),
        data_capturada_utc=datetime(2019, 7, 14, 12, 0),
    )
    imp.importar(FakeProvider(tmp_path / "t", [antes]))
    with factory() as session:
        media = session.scalars(select(MediaFile)).one()
        assert media.data_capturada_utc == media.data_capturada

    imp.importar(FakeProvider(tmp_path / "t", [depois]))
    with factory() as session:
        media = session.scalars(select(MediaFile)).one()
        assert media.data_capturada_utc == datetime(2019, 7, 14, 12, 0)


def test_asset_sem_hora_de_parede_nao_ganha_instante_absoluto(
    importer, tmp_path
):
    """O espelho da regra: absoluto preenchido com local nula diria "sei
    quando, mas não que horas eram". Nenhum provider faz isso hoje, e
    `ExternalAsset` não impede que um futuro faça."""
    factory, imp = importer
    foto = make_jpeg(tmp_path / "t" / "sem_data.jpg", data_exif=None)
    imp.importar(FakeProvider(tmp_path / "t", [ExternalAsset(
        caminho=foto,
        data_capturada=None,
        data_capturada_utc=datetime(2019, 7, 14, 12, 0),
    )]))

    with factory() as session:
        media = session.scalars(select(MediaFile)).one()
        assert media.data_capturada is None
        assert media.data_capturada_utc is None


def test_data_implausivel_de_referencia_sai_das_duas_colunas_junto(
    importer, tmp_path
):
    """O `.lrcat` do dono trazia um registro datado de 2100. Guardá-lo só no
    absoluto trocaria o problema de coluna em vez de resolvê-lo.

    Só o caminho de REFERÊNCIA: `_gravar` (asset com arquivo real) nunca
    filtrou data implausível, nem antes nem depois desta fatia."""
    factory, imp = importer
    imp.importar(FakeProvider(tmp_path / "t", [ExternalAsset(
        caminho=None, referencia="UUID-2100",
        data_capturada=datetime(2100, 1, 1, 12, 0),
        data_capturada_utc=datetime(2100, 1, 1, 15, 0),
    )]))

    with factory() as session:
        media = session.scalars(select(MediaFile)).one()
        assert media.data_capturada is None
        assert media.data_capturada_utc is None


def test_reimportar_e_idempotente(importer, tmp_path):
    factory, imp = importer
    foto = make_jpeg(tmp_path / "t" / "a.jpg")
    asset = ExternalAsset(caminho=foto, titulo="Um título")
    provider = FakeProvider(tmp_path / "t", [asset])

    imp.importar(provider)
    metrics = imp.importar(provider)

    assert metrics.pulados == 1 and metrics.importados == 0
    with factory() as session:
        assert len(session.scalars(select(MediaFile)).all()) == 1
        assert len(session.scalars(select(Source)).all()) == 1
        titulos = session.scalars(select(MetadataEntry).where(
            MetadataEntry.chave == "titulo"
        )).all()
        assert len(titulos) == 1  # namespace regravado, não duplicado


def test_arquivo_inacessivel_conta_erro_e_segue(importer, tmp_path):
    factory, imp = importer
    boa = make_jpeg(tmp_path / "t" / "boa.jpg")
    metrics = imp.importar(FakeProvider(tmp_path / "t", [
        ExternalAsset(caminho=tmp_path / "t" / "sumida.jpg"),
        ExternalAsset(caminho=boa),
    ]))
    assert metrics.erros == 1
    assert metrics.importados == 1


# -- referências sem arquivo local (biblioteca em iCloud) --------------------
def test_referencia_aparece_na_biblioteca_e_fica_fora_do_organizavel(
    importer, tmp_path
):
    """Foto só na nuvem não tem arquivo, mas tem horário e GPS. Ela entra
    para doar correlação e não aparece na grade — não há o que abrir."""
    from fotoorganizer.repositories import MediaRepository
    from fotoorganizer.repositories.media import MediaFilters

    factory, imp = importer
    referencia = ExternalAsset(
        caminho=None, referencia="UUID-1",
        data_capturada=datetime(2025, 11, 1, 9, 30),
        gps_lat=25.2, gps_lon=55.3, titulo="Do iPhone",
    )
    metrics = imp.importar(FakeProvider(tmp_path / "t", [referencia]))
    assert metrics.importados == 1

    with factory() as session:
        media = session.scalars(select(MediaFile)).one()
        assert media.arquivo_ausente is True
        assert media.gps_lat == 25.2
        assert media.tamanho == 0 and media.hash_rapido is None
        assert media.caminho == "google://UUID-1"

    repo = MediaRepository(factory)
    # Visível, e não organizável — são coisas diferentes. Antes a referência
    # sumia da grade, e o dono, que mandou o app ler a biblioteca do Apple
    # Fotos e viu 44.661 fotos virarem "(0)", descreveu isso como "o sistema
    # esquece". Ela aparece marcada pelo que é; a revisão e o plano de cópia
    # continuam vendo só o que tem arquivo.
    assert repo.contar(MediaFilters(alcance="tudo")) == 1
    assert repo.contar(MediaFilters(alcance="faltantes")) == 1
    assert repo.contar(MediaFilters(alcance="organizaveis")) == 0
    assert repo.estatisticas()["total"] == 0
    assert repo.estatisticas()["referencias"] == 1
    assert repo.estatisticas()["referencias_com_gps"] == 1


def test_referencia_e_idempotente(importer, tmp_path):
    factory, imp = importer
    asset = ExternalAsset(
        caminho=None, referencia="UUID-1",
        data_capturada=datetime(2025, 11, 1, 9, 30), gps_lat=1.0, gps_lon=2.0,
    )
    provider = FakeProvider(tmp_path / "t", [asset])
    imp.importar(provider)
    imp.importar(provider)
    with factory() as session:
        assert len(list(session.scalars(select(MediaFile)))) == 1


def test_referencia_doa_gps_para_foto_de_camera(importer, tmp_path):
    """O caso real: câmera sem GPS herda a coordenada da foto de celular
    tirada nos mesmos minutos, mesmo o celular não tendo arquivo local."""
    from fotoorganizer.classification import SuggestionEngine
    from fotoorganizer.geolocation import LocationResolver
    from fotoorganizer.geolocation.offline import OfflineGeocoder
    from fotoorganizer.models import Source

    factory, imp = importer

    # Duas referências de celular com GPS, minutos antes e depois.
    imp.importar(FakeProvider(tmp_path / "t", [
        ExternalAsset(caminho=None, referencia=f"U{i}",
                      data_capturada=datetime(2025, 11, 1, 9, 30 + i),
                      gps_lat=25.2, gps_lon=55.3)
        for i in range(3)
    ]))

    # Uma foto de câmera, sem GPS, no meio do intervalo.
    pasta = tmp_path / "camera"
    arquivo = make_jpeg(pasta / "ACM_1.jpg", seed=1,
                        data_exif="2025:11:01 09:31:00")
    with factory() as session:
        fonte = Source(caminho=str(pasta))
        session.add(fonte)
        session.flush()
        session.add(MediaFile(
            source_id=fonte.id, caminho=str(arquivo), pasta=str(pasta),
            nome=arquivo.name, extensao="jpg", tamanho=arquivo.stat().st_size,
            data_capturada=datetime(2025, 11, 1, 9, 31),
        ))
        session.commit()

    resultado = SuggestionEngine(
        factory, LocationResolver(OfflineGeocoder())
    ).gerar()

    assert resultado["herancas_gps"] >= 1
    # Só a foto de câmera vira sugestão; referência não tem destino.
    assert resultado["sugestoes"] == 1
