"""Executor de planos de escrita EXIF de localização (D-075) — dry-run
autoritativo e execução verificada por diff completo de tags.

Regras rígidas (CLAUDE.md, invariante 7 revogado em parte por D-075):
- executar sem dry-run aprovado é impossível (EXIF-01);
- só campo comprovadamente vazio, reconferido AO VIVO no instante da
  escrita, é preenchido — nunca sobrescreve (EXIF-02);
- o veredito de cada escrita é o diff completo de tags antes/depois, nunca
  o exit code do subprocesso nem a mensagem-resumo dele (EXIF-03/EXIF-04);
- falha parcial é resultado real e esperado, registrado campo a campo no
  audit log, não um erro genérico que esconde o que entrou;
- rerodar o mesmo plano é idempotente: campo já gravado ou já preenchido
  não é tocado de novo;
- item desmarcado pelo dono não é escrito — nenhum subprocesso roda para
  ele (D-02);
- linha de formato não suportado marcada pelo dono grava sidecar `.xmp`,
  nunca o original (D-06/EXIF-05).

Existe um analog estrutural em `fotoorganizer/operations/executor.py`
(execução de cópia física) — mesmo padrão de rigor (plano -> dry-run ->
aprovação -> execução -> auditoria), mas o modelo mental de lá **não
transfere** e nada de lá é herdado aqui:

1. A cópia física se protege criando um caminho novo que ainda não existe
   — o próprio sistema operacional recusa sobrescrita por construção.
   Mutação in-place não tem esse truque: o arquivo já existe, sempre, e
   quem decide se pode escrever é o diff de tags, não a criação exclusiva.
2. O subprocesso de escrita (exiftool) sai 0 mesmo quando pulou uma tag
   malformada — o veredito de sucesso da cópia física (hash do arquivo
   inteiro) não serve aqui: hash de arquivo inteiro muda por construção
   numa mutação intencional, e o exit code é comprovadamente enganoso
   (RESEARCH.md Pitfall 1/2). O único sinal confiável é
   `verificacao.diferenca`/`campo_gravado`.
3. O resultado é por CAMPO (GPS/cidade/país), não por item — o
   subprocesso de escrita não é atômico por tag dentro de uma mesma
   invocação.
4. O backup `_original` que o próprio exiftool cria (o writer nunca passa
   `-overwrite_original`) é a cópia de recuperação durante a janela entre
   escrita e verificação; só é apagado depois que o diff aprovar tudo —
   quem decide restaurar manualmente é o dono, o app nunca desfaz nada
   sozinho (invariante 8 do CLAUDE.md).
5. `AuditLog.plan_id` fica sempre `None` nas linhas geradas aqui: a coluna
   tem FK real e ativa para o plano de cópia física, uma sequência de PK
   independente da deste domínio (RESEARCH.md Pitfall 5, herdado de 06-01).
   O id do `ExifWritePlan` viaja em `detalhe["exif_plan_id"]`.
6. Rerodar é idempotente pela pré-condição de campo vazio, reconferida ao
   vivo a cada execução — não por um flag de "já processado" no item.

Reusado do analog: só `ExecutionControl` (cancelamento cooperativo
genérico, sem nenhuma semântica de cópia de arquivo).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.exif_write import sync_detect, verificacao
from fotoorganizer.exif_write.writer import ExifToolWriter, ValorInvalido, validar_campos
from fotoorganizer.models import (
    AuditLog,
    CampoStatus,
    ExifWriteItem,
    ExifWritePlan,
    ExifWriteStatus,
)
from fotoorganizer.operations.executor import ExecutionControl
from fotoorganizer.security.hashing import sha256_full

log = logging.getLogger(__name__)

_MOTIVO_SEM_VALOR = "nenhum valor inferido para este campo"
_MOTIVO_SIDECAR_EXISTE = "sidecar já existe — nunca será sobrescrito"

# Rótulo de UI (06-UI-SPEC.md "per-tag failure breakdown") por campo — usado
# na mensagem de falha, nunca no nome interno do campo.
_ROTULOS_CAMPO = {"gps": "GPS", "cidade": "Cidade", "pais": "País"}


class DryRunObrigatorioExif(RuntimeError):
    """Levantada quando `executar()` é chamado sem dry-run aprovado."""


def _agora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _valor_a_gravar(item: ExifWriteItem, campo: str) -> object | None:
    """Valor inferido pelo planner para `campo`, ou `None` se o motor não
    inferiu nada. GPS devolve `(lat, lon)`, os outros dois um `str`."""
    if campo == "gps":
        if item.valor_gps_lat is None or item.valor_gps_lon is None:
            return None
        return (item.valor_gps_lat, item.valor_gps_lon)
    if campo == "cidade":
        return item.valor_cidade
    if campo == "pais":
        return item.valor_pais
    raise ValueError(f"campo desconhecido: {campo!r}")  # pragma: no cover


def _campo_ja_preenchido(
    campo: str, dump_alvo: dict[str, str], sidecar: bool,
) -> tuple[bool, str | None]:
    """`True` e um valor legível quando alguma tag de `campo` já está
    presente e não-vazia em `dump_alvo` — a checagem AO VIVO que decide
    `PULADO` (EXIF-02), tanto no dry-run quanto na reconferência TOCTOU da
    execução."""
    tags = verificacao.TAGS_POR_CAMPO_SIDECAR if sidecar else verificacao.TAGS_POR_CAMPO
    presentes = {tag: dump_alvo[tag] for tag in tags.get(campo, ()) if dump_alvo.get(tag)}
    if not presentes:
        return False, None
    if campo != "gps":
        return True, next(iter(presentes.values()))

    # GPS: tenta montar "lat, lon" com sinal do Ref quando disponível
    # (escrita direta grava Ref separado; sidecar grava valor já assinado).
    if sidecar:
        lat = presentes.get("XMP-exif:GPSLatitude")
        lon = presentes.get("XMP-exif:GPSLongitude")
    else:
        lat_bruto = presentes.get("GPS:GPSLatitude")
        lon_bruto = presentes.get("GPS:GPSLongitude")
        lat_ref = dump_alvo.get("GPS:GPSLatitudeRef")
        lon_ref = dump_alvo.get("GPS:GPSLongitudeRef")
        lat = f"-{lat_bruto}" if lat_bruto and lat_ref == "S" else lat_bruto
        lon = f"-{lon_bruto}" if lon_bruto and lon_ref == "W" else lon_bruto
    if lat and lon:
        return True, f"{lat}, {lon}"
    return True, next(iter(presentes.values()))


class ExifWriteExecutor:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._factory = session_factory

    # -- dry-run --------------------------------------------------------
    def dry_run(self, plan_id: int) -> dict:
        """Passo autoritativo (EXIF-01/EXIF-02): o plano foi montado pelo
        planner a partir do catálogo, que pode estar desatualizado em
        relação ao disco. Aqui o disco é lido AO VIVO, em lote, e cada
        campo é promovido a `PRONTO`/`PULADO`/`SEM_VALOR`/`FALHA` com
        motivo — o resultado é o que `executar()` exige ter acontecido
        antes de escrever qualquer byte."""
        with self._factory() as session:
            plano = session.get(ExifWritePlan, plan_id)
            itens = self._itens(session, plan_id)

            caminhos_diretos = [Path(item.origem) for item in itens if item.formato_suportado]
            # Uma única invocação em lote, não uma por arquivo: ~1.400
            # arquivos a ~200 ms cada seriam ~5 min de dry-run; em lote são
            # segundos (mesmo raciocínio do leitor de scan aplicado à
            # escrita).
            dumps = verificacao.dump_lote(caminhos_diretos) if caminhos_diretos else {}

            problemas: list[str] = []
            prontos = 0
            campos_a_gravar = 0
            sidecars = 0
            nao_suportados = 0
            sincronizados = 0

            for item in itens:
                origem = Path(item.origem)
                # Recomputado sempre, mesmo se a origem sumiu — é checagem
                # pura de caminho, não depende do arquivo existir.
                item.pasta_sincronizada = sync_detect.pasta_sincronizada(origem)
                if item.pasta_sincronizada is not None:
                    sincronizados += 1
                if not item.formato_suportado:
                    nao_suportados += 1

                if not origem.is_file():
                    problemas.append(f"{origem.name}: origem indisponível (volume desmontado?)")
                    continue  # nenhum campo muda de status

                if item.formato_suportado:
                    sidecar = False
                    dump_alvo = dumps.get(str(origem), {})
                else:
                    sidecar = True
                    alvo_sidecar = Path(item.sidecar_destino)
                    if alvo_sidecar.exists():
                        problemas.append(f"{origem.name}: {_MOTIVO_SIDECAR_EXISTE}")
                        for campo in ("gps", "cidade", "pais"):
                            setattr(item, f"status_{campo}", CampoStatus.PULADO)
                            setattr(item, f"motivo_{campo}", _MOTIVO_SIDECAR_EXISTE)
                        continue
                    dump_alvo = {}

                campos_prontos_item = 0
                for campo in ("gps", "cidade", "pais"):
                    valor = _valor_a_gravar(item, campo)
                    if valor is None:
                        status, motivo = CampoStatus.SEM_VALOR, _MOTIVO_SEM_VALOR
                    else:
                        ja_preenchido, valor_existente = _campo_ja_preenchido(
                            campo, dump_alvo, sidecar
                        )
                        if ja_preenchido:
                            status = CampoStatus.PULADO
                            motivo = f"já preenchido: {valor_existente} — não sobrescrito"
                        else:
                            try:
                                validar_campos({campo: valor})
                            except ValorInvalido as exc:
                                status, motivo = CampoStatus.FALHA, str(exc)
                            else:
                                status, motivo = CampoStatus.PRONTO, None
                                campos_prontos_item += 1
                    setattr(item, f"status_{campo}", status)
                    setattr(item, f"motivo_{campo}", motivo)

                if item.incluido and campos_prontos_item:
                    prontos += 1
                    campos_a_gravar += campos_prontos_item
                    if sidecar:
                        sidecars += 1

            plano.dry_run_em = _agora()
            session.add(AuditLog(plan_id=None, acao="dry_run_exif", detalhe={
                "exif_plan_id": plan_id, "prontos": prontos,
                "problemas": len(problemas), "campos_a_gravar": campos_a_gravar,
                "sidecars": sidecars, "nao_suportados": nao_suportados,
                "sincronizados": sincronizados,
            }, resultado="ok"))
            session.commit()
            return {
                "prontos": prontos, "problemas": problemas,
                "campos_a_gravar": campos_a_gravar, "sidecars": sidecars,
                "nao_suportados": nao_suportados, "sincronizados": sincronizados,
            }

    @staticmethod
    def _prontos_no_ultimo_dry_run(session: Session, plan_id: int) -> int | None:
        """Quantos itens o último dry-run considerou graváveis.

        `AuditLog.plan_id` fica sempre `None` neste domínio (Pitfall 5) —
        o filtro é por `acao == "dry_run_exif"` e pelo id do plano dentro
        de `detalhe` (JSON), não pela coluna `plan_id`."""
        detalhe = session.scalar(
            select(AuditLog.detalhe)
            .where(
                AuditLog.acao == "dry_run_exif",
                AuditLog.detalhe["exif_plan_id"].as_integer() == plan_id,
            )
            .order_by(AuditLog.id.desc())
            .limit(1)
        )
        return detalhe.get("prontos") if detalhe else None

    # -- seleção (D-02) ---------------------------------------------------
    def aplicar_selecao(self, plan_id: int, itens: list[int] | None) -> int:
        """Materializa D-02 (o dono desmarca item pontual antes de
        confirmar): persiste `ExifWriteItem.incluido` ANTES de `executar()`
        começar. A execução relê do banco, então passar a seleção só como
        argumento perderia o registro de auditoria e a fonte de verdade da
        retomada. `itens is None` não muda nada, só devolve a contagem
        atual."""
        with self._factory() as session:
            todos = self._itens(session, plan_id)
            if itens is not None:
                selecionados = set(itens)
                for item in todos:
                    item.incluido = item.id in selecionados
                incluidos = sum(1 for item in todos if item.incluido)
                session.add(AuditLog(plan_id=None, acao="selecao_exif", detalhe={
                    "exif_plan_id": plan_id, "incluidos": incluidos,
                    "excluidos": len(todos) - incluidos,
                }, resultado="ok"))
                session.commit()
                return incluidos
            return sum(1 for item in todos if item.incluido)

    def _itens(self, session: Session, plan_id: int) -> list[ExifWriteItem]:
        return list(session.scalars(
            select(ExifWriteItem).where(ExifWriteItem.plan_id == plan_id)
            .order_by(ExifWriteItem.id)
        ))

    # -- execução ---------------------------------------------------------
    def executar(
        self,
        plan_id: int,
        progress: Callable[[int, int, str], None] | None = None,
        control: ExecutionControl | None = None,
    ) -> dict:
        control = control or ExecutionControl()
        with self._factory() as session:
            plano = session.get(ExifWritePlan, plan_id)
            if plano.dry_run_em is None:
                raise DryRunObrigatorioExif("execute o dry-run antes de qualquer escrita")
            # Ter rodado o dry-run não basta: ele precisa ter aprovado algo
            # (caso real que motivou o mesmo gate no analog de cópia física
            # — origens todas num volume desmontado "executavam" sem
            # escrever nada).
            prontos = self._prontos_no_ultimo_dry_run(session, plan_id)
            if prontos == 0:
                raise DryRunObrigatorioExif(
                    "o último dry-run não encontrou nada a gravar — verifique as "
                    "origens e rode o dry-run de novo"
                )

            plano.status = ExifWriteStatus.EXECUTANDO
            session.add(AuditLog(plan_id=None, acao="execucao_exif_iniciada", detalhe={
                "exif_plan_id": plan_id,
            }, resultado="ok"))
            session.commit()

            itens = self._itens(session, plan_id)
            pendentes = [
                item for item in itens
                if item.incluido and CampoStatus.PRONTO in (
                    item.status_gps, item.status_cidade, item.status_pais,
                )
            ]
            # Item não incluído (D-02) entra direto em "pulados" — nenhuma
            # chamada de escrita acontece para ele, é isso que prova o
            # opt-out.
            stats = {
                "gravados": 0, "sidecars": 0,
                "pulados": len(itens) - len(pendentes),
                "falhas_parciais": 0, "erros": 0, "cancelado": False,
            }

            for n, item in enumerate(pendentes, start=1):
                if control.cancelado:
                    stats["cancelado"] = True
                    break
                if progress:
                    progress(n, len(pendentes), item.origem)
                self._executar_item(session, item, stats)
                session.commit()  # por item — retomada segura

            if stats["cancelado"]:
                plano.status = ExifWriteStatus.CANCELADA
            elif stats["erros"]:
                plano.status = ExifWriteStatus.ERRO
            else:
                # falhas_parciais NÃO derruba o plano para ERRO — parcial é
                # resultado esperado e já está registrado campo a campo.
                plano.status = ExifWriteStatus.CONCLUIDA
            session.add(AuditLog(plan_id=None, acao="execucao_exif_finalizada", detalhe={
                "exif_plan_id": plan_id, **stats,
            }, resultado=plano.status.value))
            session.commit()
            return stats

    def _executar_item(self, session: Session, item: ExifWriteItem, stats: dict) -> None:
        origem = Path(item.origem)
        if not origem.is_file():
            item.erro = "origem indisponível (volume desconectado?)"
            stats["erros"] += 1
            self._audit_item(session, item, "escrita_exif", "erro")
            return  # nenhum campo muda de status — rerodar depois retoma

        sidecar = not item.formato_suportado
        alvo = Path(item.sidecar_destino) if sidecar else origem
        if sidecar and alvo.exists():
            item.erro = _MOTIVO_SIDECAR_EXISTE
            stats["erros"] += 1
            self._audit_item(session, item, "escrita_exif", "erro")
            return

        try:
            antes_alvo = verificacao.dump(alvo) if alvo.exists() else {}
            avisos_antes = verificacao.avisos(alvo) if alvo.exists() else set()

            # Reconferência AO VIVO (TOCTOU, T-06-22): só entra na lista de
            # campos a gravar quem continua PRONTO no dry-run E cujas tags
            # continuam ausentes agora — campo que passou a estar
            # preenchido entre o dry-run e agora vira PULADO sem tocar em
            # nada. É isto que torna rerodar idempotente (EXIF-02), sem
            # depender do dry-run estar fresco.
            campos: dict[str, object] = {}
            for campo in ("gps", "cidade", "pais"):
                if getattr(item, f"status_{campo}") != CampoStatus.PRONTO:
                    continue
                ja_preenchido, valor_existente = _campo_ja_preenchido(campo, antes_alvo, sidecar)
                if ja_preenchido:
                    setattr(item, f"status_{campo}", CampoStatus.PULADO)
                    setattr(
                        item, f"motivo_{campo}",
                        f"já preenchido: {valor_existente} — não sobrescrito",
                    )
                    continue
                campos[campo] = _valor_a_gravar(item, campo)

            if not campos:
                # Nenhum subprocesso é chamado — é isso que garante que
                # rerodar não mexe em nada.
                stats["pulados"] += 1
                self._audit_item(session, item, "escrita_exif", "pulado")
                return

            try:
                validar_campos(campos)
            except ValorInvalido as exc:
                for campo in campos:
                    setattr(item, f"status_{campo}", CampoStatus.FALHA)
                    setattr(item, f"motivo_{campo}", str(exc))
                item.erro = str(exc)
                stats["erros"] += 1
                self._audit_item(session, item, "escrita_exif", "erro")
                return

            item.hash_pre = sha256_full(origem)
            # `resultado.stderr` só compõe motivo de falha — o veredito
            # NUNCA vem do processo em si (T-06-23): ele sai 0 mesmo tendo
            # aceitado GPS fora de faixa em silêncio.
            resultado = ExifToolWriter().escrever(
                origem, campos, destino=alvo if alvo != origem else None,
            )
            log.debug(
                "exiftool escreveu %s (stderr=%r)", alvo, resultado.stderr.strip()
            )

            depois = verificacao.dump(alvo)
            avisos_depois = verificacao.avisos(alvo)
            diff = verificacao.diferenca(antes_alvo, depois)

            # Allowlist condicional D-077 (06-04b): sem isto, toda escrita
            # real em .jpg/.cr2 reprova de novo por deslocamento de offset
            # de bloco binário pré-existente (miniatura, MPF) — regressão
            # silenciosa do que a remedição acabou de aprovar. O backup
            # `_original` é byte a byte o "antes" da reclassificação, sem
            # precisar de snapshot extra (mesmo padrão de
            # scripts/testar_escrita_exif.py::testar_amostra).
            backup = ExifToolWriter.caminho_backup(alvo)
            if diff.inesperadas and backup.exists():
                diff = verificacao.reclassificar_deslocamentos_de_offset(
                    diff, antes_alvo, depois, backup, alvo
                )
            novos_avisos = avisos_depois - avisos_antes

            # Veredito por campo (T-06-23): campo_gravado exige TODAS as
            # tags do campo em diff.esperadas — meio campo gravado é falha.
            for campo in campos:
                if verificacao.campo_gravado(campo, diff, sidecar=sidecar):
                    setattr(item, f"status_{campo}", CampoStatus.GRAVADO)
                    setattr(item, f"motivo_{campo}", None)
                else:
                    setattr(item, f"status_{campo}", CampoStatus.FALHA)
                    setattr(
                        item, f"motivo_{campo}",
                        f"{_ROTULOS_CAMPO[campo]}: valor rejeitado pelo exiftool "
                        "(ver auditoria)",
                    )

            item.hash_pos = sha256_full(origem)

            if diff.inesperadas or novos_avisos:
                # Corrupção (T-06-24): tag fora de escopo mudou, ou o
                # exiftool passou a avisar algo novo — reprova TUDO que foi
                # tentado, preserva o backup (quem decide restaurar é o
                # dono, invariante 8).
                for campo in campos:
                    setattr(item, f"status_{campo}", CampoStatus.FALHA)
                item.erro = (
                    f"tags fora de localização mudaram: {sorted(diff.inesperadas)}"
                    if diff.inesperadas
                    else f"exiftool passou a avisar: {sorted(novos_avisos)}"
                )
                if backup.exists():
                    item.backup_original = str(backup)
                stats["erros"] += 1
                self._audit_item(
                    session, item, "escrita_exif", "falha_verificacao",
                    extra={"tags_gravadas": sorted(diff.esperadas)},
                )
                return  # backup NUNCA é apagado numa falha de verificação

            todos_gravados = all(
                getattr(item, f"status_{campo}") == CampoStatus.GRAVADO for campo in campos
            )
            if todos_gravados:
                # Limpeza do backup (Pitfall 7): só depois do diff e do
                # delta de avisos aprovarem TUDO — o backup é cópia
                # idêntica do original antes da mutação já verificada;
                # mantê-lo para sempre polui a árvore que o scanner trata
                # como observada-somente-leitura e confunde cliente de
                # sync.
                if backup.exists():
                    try:
                        backup.unlink()
                    except OSError as exc:
                        # Nunca pode derrubar uma escrita já verificada —
                        # a limpeza é auxiliar, a escrita real já está
                        # correta e confirmada pelo diff.
                        log.warning("falha ao apagar backup %s: %s", backup, exc)
                    else:
                        session.add(AuditLog(
                            plan_id=None, acao="limpeza_backup_exiftool", detalhe={
                                "exif_plan_id": item.plan_id, "item_id": item.id,
                                "backup": str(backup),
                            }, resultado="ok",
                        ))
                item.erro = None
                item.backup_original = None
                if sidecar:
                    stats["sidecars"] += 1
                else:
                    stats["gravados"] += 1
                self._audit_item(
                    session, item, "escrita_exif_verificada", "ok",
                    extra={"tags_gravadas": sorted(diff.esperadas)},
                )
            else:
                # Falha parcial (EXIF-03): algum campo gravou, algum não,
                # sem tag inesperada — resultado real e esperado, mantém o
                # backup.
                stats["falhas_parciais"] += 1
                if backup.exists():
                    item.backup_original = str(backup)
                self._audit_item(
                    session, item, "escrita_exif", "falha_parcial",
                    extra={"tags_gravadas": sorted(diff.esperadas)},
                )
        except OSError as exc:
            # I/O inesperado (ex.: origem some entre o `is_file()` acima e
            # `sha256_full`, ou o subprocesso não sobe) — item por item,
            # nunca derruba o plano inteiro (T-06-30), no molde do analog.
            item.erro = str(exc)
            stats["erros"] += 1
            self._audit_item(session, item, "escrita_exif", "erro")

    def _audit_item(
        self, session: Session, item: ExifWriteItem, acao: str, resultado: str,
        extra: dict | None = None,
    ) -> None:
        """`campos` + `tags_gravadas` juntos são exatamente o que EXIF-03
        pede: quais tags entraram antes do erro, numa linha só."""
        detalhe = {
            "exif_plan_id": item.plan_id, "item_id": item.id,
            "origem": item.origem,
            "alvo": item.sidecar_destino if not item.formato_suportado else item.origem,
            "hash_pre": item.hash_pre, "hash_pos": item.hash_pos,
            "campos": {
                "gps": item.status_gps.value,
                "cidade": item.status_cidade.value,
                "pais": item.status_pais.value,
            },
            "tags_gravadas": [],
        }
        if extra:
            detalhe.update(extra)
        session.add(AuditLog(plan_id=None, acao=acao, detalhe=detalhe, resultado=resultado))
