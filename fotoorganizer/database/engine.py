"""Engine SQLite com WAL e foreign keys ligados em toda conexão."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker


def _set_sqlite_pragmas(dbapi_connection, _record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    # Pré-requisito para o planner do SQLite reescrever
    # `pasta LIKE 'prefixo/%'` em varredura de faixa sobre
    # ix_media_files_pasta (_sob_a_pasta, repositories/media.py:171) — sem
    # esta linha o índice existe e a consulta continua em SCAN (RESEARCH.md
    # Pitfall 3, verificado por EXPLAIN QUERY PLAN). Varredura de segurança
    # já feita em todo o codebase: `.ilike()` (busca, câmera, país, cidade,
    # palavra-chave) compila para `lower(x) LIKE lower(y)` no SQLite,
    # independente deste PRAGMA; `.not_like("%://%")`
    # (scanner/reconciliacao.py:86, scanner/scanner.py:379,
    # repositories/inventario.py:190,207) não tem caractere alfabético e já
    # tinha curinga à esquerda — nunca foi elegível a índice de qualquer
    # forma. O único `.like()` afetado é o de `pasta`, cujo valor vem de
    # `/api/pastas` (que por sua vez lê de MediaFile.pasta), nunca de texto
    # digitado livremente pelo usuário.
    cursor.execute("PRAGMA case_sensitive_like=ON")
    cursor.close()


def db_url(db_path: Path) -> str:
    return f"sqlite:///{db_path}"


def create_db_engine(db_path: Path) -> Engine:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: o scan roda fora da thread da UI; cada thread
    # usa a própria Session, e o WAL + busy_timeout cuidam da concorrência.
    engine = create_engine(
        db_url(db_path), connect_args={"check_same_thread": False}
    )
    event.listen(engine, "connect", _set_sqlite_pragmas)
    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
