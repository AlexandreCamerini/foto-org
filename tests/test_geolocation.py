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


def test_hierarquia_tolera_o_que_vem_junto_no_segmento():
    """Caso real: "Chile e Atacama Abr.18" (880 fotos) não dava país
    nenhum. A sobra ("Atacama") NÃO vira cidade por enquanto — só quando
    o dataset offline confirmar que é lugar (fatia 2 de D-082); e a
    subpasta de workflow logo abaixo também não."""
    h = extrair_hierarquia_da_pasta(
        "/Volumes/photo/Portfolio/Chile e Atacama Abr.18/[Developed]"
    )
    assert (h.pais, h.regiao, h.cidade) == ("Chile", None, None)
    assert h.segmento_pais == "Chile e Atacama Abr.18"


def test_subpasta_tecnica_abaixo_do_pais_nao_e_cidade():
    h = extrair_hierarquia_da_pasta("/fotos/Japão/Tóquio/Revelados")
    assert (h.pais, h.regiao, h.cidade) == ("Japão", None, "Tóquio")
    h = extrair_hierarquia_da_pasta("/fotos/Japão/2019")
    assert (h.pais, h.regiao, h.cidade) == ("Japão", None, None)


def test_pasta_multi_pais_nao_escolhe_e_continua_descendo():
    """"Peru-Bolivia-Chile" (5.516 fotos): nenhum dos três é O país da
    foto — o nome da viagem é que lista todos (regra 3 do classificador).
    A pasta de cada país logo abaixo continua valendo."""
    h = extrair_hierarquia_da_pasta(
        "/Volumes/photo/Portfolio/Viagens Antigas/Peru-Bolivia-Chile"
    )
    assert (h.pais, h.regiao, h.cidade) == (None, None, None)
    h = extrair_hierarquia_da_pasta("/Volumes/Viagens/Peru-Bolivia-Chile/Peru/Cusco")
    assert (h.pais, h.regiao, h.cidade) == ("Peru", None, "Cusco")


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


def test_resolver_cache_em_memoria_evita_select_repetido(migrated_engine):
    """Uma geração chama `resolve()` várias vezes pela MESMA coordenada
    (herança de GPS, tz estimado, evidência geo — cada uma resolve por
    conta própria) — sem atalho em memória, cada uma vira um SELECT.

    O cache na tabela (`test_resolver_usa_cache_da_tabela`, acima) já evita
    reconsultar o provedor; este teste prova a camada de cima, que evita
    reconsultar o BANCO dentro da mesma sessão — e que trocar de sessão
    zera o atalho em memória sem reabrir a porta pro provedor (a tabela
    continua protegendo)."""
    factory = create_session_factory(migrated_engine)
    fake = FakeGeocoder()
    resolver = LocationResolver(fake)

    chamadas_sem_cache = []
    original = resolver._resolve_sem_cache

    def contando(*args, **kwargs):
        chamadas_sem_cache.append(1)
        return original(*args, **kwargs)

    resolver._resolve_sem_cache = contando

    with factory() as session:
        a = resolver.resolve(session, 43.9500, 4.8083)
        b = resolver.resolve(session, 43.9501, 4.8083)  # ~10m: mesma chave
        session.commit()
        assert b.id == a.id
    assert len(chamadas_sem_cache) == 1  # só a primeira foi ao banco

    # Sessão nova: o atalho em memória zera (objeto da sessão anterior
    # pode estar destacado), mas a tabela ainda serve de cache — o
    # provedor não é consultado de novo.
    with factory() as session:
        c = resolver.resolve(session, 43.95, 4.8083)
        assert c.id == a.id
    assert len(chamadas_sem_cache) == 2
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
