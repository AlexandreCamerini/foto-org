"""Catálogo do Adobe Lightroom Classic (`.lrcat`) — somente leitura.

É o inventário mais valioso de um acervo espalhado, e por um motivo que
nenhuma outra fonte tem: **ele responde com os discos desligados**. O
Lightroom guarda, para cada foto já importada, o caminho completo, o volume
onde ela mora, a data de captura, o GPS e o que o dono fez com ela — nota,
sinalização, coleção.

Num acervo real, o `.lrcat` conhecia 54.086 fotos, das quais 44.474 num
volume externo desmontado. Varrer o disco teria encontrado zero.

O `.lrcat` é um SQLite. Abrimos com `immutable=1`: sem lock, sem journal,
sem escrita — o Lightroom pode estar aberto ao lado (invariante 1).

Os itens entram como REFERÊNCIA, não como acervo: o arquivo pode estar
inacessível, e mesmo acessível é o scanner quem cataloga arquivo. O valor
aqui é saber que a foto existe, onde ela estava e o que se sabe dela.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterator

from fotoorganizer.models import SourceType
from fotoorganizer.sources.base import ExternalAsset

log = logging.getLogger(__name__)


class LightroomError(RuntimeError):
    """Falha que o usuário precisa ver com instrução do que fazer."""


# Os pedaços do caminho vêm SEPARADOS de propósito. Concatenar em SQL
# (`rf.absolutePath || fo.pathFromRoot || ...`) parecia mais direto e era um
# defeito silencioso: em SQL, `a || b` é NULL se QUALQUER parte for NULL, e
# uma extensão ausente apagava o caminho inteiro — a referência perdia a única
# pista de LUGAR que tinha, que é justamente o valor desta fonte. Sem exceção
# e sem log: a linha simplesmente vinha vazia.
#
# `pathFromRoot` já vem com barra ao final; `absolutePath` também.
_CONSULTA = """
select
    f.id_global,
    rf.absolutePath,
    fo.pathFromRoot,
    f.baseName,
    f.extension,
    i.captureTime,
    e.gpsLatitude,
    e.gpsLongitude,
    i.rating,
    i.pick
from Adobe_images i
join AgLibraryFile f       on f.id_local  = i.rootFile
join AgLibraryFolder fo    on fo.id_local = f.folder
join AgLibraryRootFolder rf on rf.id_local = fo.rootFolder
left join AgHarvestedExifMetadata e on e.image = i.id_local
"""

# Coleções são o agrupamento que o dono montou à mão — o mesmo papel que o
# álbum tem no Apple Fotos.
_COLECOES = """
select f.id_global, c.name
from AgLibraryCollectionimage ci
join AgLibraryCollection c on c.id_local = ci.collection
join Adobe_images i        on i.id_local = ci.image
join AgLibraryFile f       on f.id_local = i.rootFile
"""

_PALAVRAS = """
select f.id_global, k.name
from AgLibraryKeywordImage ki
join AgLibraryKeyword k on k.id_local = ki.tag
join Adobe_images i     on i.id_local = ki.image
join AgLibraryFile f    on f.id_local = i.rootFile
where k.name is not null and k.name <> ''
"""

# Nota a partir da qual o dono considerou a foto boa. 4 e 5 estrelas são o
# corte usual de portfólio; abaixo disso é material de trabalho.
_NOTA_DE_FAVORITO = 4


def _data(valor: str | None) -> datetime | None:
    """`captureTime` do Lightroom: "2020-02-14T12:35:23.67", às vezes só a
    data, às vezes com fuso colado."""
    if not valor:
        return None
    texto = str(valor).strip().replace("Z", "+00:00")
    for corte in (texto, texto.split(".")[0], texto[:19], texto[:10]):
        try:
            return datetime.fromisoformat(corte).replace(tzinfo=None)
        except ValueError:
            continue
    return None


def _nome_e_caminho(
    absoluto: str | None,
    relativo: str | None,
    base: str | None,
    extensao: str | None,
) -> tuple[str | None, Path | None]:
    """Monta nome e caminho tolerando pedaço ausente.

    Cada pedaço que falta custa uma coisa diferente, e nenhuma delas justifica
    perder o resto:

    - sem `baseName` não há arquivo que nomear — devolve nada;
    - sem `extension` o nome é só a base (arquivo sem extensão existe, e o
      Lightroom guarda alguns assim);
    - sem `absolutePath` sabe-se o nome mas não o lugar — o caminho fica
      `None` e a referência continua doando data, GPS e nome;
    - sem `pathFromRoot` a foto está na raiz do volume.
    """
    if not base:
        return None, None
    nome = f"{base}.{extensao}" if extensao else str(base)
    if not absoluto:
        return nome, None
    return nome, Path(f"{absoluto}{relativo or ''}{nome}")


class LightroomProvider:
    """Lê um `.lrcat`. `raiz` é o arquivo do catálogo, não a pasta."""

    def __init__(self, catalogo: Path) -> None:
        self._catalogo = Path(catalogo).expanduser()

    @property
    def tipo(self) -> SourceType:
        return SourceType.LIGHTROOM

    @property
    def raiz(self) -> Path:
        return self._catalogo

    @property
    def apelido(self) -> str:
        return f"Lightroom · {self._catalogo.stem}"

    def _abrir(self) -> sqlite3.Connection:
        if not self._catalogo.is_file():
            raise LightroomError(
                f"catálogo do Lightroom não encontrado: {self._catalogo}"
            )
        try:
            # immutable=1 promete que ninguém está escrevendo. É o que
            # permite ler com o Lightroom aberto, sem tocar em lock nem WAL.
            con = sqlite3.connect(
                f"file:{self._catalogo}?immutable=1", uri=True
            )
            con.execute("select count(*) from Adobe_images").fetchone()
            return con
        except sqlite3.Error as exc:
            raise LightroomError(
                f"não consegui ler {self._catalogo.name}: {exc}. "
                "Se o arquivo for de uma versão muito antiga do Lightroom, "
                "abra-o uma vez no Lightroom Classic para ele atualizar o "
                "formato."
            ) from exc

    @staticmethod
    def _agrupar(con: sqlite3.Connection, consulta: str) -> dict[str, tuple]:
        agrupado: dict[str, list[str]] = {}
        try:
            for chave, valor in con.execute(consulta):
                if valor:
                    agrupado.setdefault(chave, []).append(valor)
        except sqlite3.Error as exc:
            # Tabela ausente numa versão diferente do Lightroom não pode
            # derrubar a importação inteira — perde-se o contexto, não o mapa.
            log.warning("lightroom: consulta auxiliar falhou (%s)", exc)
            return {}
        return {k: tuple(dict.fromkeys(v)) for k, v in agrupado.items()}

    def iter_assets(self) -> Iterator[ExternalAsset]:
        con = self._abrir()
        sem_lugar = 0
        try:
            colecoes = self._agrupar(con, _COLECOES)
            palavras = self._agrupar(con, _PALAVRAS)
            for (uuid, absoluto, relativo, base, extensao, captura, lat, lon,
                 nota, pick) in con.execute(_CONSULTA):
                if not uuid:
                    continue
                nome, caminho = _nome_e_caminho(
                    absoluto, relativo, base, extensao
                )
                if caminho is None:
                    sem_lugar += 1
                yield ExternalAsset(
                    caminho=None,                 # referência: nada é aberto
                    referencia=uuid,
                    caminho_original=caminho,
                    nome=nome,
                    data_capturada=_data(captura),
                    gps_lat=lat, gps_lon=lon,
                    favorito=bool(
                        (nota or 0) >= _NOTA_DE_FAVORITO or (pick or 0) > 0
                    ),
                    albuns=colecoes.get(uuid, ()),
                    palavras_chave=palavras.get(uuid, ()),
                )
            if sem_lugar:
                # Antes isto acontecia calado. Um acervo que perde o lugar de
                # milhares de referências precisa dizer quantas.
                log.warning(
                    "lightroom: %d itens sem caminho reconstruível "
                    "(campo ausente no catálogo) — entram sem lugar de origem",
                    sem_lugar,
                )
        finally:
            con.close()
