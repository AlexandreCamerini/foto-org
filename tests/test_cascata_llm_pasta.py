"""Degrau `llm_pasta` na cascata do `SuggestionEngine` (plano 07-05).

Prova três coisas separadas exigidas pelo GENAI-03 e pelo `<threat_model>`
do plano: (1) a proposta aprovada vira `Evidence` com origem própria
`llm_pasta`, nunca reaproveitando `llm` (T-07-05-01); (2) a evidência
sobrevive a uma segunda `gerar()` sem nenhuma chamada externa nova
(durabilidade — T-07-05-03, D-07); (3) o degrau é sempre o ÚLTIMO recurso
da cascata — todo degrau determinístico e o advisor de cluster continuam
vencendo, e sem proposta aprovada o motor se comporta exatamente como
antes desta fase.

Nenhum classificador real, nenhum cliente HTTP: `pastas_classificadas` é
montado à mão, no formato que `ClassificacaoPastaRepository.aprovadas()`
devolveria — o alvo aqui é só a cascata (engine.py), não a chamada ao
Claude (07-02) nem o gate de consentimento (07-04).
"""

from datetime import datetime, timedelta

from sqlalchemy import select

from fotoorganizer.classification import SuggestionEngine
from fotoorganizer.classification.advisor import AdvisorResult
from fotoorganizer.database import create_session_factory
from fotoorganizer.models import Evidence, MediaFile, PastaClassificada, Source
from fotoorganizer.repositories.pasta_classificacao import (
    ClassificacaoPastaRepository,
    PropostaDePasta,
)


def _media(source_id, nome, pasta, data=None, gps=None):
    return MediaFile(
        source_id=source_id, caminho=f"{pasta}/{nome}", pasta=pasta, nome=nome,
        extensao="jpg", tamanho=100, data_capturada=data,
        gps_lat=gps[0] if gps else None, gps_lon=gps[1] if gps else None,
    )


def _proposta(pasta, **kw) -> PropostaDePasta:
    base = dict(cidade=None, pais=None, categoria=None, evento=None,
                justificativa="cidade/país/categoria inferidos do nome da "
                               "pasta pelo Claude")
    base.update(kw)
    return PropostaDePasta(pasta=pasta, **base)


def _evidencias_de(factory, nome) -> dict[str, Evidence]:
    with factory() as session:
        media = session.scalar(select(MediaFile).where(MediaFile.nome == nome))
        evidencias = list(
            session.scalars(select(Evidence).where(Evidence.media_id == media.id))
        )
        return {e.campo: e for e in evidencias}


class FakeAdvisorComCategoria:
    """Só decide categoria (nunca 'Viagens', nunca evento) — mantém a
    sessão 'neutra' para que `_categoria` chegue ao passo 3 (advisor) sem
    virar Trip/Event, isolando o teste do degrau 3b (`llm_pasta`)."""

    def __init__(self, categoria="Eventos", evento=None,
                 justificativa="metadados citam o motivo"):
        self._categoria = categoria
        self._evento = evento
        self._justificativa = justificativa
        self.clusters = []

    @property
    def local(self):
        return False

    def classificar(self, cluster):
        self.clusters.append(cluster)
        return AdvisorResult(
            categoria=self._categoria, evento=self._evento,
            justificativa=self._justificativa,
        )


def test_evidencia_tem_origem_propria(migrated_engine):
    """GENAI-03: proposta aprovada de cidade/país para uma pasta sem GPS e
    sem hierarquia reconhecível vira `Evidence` de origem `llm_pasta` — e
    nenhuma dessas evidências sai com origem `llm` (que é do Advisor de
    cluster, T-07-05-01)."""
    pasta = "/fotos/Sítio da Vovó"
    factory = create_session_factory(migrated_engine)
    base = datetime(2024, 3, 10, 9, 0)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        session.add(_media(fonte.id, "sitio_0.jpg", pasta, data=base))
        session.commit()

    proposta = _proposta(pasta, cidade="Corumbá", pais="Brasil")
    engine = SuggestionEngine(factory, pastas_classificadas={pasta: proposta})
    engine.gerar()

    evidencias = _evidencias_de(factory, "sitio_0.jpg")
    assert evidencias["pais"].origem == "llm_pasta"
    assert evidencias["pais"].valor == "Brasil"
    assert evidencias["cidade"].origem == "llm_pasta"
    assert evidencias["cidade"].valor == "Corumbá"
    assert not any(e.origem == "llm" for e in evidencias.values())


def test_sobrevive_a_segunda_geracao(migrated_engine):
    """A evidência não é escrita direto em `Evidence` de fora do `gerar()`
    — ela é RE-DERIVADA da tabela toda rodada, então sobrevive a uma
    segunda geração sem nova chamada externa (D-07, T-07-05-03). O motor
    nem recebe classificador: nenhuma chamada é sequer possível aqui."""
    pasta = "/fotos/Sítio da Vovó"
    factory = create_session_factory(migrated_engine)
    base = datetime(2024, 3, 10, 9, 0)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        session.add(_media(fonte.id, "sitio_0.jpg", pasta, data=base))
        session.commit()

    proposta = _proposta(pasta, cidade="Corumbá", pais="Brasil")
    # advisor=None (padrão) — o motor não tem como fazer chamada externa.
    engine = SuggestionEngine(factory, pastas_classificadas={pasta: proposta})

    engine.gerar()
    primeira = _evidencias_de(factory, "sitio_0.jpg")
    assert primeira["pais"].origem == "llm_pasta"

    engine.gerar()
    segunda = _evidencias_de(factory, "sitio_0.jpg")
    assert segunda["pais"].origem == "llm_pasta"
    assert segunda["pais"].valor == "Brasil"


def test_proposta_nao_aprovada_nao_vira_evidencia(migrated_engine):
    """Linha em `status='proposta'` (ainda não aprovada pelo dono) não
    passa por `ClassificacaoPastaRepository.aprovadas()` — e por isso não
    chega à cascata como evidência nenhuma."""
    pasta = "/fotos/Sítio da Vovó"
    factory = create_session_factory(migrated_engine)
    base = datetime(2024, 3, 10, 9, 0)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        session.add(_media(fonte.id, "sitio_0.jpg", pasta, data=base))
        session.add(PastaClassificada(
            pasta=pasta, cidade="Corumbá", pais="Brasil", categoria=None,
            evento=None, justificativa="proposto pelo GenAI", origem="llm",
            status="proposta", sessao="s1",
        ))
        session.commit()

    pastas_classificadas = ClassificacaoPastaRepository(factory).aprovadas()
    assert pastas_classificadas == {}  # status 'proposta' não é 'aprovada'

    engine = SuggestionEngine(factory, pastas_classificadas=pastas_classificadas)
    engine.gerar()

    evidencias = _evidencias_de(factory, "sitio_0.jpg")
    assert "pais" not in evidencias
    assert "cidade" not in evidencias
    assert not any(e.origem == "llm_pasta" for e in evidencias.values())


def test_determinismo_vence_o_llm(migrated_engine):
    """Mídia cuja pasta tem país reconhecível na hierarquia recebe
    `Evidence` de origem `pasta`, nunca `llm_pasta` — mesmo com proposta
    aprovada divergente (T-07-05-01: o degrau novo nunca se sobrepõe ao
    determinístico)."""
    pasta = "/fotos/Japão/Tóquio"
    factory = create_session_factory(migrated_engine)
    base = datetime(2024, 8, 1, 9, 0)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        session.add(_media(fonte.id, "toquio_0.jpg", pasta, data=base))
        session.commit()

    # Proposta discordante — jamais deveria vencer o parse determinístico.
    proposta = _proposta(pasta, cidade="Rio de Janeiro", pais="Brasil")
    engine = SuggestionEngine(factory, pastas_classificadas={pasta: proposta})
    engine.gerar()

    evidencias = _evidencias_de(factory, "toquio_0.jpg")
    assert evidencias["pais"].origem == "pasta"
    assert evidencias["pais"].valor == "Japão"
    assert evidencias["cidade"].origem == "pasta"
    assert evidencias["cidade"].valor == "Tóquio"


def test_advisor_de_cluster_vence_na_categoria(migrated_engine):
    """Com sessão do advisor devolvendo categoria E proposta aprovada de
    categoria, a `Evidence` sai com origem `llm` — o degrau `llm_pasta` é
    fallback (passo 3b), nunca substituição do advisor (passo 3)."""
    pasta = "/fotos/2025_05_24"
    factory = create_session_factory(migrated_engine)
    base = datetime(2025, 5, 24, 14, 0)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        for i in range(3):
            session.add(_media(
                fonte.id, f"evento_{i}.jpg", pasta,
                data=base + timedelta(minutes=10 * i),
            ))
        session.commit()

    advisor = FakeAdvisorComCategoria(categoria="Eventos", evento=None)
    proposta = _proposta(pasta, categoria="Família")
    engine = SuggestionEngine(
        factory, advisor=advisor, pastas_classificadas={pasta: proposta},
    )
    engine.gerar()

    evidencias = _evidencias_de(factory, "evento_0.jpg")
    assert evidencias["categoria"].origem == "llm"
    assert evidencias["categoria"].valor == "Eventos"


def test_evento_da_sessao_prevalece(migrated_engine):
    """Com evento vindo da sessão (advisor), a proposta de evento não gera
    draft duplicado — a sessão tem precedência, a proposta só preenche o
    silêncio (regra explícita da Task 2 do plano)."""
    pasta = "/fotos/2025_06"
    factory = create_session_factory(migrated_engine)
    base = datetime(2025, 6, 6, 9, 0)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        for i in range(3):
            session.add(_media(
                fonte.id, f"buzios_{i}.jpg", pasta,
                data=base + timedelta(hours=6 * i),
            ))
        session.commit()

    advisor = FakeAdvisorComCategoria(
        categoria="Eventos", evento="Aniversário da Serena",
    )
    proposta = _proposta(pasta, evento="Outro evento qualquer")
    engine = SuggestionEngine(
        factory, advisor=advisor, pastas_classificadas={pasta: proposta},
    )
    engine.gerar()

    with factory() as session:
        media = session.scalar(
            select(MediaFile).where(MediaFile.nome == "buzios_0.jpg")
        )
        eventos = list(session.scalars(
            select(Evidence).where(
                Evidence.media_id == media.id, Evidence.campo == "evento",
            )
        ))
    assert len(eventos) == 1
    assert eventos[0].origem == "llm"
    assert eventos[0].valor == "Aniversário da Serena"


def test_sem_proposta_o_resultado_e_identico(migrated_engine):
    """`gerar()` sem `pastas_classificadas` (parâmetro omitido, igual a
    antes desta fase existir) produz o mesmo conjunto de evidências que
    produzia antes — mesmo com uma linha `aprovada` de verdade no banco:
    se o chamador não LÊ e passa a tabela, ela não tem efeito nenhum na
    cascata (a leitura em lote é responsabilidade de `jobs.py`, não do
    `SuggestionEngine`)."""
    pasta = "/fotos/Sítio da Vovó"
    factory = create_session_factory(migrated_engine)
    base = datetime(2024, 3, 10, 9, 0)
    with factory() as session:
        fonte = Source(caminho="/fotos")
        session.add(fonte)
        session.flush()
        session.add(_media(fonte.id, "sitio_0.jpg", pasta, data=base))
        # Linha aprovada de verdade no banco — mas ninguém a lê aqui.
        session.add(PastaClassificada(
            pasta=pasta, cidade="Corumbá", pais="Brasil", categoria=None,
            evento=None, justificativa="proposto pelo GenAI", origem="llm",
            status="aprovada", sessao="s1",
        ))
        session.commit()

    engine = SuggestionEngine(factory)  # pastas_classificadas OMITIDO
    engine.gerar()

    evidencias = _evidencias_de(factory, "sitio_0.jpg")
    # Baseline de antes desta fase: pasta sem hierarquia reconhecível e
    # sem GPS não produz NENHUMA evidência de lugar — só a data do EXIF.
    assert set(evidencias) == {"data"}
    assert evidencias["data"].origem == "exif"
    assert not any(e.origem == "llm_pasta" for e in evidencias.values())
