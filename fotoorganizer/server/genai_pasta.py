"""Sessão de classificação de pasta por GenAI — o gate de dois
consentimentos e o ciclo candidatas → custo → rodar → aprovar por trás dos
endpoints `/api/genai-pasta/*` (`fotoorganizer/server/app.py`).

Liga as três peças da Wave 1 desta fase (07-01 persistência, 07-02 cliente
Claude, 07-03 pré-filtro + custo) atrás de um gate que exige a CONJUNÇÃO de
dois consentimentos: `servicos_externos` (chave MESTRA, invariante 4,
TOML-only) E `classificacao_pasta_genai` (opt-in PRÓPRIO deste recurso,
gravável pela UI via `SettingsRepository` — D-080). Copiar o gate de UM
flag só, como `jobs.py::_advisor` faz para o Advisor de cluster, é a
regressão nomeada em `07-RESEARCH.md` Pitfall 4: este recurso não pega
carona no consentimento já dado ao Advisor.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.classification import candidatas_de_pasta, custo_genai
from fotoorganizer.classification.location_advisor import (
    ClassificacaoDePastaNula,
    ClassificadorDePasta,
    PastaPayload,
    PropostaDoModelo,
)
from fotoorganizer.config.settings import Settings
from fotoorganizer.models import Evidence, MediaFile
from fotoorganizer.repositories.pasta_classificacao import (
    ClassificacaoPastaRepository,
    PropostaDePasta,
)
from fotoorganizer.repositories.settings import SettingsRepository

log = logging.getLogger(__name__)

# Copywriting Contract (07-UI-SPEC.md § Master-switch-off message) — texto
# literal, não parafrasear: a UI reusa exatamente esta string.
MENSAGEM_MESTRE_DESLIGADO = (
    "Serviços externos estão desligados nas configurações do app — habilite "
    "[privacidade] servicos_externos antes de usar este recurso."
)

# Mensagem de defesa em profundidade: a UI nunca deveria deixar o dono
# chegar aqui com o gate fechado (o passo 0 do assistente bloqueia antes),
# mas um cliente HTTP direto (curl, extensão) pode. Mesmo título do "Opt-in
# gate heading" do Copywriting Contract, para não inventar cópia nova.
MENSAGEM_GATE_FECHADO = (
    "Classificação de pasta por IA está desligada — habilite os dois "
    "consentimentos (serviços externos e o opt-in do recurso) antes de "
    "continuar."
)

_CAMPOS_DE_VALOR = ("categoria", "cidade", "pais", "evento")


class RecursoDesligado(Exception):
    """Levantada por `candidatas()`/`estimar_custo()`/`rodar()` quando o
    gate de dois consentimentos está fechado. O endpoint converte isto em
    `HTTPException(409, ...)`."""


class ClassificacaoIndisponivel(Exception):
    """Levantada quando o classificador escapa do próprio contrato
    never-crash (nunca deveria acontecer — `ClassificacaoDePastaClaude` já
    captura tudo internamente — mas se acontecer o servidor não pode cair).
    O endpoint converte isto em `HTTPException(502, ...)`."""


def _candidata_json(c: candidatas_de_pasta.CandidataDePasta) -> dict:
    return {
        "pasta": c.pasta,
        "n_fotos": c.n_fotos,
        "campos_ausentes": list(c.campos_ausentes),
        "periodo": c.periodo,
    }


def _custo_json(c: custo_genai.CustoEstimado) -> dict:
    return {
        "tokens_entrada": c.tokens_entrada,
        "entrada_exata": c.entrada_exata,
        "custo_entrada_usd": c.custo_entrada_usd,
        "teto_tokens_saida": c.teto_tokens_saida,
        "teto_custo_saida_usd": c.teto_custo_saida_usd,
        "teto_custo_total_usd": c.teto_custo_total_usd,
        "teto_custo_total_brl": c.teto_custo_total_brl,
        "cambio_usd_brl": c.cambio_usd_brl,
        "cambio_fonte": c.cambio_fonte,
    }


def _achatar_proposta(pasta: str, valores: dict[str, str | None], justificativa: str) -> list[dict]:
    """Uma entrada por CAMPO proposto — nunca uma por pasta. `valor_antes`
    é sempre `None`: o pré-filtro (D-01) garante que só campo VAZIO chega
    aqui como candidato."""
    return [
        {
            "pasta": pasta,
            "campo": campo,
            "valor_antes": None,
            "valor_proposto": valor,
            "justificativa": justificativa,
        }
        for campo in _CAMPOS_DE_VALOR
        if (valor := valores.get(campo)) is not None
    ]


class SessaoDeClassificacaoDePasta:
    def __init__(
        self,
        settings: Settings,
        session_factory: sessionmaker[Session],
        classificador: ClassificadorDePasta | None = None,
    ) -> None:
        self._settings = settings
        self._session_factory = session_factory
        self._settings_repo = SettingsRepository(session_factory)
        self._classificacao_repo = ClassificacaoPastaRepository(session_factory)
        # Injeção para teste; quando `None`, `_resolver_classificador()`
        # resolve sozinho a partir do gate.
        self._classificador_injetado = classificador

    # -- gate -----------------------------------------------------------
    def liberado(self) -> bool:
        """A conjunção dos DOIS consentimentos — nunca um só (D-080,
        07-RESEARCH.md Pitfall 4)."""
        return (
            self._settings.privacidade.servicos_externos
            and self._settings_repo.genai_pasta_habilitado()
        )

    def config(self) -> dict:
        return {
            "servicos_externos": self._settings.privacidade.servicos_externos,
            "classificacao_pasta_genai": self._settings_repo.genai_pasta_habilitado(),
        }

    def habilitar(self, habilitado: bool) -> dict:
        """Grava só o opt-in PRÓPRIO — nunca a chave mestra (T-07-04-02).
        Levanta `ValueError` quando `habilitado=True` e o mestre está
        desligado; o endpoint converte isto em 409 com a mensagem exata do
        Copywriting Contract."""
        if habilitado and not self._settings.privacidade.servicos_externos:
            raise ValueError(MENSAGEM_MESTRE_DESLIGADO)
        self._settings_repo.definir_genai_pasta(habilitado)
        return self.config()

    def _resolver_classificador(self) -> ClassificadorDePasta:
        if self._classificador_injetado is not None:
            return self._classificador_injetado
        if not self.liberado():
            return ClassificacaoDePastaNula()
        try:
            from fotoorganizer.classification.location_advisor import (
                ClassificacaoDePastaClaude,
            )

            return ClassificacaoDePastaClaude()
        except Exception as exc:
            log.warning(
                "classificador de pasta indisponível (%s); seguindo local", exc
            )
            return ClassificacaoDePastaNula()

    # -- candidatas -------------------------------------------------------
    def _candidatas_atuais(self) -> list[candidatas_de_pasta.CandidataDePasta]:
        with self._session_factory() as session:
            return candidatas_de_pasta.candidatas(
                session, self._classificacao_repo.conhecidas()
            )

    def candidatas(self) -> list[dict]:
        if not self.liberado():
            raise RecursoDesligado(MENSAGEM_GATE_FECHADO)
        return [_candidata_json(c) for c in self._candidatas_atuais()]

    def _payloads(self, pastas: list[str]) -> list[PastaPayload]:
        """Monta os `PastaPayload` das pastas PEDIDAS que ainda são
        candidatas de verdade agora — uma pasta pedida que já saiu da
        lista de candidatas (o catálogo mudou entre o passo 1 e o passo 2
        do assistente, ou foi classificada por outra sessão) é ignorada,
        não vira erro (T-07-04-03: reconcilia contra as candidatas reais,
        nunca confia cegamente no corpo da requisição)."""
        candidatas_por_pasta = {c.pasta: c for c in self._candidatas_atuais()}
        confirmadas = [p for p in pastas if p in candidatas_por_pasta]
        if not confirmadas:
            return []

        # Uma consulta agregada para TODAS as pastas confirmadas — nunca
        # uma consulta por pasta (mesma disciplina de
        # candidatas_de_pasta.py::candidatas). Só os campos que ainda são
        # relevantes ao payload (D-02: o modelo precisa saber o valor já
        # confirmado para não propor de novo).
        with self._session_factory() as session:
            linhas = session.execute(
                select(Evidence.campo, Evidence.valor, MediaFile.pasta)
                .join(MediaFile, Evidence.media_id == MediaFile.id)
                .where(
                    MediaFile.organizavel,
                    MediaFile.pasta.in_(confirmadas),
                    Evidence.campo.in_(("categoria", "cidade", "pais")),
                )
            ).all()

        conhecidos_por_pasta: dict[str, dict[str, str]] = {}
        for campo, valor, pasta in linhas:
            if valor is None:
                continue
            conhecidos_por_pasta.setdefault(pasta, {}).setdefault(campo, valor)

        payloads: list[PastaPayload] = []
        for pasta in confirmadas:
            c = candidatas_por_pasta[pasta]
            campos_a_preencher: list[str] = []
            if "categoria" in c.campos_ausentes:
                campos_a_preencher.append("categoria")
            if "cidade_pais" in c.campos_ausentes:
                campos_a_preencher.extend(["cidade", "pais"])
            payloads.append(PastaPayload(
                pasta=pasta,
                n_fotos=c.n_fotos,
                periodo=c.periodo,
                campos_a_preencher=tuple(campos_a_preencher),
                ja_conhecido=conhecidos_por_pasta.get(pasta, {}),
            ))
        return payloads

    # -- custo --------------------------------------------------------------
    def estimar_custo(self, pastas: list[str]) -> dict:
        if not self.liberado():
            raise RecursoDesligado(MENSAGEM_GATE_FECHADO)
        payloads = self._payloads(pastas)
        if not payloads:
            # Sessão vazia: zero sem invocar o classificador (nem sequer
            # resolvê-lo) — não há nada a estimar.
            return _custo_json(
                custo_genai.estimar({}, custo_genai.CAMBIO_USD_BRL_PADRAO)
            )
        classificador = self._resolver_classificador()
        corpo = classificador.corpo_da_chamada(payloads)
        return _custo_json(
            custo_genai.estimar(corpo, custo_genai.CAMBIO_USD_BRL_PADRAO)
        )

    def _custo_real(self, classificador: ClassificadorDePasta, corpo: dict) -> dict | None:
        """Contagem exata de tokens de entrada — só chamada DEPOIS que a
        chamada ao modelo já rodou (a mesma transmissão consentida, D-079).
        `None` quando o classificador é local/nulo (nada foi transmitido,
        não há custo real a mostrar) ou quando `contar_exato()` falhou
        (never-crash, 07-03) — o passo 5 da UI cai no fallback de
        estimativa nesse caso."""
        if classificador.local or not corpo:
            return None
        client = getattr(classificador, "_client", None)
        if client is None:
            return None
        tokens_exatos = custo_genai.contar_exato(client, corpo)
        if tokens_exatos == 0:
            return None
        custo_entrada_usd = (
            tokens_exatos / 1_000_000 * custo_genai.PRECO_ENTRADA_USD_POR_MTOK
        )
        teto_tokens_saida = corpo.get("max_tokens", 0)
        teto_custo_saida_usd = (
            teto_tokens_saida / 1_000_000 * custo_genai.PRECO_SAIDA_USD_POR_MTOK
        )
        teto_custo_total_usd = custo_entrada_usd + teto_custo_saida_usd
        cambio = custo_genai.CAMBIO_USD_BRL_PADRAO
        return {
            "tokens_entrada": tokens_exatos,
            "entrada_exata": True,
            "custo_entrada_usd": custo_entrada_usd,
            "teto_tokens_saida": teto_tokens_saida,
            "teto_custo_saida_usd": teto_custo_saida_usd,
            "teto_custo_total_usd": teto_custo_total_usd,
            "teto_custo_total_brl": teto_custo_total_usd * cambio,
            "cambio_usd_brl": cambio,
            "cambio_fonte": custo_genai.CAMBIO_FONTE_PADRAO,
        }

    # -- rodar / propostas / aprovar -----------------------------------------
    def rodar(self, pastas: list[str]) -> dict:
        if not self.liberado():
            raise RecursoDesligado(MENSAGEM_GATE_FECHADO)

        payloads = self._payloads(pastas)
        if not payloads:
            return {
                "propostas": [],
                "pastas_sem_resposta": list(pastas),
                "custo_real": None,
            }

        classificador = self._resolver_classificador()
        corpo = classificador.corpo_da_chamada(payloads)
        try:
            # UMA chamada para a lista inteira (D-03) — o classificador já
            # não deveria levantar (never-crash, 07-02), mas se algo
            # escapar mesmo assim, o servidor não pode cair.
            resultado: list[PropostaDoModelo] = classificador.classificar(payloads)
        except Exception as exc:
            log.warning("classificação de pasta falhou de forma inesperada: %s", exc)
            raise ClassificacaoIndisponivel(str(exc)) from exc

        sessao = datetime.now(timezone.utc).isoformat()
        propostas_para_gravar = [
            PropostaDePasta(
                pasta=p.pasta, cidade=p.cidade, pais=p.pais,
                categoria=p.categoria, evento=p.evento,
                justificativa=p.justificativa,
            )
            for p in resultado
        ]
        if propostas_para_gravar:
            self._classificacao_repo.salvar_propostas(
                propostas_para_gravar, sessao=sessao
            )

        pastas_pedidas = {p.pasta for p in payloads}
        pastas_respondidas = {p.pasta for p in resultado}
        pastas_sem_resposta = sorted(pastas_pedidas - pastas_respondidas)

        propostas_achatadas = [
            linha
            for p in resultado
            for linha in _achatar_proposta(
                p.pasta,
                {
                    "categoria": p.categoria, "cidade": p.cidade,
                    "pais": p.pais, "evento": p.evento,
                },
                p.justificativa,
            )
        ]

        custo_real = None
        try:
            custo_real = self._custo_real(classificador, corpo)
        except Exception as exc:  # never deixar o resumo pós-execução cair
            log.warning("contagem exata de custo real indisponível: %s", exc)
            custo_real = None

        return {
            "propostas": propostas_achatadas,
            "pastas_sem_resposta": pastas_sem_resposta,
            "custo_real": custo_real,
        }

    def propostas_pendentes(self) -> list[dict]:
        """O que ainda está em `status='proposta'` — permite ao dono
        reabrir uma sessão paga depois de um refresh do navegador sem
        pagar de novo. Não exige o gate (o dono pode ter desligado o
        recurso e ainda assim precisar rever o que já foi pago)."""
        pendentes = self._classificacao_repo.propostas()
        return [
            linha
            for pasta, proposta in pendentes.items()
            for linha in _achatar_proposta(
                pasta,
                {
                    "categoria": proposta.categoria, "cidade": proposta.cidade,
                    "pais": proposta.pais, "evento": proposta.evento,
                },
                proposta.justificativa,
            )
        ]

    def aprovar(self, pastas: list[str]) -> dict:
        """Aprova as listadas, descarta as demais que estavam em
        'proposta'. Nenhuma linha é apagada em nenhum caminho
        (invariante 8)."""
        todas_pendentes = set(self._classificacao_repo.propostas().keys())
        aprovadas = self._classificacao_repo.aprovar(pastas)
        restantes = sorted(todas_pendentes - set(pastas))
        descartadas = self._classificacao_repo.descartar(restantes)
        return {"aprovadas": aprovadas, "descartadas": descartadas}
