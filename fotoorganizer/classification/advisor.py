"""Advisor de classificação via LLM — apoio opt-in para sessões que a
cascata determinística não resolveu (docs/AGRUPAMENTO.md §3).

Privacidade: apenas METADADOS saem da máquina (pastas, amostra de nomes de
arquivo, período, contagem, lugares já geocodificados) — nunca a imagem.
Requer [privacidade] servicos_externos = true, `pip install -e ".[llm]"` e
credencial Anthropic no ambiente. O resultado é evidência de nível médio-
baixo, sempre abaixo das regras determinísticas, e sempre sujeito a
revisão humana.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

log = logging.getLogger(__name__)

# Decisão 1 do gate da fase 5 (docs/DECISOES.md D-047 a D-060). Descer
# para Haiku 4.5 foi medido e descartado: em 104 clusters reais, Haiku
# afirmava categoria onde Opus recusava por falta de evidência em pelo
# menos 19/31 discordâncias (D-049) — violava a instrução "nunca invente"
# do próprio `_SYSTEM` abaixo. Sonnet 5, medido depois (D-060) nos mesmos
# 104 clusters, cai nesse padrão só 7 vezes (contra o piso de 19 do
# Haiku) — motivo da escolha.
MODELO_PADRAO = "claude-sonnet-5"


@dataclass(frozen=True, slots=True)
class ClusterInfo:
    """Metadados de uma sessão — tudo que o advisor pode ver."""

    pastas: tuple[str, ...]
    exemplos_arquivos: tuple[str, ...]
    inicio: datetime
    fim: datetime
    n_fotos: int
    lugares: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class AdvisorResult:
    categoria: str | None   # "Viagens" | "Eventos" | "Família" | None
    evento: str | None      # nome curto do evento/álbum, se houver
    justificativa: str


class ClassificationAdvisor(Protocol):
    @property
    def local(self) -> bool: ...

    def classificar(self, cluster: ClusterInfo) -> AdvisorResult | None:
        """None = sem opinião (indisponível, recusa ou erro)."""
        ...


class NullAdvisor:
    """Padrão: nenhum dado sai da máquina, nenhuma opinião."""

    @property
    def local(self) -> bool:
        return True

    def classificar(self, cluster: ClusterInfo) -> AdvisorResult | None:
        return None


_SCHEMA = {
    "type": "object",
    "properties": {
        "categoria": {
            "anyOf": [
                {"type": "string", "enum": ["Viagens", "Eventos", "Família"]},
                {"type": "null"},
            ],
            "description": "Categoria mais provável, ou null se incerto",
        },
        "evento": {
            "anyOf": [{"type": "string"}, {"type": "null"}],
            "description": "Nome curto do evento/álbum (ex.: 'Aniversário da "
                           "Serena'), ou null",
        },
        "justificativa": {
            "type": "string",
            "description": "Uma frase, em português, citando o indício usado",
        },
    },
    "required": ["categoria", "evento", "justificativa"],
    "additionalProperties": False,
}

_SYSTEM = (
    "Você classifica grupos de fotos de um acervo pessoal a partir de "
    "METADADOS (nomes de pastas e arquivos, datas, lugares). Você nunca vê "
    "as imagens. Responda apenas o que os metadados sustentam: nomes de "
    "pasta como 'Serena 15 Anos' indicam aniversário (Eventos); estadias "
    "de dias em outro país indicam Viagens. Se os metadados não bastarem, "
    "devolva categoria e evento nulos — nunca invente."
)


class ClaudeAdvisor:
    """Consulta o Claude via SDK oficial com structured outputs.

    A credencial vem do ambiente (ANTHROPIC_API_KEY ou perfil `ant auth`) —
    nunca do código ou do repositório.
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

    def classificar(self, cluster: ClusterInfo) -> AdvisorResult | None:
        payload = {
            "pastas": list(cluster.pastas),
            "exemplos_de_arquivos": list(cluster.exemplos_arquivos[:8]),
            "periodo": {
                "inicio": cluster.inicio.isoformat(),
                "fim": cluster.fim.isoformat(),
            },
            "quantidade_de_fotos": cluster.n_fotos,
            "lugares_geocodificados": list(cluster.lugares),
        }
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=1024,
                # Sem raciocínio estendido, e explicitamente. No Opus 4.8
                # omitir `thinking` já significava não pensar; no Opus 5 o
                # padrão passou a ser pensar, e `max_tokens` cobre
                # raciocínio MAIS resposta — 1024 truncaria o JSON no meio.
                # A tarefa é rotular um punhado de metadados em três
                # categorias; não é onde raciocínio longo paga.
                thinking={"type": "disabled"},
                system=_SYSTEM,
                output_config={
                    "format": {"type": "json_schema", "schema": _SCHEMA}
                },
                messages=[{
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False),
                }],
            )
        except Exception as exc:  # rede/auth/limite: nunca derruba a geração
            log.warning("advisor LLM indisponível: %s", exc)
            return None

        if response.stop_reason == "refusal":
            log.info("advisor LLM recusou a consulta")
            return None
        texto = next(
            (b.text for b in response.content if b.type == "text"), None
        )
        if not texto:
            return None
        try:
            dados = json.loads(texto)
        except json.JSONDecodeError:
            log.warning("advisor LLM devolveu JSON inválido")
            return None
        return AdvisorResult(
            categoria=dados.get("categoria"),
            evento=dados.get("evento"),
            justificativa=dados.get("justificativa", ""),
        )
