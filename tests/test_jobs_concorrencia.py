"""Corrida no JobManager (A1, achado da auditoria 2026-09-19).

`ocupado()` (o check) e a criação/partida da thread (o act) não eram
atômicos — nem em `_iniciar`, nem na camada extra de `iniciar_execucao`/
`iniciar_escrita_exif`, que criam o `ExecutionControl` e escrevem
`self._exec_control` ANTES de chamar `_iniciar`. Duplo clique real medido:
55/200 chamadas simultâneas iniciavam duas threads. Um teste de diff não
pega bug de corrida — só um teste que solta várias chamadas pela mesma
barreira, forçando a janela a abrir sempre, prova a correção.
"""

import threading

from fotoorganizer.config.settings import Settings
from fotoorganizer.database import create_session_factory
from fotoorganizer.server.jobs import JobManager


def _manager(tmp_path, migrated_engine) -> JobManager:
    settings = Settings(data_dir=tmp_path / "d", cache_dir=tmp_path / "c")
    factory = create_session_factory(migrated_engine)
    return JobManager(settings, factory)


def test_duplo_clique_so_uma_chamada_vence(tmp_path, migrated_engine):
    """N chamadas a `_iniciar` soltas ao mesmo tempo (barreira) — sem lock
    cobrindo o check-then-act, mais de uma passa. Usa uma função-alvo que
    bloqueia até o teste liberar, pra garantir que a primeira thread ainda
    esteja viva quando as demais chamadas checarem `ocupado()`."""
    manager = _manager(tmp_path, migrated_engine)
    liberado = threading.Event()

    def devagar(*_args) -> None:
        liberado.wait(timeout=2)

    n = 50
    barreira = threading.Barrier(n)
    resultados: list[bool] = []
    trava = threading.Lock()

    def chamar() -> None:
        barreira.wait()
        ok = manager._iniciar("teste", "alvo", devagar)
        with trava:
            resultados.append(ok)

    threads = [threading.Thread(target=chamar) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    liberado.set()
    assert manager._thread is not None
    manager._thread.join(timeout=2)

    assert resultados.count(True) == 1, resultados
    assert resultados.count(False) == n - 1, resultados


def test_execucao_concorrente_nao_deixa_exec_control_orfao(tmp_path, migrated_engine):
    """A segunda janela de corrida, independente da de `_iniciar`:
    `iniciar_execucao`/`iniciar_escrita_exif` criam o `ExecutionControl` e
    gravam `self._exec_control` ANTES de chamar `_iniciar` — duas chamadas
    concorrentes podiam sobrescrever esse campo mesmo já com o lock de
    `_iniciar` corrigido, deixando `cancelar()` operando sobre o controle
    de uma chamada perdedora (que nenhuma thread real lê) em vez do da
    thread vencedora. Prova: só uma chamada de `_rodar_execucao` deve
    rodar, e o controle que ela recebeu tem que ser exatamente
    `manager._exec_control` ao final."""
    manager = _manager(tmp_path, migrated_engine)
    liberado = threading.Event()
    controles_vistos: list = []
    trava = threading.Lock()

    def devagar(_plan_id, controle) -> None:
        with trava:
            controles_vistos.append(controle)
        liberado.wait(timeout=2)

    manager._rodar_execucao = devagar  # substitui só a instância, sem bind de self

    n = 30
    barreira = threading.Barrier(n)

    def chamar(i: int) -> None:
        barreira.wait()
        manager.iniciar_execucao(i)

    threads = [threading.Thread(target=chamar, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    liberado.set()
    assert manager._thread is not None
    manager._thread.join(timeout=2)

    assert len(controles_vistos) == 1
    assert manager._exec_control is controles_vistos[0]
