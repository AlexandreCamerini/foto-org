#!/usr/bin/env python3
"""Mede acerto/abstenção/erro do classificador de PASTA (07-02) contra a
verdade determinística do próprio catálogo — o método de D-059/D-060 (Sonnet
sobre Haiku, medido) e D-074 (calibração de GPS contra 40.678 fotos),
aplicado a `SCORES_REFERENCIA["llm_pasta"]` (07-05), hoje `0.55` e marcado
`PROVISÓRIO` até esta medição existir (07-09, GENAI-03).

O truque da medição: a verdade de referência é o PRÓPRIO catálogo. Uma pasta
cuja `categoria` e/ou `cidade`/`país` já foi resolvida pela cascata
DETERMINÍSTICA (origem `pasta`, `gps`, `geocoding_offline` — a mesma família
que `docs/CONFIANCA.md` classifica como alta/média por evidência objetiva,
nunca opinião de modelo) tem resposta certa conhecida SEM perguntar a
ninguém. Este script pega essas pastas, monta o `PastaPayload` EXATO que a
produção (`location_advisor.py`) enviaria, com o(s) campo(s) em medição
marcados como `campos_a_preencher` (e portanto ausentes de `ja_conhecido` —
o modelo nunca vê a resposta), manda ao Claude e compara a proposta com a
verdade.

ATENÇÃO — este script, fora de `--dry-run`, ENVIA nome de pasta e metadado
já catalogado (contagem de fotos, período) para a api.anthropic.com — é a
ação que `docs/prompts/00-protocolo.md` classifica como Classe C. Só rode
isto você mesmo, no seu terminal, com a sua própria credencial exportada no
ambiente (a variável que o SDK oficial já espera, documentada no README da
Anthropic): esta sessão de desenvolvimento não manuseia nem menciona essa
credencial em lugar nenhum (mesmo protocolo de D-048/D-049/D-059).
`client = anthropic.Anthropic()` resolve o segredo sozinho, a partir do SEU
ambiente — nada aqui lê, guarda ou registra em log o valor dela. Rode
`--dry-run` primeiro, sempre: monta a amostra e imprime o custo estimado
sem chamar a API (não precisa de credencial nenhuma no ambiente para isso).

SOMENTE LEITURA: abre o catálogo, não grava nada nele, não altera
`confidence.py` (isso é trabalho da Task 3 deste plano, depois que você
decidir o número com o relatório desta medição em mãos).

Uso:
    .venv/bin/python scripts/medir_score_llm_pasta.py --dry-run --limite 60
    .venv/bin/python scripts/medir_score_llm_pasta.py --limite 60
    # (a segunda chamada exige a credencial da Anthropic exportada no seu
    # ambiente antes de rodar — este script não a define nem a lê por nome)
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from fotoorganizer.classification import custo_genai  # noqa: E402
from fotoorganizer.classification.location_advisor import (  # noqa: E402
    ClassificacaoDePastaClaude,
    PastaPayload,
    PropostaDoModelo,
)
from fotoorganizer.config import paths  # noqa: E402
from fotoorganizer.database.engine import create_db_engine, create_session_factory  # noqa: E402
from fotoorganizer.geolocation.folder_names import _normalizar as normalizar_local  # noqa: E402
from fotoorganizer.models import Evidence, MediaFile  # noqa: E402

# As únicas origens que contam como "resposta certa conhecida sem perguntar
# a ninguém" — cascata determinística, nunca opinião de modelo (advisor
# `llm`, GenAI de pasta `llm_pasta`) nem inferência por proximidade
# (`vizinhanca`/`vizinhanca_temporal`) ou palavra do dono em metadado de
# terceiro (`curadoria`/`album_externo`). `exif` está na lista por
# completude do vocabulário de `confidence.py` (data DateTimeOriginal); não
# alimenta categoria/cidade/país hoje, mas se um dia alimentar, já está
# coberto sem precisar tocar este script de novo.
ORIGENS_DETERMINISTICAS = frozenset({"pasta", "gps", "geocoding_offline", "exif"})

_CAMPOS_LUGAR = ("cidade", "pais")

# Preço de referência — mesma constante de `custo_genai.py` (D-079), só
# para o dono ver o custo em BRL na prévia sem precisar converter de cabeça.
_CAMBIO_USD_BRL = custo_genai.CAMBIO_USD_BRL_PADRAO


@dataclass(frozen=True, slots=True)
class ItemDeAmostra:
    """Uma pasta da amostra, com a verdade determinística conhecida para
    pelo menos um dos dois grupos (categoria | cidade_pais) e o payload
    exato que seria mandado ao modelo."""

    pasta: str
    payload: PastaPayload
    verdade_categoria: str | None
    verdade_cidade: str | None
    verdade_pais: str | None


def _abrir_sessao(db: Path) -> Session:
    engine = create_db_engine(db)
    factory = create_session_factory(engine)
    return factory()


def _verdade_por_pasta(session: Session) -> dict[str, dict[str, str]]:
    """pasta -> {campo: valor}, só quando TODAS as linhas de evidência
    determinística daquele campo, naquela pasta, concordam no valor.

    Discordância dentro da mesma pasta (uma pasta cujas fotos têm GPS em
    dois países, por exemplo) não vira verdade nenhuma para aquele campo —
    inventar uma "verdade" ambígua contaminaria a medição, que é exatamente
    o erro que este script existe para não cometer.
    """
    linhas = session.execute(
        select(Evidence.campo, Evidence.valor, MediaFile.pasta)
        .join(MediaFile, Evidence.media_id == MediaFile.id)
        .where(
            MediaFile.organizavel,
            Evidence.campo.in_(("categoria",) + _CAMPOS_LUGAR),
            Evidence.origem.in_(ORIGENS_DETERMINISTICAS),
        )
    ).all()

    valores: dict[str, dict[str, set[str]]] = {}
    for campo, valor, pasta in linhas:
        if valor is None:
            continue
        valores.setdefault(pasta, {}).setdefault(campo, set()).add(valor)

    verdade: dict[str, dict[str, str]] = {}
    for pasta, por_campo in valores.items():
        for campo, vistos in por_campo.items():
            if len(vistos) == 1:
                verdade.setdefault(pasta, {})[campo] = next(iter(vistos))
    return verdade


def _metadado_por_pasta(session: Session) -> dict[str, tuple[int, str | None]]:
    """pasta -> (n_fotos, periodo) — mesma consulta agregada de
    `candidatas_de_pasta.candidatas()`, sem laço por pasta."""
    agregados = session.execute(
        select(
            MediaFile.pasta,
            func.count(MediaFile.id),
            func.min(MediaFile.data_capturada),
            func.max(MediaFile.data_capturada),
        )
        .where(MediaFile.organizavel)
        .group_by(MediaFile.pasta)
    ).all()
    saida: dict[str, tuple[int, str | None]] = {}
    for pasta, n_fotos, minimo, maximo in agregados:
        periodo = None
        if minimo is not None and maximo is not None:
            periodo = f"{minimo:%Y-%m-%d} a {maximo:%Y-%m-%d}"
        saida[pasta] = (n_fotos, periodo)
    return saida


def montar_amostra(session: Session, limite: int | None) -> list[ItemDeAmostra]:
    verdade = _verdade_por_pasta(session)
    metadado = _metadado_por_pasta(session)

    itens: list[ItemDeAmostra] = []
    for pasta in sorted(verdade):
        v = verdade[pasta]
        v_categoria = v.get("categoria")
        v_cidade = v.get("cidade")
        v_pais = v.get("pais")
        if v_categoria is None and v_cidade is None and v_pais is None:
            continue  # não deveria acontecer (verdade só existe com >=1 campo)

        campos_a_preencher: list[str] = []
        if v_categoria is not None:
            campos_a_preencher.append("categoria")
        if v_cidade is not None or v_pais is not None:
            campos_a_preencher.extend(_CAMPOS_LUGAR)

        n_fotos, periodo = metadado.get(pasta, (0, None))
        payload = PastaPayload(
            pasta=pasta,
            n_fotos=n_fotos,
            periodo=periodo,
            campos_a_preencher=tuple(campos_a_preencher),
            # O campo em medição NUNCA aparece aqui — é o que garante que o
            # modelo não vê a resposta, nem no `ja_conhecido` nem em outro
            # canal do payload.
            ja_conhecido={},
        )
        itens.append(ItemDeAmostra(
            pasta=pasta,
            payload=payload,
            verdade_categoria=v_categoria,
            verdade_cidade=v_cidade,
            verdade_pais=v_pais,
        ))
        if limite is not None and len(itens) >= limite:
            break
    return itens


# -- comparação -------------------------------------------------------------

@dataclass
class ContadorDeCampo:
    acertou: int = 0
    recusou: int = 0
    errou: int = 0
    exemplos_erro: list[tuple[str, str, str]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.acertou + self.recusou + self.errou

    def registrar(self, pasta: str, verdade: str, proposto: str | None,
                   normalizar: bool) -> None:
        if proposto is None:
            self.recusou += 1
            return
        a, b = (verdade, proposto)
        if normalizar:
            a, b = normalizar_local(a), normalizar_local(b)
        if a == b:
            self.acertou += 1
        else:
            self.errou += 1
            if len(self.exemplos_erro) < 10:
                self.exemplos_erro.append((pasta, verdade, proposto))

    def linha(self, rotulo: str) -> str:
        if self.total == 0:
            return f"  {rotulo}: nenhum item na amostra"
        return (
            f"  {rotulo}: {self.total} itens — "
            f"acertou {self.acertou} ({100*self.acertou/self.total:.1f}%)  "
            f"recusou {self.recusou} ({100*self.recusou/self.total:.1f}%)  "
            f"errou {self.errou} ({100*self.errou/self.total:.1f}%)"
        )


def comparar(itens: list[ItemDeAmostra],
             propostas: list[PropostaDoModelo]) -> dict[str, ContadorDeCampo]:
    por_pasta = {p.pasta: p for p in propostas}
    contadores = {
        "categoria": ContadorDeCampo(),
        "cidade": ContadorDeCampo(),
        "pais": ContadorDeCampo(),
    }
    for item in itens:
        proposta = por_pasta.get(item.pasta)  # None = recusa total da pasta
        if "categoria" in item.payload.campos_a_preencher:
            proposto = proposta.categoria if proposta else None
            contadores["categoria"].registrar(
                item.pasta, item.verdade_categoria, proposto, normalizar=False
            )
        if "cidade" in item.payload.campos_a_preencher and item.verdade_cidade:
            proposto = proposta.cidade if proposta else None
            contadores["cidade"].registrar(
                item.pasta, item.verdade_cidade, proposto, normalizar=True
            )
        if "pais" in item.payload.campos_a_preencher and item.verdade_pais:
            proposto = proposta.pais if proposta else None
            contadores["pais"].registrar(
                item.pasta, item.verdade_pais, proposto, normalizar=True
            )
    return contadores


def imprimir_relatorio(itens: list[ItemDeAmostra],
                        contadores: dict[str, ContadorDeCampo]) -> None:
    print(f"\n{'='*70}")
    print(f"RELATÓRIO — {len(itens)} pastas na amostra")
    print(f"{'='*70}\n")

    print("CATEGORIA (separado de cidade/país — docs/CONFIANCA.md: são "
          "afirmações de natureza diferente, nunca somadas/misturadas)")
    print(contadores["categoria"].linha("categoria"))

    print("\nCIDADE/PAÍS (cada linha é o campo isolado; ambos vieram do "
          "MESMO payload, pedidos juntos como produção pede)")
    print(contadores["cidade"].linha("cidade"))
    print(contadores["pais"].linha("país"))

    todos_erros = (
        contadores["categoria"].exemplos_erro
        + contadores["cidade"].exemplos_erro
        + contadores["pais"].exemplos_erro
    )
    if todos_erros:
        print(f"\nAmostra literal de erros (até 10, para julgar se o erro é "
              f"do modelo ou da verdade de referência):")
        for pasta, verdade, proposto in todos_erros[:10]:
            print(f"  pasta={pasta!r}  verdade={verdade!r}  "
                  f"proposto={proposto!r}")


# -- main ---------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=paths.default_db_path())
    ap.add_argument(
        "--limite", type=int, default=None,
        help="quantas pastas entram na amostra (controla o custo). "
             "Sem isto, usa TODAS as pastas com verdade determinística — "
             "não recomendado sem rodar --dry-run antes para ver o tamanho.",
    )
    ap.add_argument(
        "--dry-run", action="store_true",
        help="monta a amostra e imprime o custo estimado, sem chamar a API "
             "(não precisa de credencial nenhuma no ambiente).",
    )
    args = ap.parse_args()

    if not args.db.exists():
        print(f"catálogo não encontrado: {args.db}", file=sys.stderr)
        return 1

    session = _abrir_sessao(args.db)
    try:
        itens = montar_amostra(session, args.limite)
    finally:
        session.close()

    if not itens:
        print("nenhuma pasta com verdade determinística encontrada — "
              "nada para medir neste catálogo.", file=sys.stderr)
        return 1

    print(f"amostra: {len(itens)} pastas "
          f"(categoria: {sum('categoria' in i.payload.campos_a_preencher for i in itens)}, "
          f"cidade/país: {sum('cidade' in i.payload.campos_a_preencher for i in itens)})")

    # Corpo/custo montados SEM credencial: `client` é um stub — só usado
    # para ler `self._model`, nunca para chamar rede (T-07-09-03).
    payloads = [item.payload for item in itens]
    classificador_para_custo = ClassificacaoDePastaClaude(client=object())
    corpo = classificador_para_custo.corpo_da_chamada(payloads)
    custo = custo_genai.estimar(corpo, _CAMBIO_USD_BRL)
    print(
        f"custo estimado: ~{custo.tokens_entrada} tokens de entrada, "
        f"teto de {custo.teto_tokens_saida} de saída — "
        f"US$ {custo.teto_custo_total_usd:.4f} "
        f"(R$ {custo.teto_custo_total_brl:.4f}, câmbio de referência, "
        f"{custo.cambio_fonte})"
    )

    if args.dry_run:
        print("\n--dry-run: nenhuma chamada à API foi feita.")
        return 0

    # Só a partir daqui a credencial é resolvida — pelo SDK, do ambiente do
    # dono, nunca lida ou logada por este script (T-07-09-03).
    classificador = ClassificacaoDePastaClaude()
    propostas = classificador.classificar(payloads)

    contadores = comparar(itens, propostas)
    imprimir_relatorio(itens, contadores)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
