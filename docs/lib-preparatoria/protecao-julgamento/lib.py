"""Proteção da camada de julgamento — export legível, backup com retenção,
checagem de esquema no boot.

Staging fora de `fotoorganizer/**` (protocolo em `docs/prompts/00-protocolo.md`).
Reimplementa o MECANISMO descrito em `docs/prompts/fase-14-photoprism-e-sintese.md`
§4 (Item B) — nunca código do PhotoPrism ou do Immich (AGPLv3). O mecanismo
copiado é a FORMA (export legível + rotina agendável com retenção do
PhotoPrism, checagem de esquema no boot do Immich), descrita em
`docs/referencia-photoprism/` e `docs/referencia-immich/`; a implementação
abaixo nasce do schema e dos scripts reais do foto-organizer.

Três mecanismos, cada um self-contained e testável sem o resto do app:

1. `exportar_julgamento` — dump legível (JSON) de `evidence` + decisões
   (`Suggestion`), para diff e revisão em git. Aceita dados já lidos do
   banco (dicts), não SQLAlchemy: mantém este módulo sem dependência do ORM
   do foto-organizer. Ver README para o ponto exato de leitura real.
2. `executar_backup_com_retencao` / `deve_rodar_backup` — mesmo padrão
   `sqlite3 .backup` já usado em quatro scripts do projeto (ver README),
   com a peça que falta: rotação por retenção configurável e uma função
   pura de agendamento, testável sem esperar relógio de verdade.
3. `verificar_esquema` — compara a revisão Alembic gravada no banco com a
   esperada pelo app e recusa abrir com uma mensagem clara em vez de deixar
   o erro estourar mais adiante como "duplicate column" ou pior, em
   silêncio. Cobre exatamente o risco que D-038 registra sobre a migração
   `0014` não ser atômica.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

# --- 1. export legível ----------------------------------------------------
#
# Decisão de formato (Classe A, registrada em docs/DECISOES.md): JSON, não
# YAML. O prompt de origem descreve o mecanismo do PhotoPrism como YAML
# (`internal/photoprism/backup/albums.go:19`), mas dá liberdade de escolha
# aqui. JSON é biblioteca padrão (zero dependência nova — este item não
# pode editar `pyproject.toml` enquanto a fronteira estiver fechada, e nem
# depois isso deveria custar uma dependência para um export de manutenção),
# é git-diffable com `indent=2` e não perde nada de expressividade para o
# formato dos dados aqui (evidência e sugestão são registros achatados, sem
# a necessidade de comentário inline que YAML ofereceria).


@dataclass(frozen=True)
class LinhaEvidencia:
    """Espelha `fotoorganizer/models/inference.py:39-58` (`Evidence`), como
    dict simples — quem integrar preenche a partir do ORM real."""

    media_id: int
    campo: str
    origem: str
    valor: str
    nivel: str
    score: float
    justificativa: str
    versao_logica: str


@dataclass(frozen=True)
class LinhaSugestao:
    """Espelha `fotoorganizer/models/inference.py:61-79` (`Suggestion`)."""

    media_id: int
    destino_sugerido: str
    nivel: str
    status: str
    versao_logica: str


def exportar_julgamento(
    evidencias: list[LinhaEvidencia],
    sugestoes: list[LinhaSugestao],
    *,
    versao_logica_atual: str,
) -> dict:
    """Monta o documento exportável — puro, sem tocar disco.

    `salvar_export` grava o resultado. Separar as duas é o que torna esta
    função testável sem `tmp_path` nem I/O: dado o mesmo par de listas, a
    saída é sempre o mesmo dict.
    """
    return {
        "versao_logica_atual": versao_logica_atual,
        "gerado_em": None,  # o chamador real carimba (ver README — Date.now
        # equivalente não existe aqui de propósito; este módulo não tem
        # relógio próprio, o caller decide o timestamp).
        "evidencias": [_evidencia_para_dict(e) for e in evidencias],
        "sugestoes": [_sugestao_para_dict(s) for s in sugestoes],
    }


def _evidencia_para_dict(e: LinhaEvidencia) -> dict:
    return {
        "media_id": e.media_id,
        "campo": e.campo,
        "origem": e.origem,
        "valor": e.valor,
        "nivel": e.nivel,
        "score": e.score,
        "justificativa": e.justificativa,
        "versao_logica": e.versao_logica,
    }


def _sugestao_para_dict(s: LinhaSugestao) -> dict:
    return {
        "media_id": s.media_id,
        "destino_sugerido": s.destino_sugerido,
        "nivel": s.nivel,
        "status": s.status,
        "versao_logica": s.versao_logica,
    }


def salvar_export(documento: dict, destino: Path) -> Path:
    """Grava o export em JSON legível (`indent=2`, `ensure_ascii=False` —
    português com acento não vira `\\u00e9` no arquivo)."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(documento, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return destino


# --- 2. backup com retenção ------------------------------------------------
#
# Mesmo padrão já em produção nos scripts de manutenção:
# `scripts/preparar_versao.sh:121-125`, `scripts/rebaixar_nao_acervo.py:88-90`,
# `scripts/podar_metadados.py:55`, `scripts/medir_nome_de_album.py:105-110` —
# todos usam `sqlite3 .backup` (ou `sqlite3.Connection.backup()` em Python,
# em `medir_nome_de_album.py`) porque copiar o arquivo `.db` com `cp` pode
# capturar um WAL aberto em transação. O que falta é a retenção e o
# agendamento; a cópia em si já é disciplina validada.

_SUFIXO_BACKUP = "-backup-"
_FORMATO_CARIMBO = "%Y%m%d-%H%M%S"


def nome_backup(db_path: Path, agora: datetime) -> Path:
    carimbo = agora.strftime(_FORMATO_CARIMBO)
    return db_path.with_name(f"{db_path.stem}{_SUFIXO_BACKUP}{carimbo}.db")


def _copiar_com_backup_api(origem: Path, destino: Path) -> None:
    """`.backup()` do módulo padrão `sqlite3` — mesma API que
    `scripts/medir_nome_de_album.py:106-109` já usa, e o que
    `scripts/preparar_versao.sh`/`rebaixar_nao_acervo.py`/`podar_metadados.py`
    fazem via `sqlite3 .backup` na CLI. Ambos respeitam transação em curso;
    `shutil.copy2` de um WAL aberto não."""
    origem_con = sqlite3.connect(f"file:{origem}?mode=ro", uri=True)
    destino_con = sqlite3.connect(destino)
    try:
        with destino_con:
            origem_con.backup(destino_con)
    finally:
        origem_con.close()
        destino_con.close()


def fazer_backup(db_path: Path, agora: datetime) -> Path:
    """Copia o catálogo com segurança de WAL. Levanta se a cópia não existir
    ao final — mesmo contrato de `_copiar` nos scripts (nunca falha em
    silêncio: `scripts/podar_metadados.py:58-59`)."""
    destino = nome_backup(db_path, agora)
    if shutil.which("sqlite3"):
        subprocess.run(
            ["sqlite3", str(db_path), f".backup '{destino}'"], check=True
        )
    else:
        _copiar_com_backup_api(db_path, destino)
    if not destino.is_file():
        raise RuntimeError(f"não consegui copiar o catálogo — {destino} não existe")
    return destino


def listar_backups(db_path: Path) -> list[Path]:
    """Backups existentes do MESMO catálogo, do mais antigo ao mais novo —
    ordem lexicográfica do carimbo já é ordem cronológica (`%Y%m%d-%H%M%S`)."""
    padrao = f"{db_path.stem}{_SUFIXO_BACKUP}*.db"
    return sorted(db_path.parent.glob(padrao))


def aplicar_retencao(db_path: Path, reter: int) -> list[Path]:
    """Apaga os backups mais antigos além de `reter`. Devolve o que foi
    apagado — nunca apaga o catálogo real (só nomes que casam o padrão de
    backup) nem nada além do excedente."""
    if reter < 0:
        raise ValueError(f"reter precisa ser >= 0, recebi {reter}")
    existentes = listar_backups(db_path)
    excedente = existentes[: max(0, len(existentes) - reter)]
    for caminho in excedente:
        caminho.unlink()
    return excedente


def executar_backup_com_retencao(db_path: Path, agora: datetime, reter: int) -> Path:
    """O laço completo: copia, depois poda o excedente. Ordem importa — o
    backup novo entra na contagem antes da poda, então `reter=3` sempre
    deixa exatamente 3 arquivos (o novo incluso), nunca 2 durante a janela
    entre copiar e podar."""
    novo = fazer_backup(db_path, agora)
    aplicar_retencao(db_path, reter)
    return novo


def deve_rodar_backup(
    ultimo_backup: datetime | None, intervalo: timedelta, agora: datetime
) -> bool:
    """Função pura de agendamento — testável sem relógio de verdade nem
    scheduler real. Mecanismo equivalente ao `StartScheduled` descrito em
    `docs/referencia-photoprism/README.md` (rodar sozinho, não só quando
    alguém lembra), reduzido à decisão booleana que um laço externo (cron,
    thread com sleep, o que o app já tiver) consulta a cada tick."""
    if ultimo_backup is None:
        return True
    return agora - ultimo_backup >= intervalo


# --- 3. checagem de esquema no boot -----------------------------------------
#
# D-038 registra, por escrito, que a migração `0014` não é atômica: sob
# pysqlite `ADD COLUMN` comita sozinho, e uma interrupção entre a coluna
# criada e o `alembic_version` atualizado deixaria a tentativa seguinte
# morrer em "duplicate column name" — o app deixaria de abrir sem dizer por
# quê. Esta checagem roda ANTES do resto do boot e transforma esse cenário
# (e o de downgrade acidental) num erro com nome.


class EsquemaDivergente(RuntimeError):
    """Levantado quando o catálogo não está na revisão que o app espera.
    A mensagem sempre diz a revisão encontrada e a esperada — nunca só
    "erro ao abrir banco"."""


@dataclass(frozen=True)
class ResultadoChecagem:
    ok: bool
    revisao_encontrada: str | None
    revisao_esperada: str
    motivo: str | None = None


def verificar_esquema(
    con: sqlite3.Connection, revisao_esperada: str
) -> ResultadoChecagem:
    """Lê `alembic_version` (a mesma tabela que o Alembic do projeto já
    mantém — `fotoorganizer/database/migrate.py`) e decide um de três
    resultados:

    - tabela ausente: banco nunca migrado (ou arquivo não é o catálogo) —
      motivo `"nao_inicializado"`.
    - revisão abaixo da esperada: precisa migrar — o boot deve rodar
      `upgrade_to_head` antes de continuar, não é por si só um erro fatal
      aqui (quem chama decide); motivo `"desatualizado"`.
    - revisão acima da esperada: um catálogo de versão mais nova do app foi
      aberto por um binário mais antigo (downgrade) — recusa explícita,
      no espírito de `repositories/database.repository.ts:387-394` descrito
      em `docs/referencia-immich/`; motivo `"downgrade"`.

    Só o terceiro caso é sempre erro do ponto de vista do boot; os outros
    dois viram `ResultadoChecagem(ok=False, motivo=...)` para o chamador
    decidir (migrar automaticamente é comportamento já existente do app,
    não deste módulo).
    """
    linha = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'"
    ).fetchone()
    if linha is None:
        return ResultadoChecagem(
            ok=False,
            revisao_encontrada=None,
            revisao_esperada=revisao_esperada,
            motivo="nao_inicializado",
        )
    row = con.execute("SELECT version_num FROM alembic_version").fetchone()
    encontrada = row[0] if row else None
    if encontrada == revisao_esperada:
        return ResultadoChecagem(True, encontrada, revisao_esperada)
    if encontrada is None:
        return ResultadoChecagem(
            False, None, revisao_esperada, motivo="nao_inicializado"
        )
    # Comparação lexicográfica: as revisões deste projeto são numeradas com
    # zero à esquerda (`0001`..`0016`, ver
    # `fotoorganizer/database/migrations/versions/`), então ordem
    # lexicográfica == ordem cronológica. Se o esquema de nomenclatura
    # mudar (hash aleatório do Alembic, por exemplo), esta comparação para
    # de valer — documentado aqui para não virar bug silencioso.
    motivo = "downgrade" if encontrada > revisao_esperada else "desatualizado"
    return ResultadoChecagem(False, encontrada, revisao_esperada, motivo=motivo)


def exigir_esquema_compativel(
    con: sqlite3.Connection, revisao_esperada: str
) -> None:
    """A checagem que o boot chama de verdade: levanta em downgrade (nunca
    seguro abrir), deixa passar em `ok` ou `desatualizado` (quem chama roda
    a migração)."""
    resultado = verificar_esquema(con, revisao_esperada)
    if resultado.motivo == "downgrade":
        raise EsquemaDivergente(
            f"catálogo está na revisão {resultado.revisao_encontrada!r}, "
            f"mais nova que a que este app conhece "
            f"({resultado.revisao_esperada!r}) — abra com uma versão mais "
            f"recente do app; abrir agora arriscaria escrever sobre uma "
            f"coluna que este binário não entende."
        )
