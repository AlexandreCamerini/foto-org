"""GENAI-02: só nome de pasta e metadado catalogado saem da máquina.

Cada teste protege uma regra específica: GENAI-02 (payload/modelo), D-02
(campo já conhecido nunca é sobrescrito), D-03 (uma chamada por sessão),
D-06 (resposta ambígua não vira proposta) e o contrato never-crash.
"""

import json

import pytest

from fotoorganizer.classification.location_advisor import (
    ClassificacaoDePastaClaude,
    ClassificacaoDePastaNula,
    PastaPayload,
)


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


def _payload(pasta="Pantanal Jul.2023", **kw) -> PastaPayload:
    kw.setdefault("ja_conhecido", {})
    return PastaPayload(
        pasta=pasta,
        n_fotos=42,
        periodo="2023-07-12 a 2023-07-19",
        campos_a_preencher=("cidade", "pais", "categoria", "evento"),
        **kw,
    )


def _resposta_com(**item_kw):
    base = {
        "pasta": "Pantanal Jul.2023",
        "cidade": None,
        "pais": None,
        "categoria": None,
        "evento": None,
        "justificativa": "",
    }
    base.update(item_kw)
    return _RespostaFalsa(json.dumps({"pastas": [base]}))


def test_payload_nunca_envia_imagem():
    """O contrato de privacidade (invariante 4, GENAI-02): só o que está
    na allowlist de PastaPayload sai da máquina — nunca imagem, caminho
    de arquivo ou miniatura."""
    payload = _payload(ja_conhecido={"categoria": "Viagens"})
    cliente = _ClienteFalso(_resposta_com())
    ClassificacaoDePastaClaude(client=cliente).classificar([payload])

    corpo_texto = cliente.chamadas[0]["messages"][0]["content"]
    corpo = json.loads(corpo_texto)
    assert set(corpo.keys()) == {"pastas"}

    item = corpo["pastas"][0]
    assert set(item.keys()) == {
        "pasta", "n_fotos", "periodo", "campos_a_preencher", "ja_conhecido",
    }

    proibidos = ("caminho", "thumb", "miniatura", "base64", "image",
                 ".jpg", ".cr2", ".heic")
    for chave, valor in item.items():
        texto = f"{chave}={valor}".lower()
        for termo in proibidos:
            assert termo not in texto, f"'{termo}' vazou em {chave}={valor}"


def test_modelo_e_thinking():
    """GENAI-02: modelo é Sonnet 5, com thinking desabilitado."""
    cliente = _ClienteFalso(_resposta_com())
    corpo = ClassificacaoDePastaClaude(client=cliente).corpo_da_chamada(
        [_payload()]
    )
    assert corpo["model"] == "claude-sonnet-5"
    assert corpo["thinking"] == {"type": "disabled"}


def test_uma_chamada_para_muitas_pastas():
    """D-03: uma sessão inteira sai numa única chamada, não uma por
    pasta."""
    pastas = [_payload(pasta=f"Pasta {i}") for i in range(12)]
    cliente = _ClienteFalso(_RespostaFalsa(json.dumps({"pastas": []})))
    ClassificacaoDePastaClaude(client=cliente).classificar(pastas)
    assert len(cliente.chamadas) == 1


@pytest.mark.parametrize("falha", [
    RuntimeError("sem rede"),
    _RespostaFalsa("", stop_reason="refusal"),
    _RespostaFalsa("isto não é json"),
    RuntimeError("429 Too Many Requests"),
])
def test_falha_nunca_derruba(falha):
    """Rede caída, recusa, JSON inválido ou 429: devolve vazio, nunca
    levanta exceção (contrato never-crash)."""
    resultado = ClassificacaoDePastaClaude(
        client=_ClienteFalso(falha)
    ).classificar([_payload()])
    assert resultado == []


def test_ignora_pasta_que_nao_foi_pedida():
    """Pasta que o modelo devolveu mas que não foi pedida é descartada;
    a pedida é aceita (anti-alucinação)."""
    resposta = _RespostaFalsa(json.dumps({"pastas": [
        {"pasta": "Pantanal Jul.2023", "cidade": None, "pais": None,
         "categoria": "Viagens", "evento": None, "justificativa": "bioma"},
        {"pasta": "Inventada", "cidade": "Paris", "pais": "França",
         "categoria": None, "evento": None, "justificativa": "?"},
    ]}))
    resultado = ClassificacaoDePastaClaude(
        client=_ClienteFalso(resposta)
    ).classificar([_payload()])

    assert [p.pasta for p in resultado] == ["Pantanal Jul.2023"]
    assert resultado[0].categoria == "Viagens"


def test_resposta_incerta_nao_vira_proposta():
    """D-06: item com cidade/país/categoria/evento todos null não gera
    proposta nenhuma."""
    resultado = ClassificacaoDePastaClaude(
        client=_ClienteFalso(_resposta_com())
    ).classificar([_payload()])
    assert resultado == []


def test_nao_propoe_campo_ja_conhecido():
    """D-02: campo cuja pasta já declarou ja_conhecido é descartado da
    resposta mesmo que o modelo o tenha devolvido."""
    payload = _payload(ja_conhecido={"categoria": "Viagens"})
    resposta = _resposta_com(categoria="Eventos", cidade="Corumbá")
    resultado = ClassificacaoDePastaClaude(
        client=_ClienteFalso(resposta)
    ).classificar([payload])

    assert len(resultado) == 1
    assert resultado[0].categoria is None
    assert resultado[0].cidade == "Corumbá"


def test_nula_e_o_padrao():
    """Padrão: ClassificacaoDePastaNula não fala com ninguém."""
    nulo = ClassificacaoDePastaNula()
    assert nulo.local is True
    assert nulo.classificar([_payload()]) == []
    assert not ClassificacaoDePastaClaude(client=_ClienteFalso(None)).local
