"""Detecção incremental de `.xmp` alterado — o gatilho que falta para a
leitura de sidecar já implementada.

Staging fora de `fotoorganizer/**` (protocolo em `docs/prompts/00-protocolo.md`).
Reimplementa o MECANISMO descrito em `docs/prompts/fase-14-photoprism-e-sintese.md`
§5 (Item C) — nunca código do PhotoPrism ou do Immich (AGPLv3). O mecanismo
copiado é a resolução REVERSA (dado o `.xmp`, ache a mídia principal contra
um cache em memória, sem tocar o banco por candidato) descrita em
`docs/referencia-photoprism/` — não a resolução para frente do Immich
(`docs/referencia-immich/`), que o prompt de origem já descarta por não caber
na estrutura de scanner deste projeto.

O que já existe e não muda aqui (evidência lida nesta sessão):

- `fotoorganizer/metadata/exiftool.py:161-183` (`_sidecar_de`) já resolve
  PARA FRENTE — dado o arquivo principal, acha o `.xmp` — e reconhece as
  duas convenções (`foto.jpg.xmp` do Adobe, `foto.xmp` do darktable/parte
  do Lightroom).
- `fotoorganizer/metadata/exiftool.py:186-219` (`_fundir_sidecar`) já funde
  com a precedência certa: o sidecar vence, e se declara qualquer data,
  TODAS as datas do original saem junto (inclusive fuso).
- `fotoorganizer/metadata/purepython.py:249-254`
  (`PurePythonExtractor.supported_extensions`) não inclui `.xmp` — o
  scanner nunca enumera o sidecar como arquivo próprio.
- `fotoorganizer/scanner/scanner.py:281-283,526-534` (`_unchanged_sig`) pula
  arquivo cuja assinatura `(tamanho, mtime, inode)` não mudou. Um `.xmp`
  editado depois da indexação não muda a assinatura do arquivo de mídia —
  fica invisível até `scan --reprocessar` reler o acervo inteiro.

Este módulo resolve o que falta: (1) dado um `.xmp` novo/alterado, achar
a mídia principal SEM adivinhar quando há ambiguidade; (2) decidir se essa
mudança é o caso que o scan incremental de hoje NÃO cobre (só o sidecar
mudou, a mídia não).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from pathlib import PurePosixPath

# Só a extensão de sidecar — enumerada pela descoberta sem virar linha em
# `media_files` (nota de esforço do prompt de origem: "sidecar não é
# acervo"). Mantida como conjunto, não string, para o mesmo formato de
# `PILLOW_EXTENSIONS`/`RAW_EXTENSIONS` em `metadata/purepython.py:43-51`.
EXTENSOES_SIDECAR = frozenset({".xmp"})


# --- 1. resolução reversa: do .xmp para a mídia principal ------------------


@dataclass(frozen=True)
class ResolucaoSidecar:
    """Resultado de tentar casar um `.xmp` com a mídia principal.

    `candidatos` sempre lista o que foi tentado, mesmo quando `midia` é
    `None` — é o que permite logar "não achei" vs. "achei dois" com o
    mesmo shape de dado.
    """

    xmp: PurePosixPath
    midia: PurePosixPath | None
    ambiguo: bool


def resolver_sidecar(
    caminho_xmp: PurePosixPath, conhecidos: frozenset[PurePosixPath]
) -> ResolucaoSidecar:
    """Dado um `.xmp`, acha a mídia principal contra um cache em memória —
    nunca um SELECT por candidato (mesma exigência do mecanismo original).

    `conhecidos` é o conjunto de caminhos já catalogados NA MESMA PASTA
    (quem chama filtra por pasta antes; resolver aqui não faz I/O nem
    conhece o banco). Testa as duas convenções:

    - Adobe (`foto.jpg.xmp`): remover só o `.xmp` do nome inteiro devolve
      `foto.jpg` — testado primeiro porque é inequívoco por construção
      (o nome antes do `.xmp` já é o nome completo do arquivo principal,
      extensão inclusa).
    - darktable/Lightroom (`foto.xmp`): o "stem" é `foto`, sem extensão
      própria — pode casar com QUALQUER extensão principal conhecida do
      catálogo (`foto.jpg`, `foto.cr3`, ...). Aqui mora a ambiguidade: uma
      pasta com `foto.jpg` E `foto.cr3` tem duas respostas possíveis, e o
      mecanismo original resolve isso não adivinhando — mesma regra aqui.

    Comparação de extensão é case-insensitive (`.JPG` casa com `.jpg`) —
    mesma cautela do mecanismo original ("ambos os casos de maiúscula/
    minúscula"), porque sistemas de arquivo preservam caixa sem exigi-la.
    """
    candidatos: set[PurePosixPath] = set()

    if caminho_xmp.suffix.lower() != ".xmp":
        raise ValueError(f"não é um sidecar .xmp: {caminho_xmp}")

    conhecidos_lower = {_chave(c): c for c in conhecidos}

    # Convenção Adobe: foto.jpg.xmp -> foto.jpg (remove só o último ".xmp").
    candidato_adobe = caminho_xmp.with_suffix("")
    if _chave(candidato_adobe) in conhecidos_lower:
        candidatos.add(conhecidos_lower[_chave(candidato_adobe)])

    # Convenção darktable: foto.xmp -> foto.<qualquer extensão conhecida>.
    # `stem` de "foto.jpg.xmp" já é "foto.jpg" (Path só remove o último
    # sufixo) — testar esta convenção também para o caso Adobe é inofensivo
    # por construção: procurar um arquivo real chamado "foto.jpg.jpg" ou
    # "foto.jpg.cr3" não encontra nada no acervo real, então as duas
    # convenções podem sempre rodar juntas sem checar qual "é" o caso.
    for outro in conhecidos:
        if outro.parent == caminho_xmp.parent and outro.stem == caminho_xmp.stem:
            candidatos.add(outro)

    if not candidatos:
        return ResolucaoSidecar(caminho_xmp, None, ambiguo=False)
    if len(candidatos) > 1:
        return ResolucaoSidecar(caminho_xmp, None, ambiguo=True)
    return ResolucaoSidecar(caminho_xmp, next(iter(candidatos)), ambiguo=False)


def _chave(caminho: PurePosixPath) -> str:
    """Comparação case-insensitive só na extensão — o nome-base de imagem
    real deste acervo é sensível a caixa (não normalizamos o resto)."""
    return str(caminho.with_suffix(caminho.suffix.lower()))


# --- 2. o gatilho: sidecar mudou, mídia não ---------------------------------


class CasoDeteccao(enum.StrEnum):
    """O que uma passada incremental encontrou para um par (sidecar, mídia).

    `SO_SIDECAR_MUDOU` é o caso que hoje é invisível — o scan incremental
    (`scanner.py:281-283`) só olha a assinatura da MÍDIA, então um `.xmp`
    editado sozinho não dispara reprocessamento nenhum.
    """

    SEM_MUDANCA = "sem_mudanca"
    SIDECAR_NOVO = "sidecar_novo"
    SO_SIDECAR_MUDOU = "so_sidecar_mudou"
    MIDIA_MUDOU = "midia_mudou"
    AMBOS_MUDARAM = "ambos_mudaram"


@dataclass(frozen=True)
class AssinaturaConhecida:
    """O que a última passada sabia sobre este par — equivalente sidecar do
    `(tamanho, mtime, inode)` que `scanner.py:384-402`
    (`_carregar_conhecidos`) já mantém para a mídia. Aqui só `mtime`
    porque é o único sinal barato e suficiente para detectar edição de
    texto/XML: tamanho de `.xmp` varia pouco e inode sobrevive a editores
    que reescrevem o arquivo inteiro (muda mtime, pode ou não mudar inode
    dependendo do editor — mtime é o sinal que todo editor XMP toca)."""

    mtime_sidecar: float
    mtime_midia: float | None


def classificar(
    mtime_sidecar_atual: float,
    mtime_midia_atual: float | None,
    conhecida: AssinaturaConhecida | None,
) -> CasoDeteccao:
    """Compara o estado atual do par (sidecar, mídia) com o que a última
    passada registrou, e diz qual dos cinco casos é este.

    Sem estado conhecido (par nunca visto): sempre `SIDECAR_NOVO`, mesmo
    que a mídia já exista há tempos — é a primeira vez que ESTE módulo viu
    o `.xmp`, que é o que importa para decidir se precisa ler.
    """
    if conhecida is None:
        return CasoDeteccao.SIDECAR_NOVO

    sidecar_mudou = mtime_sidecar_atual != conhecida.mtime_sidecar
    midia_mudou = (
        conhecida.mtime_midia is not None
        and mtime_midia_atual is not None
        and mtime_midia_atual != conhecida.mtime_midia
    )

    if sidecar_mudou and midia_mudou:
        return CasoDeteccao.AMBOS_MUDARAM
    if sidecar_mudou:
        return CasoDeteccao.SO_SIDECAR_MUDOU
    if midia_mudou:
        return CasoDeteccao.MIDIA_MUDOU
    return CasoDeteccao.SEM_MUDANCA


# Casos em que o arquivo principal precisa ser reenfileirado PELO GATILHO do
# sidecar. `MIDIA_MUDOU` fica de fora de propósito: o scan incremental
# normal já reprocessa a mídia quando a assinatura dela muda — reenfileirar
# de novo aqui seria trabalho duplicado, não uma cobertura a mais.
_CASOS_QUE_REENFILEIRAM = frozenset({
    CasoDeteccao.SIDECAR_NOVO,
    CasoDeteccao.SO_SIDECAR_MUDOU,
    CasoDeteccao.AMBOS_MUDARAM,
})


def precisa_reenfileirar(caso: CasoDeteccao) -> bool:
    return caso in _CASOS_QUE_REENFILEIRAM
