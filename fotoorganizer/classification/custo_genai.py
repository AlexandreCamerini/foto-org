"""Estimativa de custo da sessão de classificação de pasta por GenAI —
D-04 (mostrar custo antes de gastar) / D-05 (sem teto automático, uma
confirmação basta).

D-079 (docs/DECISOES.md) decidiu COMO a entrada é contada: híbrida. Nada
sai da máquina antes do dono confirmar (critério 2 do ROADMAP,
`.planning/ROADMAP.md` § Phase 7) — `client.messages.count_tokens`
transmite o payload inteiro, então não pode rodar antes da confirmação.
`estimar()` conta a entrada LOCALMENTE, de propósito conservadora (nunca
abaixo do real). Só depois que o dono confirma, o chamador (endpoint,
07-04) roda `contar_exato()` imediatamente antes de `messages.create` —
a mesma transmissão que já ia acontecer, só que a contagem exata que ela
devolve vai para o resumo pós-execução (passo 5 da UI), não para a
prévia.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from math import ceil

log = logging.getLogger(__name__)

PRECO_ENTRADA_USD_POR_MTOK = 2.0
PRECO_SAIDA_USD_POR_MTOK = 10.0

# Taxa de câmbio de REFERÊNCIA — este módulo não busca cotação online
# (T-07-03-04: abrir uma segunda saída de rede não consentida, fora do
# escopo do que o dono aprovou para este recurso). É só o valor default
# de fallback; o endpoint (07-04) pode repassar uma taxa mais recente via
# o parâmetro `cambio_usd_brl` de `estimar()`.
CAMBIO_USD_BRL_PADRAO = 5.0
CAMBIO_FONTE_PADRAO = (
    "taxa de referência fixa, capturada em 2026-08 — conversão de exibição,"
    " não cotação ao vivo"
)

# A Anthropic desaconselha tokenizador genérico para estimar tokens de
# Claude: ele subconta em texto típico (15-20%), e mais ainda em PT-BR
# (acentuação) e JSON estruturado (aspas, chaves, escapes) — exatamente o
# formato do payload deste módulo (07-RESEARCH.md § Pitfall 3). Um custo
# mostrado ABAIXO do real é a falha que importa aqui (T-07-03-03): o dono
# aprova um teto e o gasto real ultrapassa o que ele viu. Por isso o
# fator abaixo NÃO segue a razão nominal de ~4 caracteres por token — ele
# reduz esse fator deliberadamente para CIMA (menos caracteres por token
# assumido = mais tokens estimados), compensando a subcontagem conhecida
# em vez de segui-la.
_CARACTERES_POR_TOKEN_CONSERVADOR = 3.0


def _estimar_tokens_local(corpo: dict) -> int:
    """Contagem local conservadora — nunca chama rede, nunca é exata."""
    texto = json.dumps(corpo, ensure_ascii=False)
    return max(1, ceil(len(texto) / _CARACTERES_POR_TOKEN_CONSERVADOR))


@dataclass(frozen=True, slots=True)
class CustoEstimado:
    """Os números que o passo 2 (prévia) e o passo 5 (resumo) da UI leem."""

    tokens_entrada: int
    entrada_exata: bool           # False quando a contagem é local/aproximada
    custo_entrada_usd: float
    teto_tokens_saida: int
    teto_custo_saida_usd: float
    teto_custo_total_usd: float
    teto_custo_total_brl: float
    cambio_usd_brl: float
    cambio_fonte: str             # de onde veio a taxa e quando


def estimar(corpo: dict, cambio_usd_brl: float) -> CustoEstimado:
    """Estimativa da sessão, ANTES da confirmação do dono — sem rede.

    `corpo` é o dict de `ClassificadorDePasta.corpo_da_chamada(pastas)`
    (`location_advisor.py`) — o mesmo objeto que seria enviado a
    `messages.create`, usado aqui só para ler `max_tokens` e medir o
    tamanho do texto, nunca transmitido. `corpo` vazio (nenhuma pasta
    selecionada, ou `ClassificacaoDePastaNula.corpo_da_chamada`) devolve
    custo zero em todos os campos, sem calcular nada.
    """
    if not corpo:
        return CustoEstimado(
            tokens_entrada=0,
            entrada_exata=False,
            custo_entrada_usd=0.0,
            teto_tokens_saida=0,
            teto_custo_saida_usd=0.0,
            teto_custo_total_usd=0.0,
            teto_custo_total_brl=0.0,
            cambio_usd_brl=cambio_usd_brl,
            cambio_fonte=CAMBIO_FONTE_PADRAO,
        )

    tokens_entrada = _estimar_tokens_local(corpo)
    # Nunca um palpite solto: o teto de saída é o MESMO MAX_TOKENS que o
    # payload real leva para `messages.create` — se `location_advisor.py`
    # mudar esse teto, a estimativa acompanha sem precisar de ajuste aqui.
    teto_tokens_saida = corpo.get("max_tokens", 0)

    custo_entrada_usd = tokens_entrada / 1_000_000 * PRECO_ENTRADA_USD_POR_MTOK
    teto_custo_saida_usd = teto_tokens_saida / 1_000_000 * PRECO_SAIDA_USD_POR_MTOK
    teto_custo_total_usd = custo_entrada_usd + teto_custo_saida_usd

    return CustoEstimado(
        tokens_entrada=tokens_entrada,
        entrada_exata=False,
        custo_entrada_usd=custo_entrada_usd,
        teto_tokens_saida=teto_tokens_saida,
        teto_custo_saida_usd=teto_custo_saida_usd,
        teto_custo_total_usd=teto_custo_total_usd,
        teto_custo_total_brl=teto_custo_total_usd * cambio_usd_brl,
        cambio_usd_brl=cambio_usd_brl,
        cambio_fonte=CAMBIO_FONTE_PADRAO,
    )


def contar_exato(client, corpo: dict) -> int:
    """Contagem exata de tokens de entrada — só depois da confirmação.

    Esta é a ÚNICA função deste módulo que transmite o payload para
    `api.anthropic.com` (via `client.messages.count_tokens`), e por isso
    o chamador (07-04) só pode invocá-la depois que o dono clicar
    "Confirmar e classificar" — chamá-la antes disso reabriria exatamente
    a violação do critério 2 do ROADMAP que D-079 resolveu.

    `max_tokens` é removido do corpo antes da chamada: é um parâmetro de
    GERAÇÃO (quanto o modelo pode responder), não de CONTAGEM DE ENTRADA,
    e `count_tokens` não o aceita.

    Mesmo contrato never-crash do 07-02: qualquer exceção (rede, auth,
    parâmetro não suportado pela versão do SDK) devolve `0` e loga, nunca
    propaga — uma falha aqui não pode travar o resumo pós-execução, que
    já tem a classificação em mãos e só está tentando mostrar o custo
    real dela.
    """
    corpo_sem_max_tokens = {k: v for k, v in corpo.items() if k != "max_tokens"}
    try:
        return client.messages.count_tokens(**corpo_sem_max_tokens).input_tokens
    except Exception as exc:
        log.warning("contagem exata de tokens indisponível: %s", exc)
        return 0
