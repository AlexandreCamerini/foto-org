"""Pré-filtro D-01 — pastas candidatas à classificação de pasta por GenAI.

O dono nunca digita nada aqui: o sistema lista sozinho toda pasta com AO
MENOS UM dos dois campos-alvo (categoria, cidade/país) ainda vazio. Isto
é o que decide QUANTO custa a sessão (07-04 monta o payload só com estas
pastas) e QUEM aparece no passo 1 do assistente (07-06) — errar este
filtro para mais gera custo sem necessidade, errar para menos esconde
pasta que precisava de ajuda.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fotoorganizer.models import Evidence, MediaFile

# Os dois campos-alvo deste recurso. "cidade_pais" é tratado como UM campo
# lógico (basta um dos dois estar resolvido para o par contar como
# preenchido) — mesma granularidade que o passo 1 da UI mostra ao dono
# (07-UI-SPEC.md § Step 1, tag "categoria" / "cidade/país").
_CAMPOS_DE_LUGAR = ("cidade", "pais")


@dataclass(frozen=True, slots=True)
class CandidataDePasta:
    """Uma pasta que o pré-filtro D-01 decidiu incluir na sessão."""

    pasta: str
    n_fotos: int
    campos_ausentes: tuple[str, ...]   # ("categoria",) | ("cidade_pais",) | ambos
    periodo: str | None                # "2024-03-12 a 2024-03-19" ou None


def candidatas(
    session: Session, ja_classificadas: set[str]
) -> list[CandidataDePasta]:
    """Pastas com categoria OU cidade/país vazios, prontas para a sessão.

    Duas consultas agregadas sobre o catálogo inteiro — nunca uma consulta
    por pasta (mesma disciplina de `engine.py::_carregar_curadoria`, que
    já resolveu o mesmo problema de N+1 para outra pergunta). A primeira
    conta fotos e período por pasta; a segunda descobre, por pasta, quais
    dos dois campos-alvo já têm ao menos uma linha de `Evidence`. As duas
    são combinadas em memória.

    `MediaFile.organizavel` é o filtro em AMBAS as consultas — não só na
    contagem. Miniatura de cache (Apple Fotos) e referência de catálogo
    externo (Lightroom) doam sinal para outras partes do produto (GPS,
    correlação temporal) mas não são acervo do dono (invariante 8): elas
    nunca aparecem na grade, na revisão nem no plano de cópia, então
    classificar a PASTA delas por GenAI gastaria dinheiro produzindo uma
    sugestão que nunca chega a existir para ninguém revisar. Pelo mesmo
    motivo, uma `Evidence` presa a uma mídia não-organizável não pode
    "resolver" um campo aos olhos deste filtro — senão uma pasta cuja
    única mídia é uma miniatura com `categoria` já inferida pareceria
    completa, quando na verdade não tem nenhuma foto real classificada.
    Uma pasta cujas mídias são só não-acervo simplesmente não aparece na
    primeira consulta (o `WHERE organizavel` a exclui por completo) e por
    isso nunca vira candidata.

    `ja_classificadas` chega de fora (será
    `ClassificacaoPastaRepository.conhecidas()` no plano 07-04) — este
    módulo não importa o repositório, para não acoplar o pré-filtro à
    camada de persistência e para o teste deste arquivo não precisar da
    tabela `pasta_classificacoes_genai`.
    """
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

    linhas_de_evidencia = session.execute(
        select(Evidence.campo, MediaFile.pasta)
        .join(MediaFile, Evidence.media_id == MediaFile.id)
        .where(
            MediaFile.organizavel,
            Evidence.campo.in_(("categoria",) + _CAMPOS_DE_LUGAR),
        )
    ).all()

    campos_por_pasta: dict[str, set[str]] = {}
    for campo, pasta in linhas_de_evidencia:
        campos_por_pasta.setdefault(pasta, set()).add(campo)

    resultado: list[CandidataDePasta] = []
    for pasta, n_fotos, minimo, maximo in agregados:
        if pasta in ja_classificadas:
            continue

        campos_resolvidos = campos_por_pasta.get(pasta, set())
        ausentes: list[str] = []
        if "categoria" not in campos_resolvidos:
            ausentes.append("categoria")
        if not campos_resolvidos.intersection(_CAMPOS_DE_LUGAR):
            ausentes.append("cidade_pais")
        if not ausentes:
            continue  # categoria E cidade/país resolvidos: não é candidata

        periodo = None
        if minimo is not None and maximo is not None:
            periodo = f"{minimo:%Y-%m-%d} a {maximo:%Y-%m-%d}"

        resultado.append(CandidataDePasta(
            pasta=pasta,
            n_fotos=n_fotos,
            campos_ausentes=tuple(ausentes),
            periodo=periodo,
        ))

    resultado.sort(key=lambda c: c.pasta)
    return resultado
