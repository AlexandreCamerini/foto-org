"""Que fontes estão alcançáveis agora — e onde o disco foi parar.

Um acervo espalhado por NAS e HDs externos passa a maior parte do tempo
parcialmente offline. O app precisa dizer três coisas diferentes, que hoje se
confundem numa só ("arquivo não encontrado"):

- **está aqui** — a fonte responde;
- **está na gaveta** — o volume tem identidade conhecida e não está montado;
- **mudou de lugar** — o volume voltou, mas noutro ponto de montagem.

O terceiro caso é o que estraga catálogo em silêncio: `/Volumes/photo` vira
`/Volumes/photo 1` quando o nome colide, e o app trata como disco novo.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.models import Source
from fotoorganizer.security.volumes import Volume, identificar, montado_em

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class EstadoDaFonte:
    source_id: int
    apelido: str
    caminho: str
    volume: Volume | None
    disponivel: bool
    # Onde o volume está montado agora, quando difere do caminho gravado.
    ponto_atual: Path | None = None
    # A identidade que a fonte guardou de quando esteve alcançável. É ela que
    # sabe QUAL disco é — a identidade descoberta agora, num volume
    # desmontado, não passa do próprio caminho e nunca seria estável.
    identidade_gravada: str | None = None

    @property
    def mudou_de_lugar(self) -> bool:
        return self.ponto_atual is not None

    @property
    def reconhecivel(self) -> bool:
        """Sabemos qual disco é, mesmo sem alcançá-lo."""
        return bool(self.identidade_gravada) and not (
            self.identidade_gravada or ""
        ).startswith("caminho:")

    def resumo(self) -> str:
        if self.mudou_de_lugar:
            return f"mudou de lugar → {self.ponto_atual}"
        if self.disponivel:
            return "disponível"
        if self.reconhecivel:
            return "na gaveta (volume conhecido, não montado)"
        return "indisponível"


def verificar(factory: sessionmaker[Session]) -> list[EstadoDaFonte]:
    """Atualiza `disponivel`, `visto_em` e a identidade de volume de cada
    fonte. Somente leitura sobre o filesystem."""
    agora = datetime.now(timezone.utc).replace(tzinfo=None)
    estados: list[EstadoDaFonte] = []

    with factory() as session:
        for source in session.scalars(select(Source).order_by(Source.id)):
            caminho = Path(source.caminho)
            # Catálogo externo é um arquivo (.lrcat) ou pacote; pasta é
            # diretório. `exists` cobre os dois.
            disponivel = caminho.exists()

            try:
                volume = identificar(caminho)
            except OSError as exc:
                log.warning("volume de %s ilegível (%s)", source.caminho, exc)
                volume = None

            if volume is not None and not source.volume_id:
                # Primeira vez que esta fonte é vista: grava a identidade
                # para que a próxima remontagem seja reconhecida.
                source.volume_id = volume.identidade
                source.volume_nome = volume.nome

            ponto_atual: Path | None = None
            if not disponivel and source.volume_id:
                encontrado = montado_em(source.volume_id)
                if encontrado is not None and str(encontrado) not in source.caminho:
                    # O volume voltou noutro ponto. Não reescrevemos o
                    # caminho aqui: mover 45 mil linhas de mídia é operação
                    # do usuário, não efeito colateral de uma verificação.
                    ponto_atual = encontrado

            source.disponivel = disponivel
            if disponivel:
                source.visto_em = agora

            estados.append(EstadoDaFonte(
                source_id=source.id,
                apelido=source.apelido or Path(source.caminho).name,
                caminho=source.caminho,
                volume=volume,
                disponivel=disponivel,
                ponto_atual=ponto_atual,
                identidade_gravada=source.volume_id,
            ))
        session.commit()
    return estados
