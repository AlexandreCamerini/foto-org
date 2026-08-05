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
class Funil:
    """Os degraus entre "o app sabe que existe" e "estou olhando isto agora".

    Existiam cinco números para esta pergunta, e cada tela mostrava um: o
    Panorama dizia 190.828 conhecidas e 91.937 alcançáveis, a Biblioteca
    dizia 197.338 no topo, a lateral e o rodapé diziam 26.023, e o contador
    depois de filtrar dizia 20.832. Nenhum estava errado — eles contavam
    coisas diferentes com a mesma palavra, e a soma disso é um usuário que
    não confia em nenhum.

    Aqui os degraus são ditos juntos, na ordem em que estreitam, para que a
    diferença entre eles seja legível em vez de ser uma contradição:

    - `conhecidas`: toda foto que o app sabe que existe, aqui ou não. Conta
      FOTO, não registro — a mesma foto vista pelo disco e pelo catálogo do
      Lightroom é uma só.
    - `alcancaveis`: dá para abrir o arquivo agora (disco montado, não é
      referência de nuvem).
    - `organizaveis`: é acervo do dono e tem arquivo — o que entra na
      revisão e no plano de cópia. Miniatura de cache e referência ficam de
      fora por não serem acervo (invariante 8), mesmo estando alcançáveis.

    O quarto degrau — quantas o filtro atual deixou passar — é da tela, não
    do catálogo, e por isso não mora aqui.
    """

    conhecidas: int
    alcancaveis: int
    organizaveis: int
    registros: int


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
    # Alcance por foto, não por linha: a mesma foto pode ser conhecida por
    # duas fontes, uma montada e outra não. Antes valia a PRIMEIRA linha que
    # o loop encontrasse — quem chegasse por uma fonte desmontada marcava a
    # foto como fora de alcance mesmo havendo outro caminho até o arquivo.
    # Medido no acervo do dono: 2.620 fotos alcançáveis contadas como fora.
    alcance: dict[str, bool] = {}
    raiz_da_chave: dict[str, str] = {}
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
            aqui = not ausente and disponiveis.get(source_id, False)
            if chave not in raiz_da_chave:
                raiz_da_chave[chave] = raiz
                dados["fotos"] += 1
                alcance[chave] = aqui
            elif aqui:
                alcance[chave] = True

    for chave, alcancavel in alcance.items():
        if alcancavel:
            por_raiz[raiz_da_chave[chave]]["alcancaveis"] += 1

    lugares = tuple(sorted(
        (Lugar(raiz, d["fotos"], d["alcancaveis"], tuple(sorted(d["fontes"])))
         for raiz, d in por_raiz.items()),
        key=lambda l: -l.fotos,
    ))
    return Inventario(lugares, sem_caminho, total)


def funil(factory: sessionmaker[Session], organizaveis: int) -> Funil:
    """Os três degraus que vêm do catálogo, num objeto só.

    `organizaveis` chega de fora porque quem já sabe contá-lo é o
    `MediaRepository` (é o mesmo filtro que a grade usa); duplicar a regra
    aqui seria criar a sexta definição no exato trabalho que existe para
    eliminar as cinco.
    """
    inv = levantar(factory)
    return Funil(
        conhecidas=inv.fotos,
        alcancaveis=inv.alcancaveis,
        organizaveis=organizaveis,
        registros=inv.total_registros,
    )


def _fontes(session: Session) -> tuple[dict[int, str], dict[int, bool]]:
    from fotoorganizer.models import Source

    apelidos, disponiveis = {}, {}
    for s in session.scalars(select(Source)):
        apelidos[s.id] = s.apelido or Path(s.caminho).name
        disponiveis[s.id] = bool(s.disponivel)
    return apelidos, disponiveis
