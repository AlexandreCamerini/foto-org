"""Repositório de preferências (fotoorganizer/repositories/settings.py) —
usado hoje só pelo template de destino configurável (fase 10)."""

from fotoorganizer.database import create_session_factory
from fotoorganizer.repositories.settings import (
    CHAVE_TEMPLATE_DESTINO,
    SettingsRepository,
)


def _repo(migrated_engine) -> SettingsRepository:
    return SettingsRepository(create_session_factory(migrated_engine))


def test_obter_chave_nunca_definida_devolve_none(migrated_engine):
    assert _repo(migrated_engine).obter("nunca_salva") is None


def test_definir_e_obter(migrated_engine):
    repo = _repo(migrated_engine)
    repo.definir("chave", {"a": 1})
    assert repo.obter("chave") == {"a": 1}


def test_definir_sobrescreve_valor_anterior(migrated_engine):
    repo = _repo(migrated_engine)
    repo.definir(CHAVE_TEMPLATE_DESTINO, "{ano}/{pais}")
    repo.definir(CHAVE_TEMPLATE_DESTINO, "{ano}/{cidade}")
    assert repo.obter(CHAVE_TEMPLATE_DESTINO) == "{ano}/{cidade}"


def test_obter_template_sem_preferencia_salva_cai_no_default(migrated_engine):
    repo = _repo(migrated_engine)
    assert repo.obter_template("{categoria}") == "{categoria}"


def test_obter_template_depois_de_salvar(migrated_engine):
    repo = _repo(migrated_engine)
    repo.salvar_template("{ano}/{pais}")
    assert repo.obter_template("{categoria}") == "{ano}/{pais}"


def test_template_persiste_entre_repositorios_diferentes(migrated_engine):
    """O aceite da fase 10 é persistir "entre reinícios do servidor" — o
    equivalente em teste é um repositório novo, com sua própria sessão, lendo
    o que outro escreveu."""
    _repo(migrated_engine).salvar_template("{ano}/{cidade}")
    assert _repo(migrated_engine).obter_template("default") == "{ano}/{cidade}"
