"""Suíte de `ExifWriteExecutor` (fotoorganizer/exif_write/executor.py, fase
6, plano 05) — prova automatizada dos cinco requisitos da fase (EXIF-01 a
EXIF-05), dos critérios 1-6 do roadmap e da idempotência do rerun.

Praticamente todo teste aqui precisa do binário `exiftool` (`dry_run()` já
chama `verificacao.dump_lote` em lote) — diferente da suíte de `writer.py`,
que consegue isolar a lógica pura de diff sem subprocesso. Só
`test_executar_sem_dry_run_levanta` (a porta fechada mais simples: nenhum
dry-run aconteceu, nada é tocado) roda sem o binário.

Deviação documentada (não coberta pelo `<behavior>` original do plano, ver
SUMMARY): `test_executar_nao_regride_por_deslocamento_de_offset` prova, de
ponta a ponta via `dry_run()`+`executar()`, que o executor chama
`verificacao.reclassificar_deslocamentos_de_offset()` (D-077, 06-04b) — sem
isso, toda escrita real num arquivo com miniatura embutida reprovaria de
novo por `IFD1:ThumbnailOffset`, regressão nomeada explicitamente em
06-04b-SUMMARY.md § Next Phase Readiness como o risco central deste plano.
"""

from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import select

from fotoorganizer.database import create_session_factory
from fotoorganizer.exif_write import verificacao
from fotoorganizer.exif_write.executor import DryRunObrigatorioExif, ExifWriteExecutor
from fotoorganizer.exif_write.planner import ExifWritePlanner
from fotoorganizer.exif_write.writer import ExifToolWriter
from fotoorganizer.metadata.exiftool import ExifToolExtractor
from fotoorganizer.models import (
    AuditLog,
    CampoStatus,
    ExifWriteItem,
    Location,
    MediaFile,
    Source,
)
from fotoorganizer.security.hashing import sha256_full
from tests.fixtures import make_jpeg

tem_exiftool = pytest.mark.skipif(
    not ExifToolExtractor.disponivel(), reason="exiftool não instalado"
)


def hashes(diretorio: Path) -> dict[str, str]:
    """SHA-256 de todo arquivo sob `diretorio` — usado pelos testes de "não
    tocou nada" para comparar a árvore inteira, nunca `mtime`."""
    return {str(p): sha256_full(p) for p in sorted(diretorio.rglob("*")) if p.is_file()}


@pytest.fixture()
def ambiente(migrated_engine, tmp_path):
    """Um candidato limpo (sem GPS, sem localização no arquivo) e um já
    preenchido (GPS real gravado, deve ser pulado) — `Source`, `MediaFile`
    com `gps_lat_estimado`/`gps_lon_estimado` e `Location` com
    cidade/país. O plano nasce do `ExifWritePlanner` real, não montado à
    mão — assim a suíte também valida a integração planner->executor."""
    origem_dir = tmp_path / "origem"
    origem_dir.mkdir()
    factory = create_session_factory(migrated_engine)
    with factory() as session:
        fonte = Source(caminho=str(origem_dir))
        session.add(fonte)
        session.flush()
        fonte_id = fonte.id

        loc = Location(cidade="Rio de Janeiro", pais="Brasil", fonte="test")
        session.add(loc)
        session.flush()

        limpa = make_jpeg(origem_dir / "limpa.jpg", gps=None)
        session.add(MediaFile(
            source_id=fonte_id, caminho=str(limpa), pasta=str(limpa.parent),
            nome=limpa.name, extensao="jpg", tamanho=limpa.stat().st_size,
            data_capturada=datetime(2024, 1, 1),
            gps_lat_estimado=-22.95, gps_lon_estimado=-43.18,
            location_id=loc.id,
        ))

        preenchida = make_jpeg(origem_dir / "preenchida.jpg", gps=(-22.95, -43.18))
        session.add(MediaFile(
            source_id=fonte_id, caminho=str(preenchida), pasta=str(preenchida.parent),
            nome=preenchida.name, extensao="jpg", tamanho=preenchida.stat().st_size,
            data_capturada=datetime(2024, 1, 1),
            gps_lat=-22.95, gps_lon=-43.18,
            gps_lat_estimado=-22.95, gps_lon_estimado=-43.18,
            location_id=loc.id,
        ))
        session.commit()

    planner = ExifWritePlanner(factory)
    executor = ExifWriteExecutor(factory)
    plan_id = planner.criar_plano_exif()
    assert plan_id is not None
    return factory, executor, origem_dir, plan_id


def _item_manual(
    session, plan_id: int, media: MediaFile, *,
    formato_suportado: bool = True, sidecar_destino: str | None = None,
    valor_cidade: str = "Rio de Janeiro", valor_pais: str = "Brasil",
    valor_gps: tuple[float, float] = (-22.95, -43.18),
) -> ExifWriteItem:
    """Item de `ExifWriteItem` construído à mão — usado nos testes que
    precisam de um formato não suportado (sidecar) ou de um arquivo
    preparado fora do candidato padrão da fixture `ambiente`."""
    item = ExifWriteItem(
        plan_id=plan_id, media_id=media.id, origem=media.caminho,
        valor_gps_lat=valor_gps[0], valor_gps_lon=valor_gps[1],
        valor_cidade=valor_cidade, valor_pais=valor_pais,
        status_gps=CampoStatus.PENDENTE, status_cidade=CampoStatus.PENDENTE,
        status_pais=CampoStatus.PENDENTE,
        formato_suportado=formato_suportado,
        motivo_nao_suportado=None if formato_suportado else "teste",
        sidecar_destino=sidecar_destino, incluido=True,
    )
    session.add(item)
    session.flush()
    return item


def _media_avulsa(session, fonte_id: int, caminho: Path, loc_id: int) -> MediaFile:
    media = MediaFile(
        source_id=fonte_id, caminho=str(caminho), pasta=str(caminho.parent),
        nome=caminho.name, extensao="jpg", tamanho=caminho.stat().st_size,
        data_capturada=datetime(2024, 1, 1), location_id=loc_id,
    )
    session.add(media)
    session.flush()
    return media


# -- EXIF-01: dry-run obrigatório --------------------------------------------

def test_executar_sem_dry_run_levanta(ambiente):
    """Não precisa do binário: a porta fecha antes de qualquer I/O."""
    factory, executor, origem_dir, plan_id = ambiente
    antes = hashes(origem_dir)
    with pytest.raises(DryRunObrigatorioExif):
        executor.executar(plan_id)
    assert hashes(origem_dir) == antes


@tem_exiftool
def test_dry_run_nao_escreve(ambiente):
    factory, executor, origem_dir, plan_id = ambiente
    antes = hashes(origem_dir)
    executor.dry_run(plan_id)
    assert hashes(origem_dir) == antes
    assert not any(p.name.endswith("_original") for p in origem_dir.rglob("*"))
    assert not any(p.suffix == ".xmp" for p in origem_dir.rglob("*"))


# -- EXIF-02: só campo vazio ao vivo -----------------------------------------

@tem_exiftool
def test_dry_run_promove_campo_vazio_e_pula_preenchido(ambiente):
    factory, executor, origem_dir, plan_id = ambiente
    relatorio = executor.dry_run(plan_id)
    assert relatorio["prontos"] >= 1

    with factory() as session:
        item_limpa = session.scalar(select(ExifWriteItem).where(
            ExifWriteItem.plan_id == plan_id,
            ExifWriteItem.origem == str(origem_dir / "limpa.jpg"),
        ))
        assert item_limpa.status_gps == CampoStatus.PRONTO
        assert item_limpa.status_cidade == CampoStatus.PRONTO
        assert item_limpa.status_pais == CampoStatus.PRONTO

        item_preenchida = session.scalar(select(ExifWriteItem).where(
            ExifWriteItem.plan_id == plan_id,
            ExifWriteItem.origem == str(origem_dir / "preenchida.jpg"),
        ))
        assert item_preenchida.status_gps == CampoStatus.PULADO
        assert "não sobrescrito" in item_preenchida.motivo_gps


# -- EXIF-03: diff completo de tags como veredito ----------------------------

@tem_exiftool
def test_escreve_e_verifica_por_diff(ambiente):
    factory, executor, origem_dir, plan_id = ambiente
    executor.dry_run(plan_id)
    stats = executor.executar(plan_id)
    assert stats["gravados"] >= 1

    with factory() as session:
        item = session.scalar(select(ExifWriteItem).where(
            ExifWriteItem.plan_id == plan_id,
            ExifWriteItem.origem == str(origem_dir / "limpa.jpg"),
        ))
        assert item.status_gps == CampoStatus.GRAVADO
        assert item.status_cidade == CampoStatus.GRAVADO
        assert item.status_pais == CampoStatus.GRAVADO
        assert item.hash_pos != item.hash_pre  # mudar é esperado, não é falha

    dump_final = verificacao.dump(origem_dir / "limpa.jpg")
    for tag in (
        "GPS:GPSLatitude", "GPS:GPSLatitudeRef",
        "GPS:GPSLongitude", "GPS:GPSLongitudeRef",
        "IPTC:City", "XMP-photoshop:City",
        "IPTC:Country-PrimaryLocationName", "XMP-photoshop:Country",
    ):
        assert tag in dump_final


# -- EXIF-04: nunca escreve fora de localização ------------------------------

@tem_exiftool
def test_nunca_escreve_fora_de_localizacao(ambiente):
    factory, executor, origem_dir, plan_id = ambiente
    foto = origem_dir / "limpa.jpg"
    antes = verificacao.dump(foto)

    executor.dry_run(plan_id)
    executor.executar(plan_id)

    depois = verificacao.dump(foto)
    diff = verificacao.diferenca(antes, depois)
    assert diff.inesperadas == {}


# -- EXIF-03: falha parcial ---------------------------------------------------

def _monkeypatch_sem_gps(monkeypatch) -> None:
    """Simula a Pitfall 2 (exiftool sai 0 mas pula GPS): remove os
    argumentos de GPS antes de chamar o `escrever()` real — o caminho de
    verificação exercitado é o real, não um mock do veredito."""
    original = ExifToolWriter.escrever

    def sem_gps(self, origem, campos, destino=None):
        return original(self, origem, {k: v for k, v in campos.items() if k != "gps"},
                         destino=destino)

    monkeypatch.setattr(ExifToolWriter, "escrever", sem_gps)


@tem_exiftool
def test_diff_detecta_falha_parcial(ambiente, monkeypatch):
    factory, executor, origem_dir, plan_id = ambiente
    executor.dry_run(plan_id)
    _monkeypatch_sem_gps(monkeypatch)

    stats = executor.executar(plan_id)
    assert stats["falhas_parciais"] >= 1

    with factory() as session:
        item = session.scalar(select(ExifWriteItem).where(
            ExifWriteItem.plan_id == plan_id,
            ExifWriteItem.origem == str(origem_dir / "limpa.jpg"),
        ))
        assert item.status_gps == CampoStatus.FALHA
        assert item.status_cidade == CampoStatus.GRAVADO
        assert item.status_pais == CampoStatus.GRAVADO
        assert item.backup_original is not None
        assert Path(item.backup_original).exists()

        log_row = session.scalar(select(AuditLog).where(
            AuditLog.acao == "escrita_exif", AuditLog.resultado == "falha_parcial",
        ))
        assert log_row is not None
        assert log_row.detalhe["campos"] == {
            "gps": "falha", "cidade": "gravado", "pais": "gravado",
        }


# -- Pitfall 7: política do backup `_original` -------------------------------

@tem_exiftool
def test_backup_apagado_so_apos_sucesso_verificado(ambiente, monkeypatch):
    factory, executor, origem_dir, plan_id = ambiente
    executor.dry_run(plan_id)
    executor.executar(plan_id)

    with factory() as session:
        item_sucesso = session.scalar(select(ExifWriteItem).where(
            ExifWriteItem.plan_id == plan_id,
            ExifWriteItem.origem == str(origem_dir / "limpa.jpg"),
        ))
        assert item_sucesso.backup_original is None

        registros = list(session.scalars(select(AuditLog).where(
            AuditLog.acao == "limpeza_backup_exiftool",
        )))
        assert any(r.detalhe.get("exif_plan_id") == plan_id for r in registros)

    assert not ExifToolWriter.caminho_backup(origem_dir / "limpa.jpg").exists()

    # -- cenário de falha: backup permanece e o caminho fica no item --------
    falha_foto = make_jpeg(origem_dir / "falha.jpg", gps=None)
    with factory() as session:
        fonte_id = session.scalar(select(Source.id))
        loc = Location(cidade="Salvador", pais="Brasil", fonte="test")
        session.add(loc)
        session.flush()
        session.add(MediaFile(
            source_id=fonte_id, caminho=str(falha_foto), pasta=str(falha_foto.parent),
            nome=falha_foto.name, extensao="jpg", tamanho=falha_foto.stat().st_size,
            data_capturada=datetime(2024, 1, 1),
            gps_lat_estimado=-12.97, gps_lon_estimado=-38.5, location_id=loc.id,
        ))
        session.commit()

    plan_id_2 = ExifWritePlanner(factory).criar_plano_exif()
    assert plan_id_2 is not None
    executor.dry_run(plan_id_2)
    _monkeypatch_sem_gps(monkeypatch)
    executor.executar(plan_id_2)

    with factory() as session:
        item_falha = session.scalar(select(ExifWriteItem).where(
            ExifWriteItem.plan_id == plan_id_2,
            ExifWriteItem.origem == str(falha_foto),
        ))
        assert item_falha.backup_original is not None
        assert Path(item_falha.backup_original).exists()


# -- critério 4: idempotência do rerun ----------------------------------------

@tem_exiftool
def test_rerodar_e_idempotente(ambiente):
    factory, executor, origem_dir, plan_id = ambiente
    executor.dry_run(plan_id)
    executor.executar(plan_id)
    hash_apos_primeira = sha256_full(origem_dir / "limpa.jpg")

    # Sem novo dry-run: reaproveita o veredito do primeiro — idempotência
    # não depende do dry-run estar fresco. O item já terminou (GRAVADO/
    # PULADO), então nem entra em `pendentes`; mesmo se entrasse, a
    # reconferência ao vivo do passo 5 de `_executar_item` (TOCTOU)
    # pularia sem chamar subprocesso (EXIF-02).
    stats2 = executor.executar(plan_id)

    with factory() as session:
        item = session.scalar(select(ExifWriteItem).where(
            ExifWriteItem.plan_id == plan_id,
            ExifWriteItem.origem == str(origem_dir / "limpa.jpg"),
        ))
        # Terminal desde a primeira execução — a segunda passada não regride
        # o status nem toca no arquivo de novo.
        assert item.status_gps == CampoStatus.GRAVADO
        assert item.status_cidade == CampoStatus.GRAVADO
        assert item.status_pais == CampoStatus.GRAVADO

    assert stats2["gravados"] == 0
    assert stats2["pulados"] == 2  # os 2 itens da fixture, nenhum PRONTO restante
    assert sha256_full(origem_dir / "limpa.jpg") == hash_apos_primeira
    assert not any(p.name.endswith("_original") for p in origem_dir.rglob("*"))


# -- D-02: item desmarcado não é escrito -------------------------------------

@tem_exiftool
def test_item_desmarcado_nao_e_escrito(ambiente):
    factory, executor, origem_dir, plan_id = ambiente
    executor.dry_run(plan_id)
    antes = hashes(origem_dir)

    executor.aplicar_selecao(plan_id, [])
    with factory() as session:
        n_itens = len(list(session.scalars(
            select(ExifWriteItem).where(ExifWriteItem.plan_id == plan_id)
        )))
    stats = executor.executar(plan_id)

    assert hashes(origem_dir) == antes
    assert stats["pulados"] == n_itens
    assert stats["gravados"] == 0
    with factory() as session:
        assert all(
            not item.incluido for item in session.scalars(
                select(ExifWriteItem).where(ExifWriteItem.plan_id == plan_id)
            )
        )


# -- EXIF-05/D-06: sidecar para formato não suportado ------------------------

@tem_exiftool
def test_formato_nao_suportado_grava_sidecar(ambiente):
    factory, executor, origem_dir, plan_id = ambiente
    alvo = make_jpeg(origem_dir / "para_sidecar.jpg", gps=None)
    hash_antes = sha256_full(alvo)
    sidecar_destino = str(alvo) + ".xmp"

    with factory() as session:
        fonte_id = session.scalar(select(Source.id))
        loc = session.scalar(select(Location))
        media = _media_avulsa(session, fonte_id, alvo, loc.id)
        item = _item_manual(
            session, plan_id, media, formato_suportado=False,
            sidecar_destino=sidecar_destino,
        )
        session.commit()
        item_id = item.id

    executor.dry_run(plan_id)
    stats = executor.executar(plan_id)
    assert stats["sidecars"] >= 1

    sidecar_path = Path(sidecar_destino)
    assert sidecar_path.exists()
    dump_sidecar = verificacao.dump(sidecar_path)
    assert "XMP-photoshop:City" in dump_sidecar
    assert "XMP-photoshop:Country" in dump_sidecar
    assert "XMP-exif:GPSLatitude" in dump_sidecar
    assert sha256_full(alvo) == hash_antes

    with factory() as session:
        item = session.get(ExifWriteItem, item_id)
        assert item.status_gps == CampoStatus.GRAVADO
        assert item.status_cidade == CampoStatus.GRAVADO
        assert item.status_pais == CampoStatus.GRAVADO


@tem_exiftool
def test_sidecar_existente_nunca_e_sobrescrito(ambiente):
    """Sidecar aparece DEPOIS do dry-run (TOCTOU) — exercita a checagem
    própria de `_executar_item`, não a de `dry_run`."""
    factory, executor, origem_dir, plan_id = ambiente
    alvo = make_jpeg(origem_dir / "com_sidecar.jpg", gps=None)
    sidecar_destino = str(alvo) + ".xmp"

    with factory() as session:
        fonte_id = session.scalar(select(Source.id))
        loc = session.scalar(select(Location))
        media = _media_avulsa(session, fonte_id, alvo, loc.id)
        item = _item_manual(
            session, plan_id, media, formato_suportado=False,
            sidecar_destino=sidecar_destino,
        )
        session.commit()
        item_id = item.id

    executor.dry_run(plan_id)

    sidecar_path = Path(sidecar_destino)
    sidecar_path.write_text("conteudo pre-existente")
    conteudo_antes = sidecar_path.read_text()

    stats = executor.executar(plan_id)
    assert stats["erros"] >= 1
    assert sidecar_path.read_text() == conteudo_antes

    with factory() as session:
        item = session.get(ExifWriteItem, item_id)
        assert item.erro is not None
        assert "sobrescrito" in item.erro


# -- auditoria não viola a FK real de operation_plans ------------------------

@tem_exiftool
def test_audit_de_execucao_nao_viola_fk(ambiente):
    factory, executor, origem_dir, plan_id = ambiente
    executor.dry_run(plan_id)
    executor.executar(plan_id)

    with factory() as session:
        linhas = list(session.scalars(
            select(AuditLog).where(
                AuditLog.detalhe["exif_plan_id"].as_integer() == plan_id
            )
        ))
    assert linhas
    assert all(row.plan_id is None for row in linhas)
    assert all(row.detalhe.get("exif_plan_id") == plan_id for row in linhas)


# -- Deviação (Rule 2): 06-04b-SUMMARY.md nomeou explicitamente este risco --

@tem_exiftool
def test_executar_nao_regride_por_deslocamento_de_offset(ambiente):
    """Sem chamar `reclassificar_deslocamentos_de_offset()` (D-077) depois
    de `diferenca()`, toda escrita real num arquivo com miniatura embutida
    reprovaria de novo por `IFD1:ThumbnailOffset` — regressão silenciosa da
    allowlist que D-077 acabou de aprovar para `.jpg`/`.cr2`, nomeada
    explicitamente em 06-04b-SUMMARY.md § Next Phase Readiness."""
    factory, executor, origem_dir, plan_id = ambiente
    foto = make_jpeg(origem_dir / "com_thumb.jpg", gps=None)
    binario = shutil.which("exiftool")
    subprocess.run(
        [binario, "-overwrite_original", f"-ThumbnailImage<={foto}", str(foto)],
        capture_output=True, text=True, check=True,
    )
    assert "IFD1:ThumbnailOffset" in verificacao.dump(foto)  # pré-condição

    with factory() as session:
        fonte_id = session.scalar(select(Source.id))
        loc = session.scalar(select(Location))
        media = MediaFile(
            source_id=fonte_id, caminho=str(foto), pasta=str(foto.parent),
            nome=foto.name, extensao="jpg", tamanho=foto.stat().st_size,
            data_capturada=datetime(2024, 1, 1),
            gps_lat_estimado=-22.95, gps_lon_estimado=-43.18, location_id=loc.id,
        )
        session.add(media)
        session.flush()
        item = _item_manual(session, plan_id, media)
        session.commit()
        item_id = item.id

    executor.dry_run(plan_id)
    stats = executor.executar(plan_id)
    assert stats["erros"] == 0

    with factory() as session:
        item = session.get(ExifWriteItem, item_id)
        assert item.status_gps == CampoStatus.GRAVADO
        assert item.status_cidade == CampoStatus.GRAVADO
        assert item.status_pais == CampoStatus.GRAVADO
        assert item.erro is None
