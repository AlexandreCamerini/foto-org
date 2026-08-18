"""Classificação de PASTA por Claude — cidade, país, categoria, evento.

Privacidade (invariante 4, GENAI-02): sai da máquina apenas o NOME da
pasta e metadado JÁ CATALOGADO — contagem de fotos e período (ex.:
"2024-03-12 a 2024-03-19"). Nunca a imagem, nunca um byte de imagem,
nunca miniatura, nunca o caminho absoluto do arquivo. `PastaPayload` é a
allowlist inteira do que pode atravessar essa fronteira; nenhum campo
sai por serialização genérica de dataclass ou de objeto, só por
atribuição explícita em `ClassificacaoDePastaClaude.corpo_da_chamada`.

Requer `[privacidade] servicos_externos = true` E o opt-in próprio
`classificacao_pasta_genai` — o gate concreto fica em 07-04, este módulo
só nomeia a chave para documentar o contrato. Sem os dois, o padrão é
`ClassificacaoDePastaNula`: nenhuma pasta sai da máquina, nenhuma opinião.

Diferença para `advisor.py` (sessão/cluster) e `lexico.py` (palavra
isolada): aqui a unidade é a PASTA já confirmada como candidata, com
contagem e período que a catalogação já mediu — não um nome solto nem
um cluster temporal inteiro.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Protocol

log = logging.getLogger(__name__)

# Precedente D-059/D-060 (docs/DECISOES.md): nos 104 clusters reais do
# advisor de sessão, Haiku 4.5 afirmava categoria onde Opus recusava por
# falta de evidência em ≥19/31 discordâncias; Sonnet 5, medido depois,
# cai nesse padrão só 7 vezes. Aqui o argumento vale A FORTIORI: um nome
# de pasta sozinho é entrada mais esparsa que o cluster inteiro que foi
# medido (que tinha pastas, arquivos de exemplo, período e lugares já
# geocodificados) — logo o risco de o modelo afirmar sem base é maior
# aqui, não menor, e a mesma escolha de modelo se aplica com mais força.
# Nunca descer para haiku sem repetir a mesma medição contra o caso de
# pasta isolada.
MODELO_PADRAO = "claude-sonnet-5"

# Mesmo teto de fotoorganizer/classification/lexico.py: cobre
# raciocínio (desligado) + resposta estruturada de um lote inteiro.
MAX_TOKENS = 16000

# Vocabulário canônico de categoria de pasta — mesmos valores que a
# cascata determinística já reconhece (engine.py:_CATEGORIAS_PASTA).
# Não inventar rótulo novo aqui: um valor que a cascata não entende
# nunca converge com o resto do produto.
_CATEGORIAS_PASTA = ("Viagens", "Família", "Eventos")


@dataclass(frozen=True, slots=True)
class PastaPayload:
    """O que sai da máquina por pasta. Nada além disto (invariante 4).

    `ja_conhecido` existe por causa de D-02: o prompt precisa dizer ao
    modelo quais campos já têm dono para ele não gastar esforço propondo
    o que nunca seria gravado — e o filtro em `classificar()` reaplica
    essa regra sobre a resposta, então a obediência do modelo nunca é
    pré-requisito de segurança.
    """

    pasta: str                            # caminho relativo/nome da pasta
    n_fotos: int
    periodo: str | None                   # "2024-03-12 a 2024-03-19", já catalogado
    campos_a_preencher: tuple[str, ...]   # ("categoria",) | ("cidade","pais") | ambos
    ja_conhecido: dict[str, str]          # campos que JÁ têm valor — o modelo não deve propô-los


@dataclass(frozen=True, slots=True)
class PropostaDoModelo:
    """Uma opinião do modelo sobre uma pasta — nunca decide sozinha."""

    pasta: str
    cidade: str | None
    pais: str | None
    categoria: str | None
    evento: str | None
    justificativa: str


class ClassificadorDePasta(Protocol):
    @property
    def local(self) -> bool: ...

    def classificar(self, pastas: list[PastaPayload]) -> list[PropostaDoModelo]:
        """Uma proposta por pasta aceita. Pasta ausente = sem opinião."""
        ...

    def corpo_da_chamada(self, pastas: list[PastaPayload]) -> dict:
        """Os kwargs exatos que iriam para a chamada de criação de
        mensagem do SDK — existe para estimativa de custo (07-03) e
        para o teste de privacidade poder inspecionar o payload sem
        chamar a API."""
        ...


class ClassificacaoDePastaNula:
    """Padrão: nenhuma pasta sai da máquina, nenhuma opinião."""

    @property
    def local(self) -> bool:
        return True

    def classificar(self, pastas: list[PastaPayload]) -> list[PropostaDoModelo]:
        return []

    def corpo_da_chamada(self, pastas: list[PastaPayload]) -> dict:
        return {}


_SCHEMA = {
    "type": "object",
    "properties": {
        "pastas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "pasta": {"type": "string"},
                    "cidade": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "pais": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "categoria": {
                        "anyOf": [
                            {"type": "string", "enum": list(_CATEGORIAS_PASTA)},
                            {"type": "null"},
                        ],
                    },
                    "evento": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "justificativa": {
                        "type": "string",
                        "description": "Uma frase curta, em português, dizendo de onde veio a conclusão",
                    },
                },
                "required": [
                    "pasta", "cidade", "pais", "categoria", "evento", "justificativa",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["pastas"],
    "additionalProperties": False,
}

_SYSTEM = """\
Você classifica PASTAS de um acervo de fotos pessoal. Você recebe apenas
o nome da pasta e metadado já catalogado (contagem de fotos, período) —
nunca a imagem, nunca um caminho de arquivo, nunca uma miniatura.

Para cada pasta, proponha, quando der para concluir com segurança:

- "cidade" / "pais": onde as fotos foram tiradas, se o nome da pasta
  permitir concluir isso.
- "categoria": uma de "Viagens", "Família" ou "Eventos" — o mesmo
  vocabulário que o app já usa para agrupar pastas.
- "evento": um nome curto do acontecimento/viagem, se o nome da pasta
  sugerir um.

Regras:
- NUNCA invente. Se o nome da pasta não permitir concluir com segurança,
  devolva `null` no campo — essa é a resposta válida e preferida, não
  uma falha.
- Cada pasta traz `campos_a_preencher`: só proponha valor para os campos
  ali listados. Nunca proponha um campo que não foi pedido.
- Cada pasta traz `ja_conhecido`: campos que já têm valor confirmado.
  Nunca proponha um valor para um campo que já aparece em `ja_conhecido`
  daquela pasta — ele já tem dono e não deve ser reescrito.
- "justificativa" explica em uma frase curta, em português, de onde veio
  a conclusão (ex.: "nome da pasta é um topônimo conhecido").
- Responda TODAS as pastas recebidas, com a grafia exata em que vieram.
"""


class ClassificacaoDePastaClaude:
    """Consulta o Claude via SDK oficial, uma única chamada por sessão.

    A credencial vem do ambiente (ANTHROPIC_API_KEY ou perfil `ant auth`)
    — nunca do código nem do repositório.
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

    def corpo_da_chamada(self, pastas: list[PastaPayload]) -> dict:
        # Allowlist explícita, campo a campo — nunca serialização
        # genérica de dataclass/objeto. É o controle que garante que um
        # campo novo em PastaPayload (ou em qualquer objeto de domínio)
        # jamais vaze por acidente.
        payload = [
            {
                "pasta": p.pasta,
                "n_fotos": p.n_fotos,
                "periodo": p.periodo,
                "campos_a_preencher": list(p.campos_a_preencher),
                "ja_conhecido": dict(p.ja_conhecido),
            }
            for p in pastas
        ]
        return {
            "model": self._model,
            "max_tokens": MAX_TOKENS,
            # Classificar uma pasta pelo nome não é onde raciocínio longo
            # paga, e o teto cobre raciocínio MAIS resposta — pensar
            # aqui roubaria espaço da lista (mesmo raciocínio de lexico.py).
            "thinking": {"type": "disabled"},
            "system": _SYSTEM,
            "output_config": {
                "format": {"type": "json_schema", "schema": _SCHEMA}
            },
            "messages": [{
                "role": "user",
                "content": json.dumps({"pastas": payload}, ensure_ascii=False),
            }],
        }

    def classificar(self, pastas: list[PastaPayload]) -> list[PropostaDoModelo]:
        if not pastas:
            return []

        # UMA chamada para a lista inteira — sem laço de lote, sem
        # fatiar, sem chamada por pasta (D-03).
        try:
            resposta = self._client.messages.create(**self.corpo_da_chamada(pastas))
        except Exception as exc:  # rede/auth/limite: nunca derruba a sessão
            log.warning("classificação de pasta indisponível: %s", exc)
            return []

        if resposta.stop_reason == "refusal":
            log.info("classificação de pasta recusada pelo modelo")
            return []

        texto = next((b.text for b in resposta.content if b.type == "text"), None)
        if not texto:
            return []

        try:
            dados = json.loads(texto)
        except json.JSONDecodeError:
            log.warning("classificação de pasta devolveu JSON inválido")
            return []

        pedidos = {p.pasta: p for p in pastas}
        propostas: list[PropostaDoModelo] = []
        for item in dados.get("pastas", []):
            nome = item.get("pasta")
            pedido = pedidos.get(nome)
            if pedido is None:
                # Pasta que o modelo inventou (não estava no pedido):
                # descartada em silêncio (D-06/anti-alucinação).
                continue

            cidade = item.get("cidade")
            pais = item.get("pais")
            categoria = item.get("categoria")
            evento = item.get("evento")

            # D-06: resposta inteiramente ambígua ("não sei" nos quatro
            # campos de valor) não vira proposta nenhuma.
            if cidade is None and pais is None and categoria is None and evento is None:
                continue

            # D-02 reaplicada sobre a resposta: campo já conhecido nunca
            # é sobrescrito, mesmo que o modelo o tenha respondido — a
            # obediência do modelo ao prompt não é pré-requisito de
            # segurança.
            ja_conhecido = pedido.ja_conhecido
            if "cidade" in ja_conhecido:
                cidade = None
            if "pais" in ja_conhecido:
                pais = None
            if "categoria" in ja_conhecido:
                categoria = None
            if "evento" in ja_conhecido:
                evento = None

            propostas.append(PropostaDoModelo(
                pasta=nome,
                cidade=cidade,
                pais=pais,
                categoria=categoria,
                evento=evento,
                justificativa=item.get("justificativa", ""),
            ))

        return propostas
