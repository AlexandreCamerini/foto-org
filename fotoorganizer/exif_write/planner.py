"""Descoberta de candidatos e montagem do plano de escrita EXIF (D-075).

Assim como o `planner.py` de `operations/`, este arquivo é só registro:
nenhum arquivo do disco é tocado, aberto ou verificado aqui. A checagem de
"campo vazio" feita neste módulo é a barata — baseada só no que o catálogo
já sabe (`MediaFile`, `Location`, `MetadataEntry`) — e serve apenas para
montar a lista de candidatos. A checagem autoritativa e ao vivo (o arquivo
de fato ainda não tem o campo, agora, no disco) acontece no dry-run e de
novo na execução (plano 06-05), porque o catálogo pode estar desatualizado
em relação ao disco entre um scan e outro.

Escopo é global (06-UI-SPEC.md "Entry point"): uma linha por arquivo
catalogado elegível com pelo menos um valor inferido disponível, sem
recorte por fonte — ao contrário de `operations/planner.py`, não há filtro
de `Source` aqui.
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.exif_write import formatos, sync_detect
from fotoorganizer.models import (
    AuditLog,
    CampoStatus,
    ExifWriteItem,
    ExifWritePlan,
    ExifWriteStatus,
    Location,
    MediaFile,
    MetadataEntry,
)

log = logging.getLogger(__name__)

# Estados em que um campo não tem mais nada a fazer: já foi gravado, já
# estava preenchido no arquivo (pulado) ou nunca teve valor inferido pelo
# motor. Uma mídia só sai da lista de candidatos quando os TRÊS campos de
# um mesmo item chegaram a algum desses estados — item com qualquer campo
# em FALHA ou PENDENTE continua elegível: replanejar depois de falha
# parcial é o caminho de recuperação.
_RESOLVIDOS = (CampoStatus.GRAVADO, CampoStatus.PULADO, CampoStatus.SEM_VALOR)

_MOTIVO_SEM_VALOR = "nenhum valor inferido para este campo"


def _motivo_pulado(valor: str) -> str:
    """Copy exigida pelo contrato da UI-SPEC para campo já preenchido."""
    return f"já preenchido: {valor} — não sobrescrito"


class ExifWritePlanner:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._factory = session_factory

    def criar_plano_exif(self, nome: str | None = None) -> int | None:
        """Cria um plano de ESCRITA EXIF de localização para todo arquivo
        catalogado elegível com pelo menos um dos 3 campos (GPS, cidade,
        país) vazio e com valor inferido disponível. Devolve o id do plano
        criado, ou `None` quando não havia nada a planejar.

        Nada aqui toca o disco: só consulta o catálogo e grava o plano no
        banco, exatamente como `operations/planner.py` faz para cópia."""
        with self._factory() as session:
            candidatos = list(session.execute(
                select(MediaFile, Location)
                .outerjoin(Location, MediaFile.location_id == Location.id)
                .where(
                    MediaFile.organizavel,
                    (
                        (
                            MediaFile.gps_lat.is_(None)
                            & MediaFile.gps_lat_estimado.is_not(None)
                        )
                        | (
                            Location.cidade.is_not(None)
                            | Location.pais.is_not(None)
                        )
                    ),
                )
                .order_by(MediaFile.caminho)
            ))

            # Sem esta exclusão, todo plano novo renasceria com centenas de
            # linhas "nada a gravar" (a idempotência sozinha não basta — o
            # candidato continuaria satisfazendo o WHERE acima) e a tela
            # perderia o sinal do que ainda precisa de atenção.
            resolvidas = set(session.scalars(
                select(ExifWriteItem.media_id).where(
                    ExifWriteItem.status_gps.in_(_RESOLVIDOS),
                    ExifWriteItem.status_cidade.in_(_RESOLVIDOS),
                    ExifWriteItem.status_pais.in_(_RESOLVIDOS),
                )
            ))
            pendentes = [
                (media, location) for media, location in candidatos
                if media.id not in resolvidas
            ]
            if not pendentes:
                return None

            # Uma única consulta agregada (não N+1, T-06-13) para saber
            # quais mídias já têm cidade e/ou país gravados no próprio
            # arquivo — o valor concreto vira o motivo de PULADO.
            cidade_presente: dict[int, str] = {}
            pais_presente: dict[int, str] = {}
            for media_id, chave, valor in session.execute(
                select(
                    MetadataEntry.media_id, MetadataEntry.chave, MetadataEntry.valor
                ).where(
                    MetadataEntry.namespace.in_(("iptc", "xmp")),
                    MetadataEntry.chave.in_(
                        ("City", "Country", "Country-PrimaryLocationName")
                    ),
                )
            ):
                if not valor:
                    continue
                if chave == "City":
                    cidade_presente.setdefault(media_id, valor)
                else:
                    pais_presente.setdefault(media_id, valor)

            plano = ExifWritePlan(
                nome=nome or f"Localização — {len(pendentes)} arquivos",
                status=ExifWriteStatus.PLANEJADA,
            )
            session.add(plano)
            session.flush()
            # Local para não repetir `plano.id` em cada item — mesmo valor,
            # nome mais curto de manter na leitura do laço abaixo.
            id_do_plano = plano.id

            nao_suportados = 0
            sincronizados = 0
            for media, location in pendentes:
                valor_gps_lat = media.gps_lat_estimado
                valor_gps_lon = media.gps_lon_estimado
                valor_cidade = location.cidade if location else None
                valor_pais = location.pais if location else None

                if media.gps_lat is not None:
                    status_gps = CampoStatus.PULADO
                    motivo_gps = _motivo_pulado(f"{media.gps_lat}, {media.gps_lon}")
                elif valor_gps_lat is None:
                    status_gps = CampoStatus.SEM_VALOR
                    motivo_gps = _MOTIVO_SEM_VALOR
                else:
                    status_gps = CampoStatus.PENDENTE
                    motivo_gps = None

                if media.id in cidade_presente:
                    status_cidade = CampoStatus.PULADO
                    motivo_cidade = _motivo_pulado(cidade_presente[media.id])
                elif valor_cidade is None:
                    status_cidade = CampoStatus.SEM_VALOR
                    motivo_cidade = _MOTIVO_SEM_VALOR
                else:
                    status_cidade = CampoStatus.PENDENTE
                    motivo_cidade = None

                if media.id in pais_presente:
                    status_pais = CampoStatus.PULADO
                    motivo_pais = _motivo_pulado(pais_presente[media.id])
                elif valor_pais is None:
                    status_pais = CampoStatus.SEM_VALOR
                    motivo_pais = _MOTIVO_SEM_VALOR
                else:
                    status_pais = CampoStatus.PENDENTE
                    motivo_pais = None

                origem = Path(media.caminho)
                # MediaFile.extensao é gravada sem o ponto pelo scanner
                # (scanner.py:445); fotoorganizer.exif_write.formatos
                # espera extensão com ponto (ex.: ".jpg").
                extensao = f".{media.extensao.lower()}"
                suportado = formatos.suportado(extensao)
                motivo_nao_suportado = None
                sidecar_destino = None
                if not suportado:
                    motivo_nao_suportado = formatos.motivo(extensao)
                    sidecar_destino = str(formatos.caminho_sidecar(origem))
                    nao_suportados += 1

                sincronizada = sync_detect.pasta_sincronizada(origem)
                if sincronizada is not None:
                    sincronizados += 1

                session.add(ExifWriteItem(
                    plan_id=id_do_plano, media_id=media.id, origem=str(origem),
                    valor_gps_lat=valor_gps_lat, valor_gps_lon=valor_gps_lon,
                    valor_cidade=valor_cidade, valor_pais=valor_pais,
                    status_gps=status_gps, status_cidade=status_cidade,
                    status_pais=status_pais,
                    motivo_gps=motivo_gps, motivo_cidade=motivo_cidade,
                    motivo_pais=motivo_pais,
                    pasta_sincronizada=sincronizada,
                    formato_suportado=suportado,
                    motivo_nao_suportado=motivo_nao_suportado,
                    sidecar_destino=sidecar_destino,
                    # D-06 é opt-in: sidecar não pedido não nasce marcado.
                    # D-02 é opt-out: o resto nasce marcado, o dono desmarca.
                    incluido=False if not suportado else True,
                ))

            # O id do ExifWritePlan viaja em `detalhe` (JSON) porque a
            # coluna `AuditLog.plan_id` tem FK real e ativa para
            # `operation_plans.id` (RESEARCH.md Pitfall 5) — uma sequência
            # de PK independente da de ExifWritePlan.
            session.add(AuditLog(plan_id=None, acao="plano_exif_criado",
                detalhe={
                    "exif_plan_id": id_do_plano,
                    "itens": len(pendentes),
                    "nao_suportados": nao_suportados,
                    "sincronizados": sincronizados,
                },
                resultado="ok",
            ))
            session.commit()
            log.info(
                "plano exif %s criado com %d itens (%d não suportados, "
                "%d sincronizados)",
                plano.id, len(pendentes), nao_suportados, sincronizados,
            )
            return plano.id
