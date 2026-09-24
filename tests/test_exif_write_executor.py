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
from fotoorganizer.exif_write.executor import (
    DryRunObrigatorioExif,
    ExifWriteExecutor,
    _campo_ja_preenchido,
)
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
            gps_estimado_delta_s=300,  # herança de 5 min: sustenta cidade
            location_id=loc.id,
        ))

        preenchida = make_jpeg(origem_dir / "preenchida.jpg", gps=(-22.95, -43.18))
        session.add(MediaFile(
            source_id=fonte_id, caminho=str(preenchida), pasta=str(preenchida.parent),
            nome=preenchida.name, extensao="jpg", tamanho=preenchida.stat().st_size,
            data_capturada=datetime(2024, 1, 1),
            gps_lat=-22.95, gps_lon=-43.18,
            gps_lat_estimado=-22.95, gps_lon_estimado=-43.18,
            gps_estimado_delta_s=300,
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
# `_campo_ja_preenchido` puro (sem exiftool, dump montado à mão) — A2 da
# auditoria: GPS que mora só em XMP-exif (sem nenhuma tag GPS: binária)
# passava como "campo vazio" no caminho direto, porque a checagem olhava
# só o grupo binário. Sidecar já olhava o grupo certo (XMP-exif) desde
# sempre — só o caminho direto tinha o ponto cego.


def test_campo_ja_preenchido_direto_reconhece_gps_que_mora_so_em_xmp():
    dump = {"XMP-exif:GPSLatitude": "-33.8688", "XMP-exif:GPSLongitude": "151.2093"}
    preenchido, valor = _campo_ja_preenchido("gps", dump, sidecar=False)
    assert preenchido is True
    assert valor == "-33.8688, 151.2093"


def test_campo_ja_preenchido_direto_sem_gps_nenhum_fica_vazio():
    preenchido, valor = _campo_ja_preenchido("gps", {}, sidecar=False)
    assert preenchido is False
    assert valor is None


def test_campo_ja_preenchido_direto_ainda_reconhece_gps_binario():
    """Comportamento de sempre, inalterado: GPS no grupo EXIF binário
    (o caso comum) continua reconhecido do mesmo jeito."""
    dump = {
        "GPS:GPSLatitude": "22.95", "GPS:GPSLatitudeRef": "S",
        "GPS:GPSLongitude": "43.18", "GPS:GPSLongitudeRef": "W",
    }
    preenchido, valor = _campo_ja_preenchido("gps", dump, sidecar=False)
    assert preenchido is True
    assert valor == "-22.95, -43.18"


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


@tem_exiftool
def test_dry_run_pula_gps_que_mora_so_em_xmp_no_caminho_direto(ambiente):
    """Ponta a ponta com exiftool real, A2 da auditoria: uma foto cujo
    GPS foi gravado só em XMP-exif (por um editor externo, antes de
    chegar no fotoorganizer) não pode ser tratada como "campo vazio" —
    sem esta guarda, a escrita seguinte sobrescreveria com hemisfério
    errado (Ref não gravável nesse grupo) e sem backup (não é a primeira
    escrita do bloco)."""
    import subprocess

    factory, executor, origem_dir, plan_id = ambiente
    alvo = make_jpeg(origem_dir / "gps_so_em_xmp.jpg", gps=None)
    subprocess.run(
        ["exiftool", "-XMP-exif:GPSLatitude=-33.8688",
         "-XMP-exif:GPSLongitude=151.2093", str(alvo)],
        capture_output=True, text=True, check=True,
    )

    with factory() as session:
        fonte_id = session.scalar(select(Source.id))
        loc = session.scalar(select(Location))
        media = _media_avulsa(session, fonte_id, alvo, loc.id)
        item = _item_manual(session, plan_id, media)
        session.commit()
        item_id = item.id

    executor.dry_run(plan_id)

    with factory() as session:
        item = session.get(ExifWriteItem, item_id)
        assert item.status_gps == CampoStatus.PULADO
        assert "não sobrescrito" in (item.motivo_gps or "")


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


# -- D-097: aviso de IPTCDigest de terceiros não é sinal de corrupção --------

def test_avisos_inesperados_descarta_so_o_digest_do_iptc():
    """`Photoshop:IPTCDigest` é checksum da Adobe, não deste módulo — o
    aviso que ele gera ao ficar desatualizado nunca é sinal de que ESTE
    módulo escreveu algo errado (D-097)."""
    from fotoorganizer.exif_write.verificacao import avisos_inesperados

    antes = {"Warning: [minor] Odd offset for ExifIFD tag 0x9011 OffsetTimeOriginal"}
    depois = antes | {"Warning: IPTCDigest is not current. XMP may be out of sync"}
    assert avisos_inesperados(antes, depois) == set()


def test_avisos_inesperados_mantem_qualquer_outro_aviso_novo():
    """A allowlist é de uma linha só (D-097) — qualquer OUTRO aviso novo
    continua reprovando o item, sem exceção por engano."""
    from fotoorganizer.exif_write.verificacao import avisos_inesperados

    depois = {"Warning: [minor] Possibly corrupted TIFF trailer detected"}
    assert avisos_inesperados(set(), depois) == depois


def _simular_digest_iptc_de_terceiro(alvo: Path) -> None:
    """Reproduz contra o exiftool real o estado de um arquivo que já
    passou por Lightroom/Photoshop: um bloco IPTC pré-existente com
    `Photoshop:IPTCDigest` (checksum de terceiros) já sincronizado com
    esse bloco. Qualquer escrita IPTC depois disso desatualiza esse
    checksum — é isso que produz o aviso "IPTCDigest is not current" de
    forma determinística (verificado manualmente antes desta fatia,
    D-097).

    Achado da revisão de olhos frescos: sem a primeira escrita de IPTC
    abaixo, `fixtures.make_jpeg()` não tem NENHUM bloco IPTC — o
    `File:CurrentIPTCDigest` lido vem vazio, gravar `Photoshop:IPTCDigest`
    com valor vazio é um no-op silencioso do exiftool (0 arquivos
    atualizados), e o resto do teste passava mesmo sem reproduzir o
    cenário real (confirmado com um mutante: revertendo a correção em
    `executor.py`, os testes que usavam este helper continuavam verdes).
    O `-IPTC:Keywords=` aqui é só para criar o bloco IPTC de que o
    digest depende — nunca é o dado sob teste."""
    subprocess.run(
        ["exiftool", "-overwrite_original", "-IPTC:Keywords=selo-de-terceiro", str(alvo)],
        check=True, capture_output=True,
    )
    digest_atual = subprocess.run(
        ["exiftool", "-s3", "-File:CurrentIPTCDigest", str(alvo)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert digest_atual, "pré-condição do teste: bloco IPTC precisa existir antes do digest"
    subprocess.run(
        ["exiftool", "-overwrite_original", f"-Photoshop:IPTCDigest={digest_atual}", str(alvo)],
        check=True, capture_output=True,
    )


@tem_exiftool
def test_iptc_digest_de_terceiro_desatualizado_nao_reprova_escrita_correta(ambiente):
    """Achado real no acervo de produção (D-097, plano 3, 2026-09-23):
    329/1941 itens processados reprovavam com o único aviso "IPTCDigest
    is not current. XMP may be out of sync", apesar do diff de tags
    aprovar exatamente as tags de País/Cidade esperadas e nada mais —
    `Photoshop:IPTCDigest` é metadado de outra ferramenta, fora do
    escopo estreito de D-075."""
    factory, executor, origem_dir, plan_id = ambiente
    alvo = origem_dir / "limpa.jpg"
    _simular_digest_iptc_de_terceiro(alvo)

    executor.dry_run(plan_id)
    stats = executor.executar(plan_id)

    assert stats["erros"] == 0
    assert stats["gravados"] >= 1
    with factory() as session:
        item = session.scalar(select(ExifWriteItem).where(
            ExifWriteItem.origem == str(alvo)))
        assert item.status_gps == CampoStatus.GRAVADO
        assert item.status_cidade == CampoStatus.GRAVADO
        assert item.status_pais == CampoStatus.GRAVADO
        assert item.erro is None
        assert item.backup_original is None  # limpo como qualquer sucesso


@tem_exiftool
def test_iptc_digest_de_terceiro_nao_mascara_tag_de_localizacao_alterada(
    ambiente, monkeypatch,
):
    """Contraprova: a allowlist de D-097 é só sobre o AVISO — uma tag de
    localização gravada com valor errado continua reprovando pelo diff de
    tags (EXIF-03), mesmo com o digest de terceiro presente."""
    factory, executor, origem_dir, plan_id = ambiente
    alvo = origem_dir / "limpa.jpg"
    _simular_digest_iptc_de_terceiro(alvo)
    _monkeypatch_sem_gps(monkeypatch)  # GPS pedido, nunca escrito -> falha parcial

    executor.dry_run(plan_id)
    stats = executor.executar(plan_id)

    assert stats["falhas_parciais"] >= 1
    with factory() as session:
        item = session.scalar(select(ExifWriteItem).where(
            ExifWriteItem.origem == str(alvo)))
        assert item.status_gps == CampoStatus.FALHA
        assert item.status_pais == CampoStatus.GRAVADO


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
            gps_lat_estimado=-12.97, gps_lon_estimado=-38.5,
            gps_estimado_delta_s=300, location_id=loc.id,
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
    # A2 da auditoria: este teste já existia com estas mesmas coordenadas
    # (sul/oeste) e passava com o bug ativo — só checava presença. O
    # valor tem que bater com o sinal certo, não só a tag existir.
    assert dump_sidecar["XMP-exif:GPSLatitude"] == "-22.95"
    assert dump_sidecar["XMP-exif:GPSLongitude"] == "-43.18"
    assert sha256_full(alvo) == hash_antes

    with factory() as session:
        item = session.get(ExifWriteItem, item_id)
        assert item.status_gps == CampoStatus.GRAVADO
        assert item.status_cidade == CampoStatus.GRAVADO
        assert item.status_pais == CampoStatus.GRAVADO


@tem_exiftool
def test_gps_com_valor_errado_reprova_mesmo_com_tag_presente(ambiente, monkeypatch):
    """Rede de segurança de A2, de ponta a ponta: se o writer (por bug
    futuro, mudança de exiftool, etc.) voltar a gravar hemisfério errado,
    o executor tem que reprovar o campo `gps` — não bastar a tag existir.
    Simulado forçando o writer real a gravar o valor absoluto sem sinal
    (o comportamento de ANTES da correção), para provar que é a
    verificação nova que pega, não um acidente do writer atual."""
    factory, executor, origem_dir, plan_id = ambiente
    alvo = make_jpeg(origem_dir / "sidecar_com_bug.jpg", gps=None)
    hash_antes = sha256_full(alvo)
    sidecar_destino = str(alvo) + ".xmp"

    with factory() as session:
        fonte_id = session.scalar(select(Source.id))
        loc = session.scalar(select(Location))
        media = _media_avulsa(session, fonte_id, alvo, loc.id)
        item = _item_manual(
            session, plan_id, media, formato_suportado=False,
            sidecar_destino=sidecar_destino, valor_gps=(-22.95, -43.18),
        )
        session.commit()
        item_id = item.id

    original_escrever = ExifToolWriter.escrever

    def escrever_com_hemisferio_errado(self, origem, campos, destino=None):
        # Só substitui o comportamento para ESTE sidecar especificamente
        # — não só "quando há gps em campos" (achado da revisão com
        # olhos frescos: `limpa.jpg`, da fixture `ambiente`, também tem
        # "gps" em campos por herança e é escrita DIRETA; a fake omitia
        # `-IPTC:City`/`-IPTC:Country-PrimaryLocationName`, que o writer
        # real grava no caminho direto — quebrava cidade/país desse OUTRO
        # item por engano, mascarado por um `>= 1` frouxo na asserção).
        alvo_real = destino or origem
        if "gps" not in campos or Path(alvo_real).suffix.lower() != ".xmp":
            return original_escrever(self, origem, campos, destino)
        # Reproduz literalmente o bug de A2: abs() + Ref, que a XMP
        # aceita em silêncio sem gravar a Ref — mesma chamada que o
        # writer real fazia antes da correção.
        lat, lon = campos["gps"]
        args = [
            self._binario,
            f"-GPSLatitude={abs(lat)}", f"-GPSLatitudeRef={'N' if lat >= 0 else 'S'}",
            f"-GPSLongitude={abs(lon)}", f"-GPSLongitudeRef={'E' if lon >= 0 else 'W'}",
            f"-XMP:City={campos['cidade']}", f"-XMP:Country={campos['pais']}",
            "-charset", "filename=utf8", str(alvo_real),
        ]
        return subprocess.run(args, capture_output=True, text=True, check=False)

    monkeypatch.setattr(ExifToolWriter, "escrever", escrever_com_hemisferio_errado)

    executor.dry_run(plan_id)
    stats = executor.executar(plan_id)
    # gps sozinho reprova, sem tag fora de escopo nem aviso novo — é
    # falha PARCIAL (EXIF-03), não corrupção; o backup fica de pé. Só
    # o item do sidecar falso é afetado — os outros dois candidatos da
    # fixture `ambiente` usam o writer real, intacto.
    assert stats["falhas_parciais"] == 1

    with factory() as session:
        item = session.get(ExifWriteItem, item_id)
        assert item.status_gps == CampoStatus.FALHA
        # Mensagem distinta de "rejeitado pelo exiftool" (achado da
        # revisão): aqui o exiftool ACEITOU a tag, foi a checagem por
        # valor do app que recusou — a foto está errada.
        assert "não confere com a pedida" in (item.motivo_gps or "")
        assert item.status_cidade == CampoStatus.GRAVADO
        assert item.status_pais == CampoStatus.GRAVADO
    # Sidecar novo (o arquivo não existia antes) não tem "_original" pra
    # preservar — a garantia que importa aqui é a de sempre: a FOTO em
    # si nunca é tocada por uma escrita de sidecar, com ou sem falha.
    assert sha256_full(alvo) == hash_antes


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
            gps_lat_estimado=-22.95, gps_lon_estimado=-43.18,
            gps_estimado_delta_s=300, location_id=loc.id,
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


# -- D-095: timeout do exiftool fica no item, nunca derruba o plano -----------

@tem_exiftool
def test_timeout_do_exiftool_reprova_o_item_e_o_plano_segue(ambiente, monkeypatch):
    """`TimeoutExpired` não é `OSError`: antes atravessava o item, derrubava
    `executar()` e deixava o plano preso em EXECUTANDO (o órfão que o boot
    reconcilia). Agora: campos tentados viram FALHA com motivo claro, o
    original é medido (intacto aqui — nada chegou a rodar), o plano fecha
    em ERRO e a auditoria registra `timeout`."""
    import subprocess

    from fotoorganizer.models import ExifWritePlan, ExifWriteStatus

    factory, executor, origem_dir, plan_id = ambiente
    executor.dry_run(plan_id)
    alvo = origem_dir / "limpa.jpg"
    hash_antes = sha256_full(alvo)

    original_escrever = ExifToolWriter.escrever

    # Só `limpa.jpg` trava; `preenchida.jpg` (cidade/país ainda por gravar)
    # segue o caminho real — prova que o plano CONTINUA depois do timeout.
    def escrever_que_trava(self, origem, campos, destino=None, timeout=None):
        if not str(origem).endswith("limpa.jpg"):
            return original_escrever(self, origem, campos, destino)
        raise subprocess.TimeoutExpired(cmd=["exiftool", str(origem)], timeout=120)

    monkeypatch.setattr(ExifToolWriter, "escrever", escrever_que_trava)

    stats = executor.executar(plan_id)

    assert stats["erros"] == 1
    assert stats["gravados"] == 1  # o outro item foi gravado normalmente
    assert sha256_full(alvo) == hash_antes  # nada tocado — nem backup sobrou
    assert not ExifToolWriter.caminho_backup(alvo).exists()

    with factory() as session:
        plano = session.get(ExifWritePlan, plan_id)
        assert plano.status == ExifWriteStatus.ERRO  # NÃO ficou em EXECUTANDO
        item = session.scalar(
            select(ExifWriteItem).where(ExifWriteItem.origem.endswith("limpa.jpg"))
        )
        assert item.status_gps == CampoStatus.FALHA
        assert item.status_pais == CampoStatus.FALHA
        assert "não respondeu em 120s" in item.motivo_gps
        assert "original intacto" in item.erro
        assert item.backup_original is None
        auditoria = session.scalar(
            select(AuditLog).where(AuditLog.resultado == "timeout")
        )
        assert auditoria is not None
        assert auditoria.detalhe["timeout_s"] == 120
        assert auditoria.detalhe["original"] == "intacto"


@tem_exiftool
def test_timeout_com_original_ja_trocado_aponta_o_backup(ambiente, monkeypatch):
    """Morto entre os dois renames do exiftool, o alvo já é a versão nova e
    o `_original` é o único intacto: o item precisa dizer isso e apontar o
    backup — sem apagar nada (invariante 8)."""
    import subprocess

    factory, executor, origem_dir, plan_id = ambiente
    executor.dry_run(plan_id)
    alvo = origem_dir / "limpa.jpg"

    original_escrever = ExifToolWriter.escrever

    def escreve_e_depois_estoura(self, origem, campos, destino=None, timeout=None):
        # Simula o pior caso: a escrita real aconteceu (arquivo trocado,
        # backup ao lado) e SÓ ENTÃO o processo foi dado como travado.
        resultado = original_escrever(self, origem, campos, destino)
        if not str(origem).endswith("limpa.jpg"):
            return resultado
        raise subprocess.TimeoutExpired(cmd=["exiftool"], timeout=120)

    monkeypatch.setattr(ExifToolWriter, "escrever", escreve_e_depois_estoura)

    stats = executor.executar(plan_id)

    assert stats["erros"] == 1
    backup = ExifToolWriter.caminho_backup(alvo)
    assert backup.exists()  # nunca apagado numa falha
    with factory() as session:
        item = session.scalar(
            select(ExifWriteItem).where(ExifWriteItem.origem.endswith("limpa.jpg"))
        )
        assert "original ALTERADO" in item.erro
        assert item.backup_original == str(backup)
        assert item.hash_pos != item.hash_pre


@tem_exiftool
def test_erro_generico_do_subprocesso_fica_no_item(ambiente, monkeypatch):
    """`SubprocessError` que não é timeout (ex.: o wrapper falhou ao subir
    o processo) — também não é `OSError`, também não pode derrubar o plano."""
    import subprocess

    from fotoorganizer.models import ExifWritePlan, ExifWriteStatus

    factory, executor, origem_dir, plan_id = ambiente
    executor.dry_run(plan_id)
    original_escrever = ExifToolWriter.escrever

    def estoura(self, origem, campos, destino=None, timeout=None, folga_sigint=None):
        if not str(origem).endswith("limpa.jpg"):
            return original_escrever(self, origem, campos, destino)
        raise subprocess.SubprocessError("falha genérica do subprocesso")

    monkeypatch.setattr(ExifToolWriter, "escrever", estoura)
    stats = executor.executar(plan_id)

    assert stats["erros"] == 1 and stats["gravados"] == 1
    with factory() as session:
        assert session.get(ExifWritePlan, plan_id).status == ExifWriteStatus.ERRO
        item = session.scalar(
            select(ExifWriteItem).where(ExifWriteItem.origem.endswith("limpa.jpg"))
        )
        assert "falha genérica" in item.erro


@tem_exiftool
def test_timeout_com_original_ausente_diz_ausente_nao_intacto(ambiente, monkeypatch):
    """Morto entre os dois renames do exiftool: só `_original` e o
    temporário existem, o alvo sumiu do caminho. Dizer "intacto" aqui
    seria registrar um fato falso (invariante 3). O temporário parcial,
    criado por esta mesma escrita, é removido — senão bloquearia toda
    escrita futura; o `_original` fica."""
    import shutil
    import subprocess

    factory, executor, origem_dir, plan_id = ambiente
    executor.dry_run(plan_id)
    alvo = origem_dir / "limpa.jpg"
    backup = ExifToolWriter.caminho_backup(alvo)
    temporario = Path(str(alvo) + "_exiftool_tmp")
    original_escrever = ExifToolWriter.escrever

    def morre_entre_os_renames(self, origem, campos, destino=None, timeout=None, folga_sigint=None):
        if not str(origem).endswith("limpa.jpg"):
            return original_escrever(self, origem, campos, destino)
        shutil.copy(origem, temporario)      # temporário "pronto"
        origem.rename(backup)                # 1º rename feito, 2º não
        raise subprocess.TimeoutExpired(cmd=["exiftool"], timeout=120)

    monkeypatch.setattr(ExifToolWriter, "escrever", morre_entre_os_renames)
    stats = executor.executar(plan_id)

    assert stats["erros"] == 1
    assert not alvo.exists()
    assert backup.exists()          # nunca apagado
    assert not temporario.exists()  # parcial desta escrita: removido
    with factory() as session:
        item = session.scalar(
            select(ExifWriteItem).where(ExifWriteItem.origem.endswith("limpa.jpg"))
        )
        assert "original AUSENTE" in item.erro
        assert "temporário parcial" in item.erro and "removido" in item.erro
        assert item.backup_original == str(backup)
        auditoria = session.scalar(select(AuditLog).where(AuditLog.resultado == "timeout"))
        assert auditoria.detalhe["original"] == "ausente"
        assert auditoria.detalhe["temporario_removido"] == str(temporario)


@tem_exiftool
def test_temporario_que_ja_existia_antes_nao_e_removido_no_timeout(ambiente, monkeypatch):
    import subprocess

    factory, executor, origem_dir, plan_id = ambiente
    executor.dry_run(plan_id)
    alvo = origem_dir / "limpa.jpg"
    temporario = Path(str(alvo) + "_exiftool_tmp")
    temporario.write_bytes(b"de outro processo")  # NÃO é nosso
    original_escrever = ExifToolWriter.escrever

    def estoura(self, origem, campos, destino=None, timeout=None, folga_sigint=None):
        if not str(origem).endswith("limpa.jpg"):
            return original_escrever(self, origem, campos, destino)
        raise subprocess.TimeoutExpired(cmd=["exiftool"], timeout=120)

    monkeypatch.setattr(ExifToolWriter, "escrever", estoura)
    executor.executar(plan_id)

    assert temporario.read_bytes() == b"de outro processo"
    with factory() as session:
        item = session.scalar(
            select(ExifWriteItem).where(ExifWriteItem.origem.endswith("limpa.jpg"))
        )
        assert "já existia antes — não removido" in item.erro


@tem_exiftool
def test_leitura_que_falha_antes_da_escrita_nao_grava_nada(ambiente, monkeypatch):
    """`verificacao.dump` devolve `{}` em falha/timeout de leitura. Lido
    como "tudo vazio", a reconferência ao vivo aprovaria escrever por cima
    de campo preenchido. Não conferido = não gravado."""
    from fotoorganizer.exif_write import verificacao

    factory, executor, origem_dir, plan_id = ambiente
    executor.dry_run(plan_id)
    antes = hashes(origem_dir)
    monkeypatch.setattr(verificacao, "dump", lambda caminho, binario="exiftool": {})

    stats = executor.executar(plan_id)

    assert stats["gravados"] == 0 and stats["erros"] == 2
    assert hashes(origem_dir) == antes  # nenhum subprocesso de escrita rodou
    with factory() as session:
        item = session.scalar(
            select(ExifWriteItem).where(ExifWriteItem.origem.endswith("limpa.jpg"))
        )
        assert "não consegui ler as tags" in item.erro
        assert item.status_gps == CampoStatus.PRONTO  # nada mudou de status


@tem_exiftool
def test_timeout_no_sidecar_remove_o_xmp_parcial_e_nao_fala_do_original(ambiente, monkeypatch):
    """Sidecar é criado direto no caminho final (sem temporário): morto no
    meio, sobra um `.xmp` truncado que viraria "sidecar já existe" em todo
    dry-run seguinte, para sempre. Ele é saída parcial desta escrita
    (a guarda no topo de `_executar_item` garante que não existia antes) —
    é removido. E a origem nunca foi tocada: o motivo não pode falar em
    "original intacto/alterado"."""
    factory, executor, origem_dir, plan_id = ambiente
    alvo = make_jpeg(origem_dir / "para_sidecar.jpg", gps=None)
    hash_antes = sha256_full(alvo)
    sidecar_destino = Path(str(alvo) + ".xmp")

    with factory() as session:
        fonte_id = session.scalar(select(Source.id))
        loc = session.scalar(select(Location))
        media = _media_avulsa(session, fonte_id, alvo, loc.id)
        item = _item_manual(
            session, plan_id, media, formato_suportado=False,
            sidecar_destino=str(sidecar_destino),
        )
        session.commit()
        item_id = item.id

    executor.dry_run(plan_id)
    original_escrever = ExifToolWriter.escrever

    def trava_no_sidecar(self, origem, campos, destino=None, timeout=None, folga_sigint=None):
        if destino is None or destino.suffix.lower() != ".xmp":
            return original_escrever(self, origem, campos, destino)
        destino.write_text("<x:xmpmeta truncado")  # o que um kill deixa
        raise subprocess.TimeoutExpired(cmd=["exiftool"], timeout=120)

    monkeypatch.setattr(ExifToolWriter, "escrever", trava_no_sidecar)
    executor.executar(plan_id)

    assert not sidecar_destino.exists()
    assert sha256_full(alvo) == hash_antes
    with factory() as session:
        item = session.get(ExifWriteItem, item_id)
        assert "sidecar parcial" in item.erro and "removido" in item.erro
        assert "original" not in item.erro
        auditoria = session.scalar(
            select(AuditLog).where(
                AuditLog.resultado == "timeout",
                AuditLog.detalhe["item_id"].as_integer() == item_id,
            )
        )
        assert auditoria.detalhe["sidecar_parcial_removido"] == str(sidecar_destino)
        assert "original" not in auditoria.detalhe
