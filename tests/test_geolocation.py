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
    # O dataset é GeoNames em inglês; o país sai canonizado pelo código
    # ISO. A cidade fica como é: endônimo não é erro de tradução.
    assert resultado.pais == "França"
    assert resultado.cidade == "Avignon"
    assert resultado.fonte.startswith("offline:")


def test_cache_de_lugar_e_reescrito_quando_a_nomenclatura_muda(migrated_engine):
    """Mudar o nome do país não pode valer só para coordenadas novas: as
    fotos já resolvidas apontam para a linha em cache."""
    from fotoorganizer.database import create_session_factory
    from fotoorganizer.geolocation import GeoResult, LocationResolver

    class Provedor:
        def __init__(self, pais, fonte):
            self.pais, self._fonte = pais, fonte

        @property
        def fonte(self):
            return self._fonte

        def resolve(self, lat, lon):
            return GeoResult(self.pais, None, "Avignon", self._fonte)

    factory = create_session_factory(migrated_engine)
    with factory() as session:
        antigo = LocationResolver(Provedor("France", "offline:x/1"))
        location = antigo.resolve(session, 43.95, 4.8083)
        id_original = location.id
        assert location.pais == "France"

        novo = LocationResolver(Provedor("França", "offline:x/2"))
        atualizado = novo.resolve(session, 43.95, 4.8083)
        # Mesma linha (as fotos continuam apontando para ela), nome novo.
        assert atualizado.id == id_original
        assert atualizado.pais == "França"

        # Sem mudança de versão, o cache continua valendo (sem consulta).
        class Mudo(Provedor):
            def resolve(self, lat, lon):
                raise AssertionError("não devia consultar o provedor")

        assert Mudo("x", "offline:x/2").fonte == "offline:x/2"
        estavel = LocationResolver(Mudo("x", "offline:x/2"))
        assert estavel.resolve(session, 43.95, 4.8083).pais == "França"
