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

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.models import MediaFile, Source

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
    - `organizaveis`: das alcançáveis, as que são acervo do dono — o que
      entra na revisão e no plano de cópia. Miniatura de cache e referência
      ficam de fora por não serem acervo (invariante 8), mesmo estando
      alcançáveis; e acervo cuja única fonte está desmontada também não
      conta, porque não abre agora (D-068) — sem isto o terceiro degrau
      deixava de ser subconjunto do segundo.

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
    # Contado aqui, e não em `MediaRepository.estatisticas()`, porque lá a
    # unidade é a LINHA: as 26.023 linhas organizáveis do acervo real são
    # 22.150 fotos — a mesma foto vista pelo disco e pelo catálogo do
    # Lightroom contava duas vezes. Um funil que conta foto em dois degraus
    # e linha no terceiro é a doença dos cinco números sobrevivendo dentro
    # do próprio remédio. A REGRA continua sendo uma só: quem decide é
    # `MediaFile.organizavel`, lido do banco, nunca reescrito aqui.
    organizaveis: int = 0

    @property
    def fotos(self) -> int:
        return sum(l.fotos for l in self.lugares) + self.sem_caminho

    @property
    def alcancaveis(self) -> int:
        return sum(l.alcancaveis for l in self.lugares)


def _raiz(caminho: str) -> str:
    """O volume ou a pasta de topo — a granularidade em que o dono pensa
    ("o disco photo", "este Mac"), não a pasta de cada foto."""
    # String pura, sem `Path`: isto roda uma vez por foto do acervo, e
    # construir um `Path` por linha custava a maior parte dos 9,1 s medidos
    # em 197 mil registros. Em milhões de fotos seria o gargalo inteiro.
    if caminho.startswith("/"):
        partes = caminho.split("/", 3)     # ['', 'Volumes', 'photo', resto]
        if len(partes) >= 3 and partes[2]:
            if partes[1] == "Volumes":
                return f"/Volumes/{partes[2]}"
            if partes[1].casefold() == "users":
                return f"/Users/{partes[2]}"
        return "/"
    primeira, _, _ = caminho.partition("/")
    return primeira or caminho


def levantar(factory: sessionmaker[Session]) -> Inventario:
    """Somente leitura sobre o catálogo; não toca no filesystem.

    **A deduplicação por foto acontece no SQL, não em Python**, e a razão é
    de escala: o acervo do dono está espalhado por NAS e HDs antigos e o
    catálogo é uma fração dele (D-028). A versão anterior segurava três
    dicionários com uma entrada por foto — 7,1 s e 134 MB em 197 mil
    registros, o que projetava 72 s e 1,4 GB em 2 milhões e não terminava
    em 10 milhões. Agora o `GROUP BY` devolve uma linha por foto já
    resolvida, o Python percorre em fluxo e só guarda o agregado por
    RAIZ — dez volumes, não dez milhões de chaves. A memória deixa de
    depender do tamanho do acervo.

    Alcance e organizável valem se QUALQUER linha da foto valer (`max`), e
    não se a primeira que o loop encontrar valer: a mesma foto pode ser
    conhecida por duas fontes, uma montada e outra não, e ter um caminho
    até o arquivo é o que decide. Medido: 2.620 fotos alcançáveis eram
    contadas como fora de alcance por causa da ordem das linhas.
    """
    por_raiz: dict[str, dict] = {}
    sem_caminho = 0

    # Um inteiro por linha, para o `max` do agrupamento poder decidir.
    # Alcançável exige as três coisas: não é referência sem arquivo, a
    # FONTE responde agora, e este arquivo específico não sumiu dela.
    _e_alcancavel = and_(
        MediaFile.arquivo_ausente.is_(False),
        Source.disponivel.is_(True),
        MediaFile.arquivo_offline.is_(False),
    )
    _alcancavel = case((_e_alcancavel, 1), else_=0)
    # Organizável também exige estar alcançável — não só ser acervo
    # (`MediaFile.organizavel`). Sem isto, uma foto cuja única fonte
    # organizável está desmontada (ex.: "Dubai, Thai & Viet" saiu do disco)
    # continuava contada como organizável enquanto a grade escrevia "fora
    # de alcance" em cada miniatura — o terceiro degrau deixava de ser
    # subconjunto do segundo. Ver D-068.
    _organizavel = case(
        (and_(MediaFile.organizavel, _e_alcancavel), 1), else_=0
    )
    # macOS não distingue maiúscula no caminho, e as fontes discordam: o
    # Lightroom grava "/Users", o scan gravou "/users". Sem normalizar, o
    # mesmo lugar vira dois e a foto é contada duas vezes.
    _chave = func.lower(_CAMINHO_CONHECIDO)

    with factory() as session:
        total = session.scalar(select(func.count(MediaFile.id))) or 0
        # Referência de nuvem: o app sabe que a foto existe e não há lugar
        # no disco a informar. Fica de fora do agrupamento por caminho.
        sem_caminho = session.scalar(
            select(func.count(MediaFile.id)).where(
                or_(
                    _CAMINHO_CONHECIDO.is_(None),
                    _CAMINHO_CONHECIDO == "",
                    _CAMINHO_CONHECIDO.like("%://%"),
                )
            )
        ) or 0

        apelidos, _ = _fontes(session)
        por_foto = (
            select(
                func.min(_CAMINHO_CONHECIDO).label("caminho"),
                func.max(_alcancavel).label("alcancavel"),
                func.max(_organizavel).label("organizavel"),
                func.group_concat(MediaFile.source_id.distinct()).label("fontes"),
            )
            .join(Source, Source.id == MediaFile.source_id)
            .where(
                _CAMINHO_CONHECIDO.is_not(None),
                _CAMINHO_CONHECIDO != "",
                _CAMINHO_CONHECIDO.not_like("%://%"),
            )
            .group_by(_chave)
        )

        organizaveis = 0
        # Dois memos, porque o corpo do laço roda uma vez por foto e as duas
        # contas se repetem quase sempre: há uma dezena de raízes e uma
        # dezena de combinações de fonte num acervo inteiro. Sem eles, o
        # laço custava 2,7 s dos 3,8 s totais em 197 mil registros — e é a
        # parte que cresce linearmente com o acervo.
        raiz_de: dict[str, str] = {}
        nomes_de: dict[str, frozenset[str]] = {}
        # `yield_per` mantém o cursor em fluxo: sem isto o driver
        # materializaria todas as fotos de uma vez e a economia se perderia.
        for caminho, alcancavel, organizavel, fontes in session.execute(
            por_foto.execution_options(yield_per=10_000)
        ):
            # A raiz depende só dos dois primeiros segmentos do caminho.
            corte = caminho.find("/", caminho.find("/", 1) + 1)
            prefixo = caminho if corte <= 0 else caminho[:corte]
            raiz = raiz_de.get(prefixo)
            if raiz is None:
                raiz = raiz_de[prefixo] = _raiz(caminho)

            dados = por_raiz.setdefault(
                raiz, {"fotos": 0, "alcancaveis": 0, "fontes": set()}
            )
            dados["fotos"] += 1
            if alcancavel:
                dados["alcancaveis"] += 1
            if organizavel:
                organizaveis += 1

            nomes = nomes_de.get(fontes)
            if nomes is None:
                nomes = nomes_de[fontes] = frozenset(
                    apelidos.get(int(sid), "?")
                    for sid in (fontes or "").split(",")
                    if sid
                )
            dados["fontes"] |= nomes

    lugares = tuple(sorted(
        (Lugar(raiz, d["fotos"], d["alcancaveis"], tuple(sorted(d["fontes"])))
         for raiz, d in por_raiz.items()),
        key=lambda l: -l.fotos,
    ))
    return Inventario(lugares, sem_caminho, total, organizaveis)


def funil(factory: sessionmaker[Session]) -> Funil:
    """Os três degraus que vêm do catálogo, num objeto só.

    Os três contam FOTO. `MediaRepository.estatisticas()["total"]` conta
    linha e continua certo para o que ele serve (a grade lista registros);
    só não serve de degrau ao lado de dois que contam foto.
    """
    inv = levantar(factory)
    return Funil(
        conhecidas=inv.fotos,
        alcancaveis=inv.alcancaveis,
        organizaveis=inv.organizaveis,
        registros=inv.total_registros,
    )


def _fontes(session: Session) -> tuple[dict[int, str], dict[int, bool]]:
    from fotoorganizer.models import Source

    apelidos, disponiveis = {}, {}
    for s in session.scalars(select(Source)):
        apelidos[s.id] = s.apelido or Path(s.caminho).name
        disponiveis[s.id] = bool(s.disponivel)
    return apelidos, disponiveis
