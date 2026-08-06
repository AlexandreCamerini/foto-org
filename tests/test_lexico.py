"""O léxico: o que uma palavra é, e o que isso muda na cascata."""

from datetime import timedelta

import pytest

from fotoorganizer.classification.lexico import (
    CATEGORIAS,
    LUGAR,
    LexicoClaude,
    LexicoNulo,
)
from fotoorganizer.database import create_session_factory
from fotoorganizer.grouping.classifier import DadosSessao, classificar_sessao
from fotoorganizer.repositories.lexico import LexicoRepository


def _sessao(nome: str, duracao=timedelta(hours=3), **kw) -> DadosSessao:
    return DadosSessao(
        pastas=(f"/Users/eu/Pictures/{nome}",),
        duracao=duracao,
        pais_dominante=None,
        dist_mediana_casa_km=None,
        periodo_curto="Viagem de 01-01",
        **kw,
    )


# -- a regra que Pantanal expôs -------------------------------------------

def test_nome_de_lugar_vira_viagem_e_nao_evento():
    """O defeito visível na tela: Pantanal e Visconde de Mauá em Eventos.

    A cascata sabe medir duração; não tem como saber que "Pantanal" é
    destino de viagem. Sessão curta + nome de álbum caía sempre em evento.
    """
    # A chave é o nome que a cascata usa — `extrair_evento` já tirou a data
    # da pasta ("Pantanal Jul.2023" → "Pantanal"). Chavear pelo segmento cru
    # faria o léxico nunca casar.
    dados = _sessao("Pantanal Jul.2023", tipos_de_nome=(("Pantanal", LUGAR),))
    decisao = classificar_sessao(dados)
    assert decisao.tipo == "viagem"
    assert decisao.origem == "lexico"
    assert "lugar" in decisao.justificativa


def test_nome_de_ocasiao_continua_evento():
    """Quizomba é festa, e continua evento — o léxico confirma a regra,
    não a inverte."""
    dados = _sessao("Quizomba", tipos_de_nome=(("Quizomba", "ocasiao"),))
    assert classificar_sessao(dados).tipo == "evento"


def test_sem_lexico_a_cascata_decide_como_sempre():
    """Léxico desligado (o padrão) não muda uma vírgula do comportamento."""
    dados = _sessao("Pantanal Jul.2023")
    decisao = classificar_sessao(dados)
    assert decisao.tipo == "evento"
    assert decisao.origem == "pasta"


def test_lexico_alcanca_o_lugar_um_nivel_acima_da_folha():
    """"Pantanal Jul.2023/Dia 2": a folha nomeia a subpasta, mas quem diz o
    que a sessão É mora um nível acima — e o léxico o conhece. Antes, só o
    nome extraído da folha era consultado, e a sessão virava evento 'Dia
    2'."""
    dados = _sessao(
        "Pantanal Jul.2023/Dia 2", tipos_de_nome=(("Pantanal", LUGAR),)
    )
    decisao = classificar_sessao(dados)
    assert decisao.tipo == "viagem"
    assert decisao.rotulo == "Pantanal"
    assert decisao.origem == "lexico"


def test_lexico_reconhece_ocasiao_em_nivel_intermediario():
    """".../Quizomba 2019/Selecionadas": a ocasião num nível de cima nomeia
    o evento — melhor que a folha genérica que só diz arrumação."""
    dados = _sessao(
        "Quizomba 2019/Selecionadas",
        tipos_de_nome=(("Quizomba", "ocasiao"),),
    )
    decisao = classificar_sessao(dados)
    assert decisao.tipo == "evento"
    assert decisao.rotulo == "Quizomba"
    assert decisao.origem == "lexico"


def test_lugar_nao_transforma_sessao_longa_em_evento():
    """A regra 6 só vale para sessão curta; o léxico não muda esse limite.

    Uma sessão de 10 dias já é decidida antes de chegar na regra 6 — o
    léxico não pode ressuscitar a regra para casos que ela não cobria.
    """
    dados = _sessao(
        "Pantanal", duracao=timedelta(days=10),
        tipos_de_nome=(("Pantanal", LUGAR),),
    )
    assert classificar_sessao(dados).tipo != "evento"


# -- o cache ---------------------------------------------------------------

def test_so_o_que_falta_sai_da_maquina(migrated_engine):
    """O que já foi classificado nunca é reenviado (invariante 4)."""
    repo = LexicoRepository(create_session_factory(migrated_engine))
    repo.salvar({"Pantanal": LUGAR}, {"Pantanal": "bioma brasileiro"})

    assert repo.conhecidos() == {"Pantanal": LUGAR}
    assert repo.faltantes({"Pantanal", "Quizomba"}) == ["Quizomba"]


def test_correcao_do_dono_sobrevive_a_reclassificacao(migrated_engine):
    """A máquina propõe; o dono decide. Sem isto, a próxima consulta
    desfaria a correção em silêncio."""
    repo = LexicoRepository(create_session_factory(migrated_engine))
    repo.salvar({"TERG": "ocasiao"}, origem="llm")
    repo.salvar({"TERG": LUGAR}, origem="manual")

    repo.salvar({"TERG": "ocasiao"}, origem="llm")   # a máquina insiste
    assert repo.conhecidos()["TERG"] == LUGAR        # e não vence


# -- o cliente -------------------------------------------------------------

class _RespostaFalsa:
    def __init__(self, texto: str, stop_reason: str = "end_turn") -> None:
        self.content = [type("B", (), {"type": "text", "text": texto})()]
        self.stop_reason = stop_reason


class _ClienteFalso:
    def __init__(self, resposta) -> None:
        self._resposta = resposta
        self.chamadas: list[dict] = []

    @property
    def messages(self):
        return self

    def create(self, **kw):
        self.chamadas.append(kw)
        if isinstance(self._resposta, Exception):
            raise self._resposta
        return self._resposta


def test_manda_so_as_palavras(monkeypatch):
    """O contrato de privacidade: sai a lista de nomes, nada mais."""
    import json

    cliente = _ClienteFalso(_RespostaFalsa(json.dumps({"nomes": [
        {"nome": "Pantanal", "categoria": LUGAR, "justificativa": "bioma"},
    ]})))
    resultado = LexicoClaude(client=cliente).classificar(["Pantanal"])

    assert resultado == {"Pantanal": LUGAR}
    corpo = json.loads(cliente.chamadas[0]["messages"][0]["content"])
    assert corpo == {"nomes": ["Pantanal"]}


def test_resposta_nao_pode_inventar_nome():
    """O modelo devolve só o que foi perguntado — nome novo é descartado."""
    import json

    cliente = _ClienteFalso(_RespostaFalsa(json.dumps({"nomes": [
        {"nome": "Pantanal", "categoria": LUGAR, "justificativa": "bioma"},
        {"nome": "Inventado", "categoria": LUGAR, "justificativa": "?"},
        {"nome": "Pantanal", "categoria": "planeta", "justificativa": "?"},
    ]})))
    assert LexicoClaude(client=cliente).classificar(["Pantanal"]) == {
        "Pantanal": LUGAR
    }


@pytest.mark.parametrize("falha", [
    RuntimeError("sem rede"),
    _RespostaFalsa("", stop_reason="refusal"),
    _RespostaFalsa("isto não é json"),
])
def test_falha_nunca_derruba_a_geracao(falha):
    """Rede, recusa ou JSON quebrado: devolve vazio e a cascata segue."""
    assert LexicoClaude(client=_ClienteFalso(falha)).classificar(["x"]) == {}


def test_lexico_nulo_e_o_padrao_e_nao_fala_com_ninguem():
    nulo = LexicoNulo()
    assert nulo.local is True
    assert nulo.classificar(["Pantanal"]) == {}
    assert not LexicoClaude(client=_ClienteFalso(None)).local


def test_categorias_sao_as_quatro_documentadas():
    assert set(CATEGORIAS) == {"lugar", "ocasiao", "pessoa", "ruido"}


def test_a_chave_e_o_nome_extraido_nao_o_segmento_cru():
    """`extrair_evento` tira a data antes de a cascata decidir.

    "Pantanal Jul.2023" chega na regra 6 como "Pantanal"; classificar o
    segmento cru produziria um léxico que nunca casa com nada.
    """
    from fotoorganizer.grouping.eventos import extrair_evento

    nome, _de_keyword = extrair_evento(["/Users/eu/Pictures/Pantanal Jul.2023"])
    assert nome == "Pantanal"

    crua = _sessao("Pantanal Jul.2023",
                   tipos_de_nome=(("Pantanal Jul.2023", LUGAR),))
    assert classificar_sessao(crua).tipo == "evento"     # não casou
