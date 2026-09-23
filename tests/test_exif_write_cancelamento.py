"""Cancelamento da escrita EXIF (M8, auditoria 2026-09-19): `jobs.py:61-65`
e `exif_write/executor.py:332-334` sem teste ponta a ponta — o botão
"Cancelar" da UI nunca tinha prova automatizada neste domínio.

Dois níveis, propositalmente separados:

1. `test_cancelar_no_meio_para_o_loop_e_preserva_os_pendentes` — no
   domínio, chamando `ExifWriteExecutor.executar()` direto (mesmo padrão
   de `test_operations.py::test_cancelamento_e_retomada`): prova que o
   loop respeita `control.cancelado` ANTES do próximo item, sem tocar em
   quem ainda está PRONTO, e que retomar sem cancelar termina o resto.

2. `test_cancelar_pela_api_chega_na_thread_de_verdade_e_o_plano_fica_cancelado`
   — ponta a ponta pela API real (`TestClient` + `JobManager` + thread de
   verdade): prova que `POST /api/job/cancelar` alcança o
   `ExecutionControl` que A THREAD RODANDO recebeu, com o
   `ExifWriteExecutor` real (não um stub) executando de verdade na thread
   que o `JobManager` startou pela rota HTTP. Não é o mesmo teste de
   `tests/test_jobs_concorrencia.py` (que dispara N chamadas concorrentes
   pra provar a correção de D-090 — `self._exec_control` sobrescrito por
   uma chamada concorrente antes de `_iniciar`) nem o substitui: aquele
   cobre a corrida de partida, este cobre o caminho que nenhum dos dois
   cobria — cancelar um plano de verdade rodando de verdade.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from fotoorganizer.config.settings import Settings
from fotoorganizer.database import create_session_factory
from fotoorganizer.exif_write.executor import ExifWriteExecutor
from fotoorganizer.exif_write.planner import ExifWritePlanner
from fotoorganizer.exif_write.writer import ExifToolWriter
from fotoorganizer.metadata.exiftool import ExifToolExtractor
from fotoorganizer.models import (
    CampoStatus,
    ExifWriteItem,
    ExifWritePlan,
    ExifWriteStatus,
    Location,
    MediaFile,
    Source,
)
from fotoorganizer.operations.executor import ExecutionControl
from fotoorganizer.server.app import create_app
from tests.fixtures import make_jpeg

tem_exiftool = pytest.mark.skipif(
    not ExifToolExtractor.disponivel(), reason="exiftool não instalado"
)


def _semear_tres_candidatos(factory, origem_dir) -> None:
    """Três candidatos limpos (sem GPS) com a mesma localização — o mínimo
    para provar "cancelar no item 1 deixa 2 e 3 intocados". A fixture
    `ambiente` de `test_exif_write_executor.py` só tem 1 candidato real
    (o outro já vem preenchido), insuficiente para observar um item
    pendente sobrevivendo ao cancelamento."""
    with factory() as session:
        fonte = Source(caminho=str(origem_dir))
        session.add(fonte)
        session.flush()
        loc = Location(cidade="Rio de Janeiro", pais="Brasil", fonte="test")
        session.add(loc)
        session.flush()
        for nome in ("um.jpg", "dois.jpg", "tres.jpg"):
            caminho = make_jpeg(origem_dir / nome, gps=None)
            session.add(MediaFile(
                source_id=fonte.id, caminho=str(caminho), pasta=str(caminho.parent),
                nome=caminho.name, extensao="jpg", tamanho=caminho.stat().st_size,
                data_capturada=datetime(2024, 1, 1),
                gps_lat_estimado=-22.95, gps_lon_estimado=-43.18,
                gps_estimado_delta_s=300, location_id=loc.id,
            ))
        session.commit()


@pytest.fixture()
def ambiente_multiplo(migrated_engine, tmp_path):
    origem_dir = tmp_path / "origem"
    origem_dir.mkdir()
    factory = create_session_factory(migrated_engine)
    _semear_tres_candidatos(factory, origem_dir)

    planner = ExifWritePlanner(factory)
    executor = ExifWriteExecutor(factory)
    plan_id = planner.criar_plano_exif()
    assert plan_id is not None
    executor.dry_run(plan_id)
    return factory, executor, origem_dir, plan_id


@tem_exiftool
def test_cancelar_no_meio_para_o_loop_e_preserva_os_pendentes(ambiente_multiplo):
    factory, executor, _origem_dir, plan_id = ambiente_multiplo
    control = ExecutionControl()
    # O teste não presume qual dos 3 candidatos o planner coloca primeiro
    # (hoje é por `MediaFile.caminho`, mas isso é detalhe do planner, não
    # contrato deste teste) — só que existe UM primeiro processado e os
    # outros dois ficam de fora.
    vistos: list[str] = []

    def cancela_apos_primeiro(n: int, _total: int, origem: str) -> None:
        vistos.append(origem)
        if n == 1:
            # O cancelamento é visto SÓ na checagem do próximo item — o
            # item 1 (já em `progress()`) termina normalmente, é isso que
            # prova que o corte é entre itens, nunca no meio de uma
            # escrita já em curso.
            control.cancelar()

    stats = executor.executar(plan_id, progress=cancela_apos_primeiro, control=control)

    assert stats["cancelado"] is True
    assert len(vistos) == 1  # progress nunca chamado pro 2º/3º
    processado = vistos[0]

    with factory() as session:
        plano = session.get(ExifWritePlan, plan_id)
        assert plano.status == ExifWriteStatus.CANCELADA

        item_processado = session.scalar(select(ExifWriteItem).where(
            ExifWriteItem.origem == processado))
        assert item_processado.status_gps == CampoStatus.GRAVADO
        assert item_processado.status_pais == CampoStatus.GRAVADO

        pendentes = list(session.scalars(select(ExifWriteItem).where(
            ExifWriteItem.plan_id == plan_id,
            ExifWriteItem.origem != processado,
        )))
        assert len(pendentes) == 2
        for item in pendentes:
            # PRONTO, não FALHA/GRAVADO/PULADO — nenhum subprocesso rodou
            # pra eles, é isso que faz retomar seguro.
            assert item.status_gps == CampoStatus.PRONTO

        origens_pendentes = [item.origem for item in pendentes]

    # Nenhum backup sobrou pros dois que nunca chegaram a ser tocados.
    for origem in origens_pendentes:
        assert not ExifToolWriter.caminho_backup(Path(origem)).exists()

    # Retomada sem cancelar: termina o resto, sem refazer o item já pronto.
    stats2 = executor.executar(plan_id)
    assert stats2["cancelado"] is False
    assert stats2["gravados"] == 2
    assert stats2["pulados"] == 1  # o já terminado, nem entra em pendentes

    with factory() as session:
        plano = session.get(ExifWritePlan, plan_id)
        assert plano.status == ExifWriteStatus.CONCLUIDA


@tem_exiftool
def test_cancelar_pela_api_chega_na_thread_de_verdade_e_o_plano_fica_cancelado(
    migrated_engine, tmp_path, monkeypatch,
):
    origem_dir = tmp_path / "origem"
    origem_dir.mkdir()
    factory = create_session_factory(migrated_engine)
    _semear_tres_candidatos(factory, origem_dir)

    plan_id = ExifWritePlanner(factory).criar_plano_exif()
    assert plan_id is not None
    ExifWriteExecutor(factory).dry_run(plan_id)

    # Pausa a escrita real do PRIMEIRO item que a thread tocar até o teste
    # liberar — janela determinística (sem corrida de sleep) pra disparar
    # o cancelamento exatamente enquanto a thread real do job está dentro
    # do 1º item. Gatilho é "a 1ª chamada", não um nome específico — a
    # ordem dos 3 candidatos é detalhe do planner, não contrato do teste.
    pausado = threading.Event()
    pode_seguir = threading.Event()
    primeiro_alvo: dict[str, str] = {}
    trava = threading.Lock()
    original_escrever = ExifToolWriter.escrever

    def escrever_que_pausa(self, origem, campos, destino=None, timeout=None):
        with trava:
            é_primeiro = "origem" not in primeiro_alvo
            if é_primeiro:
                primeiro_alvo["origem"] = str(origem)
        if é_primeiro:
            pausado.set()
            pode_seguir.wait(timeout=5)
        return original_escrever(self, origem, campos, destino)

    monkeypatch.setattr(ExifToolWriter, "escrever", escrever_que_pausa)

    settings = Settings(data_dir=tmp_path / "d", cache_dir=tmp_path / "c")
    with TestClient(
        create_app(settings, factory), base_url="http://127.0.0.1:8765"
    ) as client:
        resposta = client.post(f"/api/exif/{plan_id}/executar", json={})
        assert resposta.status_code == 200, resposta.text
        assert resposta.json()["status"] == "rodando"

        assert pausado.wait(timeout=5), "a thread real do job nunca chegou no 1º item"

        resposta = client.post("/api/job/cancelar")
        assert resposta.status_code == 200

        pode_seguir.set()  # deixa "um.jpg" terminar (grava e verifica) antes do corte

        prazo = time.monotonic() + 5
        estado = client.get("/api/job").json()
        while estado.get("status") == "rodando" and time.monotonic() < prazo:
            estado = client.get("/api/job").json()
        assert estado["status"] == "cancelado", estado

    processado = primeiro_alvo["origem"]
    with factory() as session:
        plano = session.get(ExifWritePlan, plan_id)
        assert plano.status == ExifWriteStatus.CANCELADA

        item_processado = session.scalar(select(ExifWriteItem).where(
            ExifWriteItem.origem == processado))
        assert item_processado.status_gps == CampoStatus.GRAVADO  # o único que a thread terminou

        pendentes = list(session.scalars(select(ExifWriteItem).where(
            ExifWriteItem.plan_id == plan_id,
            ExifWriteItem.origem != processado,
        )))
        assert len(pendentes) == 2
        for item in pendentes:
            assert item.status_gps == CampoStatus.PRONTO  # o cancelamento chegou a tempo
