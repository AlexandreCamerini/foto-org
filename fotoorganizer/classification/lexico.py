"""O que uma palavra é: lugar, ocasião, pessoa ou ruído.

A cascata determinística (`docs/AGRUPAMENTO.md` §2) sabe medir duração e
distância. Ela não tem como saber que "Pantanal" é um lugar aonde se viaja e
"Quizomba" é uma festa — isso é conhecimento de mundo, e nenhuma regra o
resolve. Medido no acervo do dono: a regra 6 ("nome de álbum + sessão curta =
evento") classificou **Pantanal** (1d23h) e **Visconde de Maua** (18 fotos)
como eventos. São destinos de viagem.

O que este módulo classifica é o NOME, não a sessão — e essa diferença é o
que o torna barato. São 100 nomes distintos no acervo inteiro; uma consulta
resolve todos e o resultado fica gravado. O advisor (`advisor.py`) continua
existindo para o caso oposto: a sessão que a cascata não resolveu, com todo
o seu contexto temporal.

Privacidade (invariante 4): sai da máquina apenas a LISTA DE PALAVRAS —
nomes de pasta e de álbum. Nunca a imagem, o caminho completo, a data, a
coordenada ou a contagem. Requer `[privacidade] servicos_externos = true`,
que é `false` por padrão. Sem isso, `LexicoNulo` responde "não sei" para
tudo e a cascata se comporta exatamente como antes.

O resultado é evidência de confiança média, sempre revisável, e nunca decide
sozinho: ele só entra onde a cascata ia declarar evento por falta de
alternativa (regra 6).
"""

from __future__ import annotations

import json
import logging
from typing import Protocol

log = logging.getLogger(__name__)

# Opus 5 é a geração corrente. `docs/PLANO_IA_E_PRODUTO.md` §3 recomenda
# Haiku para rotulagem barata, e a recomendação vale quando a chamada é por
# sessão; aqui ela é uma só para o acervo inteiro, então o custo não é o
# critério — a qualidade da distinção lugar × ocasião é.
MODELO_PADRAO = "claude-opus-5"

LUGAR = "lugar"
OCASIAO = "ocasiao"
PESSOA = "pessoa"
RUIDO = "ruido"
CATEGORIAS = (LUGAR, OCASIAO, PESSOA, RUIDO)

# Quantos nomes cabem numa consulta. O acervo do dono tem 100 no total; o
# lote existe para o dia em que tiver 10 mil, e para a resposta não estourar
# o teto de saída.
TAMANHO_DO_LOTE = 200

_SCHEMA = {
    "type": "object",
    "properties": {
        "nomes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "nome": {"type": "string"},
                    "categoria": {
                        "type": "string",
                        "enum": [LUGAR, OCASIAO, PESSOA, RUIDO],
                    },
                    "justificativa": {
                        "type": "string",
                        "description": "Uma frase curta, em português",
                    },
                },
                "required": ["nome", "categoria", "justificativa"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["nomes"],
    "additionalProperties": False,
}

_SYSTEM = """\
Você classifica NOMES DE PASTA e NOMES DE ÁLBUM de um acervo de fotos
pessoal. Você recebe apenas as palavras — nunca as imagens, datas ou
coordenadas.

Para cada nome, responda uma categoria:

- "lugar": um lugar aonde se viaja ou se vai. Cidade, região, país, parque,
  praia, serra, bairro, estabelecimento. Ex.: "Pantanal", "Chapada dos
  Veadeiros", "Visconde de Mauá", "Aiuruoca e Tiradentes", "Dubai".
- "ocasiao": um acontecimento com hora marcada. Festa, aniversário,
  casamento, formatura, show, espetáculo, cerimônia, competição. Ex.:
  "Serena 15 Anos", "Quizomba", "Casamento da Ana", "Teatro".
- "pessoa": o nome de uma pessoa ou de um grupo de pessoas, sem indicar
  acontecimento. Ex.: "Vovó", "Meninas", "Família Silva".
- "ruido": não é acervo de foto pessoal. Nome de câmera ou equipamento,
  pasta de programação ou build, cache de aplicativo, identificador
  técnico, hash, pasta de sistema. Ex.: "Canon EOS 5D Mark IV",
  "DerivedData-access004", "node_modules", "CapCut", "Bora.build",
  "581ef37ff7c241daa5b2e8b1643a6e70".

Regras:
- Um nome pode ser as duas coisas ("Réveillon em Paraty" é ocasião E lugar).
  Escolha o que o nome enfatiza; na dúvida entre lugar e ocasião, prefira
  "lugar" apenas quando o nome for reconhecidamente um topônimo.
- Nome que você não reconhece e que não parece técnico: classifique pelo que
  a forma sugere e diga isso na justificativa. Não invente familiaridade.
- Responda TODOS os nomes recebidos, na mesma grafia em que vieram.
"""


class ClassificadorDeNomes(Protocol):
    @property
    def local(self) -> bool: ...

    def classificar(self, nomes: list[str]) -> dict[str, str]:
        """{nome: categoria}. Nome ausente do retorno = sem opinião."""
        ...


class LexicoNulo:
    """Padrão: nenhuma palavra sai da máquina, nenhuma opinião."""

    @property
    def local(self) -> bool:
        return True

    def classificar(self, nomes: list[str]) -> dict[str, str]:
        return {}


class LexicoClaude:
    """Consulta o Claude via SDK oficial, com saída estruturada.

    A credencial vem do ambiente (ANTHROPIC_API_KEY ou perfil `ant auth`) —
    nunca do código nem do repositório.
    """

    def __init__(self, model: str = MODELO_PADRAO, client=None) -> None:
        if client is None:
            import anthropic

            client = anthropic.Anthropic()
        self._client = client
        self._model = model

    @property
    def local(self) -> bool:
        return False  # a UI usa isto para indicar envio externo

    def classificar(self, nomes: list[str]) -> dict[str, str]:
        resultado: dict[str, str] = {}
        for i in range(0, len(nomes), TAMANHO_DO_LOTE):
            resultado.update(self._lote(nomes[i : i + TAMANHO_DO_LOTE]))
        return resultado

    def _lote(self, nomes: list[str]) -> dict[str, str]:
        try:
            resposta = self._client.messages.create(
                model=self._model,
                max_tokens=16000,
                # Rotular palavras em quatro categorias não é onde
                # raciocínio longo paga, e o teto cobre raciocínio MAIS
                # resposta — pensar aqui roubaria espaço da lista.
                thinking={"type": "disabled"},
                system=_SYSTEM,
                output_config={
                    "format": {"type": "json_schema", "schema": _SCHEMA}
                },
                messages=[{
                    "role": "user",
                    "content": json.dumps({"nomes": nomes}, ensure_ascii=False),
                }],
            )
        except Exception as exc:  # rede/auth/limite: nunca derruba a geração
            log.warning("léxico indisponível: %s", exc)
            return {}

        if resposta.stop_reason == "refusal":
            log.info("léxico recusou a consulta")
            return {}
        texto = next((b.text for b in resposta.content if b.type == "text"), None)
        if not texto:
            return {}
        try:
            dados = json.loads(texto)
        except json.JSONDecodeError:
            log.warning("léxico devolveu JSON inválido")
            return {}

        # Só o que veio na pergunta e com categoria conhecida: a resposta
        # não pode introduzir nome que o acervo não tem.
        pedidos = set(nomes)
        return {
            item["nome"]: item["categoria"]
            for item in dados.get("nomes", [])
            if item.get("nome") in pedidos and item.get("categoria") in CATEGORIAS
        }
