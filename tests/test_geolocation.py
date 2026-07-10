from dataclasses import dataclass

from fotoorganizer.database import create_session_factory
from fotoorganizer.geolocation import (
    GeoResult,
    LocationResolver,
    extrair_hierarquia_da_pasta,
    identificar_pais,
)


def test_identificar_pais_normaliza_acentos_e_caixa():
    assert identificar_pais("França") == "França"
    assert identificar_pais("franca") == "França"
    assert identificar_pais("JAPAO") == "Japão"
    assert identificar_pais("Gramado") is None


def test_hierarquia_da_pasta():
    h = extrair_hierarquia_da_pasta("/Volumes/HD/Viagens/França/Provence/Avignon")
    assert (h.pais, h.regiao, h.cidade) == ("França", "Provence", "Avignon")
    assert h.segmento_pais == "França"

    h = extrair_hierarquia_da_pasta("/fotos/Japão/Tóquio")
    assert (h.pais, h.regiao, h.cidade) == ("Japão", None, "Tóquio")

    h = extrair_hierarquia_da_pasta("/fotos/Japão")
    assert (h.pais, h.regiao, h.cidade) == ("Japão", None, None)


def test_sem_pais_nao_inventa():
    h = extrair_hierarquia_da_pasta("/fotos/Aniversários/2022")
    assert (h.pais, h.regiao, h.cidade) == (None, None, None)


@dataclass
class FakeGeocoder:
    chamadas: int = 0

    def resolve(self, lat, lon):
        self.chamadas += 1
        return GeoResult(pais="França", regiao="Provence", cidade="Avignon",
                         fonte="fake")


def test_resolver_usa_cache_da_tabela(migrated_engine):
    factory = create_session_factory(migrated_engine)
    fake = FakeGeocoder()
    resolver = LocationResolver(fake)

    with factory() as session:
        a = resolver.resolve(session, 43.9500, 4.8083)
        b = resolver.resolve(session, 43.9501, 4.8083)  # ~10m: mesma chave
        session.commit()
        assert a is not None and a.pais == "França"
        assert a.fonte == "fake"
        assert b.id == a.id
    assert fake.chamadas == 1  # segunda consulta veio do cache

    # Nova sessão: cache persiste no banco.
    with factory() as session:
        c = resolver.resolve(session, 43.95, 4.8083)
        assert c.id == a.id
    assert fake.chamadas == 1


def test_geocoder_offline_real():
    """Uma consulta real ao dataset local (sem rede)."""
    from fotoorganizer.geolocation.offline import OfflineGeocoder

    resultado = OfflineGeocoder().resolve(43.95, 4.8083)
    assert resultado is not None
    assert resultado.pais == "France"
    assert resultado.cidade == "Avignon"
    assert resultado.fonte.startswith("offline:")
