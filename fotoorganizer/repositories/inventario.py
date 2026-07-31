"""O inventário do acervo — o que se sabe que existe, esteja ou não alcançável.

A grade mostra o que dá para abrir agora. Isso é o certo para revisar e
organizar, e é a pergunta errada para descobrir: num acervo espalhado por NAS
e discos externos, o que dá para abrir agora é a minoria. Num caso real, o
catálogo conhecia 102.586 registros e a interface mostrava 5.191.

Aqui a pergunta é outra — *o que existe, e onde* — e ela precisa de duas
coisas que a grade não faz:

**Contar foto, não registro.** A mesma foto aparece como arquivo no disco e
como referência no catálogo do Lightroom. São dois registros e uma foto só; a
pasta Dubai tinha exatamente 2.405 de cada. A identidade é o caminho absoluto,
que é exato e barato — não é dedup por conteúdo, que é outro problema.

**Incluir o que não está aqui.** Uma foto num HD na gaveta continua existindo,
e saber disso é justamente o ponto.

"Alcançável" é uma pergunta sobre AGORA, e a resposta não está em
`arquivo_ausente` — esse campo diz que o registro é referência, não que o
arquivo esteja fora de alcance. Um arquivo catalogado do HD externo tem
`arquivo_ausente=0` e continua inalcançável com o disco na gaveta. Quem sabe
é `Source.disponivel`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.models import MediaFile

# Caminho conhecido de um registro: o do arquivo, ou o que o catálogo externo
# disse que era. Referência sem caminho (iCloud) não tem lugar no disco — e é
# uma categoria à parte, não uma lacuna.
_CAMINHO_CONHECIDO = func.coalesce(
    func.nullif(MediaFile.pasta, "") + "/" + MediaFile.nome,
    func.nullif(MediaFile.caminho, ""),
)


@dataclass(frozen=True, slots=True)
class Lugar:
    """Um lugar onde há fotos, alcançável ou não."""

    raiz: str
    fotos: int
    alcancaveis: int
    fontes: tuple[str, ...]

    @property
    def so_no_catalogo(self) -> int:
        return self.fotos - self.alcancaveis


@dataclass(frozen=True, slots=True)
class Inventario:
    lugares: tuple[Lugar, ...]
    sem_caminho: int          # referência de nuvem: existe, não tem lugar
    total_registros: int

    @property
    def fotos(self) -> int:
        return sum(l.fotos for l in self.lugares) + self.sem_caminho

    @property
    def alcancaveis(self) -> int:
        return sum(l.alcancaveis for l in self.lugares)


def _raiz(caminho: str) -> str:
    """O volume ou a pasta de topo — a granularidade em que o dono pensa
    ("o disco photo", "este Mac"), não a pasta de cada foto."""
    partes = Path(caminho).parts
    if len(partes) >= 3 and partes[1] == "Volumes":
        return str(Path(partes[0], partes[1], partes[2]))
    if len(partes) >= 3 and partes[1].casefold() == "users":
        return str(Path(partes[0], "Users", partes[2]))
    return partes[0] if partes else caminho


def levantar(factory: sessionmaker[Session]) -> Inventario:
    """Somente leitura sobre o catálogo; não toca no filesystem."""
    por_raiz: dict[str, dict] = {}
    vistos: set[str] = set()
    sem_caminho = 0

    with factory() as session:
        total = session.scalar(select(func.count(MediaFile.id))) or 0
        linhas = session.execute(
            select(
                _CAMINHO_CONHECIDO,
                MediaFile.arquivo_ausente,
                MediaFile.source_id,
            )
        )
        apelidos, disponiveis = _fontes(session)
        for caminho, ausente, source_id in linhas:
            if not caminho or "://" in caminho:
                # Referência de nuvem: o app sabe que a foto existe e não há
                # lugar no disco a informar.
                sem_caminho += 1
                continue
            # macOS não distingue maiúscula no caminho, e as fontes
            # discordam: o Lightroom grava "/Users", o scan gravou "/users".
            # Sem normalizar, o mesmo lugar vira dois e a foto é contada duas.
            chave = caminho.casefold()
            raiz = _raiz(caminho)
            dados = por_raiz.setdefault(
                raiz, {"fotos": 0, "alcancaveis": 0, "fontes": set()}
            )
            dados["fontes"].add(apelidos.get(source_id, "?"))
            if chave in vistos:
                continue          # mesma foto, outra fonte
            vistos.add(chave)
            dados["fotos"] += 1
            if not ausente and disponiveis.get(source_id, False):
                dados["alcancaveis"] += 1

    lugares = tuple(sorted(
        (Lugar(raiz, d["fotos"], d["alcancaveis"], tuple(sorted(d["fontes"])))
         for raiz, d in por_raiz.items()),
        key=lambda l: -l.fotos,
    ))
    return Inventario(lugares, sem_caminho, total)


def _fontes(session: Session) -> tuple[dict[int, str], dict[int, bool]]:
    from fotoorganizer.models import Source

    apelidos, disponiveis = {}, {}
    for s in session.scalars(select(Source)):
        apelidos[s.id] = s.apelido or Path(s.caminho).name
        disponiveis[s.id] = bool(s.disponivel)
    return apelidos, disponiveis
