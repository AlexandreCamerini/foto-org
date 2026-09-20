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
from datetime import timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.exif_write import formatos, sync_detect
from fotoorganizer.grouping.correlacao import campos_confiaveis
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

# Até onde faz sentido escrever o ponto EXATO da doadora como GPS do
# arquivo original, ou o nome da cidade que a `Location` desse mesmo
# ponto resolveu: nunca mais fundo do que a herança sustenta de verdade.
# Usa o predicado REAL do motor (`campos_confiaveis`, a MESMA função que
# `_campos_do_lugar` em `server/app.py` chama para decidir o que a tela
# mostra) em vez de uma janela derivada — uma constante paralela já
# divergiu uma vez nesta fatia (uma versão anterior usava
# `RAIO_TETO_M/VELOCIDADE_PLAUSIVEL_MS` = 2h19, 19 min além da janela de
# região real, e reabria a escrita de GPS exato para 566 mídias
# só-país nessa fresta — achado da revisão com olhos frescos).
#
# GPS exato exige "regiao" (não precisa de "cidade": região já é a escala
# de deslocamento de pessoa que `raio_incerteza` calibra). Cidade exige
# "cidade" propriamente dita (D-025). Sem isto, uma herança só-país
# (2h–48h, D-085) resolve `Location.cidade`/coordenada do MESMO ponto
# distante da doadora — a tela esconde isso (`_campos_do_lugar`), o plano
# de escrita não pode continuar propondo o que a tela se recusa a
# mostrar. País segue sem guarda: D-025 o sustenta em qualquer Δt da
# própria janela, por desenho.
def _campos_da_heranca(delta_s: int | None) -> frozenset[str]:
    if delta_s is None:
        return frozenset()
    return frozenset(c for c, _ in campos_confiaveis(timedelta(seconds=delta_s)))

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
                            # A candidatura aqui é barata e propositalmente
                            # larga (qualquer herança, qualquer Δt); a
                            # exigência de granularidade real é UMA SÓ,
                            # em Python, no laço abaixo (`_campos_da_heranca`)
                            # — repetir o predicado em SQL foi exatamente o
                            # que divergiu nesta fatia (achado da revisão).
                        )
                        | (
                            (
                                Location.cidade.is_not(None)
                                | Location.pais.is_not(None)
                            )
                            # Lugar pela cidade escrita na pasta (D-083,
                            # fonte "pasta:") NÃO entra: é a origem mais
                            # fraca (0,60) e a escrita no original é a
                            # operação mais irreversível do app — só com
                            # decisão explícita do dono.
                            & Location.fonte.not_like("pasta:%")
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
                # O predicado REAL do motor (`campos_confiaveis`), não uma
                # janela paralela: herança só-país (Δt fora de "regiao",
                # D-085) nunca fornece o par lat/lon nem o nome da cidade —
                # a linha pode ter entrado pela perna de cidade/país
                # (`Location` resolvida do MESMO ponto herdado, sem olhar
                # granularidade) mesmo com uma herança fraca demais para
                # valer como coordenada exata ou nome de cidade gravável.
                campos_herdados = _campos_da_heranca(media.gps_estimado_delta_s)
                delta_sustenta_gps = "regiao" in campos_herdados
                valor_gps_lat = media.gps_lat_estimado if delta_sustenta_gps else None
                valor_gps_lon = media.gps_lon_estimado if delta_sustenta_gps else None
                # GPS PRÓPRIO sustenta cidade sempre (é a coordenada exata
                # da própria foto); herdado só sustenta cidade quando o
                # próprio motor a sustentaria — a mesma exigência que a
                # tela já aplica para MOSTRAR a cidade (`_campos_do_lugar`,
                # `server/app.py`). Sem isto, herança só-país (2h–48h,
                # D-085) resolvia `Location.cidade` do MESMO ponto distante
                # da doadora e propunha gravá-la no original — a tela
                # esconde essa cidade, o plano não podia continuar propondo
                # o que a tela se recusa a mostrar.
                delta_sustenta_cidade = (
                    media.gps_lat is not None or "cidade" in campos_herdados
                )
                # Lugar pela cidade da pasta (D-083) nunca fornece valor,
                # mesmo que a linha tenha entrado pela perna do GPS herdado
                # — a guarda do WHERE só cobre a outra perna.
                pela_pasta = location is not None and location.fonte.startswith("pasta:")
                valor_cidade = (
                    location.cidade
                    if location and not pela_pasta and delta_sustenta_cidade
                    else None
                )
                # País continua sem guarda de granularidade: D-025 sustenta
                # o campo país em qualquer Δt da própria janela de país —
                # é o único campo desenhado para isso.
                valor_pais = location.pais if location and not pela_pasta else None

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
