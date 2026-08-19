"""GenAI de pasta: D-02 por campo, o eixo status e a durabilidade da
proposta (D-07)."""

from fotoorganizer.database import create_session_factory
from fotoorganizer.repositories.pasta_classificacao import (
    ClassificacaoPastaRepository,
    PropostaDePasta,
)


def _proposta(pasta="/Users/eu/Pictures/Pantanal", **kw) -> PropostaDePasta:
    base = dict(cidade=None, pais=None, categoria=None, evento=None,
                justificativa="proposto pelo GenAI")
    base.update(kw)
    return PropostaDePasta(pasta=pasta, **base)


def test_nunca_sobrescreve_campo_ja_preenchido(migrated_engine):
    """D-02: campo já resolvido por uma fonte determinística não é
    reescrito, mesmo por uma proposta nova e mesmo quando discorda."""
    repo = ClassificacaoPastaRepository(create_session_factory(migrated_engine))
    repo.salvar_propostas([_proposta(cidade="Lisboa")], sessao="s1")
    repo.salvar_propostas([_proposta(cidade="Porto")], sessao="s2")

    assert repo.propostas()["/Users/eu/Pictures/Pantanal"].cidade == "Lisboa"


def test_completa_campo_vazio_em_linha_existente(migrated_engine):
    """D-02: uma proposta seguinte pode preencher o que ainda está vazio,
    sem tocar o que já foi resolvido antes."""
    repo = ClassificacaoPastaRepository(create_session_factory(migrated_engine))
    repo.salvar_propostas([_proposta(categoria="viagem")], sessao="s1")
    repo.salvar_propostas(
        [_proposta(cidade="Corumbá", pais="Brasil")], sessao="s2"
    )

    linha = repo.propostas()["/Users/eu/Pictures/Pantanal"]
    assert linha.categoria == "viagem"
    assert linha.cidade == "Corumbá"
    assert linha.pais == "Brasil"


def test_linha_manual_nao_e_tocada(migrated_engine):
    """Origem 'manual' é intocável — nem os campos vazios da linha são
    completados pela máquina."""
    factory = create_session_factory(migrated_engine)
    repo = ClassificacaoPastaRepository(factory)
    with factory() as session:
        from fotoorganizer.models import PastaClassificada
        session.add(PastaClassificada(
            pasta="/Users/eu/Pictures/Pantanal", cidade="Corumbá",
            pais=None, categoria=None, evento=None,
            justificativa="o dono decidiu", origem="manual",
            status="aprovada", sessao="manual",
        ))
        session.commit()

    repo.salvar_propostas(
        [_proposta(cidade="Lisboa", pais="Brasil", categoria="viagem")],
        sessao="s1",
    )

    linha = repo.aprovadas()["/Users/eu/Pictures/Pantanal"]
    assert linha.cidade == "Corumbá"
    assert linha.pais is None
    assert linha.categoria is None


def test_so_aprovada_e_lida_pela_cascata(migrated_engine):
    """T-07-01-02: uma proposta não aprovada é dado morto — só aprovar()
    a faz aparecer em aprovadas()."""
    repo = ClassificacaoPastaRepository(create_session_factory(migrated_engine))
    repo.salvar_propostas([_proposta(cidade="Corumbá")], sessao="s1")

    assert repo.aprovadas() == {}
    assert "/Users/eu/Pictures/Pantanal" in repo.propostas()

    repo.aprovar(["/Users/eu/Pictures/Pantanal"])

    assert "/Users/eu/Pictures/Pantanal" in repo.aprovadas()
    assert "/Users/eu/Pictures/Pantanal" not in repo.propostas()


def test_descartar_nao_apaga_linha(migrated_engine):
    """Invariante 8: descartar rebaixa a linha a fonte de sinal, nunca a
    remove do banco."""
    repo = ClassificacaoPastaRepository(create_session_factory(migrated_engine))
    repo.salvar_propostas([_proposta(cidade="Corumbá")], sessao="s1")
    repo.descartar(["/Users/eu/Pictures/Pantanal"])

    assert "/Users/eu/Pictures/Pantanal" not in repo.aprovadas()
    assert "/Users/eu/Pictures/Pantanal" not in repo.propostas()
    assert "/Users/eu/Pictures/Pantanal" in repo.conhecidas()


def test_conhecidas_cobre_todos_os_status(migrated_engine):
    """conhecidas() é o pré-filtro (07-03): pasta com linha em qualquer
    status conta como já classificada, não só a proposta em aberto."""
    repo = ClassificacaoPastaRepository(create_session_factory(migrated_engine))
    repo.salvar_propostas([
        _proposta("/a", cidade="X"),
        _proposta("/b", cidade="Y"),
        _proposta("/c", cidade="Z"),
    ], sessao="s1")
    repo.aprovar(["/a"])
    repo.descartar(["/b"])
    # "/c" continua em 'proposta'.

    assert repo.conhecidas() == {"/a", "/b", "/c"}
